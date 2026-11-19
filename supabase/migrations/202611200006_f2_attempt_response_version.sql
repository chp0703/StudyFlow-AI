-- Durable B5 attempt context, response versions and signed write replay.

alter table app_private.quiz_attempts
    add column response_version bigint not null default 0 check (response_version >= 0);

-- B5 fix: load the exact durable attempt state needed for response validation and grading.
create or replace function app_private.rpc_is_read(p_routine text) returns boolean
language sql immutable set search_path = '' as $$
    select p_routine in (
        'search_tasks', 'get_study_plan', 'get_scheduling_context', 'lookup_operation_result',
        'list_time_windows', 'get_workflow_context', 'get_workflow_continuation',
        'get_ingestion_source', 'get_assessment_material', 'search_material_chunks',
        'list_questions', 'get_quiz_attempt_context', 'get_topic_stats'
    )
$$;

create function app_api.get_quiz_attempt_context(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'get_quiz_attempt_context', 'GetQuizAttemptContextArguments');
    v_uid uuid;
    v_attempt_json jsonb;
    v_total_questions integer;
    v_response_version bigint;
    v_questions jsonb;
    v_responses jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        select
            app_private.quiz_attempt_json(a),
            a.total_questions,
            a.response_version,
            (
                select coalesce(jsonb_agg(app_private.question_json(q) order by x.ord), '[]'::jsonb)
                from jsonb_array_elements_text(a.question_ids) with ordinality x(question_id, ord)
                join app_private.question_drafts q
                  on q.user_id = v_uid
                 and q.question_id = x.question_id::uuid
                 and q.material_id = a.material_id
            ),
            (
                select coalesce(jsonb_agg(app_private.quiz_response_json(r) order by x.ord), '[]'::jsonb)
                from jsonb_array_elements_text(a.question_ids) with ordinality x(question_id, ord)
                join app_private.quiz_responses r
                  on r.user_id = v_uid
                 and r.attempt_id = a.attempt_id
                 and r.question_id = x.question_id::uuid
            )
        into
            v_attempt_json,
            v_total_questions,
            v_response_version,
            v_questions,
            v_responses
        from app_private.quiz_attempts a
        where a.user_id = v_uid
          and a.attempt_id = (p_request #>> '{arguments,attempt_id}')::uuid;

        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Quiz attempt not found.');
        end if;

        if jsonb_array_length(v_questions) <> v_total_questions then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Attempt questions are no longer available.');
        end if;

        return app_private.ok_result(p_request, 'READ', jsonb_build_object(
            'attempt', v_attempt_json,
            'questions', v_questions,
            'responses', v_responses,
            'response_version', v_response_version
        ));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.rpc_is_read(text) owner to sf_rpc_owner;
revoke all on function app_private.rpc_is_read(text) from public, anon, authenticated;
alter function app_api.get_quiz_attempt_context(jsonb) owner to sf_rpc_owner;
revoke all on function app_api.get_quiz_attempt_context(jsonb) from public, anon;
grant execute on function app_api.get_quiz_attempt_context(jsonb) to authenticated;

create or replace function app_private.guard_quiz_attempt() returns trigger
language plpgsql set search_path = '' as $$
declare
    v_qid_text text;
    v_qid uuid;
    v_distinct_count integer;
begin
    if tg_op = 'DELETE' then
        raise exception 'Quiz attempts cannot be deleted' using errcode = '23514';
    end if;

    if tg_op = 'INSERT' then
        if new.response_version is distinct from 0 then
            raise exception 'Quiz attempt response_version must start at 0' using errcode = '23514';
        end if;
    end if;

    if tg_op = 'UPDATE' then
        if old.status = 'SUBMITTED' then
            raise exception 'SUBMITTED quiz attempt is immutable' using errcode = '23514';
        end if;
        if (
            new.attempt_id,
            new.user_id,
            new.material_id,
            new.assessment_version,
            new.origin,
            new.session_outcome_id,
            new.question_ids,
            new.total_questions,
            new.started_at,
            new.created_at
        ) is distinct from (
            old.attempt_id,
            old.user_id,
            old.material_id,
            old.assessment_version,
            old.origin,
            old.session_outcome_id,
            old.question_ids,
            old.total_questions,
            old.started_at,
            old.created_at
        ) then
            raise exception 'Quiz attempt identity and question list are immutable' using errcode = '23514';
        end if;
        if old.status = 'IN_PROGRESS' and new.status = 'IN_PROGRESS' then
            if new.response_version is distinct from old.response_version + 1 then
                raise exception 'IN_PROGRESS quiz attempt response_version must increment by 1' using errcode = '23514';
            end if;
            if (to_jsonb(new) - 'response_version') is distinct from (to_jsonb(old) - 'response_version') then
                raise exception 'IN_PROGRESS quiz attempt update may only increment response_version' using errcode = '23514';
            end if;
        elsif old.status = 'IN_PROGRESS' and new.status = 'SUBMITTED' then
            if new.response_version is distinct from old.response_version then
                raise exception 'Submitting quiz attempt cannot change response_version' using errcode = '23514';
            end if;
        else
            raise exception 'Invalid quiz attempt status transition' using errcode = '23514';
        end if;
    end if;

    select count(distinct value #>> '{}')
    into v_distinct_count
    from jsonb_array_elements(new.question_ids);

    if v_distinct_count <> jsonb_array_length(new.question_ids) then
        raise exception 'Quiz attempt question_ids must be unique' using errcode = '23514';
    end if;

    for v_qid_text in
        select value #>> '{}' from jsonb_array_elements(new.question_ids)
    loop
        v_qid := v_qid_text::uuid;
        if not exists (
            select 1
            from app_private.question_drafts q
            where q.question_id = v_qid
              and q.user_id = new.user_id
              and q.material_id = new.material_id
              and q.status = 'VERIFIED'
        ) then
            raise exception 'Quiz attempt requires VERIFIED questions of the same owner and material'
                using errcode = '23514';
        end if;
    end loop;

    return new;
end $$;

create or replace function app_api.save_quiz_response(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'save_quiz_response', 'SaveQuizResponseArguments');
    v_uid uuid;
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_args jsonb := p_request -> 'arguments';
    v_attempt_id uuid;
    v_question_id uuid;
    v_selected text;
    v_validity text;
    v_expected_validity text;
    v_fp text;
    v_reply jsonb;
    v_attempt app_private.quiz_attempts;
    v_question app_private.question_drafts;
    v_resp app_private.quiz_responses;
    v_result jsonb;
    v_now timestamptz := clock_timestamp();
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key is required.');
    end if;

    v_fp := app_private.domain_fingerprint(v_uid, 'save_quiz_response', v_args - 'include_replay_status');
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'save_quiz_response', v_key, v_fp);
        if v_reply is not null then
            if v_reply ->> 'outcome' = 'COMMITTED' and v_args -> 'include_replay_status' = 'true'::jsonb then
                return jsonb_set(v_reply, '{outcome}', '"READ"'::jsonb);
            end if;
            return v_reply;
        end if;

        perform app_private.lock_owner(v_uid, p_request);

        v_reply := app_private.idempotent_reply(p_request, v_uid, 'save_quiz_response', v_key, v_fp);
        if v_reply is not null then
            if v_reply ->> 'outcome' = 'COMMITTED' and v_args -> 'include_replay_status' = 'true'::jsonb then
                return jsonb_set(v_reply, '{outcome}', '"READ"'::jsonb);
            end if;
            return v_reply;
        end if;

        v_attempt_id := (v_args ->> 'attempt_id')::uuid;
        v_question_id := (v_args ->> 'question_id')::uuid;
        v_selected := case
            when v_args -> 'selected_option_id' = 'null'::jsonb then null
            else v_args ->> 'selected_option_id'
        end;
        v_validity := v_args ->> 'validity';

        select *
        into v_attempt
        from app_private.quiz_attempts a
        where a.attempt_id = v_attempt_id
          and a.user_id = v_uid;

        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Quiz attempt not found.');
        end if;

        if v_attempt.status = 'SUBMITTED' then
            return app_private.error_result(
                p_request,
                'STALE_ENTITY_VERSION',
                'Quiz attempt has already been submitted and cannot be modified.'
            );
        end if;

        if not (v_attempt.question_ids @> to_jsonb(v_question_id::text)) then
            return app_private.error_result(
                p_request,
                'ENTITY_NOT_FOUND',
                'Question does not belong to this quiz attempt.'
            );
        end if;

        select *
        into v_question
        from app_private.question_drafts q
        where q.question_id = v_question_id
          and q.user_id = v_uid
          and q.material_id = v_attempt.material_id;

        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Question not found.');
        end if;

        if v_question.status <> 'VERIFIED' then
            return app_private.error_result(
                p_request,
                'STALE_ENTITY_VERSION',
                'Question is not VERIFIED.'
            );
        end if;

        if v_selected is null then
            v_expected_validity := 'OMITTED';
        elsif exists (
            select 1
            from jsonb_array_elements(v_question.options) opt
            where opt ->> 'option_id' = v_selected
        ) then
            v_expected_validity := 'VALID';
        else
            v_expected_validity := 'INVALID';
        end if;

        if v_validity is distinct from v_expected_validity then
            return app_private.error_result(
                p_request,
                'INVALID_PARAMETER',
                'Response validity does not match question options.'
            );
        end if;

        insert into app_private.quiz_responses (
            response_id,
            attempt_id,
            question_id,
            user_id,
            selected_option_id,
            validity,
            is_correct,
            graded_at,
            created_at,
            updated_at
        )
        values (
            extensions.gen_random_uuid(),
            v_attempt_id,
            v_question_id,
            v_uid,
            v_selected,
            v_validity,
            null,
            null,
            v_now,
            v_now
        )
        on conflict (attempt_id, question_id) do update
        set selected_option_id = excluded.selected_option_id,
            validity = excluded.validity,
            is_correct = null,
            graded_at = null,
            updated_at = v_now
        returning * into v_resp;

        update app_private.quiz_attempts
        set response_version = response_version + 1
        where attempt_id = v_attempt_id
          and user_id = v_uid
          and status = 'IN_PROGRESS';

        if not found then
            raise exception 'Quiz attempt cannot increment response_version' using errcode = '23514';
        end if;

        v_result := app_private.ok_result(p_request, 'COMMITTED', app_private.quiz_response_json(v_resp));
        insert into app_private.idempotency_records (
            user_id,
            operation,
            idempotency_key,
            request_fingerprint,
            state,
            result_reference_or_response,
            expires_at
        )
        values (
            v_uid,
            'save_quiz_response',
            v_key,
            v_fp,
            'COMPLETED',
            v_result,
            clock_timestamp() + interval '7 days'
        );
        return v_result;
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

create or replace function app_api.submit_quiz_attempt(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'submit_quiz_attempt', 'SubmitQuizAttemptArguments');
    v_uid uuid;
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_args jsonb := p_request -> 'arguments';
    v_attempt_id uuid;
    v_submitted_at timestamptz;
    v_fp text;
    v_reply jsonb;
    v_attempt app_private.quiz_attempts;
    v_question app_private.question_drafts;
    v_saved app_private.quiz_responses;
    v_has_saved boolean;
    v_item jsonb;
    v_qid uuid;
    v_idx integer := 0;
    v_selected text;
    v_exp_validity text;
    v_exp_correct boolean;
    v_item_correct boolean;
    v_valid_cnt integer := 0;
    v_correct_cnt integer := 0;
    v_incorrect_cnt integer := 0;
    v_omitted_cnt integer := 0;
    v_exp_score numeric(5,2);
    v_arg_score numeric(5,2);
    v_expected_version_num numeric;
    v_expected_response_version bigint;
    v_responses_json jsonb;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key is required.');
    end if;

    v_fp := app_private.domain_fingerprint(
        v_uid,
        'submit_quiz_attempt',
        jsonb_build_object('attempt_id', v_args -> 'attempt_id')
    );

    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'submit_quiz_attempt', v_key, v_fp);
        if v_reply is not null then
            if v_reply ->> 'outcome' = 'COMMITTED' and v_args -> 'include_replay_status' = 'true'::jsonb then
                return jsonb_set(v_reply, '{outcome}', '"READ"'::jsonb);
            end if;
            return v_reply;
        end if;

        perform app_private.lock_owner(v_uid, p_request);

        v_reply := app_private.idempotent_reply(p_request, v_uid, 'submit_quiz_attempt', v_key, v_fp);
        if v_reply is not null then
            if v_reply ->> 'outcome' = 'COMMITTED' and v_args -> 'include_replay_status' = 'true'::jsonb then
                return jsonb_set(v_reply, '{outcome}', '"READ"'::jsonb);
            end if;
            return v_reply;
        end if;

        v_attempt_id := (v_args ->> 'attempt_id')::uuid;
        v_submitted_at := (v_args ->> 'submitted_at')::timestamptz;

        select *
        into v_attempt
        from app_private.quiz_attempts a
        where a.attempt_id = v_attempt_id
          and a.user_id = v_uid;

        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Quiz attempt not found.');
        end if;

        if v_attempt.status = 'SUBMITTED' then
            return app_private.error_result(
                p_request,
                'STALE_ENTITY_VERSION',
                'Quiz attempt has already been submitted.'
            );
        end if;

        if v_args ? 'expected_response_version' then
            if jsonb_typeof(v_args -> 'expected_response_version') <> 'number' then
                return app_private.error_result(
                    p_request,
                    'INVALID_PARAMETER',
                    'expected_response_version must be a non-negative safe integer.'
                );
            end if;
            v_expected_version_num := (v_args -> 'expected_response_version')::numeric;
            if v_expected_version_num <> trunc(v_expected_version_num)
               or v_expected_version_num < 0
               or v_expected_version_num > 9007199254740991 then
                return app_private.error_result(
                    p_request,
                    'INVALID_PARAMETER',
                    'expected_response_version must be a non-negative safe integer.'
                );
            end if;
            v_expected_response_version := v_expected_version_num::bigint;
            if v_attempt.response_version <> v_expected_response_version then
                return jsonb_set(
                    app_private.error_result(
                        p_request,
                        'STALE_ENTITY_VERSION',
                        'Quiz attempt responses have changed since context was loaded.'
                    ),
                    '{error,field}',
                    to_jsonb('expected_response_version'::text)
                );
            end if;
        end if;

        if jsonb_array_length(v_args -> 'graded_responses') <> v_attempt.total_questions then
            return app_private.error_result(
                p_request,
                'INVALID_PARAMETER',
                'Graded responses count does not match attempt questions.'
            );
        end if;

        for v_idx in 0 .. (v_attempt.total_questions - 1) loop
            v_qid := (v_attempt.question_ids ->> v_idx)::uuid;
            v_item := (v_args -> 'graded_responses') -> v_idx;

            select *
            into v_question
            from app_private.question_drafts q
            where q.question_id = v_qid
              and q.user_id = v_uid
              and q.material_id = v_attempt.material_id;

            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Question not found.');
            end if;

            if v_question.status <> 'VERIFIED' then
                return app_private.error_result(
                    p_request,
                    'STALE_ENTITY_VERSION',
                    'Only VERIFIED questions can be graded.'
                );
            end if;

            select *
            into v_saved
            from app_private.quiz_responses r
            where r.attempt_id = v_attempt_id
              and r.question_id = v_qid
              and r.user_id = v_uid;
            v_has_saved := found;

            v_selected := case when v_has_saved then v_saved.selected_option_id else null end;
            if v_selected is null then
                v_exp_validity := 'OMITTED';
                v_exp_correct := null;
            elsif exists (
                select 1
                from jsonb_array_elements(v_question.options) opt
                where opt ->> 'option_id' = v_selected
            ) then
                v_exp_validity := 'VALID';
                v_exp_correct := (v_selected = v_question.answer_key);
            else
                v_exp_validity := 'INVALID';
                v_exp_correct := null;
            end if;

            v_item_correct := case
                when v_item -> 'is_correct' = 'null'::jsonb then null
                else (v_item ->> 'is_correct')::boolean
            end;

            if (v_item ->> 'attempt_id')::uuid is distinct from v_attempt_id
               or (v_item ->> 'question_id')::uuid is distinct from v_qid
               or (v_item ->> 'user_id')::uuid is distinct from v_uid
               or (case when v_item -> 'selected_option_id' = 'null'::jsonb then null else v_item ->> 'selected_option_id' end)
                  is distinct from v_selected
               or (v_item ->> 'validity') is distinct from v_exp_validity
               or v_item_correct is distinct from v_exp_correct
               or v_item -> 'graded_at' = 'null'::jsonb then
                return app_private.error_result(
                    p_request,
                    'INVALID_PARAMETER',
                    'Graded response item does not match persisted attempt responses and verified answer key.'
                );
            end if;

            if v_exp_validity = 'VALID' then
                v_valid_cnt := v_valid_cnt + 1;
                if v_exp_correct then
                    v_correct_cnt := v_correct_cnt + 1;
                else
                    v_incorrect_cnt := v_incorrect_cnt + 1;
                end if;
            end if;
        end loop;

        v_omitted_cnt := v_attempt.total_questions - v_valid_cnt;
        v_exp_score := case
            when v_valid_cnt = 0 then null
            else round((v_correct_cnt::numeric * 100.0) / v_valid_cnt::numeric, 2)
        end;
        v_arg_score := case
            when v_args -> 'score_percent' = 'null'::jsonb then null
            else round((v_args ->> 'score_percent')::numeric, 2)
        end;

        if (v_args ->> 'valid_response_count')::integer is distinct from v_valid_cnt
           or (v_args ->> 'correct_count')::integer is distinct from v_correct_cnt
           or (v_args ->> 'incorrect_count')::integer is distinct from v_incorrect_cnt
           or (v_args ->> 'omitted_count')::integer is distinct from v_omitted_cnt
           or v_arg_score is distinct from v_exp_score then
            return app_private.error_result(
                p_request,
                'INVALID_PARAMETER',
                'Grading summary counts or score_percent do not match deterministic grading rules.'
            );
        end if;

        for v_idx in 0 .. (v_attempt.total_questions - 1) loop
            v_item := (v_args -> 'graded_responses') -> v_idx;
            insert into app_private.quiz_responses (
                response_id,
                attempt_id,
                question_id,
                user_id,
                selected_option_id,
                validity,
                is_correct,
                graded_at,
                created_at,
                updated_at
            )
            values (
                (v_item ->> 'response_id')::uuid,
                v_attempt_id,
                (v_item ->> 'question_id')::uuid,
                v_uid,
                case when v_item -> 'selected_option_id' = 'null'::jsonb then null else v_item ->> 'selected_option_id' end,
                v_item ->> 'validity',
                case when v_item -> 'is_correct' = 'null'::jsonb then null else (v_item ->> 'is_correct')::boolean end,
                v_submitted_at,
                (v_item ->> 'created_at')::timestamptz,
                v_submitted_at
            )
            on conflict (attempt_id, question_id) do update
            set validity = excluded.validity,
                is_correct = excluded.is_correct,
                graded_at = excluded.graded_at,
                updated_at = excluded.updated_at;
        end loop;

        update app_private.quiz_attempts
        set status = 'SUBMITTED',
            valid_response_count = v_valid_cnt,
            correct_count = v_correct_cnt,
            incorrect_count = v_incorrect_cnt,
            omitted_count = v_omitted_cnt,
            score_percent = v_exp_score,
            submitted_at = v_submitted_at,
            updated_at = v_submitted_at
        where attempt_id = v_attempt_id
          and user_id = v_uid
        returning * into v_attempt;

        select coalesce(
            jsonb_agg(app_private.quiz_response_json(r) order by q.ord),
            '[]'::jsonb
        )
        into v_responses_json
        from jsonb_array_elements_text(v_attempt.question_ids) with ordinality as q(qid, ord)
        join app_private.quiz_responses r
          on r.attempt_id = v_attempt.attempt_id
         and r.question_id = q.qid::uuid
         and r.user_id = v_uid;

        v_result := app_private.ok_result(
            p_request,
            'COMMITTED',
            jsonb_build_object(
                'attempt', app_private.quiz_attempt_json(v_attempt),
                'responses', v_responses_json
            )
        );

        insert into app_private.idempotency_records (
            user_id,
            operation,
            idempotency_key,
            request_fingerprint,
            state,
            result_reference_or_response,
            expires_at
        )
        values (
            v_uid,
            'submit_quiz_attempt',
            v_key,
            v_fp,
            'COMPLETED',
            v_result,
            clock_timestamp() + interval '7 days'
        );
        return v_result;
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;
