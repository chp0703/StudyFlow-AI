-- F2 B5: quiz_attempts and quiz_responses tables, RLS, immutability/VERIFIED triggers,
-- and signed RPCs (create_quiz_attempt, save_quiz_response, submit_quiz_attempt).

-- 1. Tables: app_private.quiz_attempts & app_private.quiz_responses
create table app_private.quiz_attempts (
    attempt_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    material_id uuid not null,
    assessment_version text not null default '1.0.0' check (assessment_version = '1.0.0'),
    origin text not null check (origin in ('MANUAL', 'SESSION_HANDOFF')),
    session_outcome_id uuid,
    status text not null default 'IN_PROGRESS' check (status in ('IN_PROGRESS', 'SUBMITTED')),
    question_ids jsonb not null check (
        jsonb_typeof(question_ids) = 'array'
        and jsonb_array_length(question_ids) between 1 and 50
    ),
    total_questions integer not null check (
        total_questions between 1 and 50
        and total_questions = jsonb_array_length(question_ids)
    ),
    valid_response_count integer not null default 0 check (
        valid_response_count between 0 and 50
        and valid_response_count <= total_questions
    ),
    correct_count integer not null default 0 check (correct_count between 0 and 50),
    incorrect_count integer not null default 0 check (incorrect_count between 0 and 50),
    omitted_count integer not null default 0 check (omitted_count between 0 and 50),
    score_percent numeric(5,2) check (
        score_percent is null or (score_percent >= 0 and score_percent <= 100)
    ),
    started_at timestamptz not null default clock_timestamp(),
    submitted_at timestamptz,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    unique (user_id, attempt_id),
    foreign key (user_id, material_id)
        references app_private.materials(user_id, material_id)
        on delete restrict,
    constraint quiz_attempts_origin_handoff_check check (
        (origin = 'MANUAL' and session_outcome_id is null)
        or (origin = 'SESSION_HANDOFF' and session_outcome_id is not null)
    ),
    constraint quiz_attempts_counts_check check (
        correct_count + incorrect_count = valid_response_count
        and valid_response_count + omitted_count = total_questions
    ),
    constraint quiz_attempts_status_shape_check check (
        (
            status = 'IN_PROGRESS'
            and submitted_at is null
            and valid_response_count = 0
            and correct_count = 0
            and incorrect_count = 0
            and omitted_count = total_questions
            and score_percent is null
        )
        or (
            status = 'SUBMITTED'
            and submitted_at is not null
            and (
                (valid_response_count = 0 and score_percent is null)
                or (valid_response_count > 0 and score_percent is not null)
            )
        )
    )
);

create table app_private.quiz_responses (
    response_id uuid primary key,
    attempt_id uuid not null,
    question_id uuid not null,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    selected_option_id text check (
        selected_option_id is null
        or (length(btrim(selected_option_id)) > 0 and length(selected_option_id) <= 32)
    ),
    validity text not null check (validity in ('VALID', 'OMITTED', 'INVALID')),
    is_correct boolean,
    graded_at timestamptz,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    unique (attempt_id, question_id),
    unique (user_id, response_id),
    foreign key (user_id, attempt_id)
        references app_private.quiz_attempts(user_id, attempt_id)
        on delete restrict,
    foreign key (user_id, question_id)
        references app_private.question_drafts(user_id, question_id)
        on delete restrict,
    constraint quiz_responses_validity_shape_check check (
        (validity = 'OMITTED' and selected_option_id is null and is_correct is null)
        or (validity = 'INVALID' and selected_option_id is not null and is_correct is null)
        or (validity = 'VALID' and selected_option_id is not null)
    ),
    constraint quiz_responses_grading_shape_check check (
        (graded_at is null and is_correct is null)
        or (
            graded_at is not null
            and (
                (validity = 'VALID' and is_correct is not null)
                or (validity in ('OMITTED', 'INVALID') and is_correct is null)
            )
        )
    )
);

create index ix_quiz_attempts_user_material_status
    on app_private.quiz_attempts(user_id, material_id, status, submitted_at desc);
create index ix_quiz_responses_user_attempt
    on app_private.quiz_responses(user_id, attempt_id);
create index ix_quiz_responses_user_question
    on app_private.quiz_responses(user_id, question_id);

-- 2. Row-Level Security & Grants
alter table app_private.quiz_attempts enable row level security;
alter table app_private.quiz_attempts force row level security;
alter table app_private.quiz_responses enable row level security;
alter table app_private.quiz_responses force row level security;

revoke all on app_private.quiz_attempts, app_private.quiz_responses
    from public, anon, authenticated;
grant select, insert, update on app_private.quiz_attempts to sf_rpc_owner;
grant select, insert, update on app_private.quiz_responses to sf_rpc_owner;

create policy quiz_attempts_select on app_private.quiz_attempts
    for select to sf_rpc_owner using (user_id = app_private.current_uid());
create policy quiz_attempts_insert on app_private.quiz_attempts
    for insert to sf_rpc_owner with check (user_id = app_private.current_uid());
create policy quiz_attempts_update on app_private.quiz_attempts
    for update to sf_rpc_owner
    using (user_id = app_private.current_uid())
    with check (user_id = app_private.current_uid());

create policy quiz_responses_select on app_private.quiz_responses
    for select to sf_rpc_owner using (user_id = app_private.current_uid());
create policy quiz_responses_insert on app_private.quiz_responses
    for insert to sf_rpc_owner with check (user_id = app_private.current_uid());
create policy quiz_responses_update on app_private.quiz_responses
    for update to sf_rpc_owner
    using (user_id = app_private.current_uid())
    with check (user_id = app_private.current_uid());

-- 3. Triggers enforcing VERIFIED-only questions and SUBMITTED immutability
create function app_private.guard_quiz_attempt() returns trigger
language plpgsql set search_path = '' as $$
declare
    v_qid_text text;
    v_qid uuid;
    v_distinct_count integer;
begin
    if tg_op = 'DELETE' then
        raise exception 'Quiz attempts cannot be deleted' using errcode = '23514';
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

create trigger trg_guard_quiz_attempt
    before insert or update or delete on app_private.quiz_attempts
    for each row execute function app_private.guard_quiz_attempt();

create function app_private.guard_quiz_response() returns trigger
language plpgsql set search_path = '' as $$
declare
    v_attempt app_private.quiz_attempts;
begin
    if tg_op = 'DELETE' then
        raise exception 'Quiz responses cannot be deleted' using errcode = '23514';
    end if;

    select *
    into v_attempt
    from app_private.quiz_attempts a
    where a.attempt_id = new.attempt_id
      and a.user_id = new.user_id;

    if not found then
        raise exception 'Quiz attempt not found for response' using errcode = '23514';
    end if;

    if v_attempt.status = 'SUBMITTED' then
        raise exception 'Responses of a SUBMITTED attempt are immutable' using errcode = '23514';
    end if;

    if tg_op = 'UPDATE' then
        if old.graded_at is not null then
            raise exception 'Graded quiz response is immutable' using errcode = '23514';
        end if;
        if (
            new.response_id,
            new.attempt_id,
            new.question_id,
            new.user_id,
            new.created_at
        ) is distinct from (
            old.response_id,
            old.attempt_id,
            old.question_id,
            old.user_id,
            old.created_at
        ) then
            raise exception 'Quiz response identity is immutable' using errcode = '23514';
        end if;
    end if;

    if not (v_attempt.question_ids @> to_jsonb(new.question_id::text)) then
        raise exception 'Question does not belong to quiz attempt' using errcode = '23514';
    end if;

    if not exists (
        select 1
        from app_private.question_drafts q
        where q.question_id = new.question_id
          and q.user_id = new.user_id
          and q.material_id = v_attempt.material_id
          and q.status = 'VERIFIED'
    ) then
        raise exception 'Quiz response requires a VERIFIED question' using errcode = '23514';
    end if;

    return new;
end $$;

create trigger trg_guard_quiz_response
    before insert or update or delete on app_private.quiz_responses
    for each row execute function app_private.guard_quiz_response();

-- 4. Update canonical_json to support bounded decimal fields (score_percent, error_rate) alongside priority
create or replace function app_private.canonical_json(p_value jsonb) returns text
language plpgsql immutable set search_path = '' as $$
declare
    v_type text := jsonb_typeof(p_value);
    v_text text;
begin
    if v_type = 'null' then
        return 'null';
    elsif v_type = 'boolean' then
        return p_value::text;
    elsif v_type = 'number' then
        v_text := p_value::text;
        if v_text !~ '^-?(0|[1-9][0-9]{0,15})$' or abs(v_text::numeric) > 9007199254740991 then
            raise exception using errcode = '22023',
                message = 'canonical JSON accepts only safe integers';
        end if;
        return v_text;
    elsif v_type = 'string' then
        return to_jsonb(p_value #>> '{}')::text;
    elsif v_type = 'array' then
        return '[' || coalesce((select string_agg(app_private.canonical_json(e.value), ',' order by e.ord)
                                from jsonb_array_elements(p_value) with ordinality e(value, ord)), '') || ']';
    end if;
    return '{' || coalesce((select string_agg(
        to_jsonb(e.key)::text || ':' ||
        case
            when e.key = 'priority' and jsonb_typeof(e.value) = 'number' and e.value::text in ('0.1', '0.5')
                then e.value::text
            when e.key = 'score_percent' and jsonb_typeof(e.value) = 'number'
                 and e.value::numeric >= 0 and e.value::numeric <= 100
                 and e.value::text ~ '^(0|[1-9][0-9]{0,2})(\.[0-9]{1,2})?$'
                then e.value::text
            when e.key = 'error_rate' and jsonb_typeof(e.value) = 'number'
                 and e.value::numeric >= 0 and e.value::numeric <= 1
                 and e.value::text ~ '^(0|1)(\.[0-9]{1,4})?$'
                then e.value::text
            else app_private.canonical_json(e.value)
        end,
        ',' order by convert_to(e.key, 'UTF8'))
        from jsonb_each(p_value) e), '') || '}';
end $$;

-- 5. JSON serializers for QuizAttempt and QuizResponse
create function app_private.quiz_attempt_json(r app_private.quiz_attempts) returns jsonb
language sql stable set search_path = '' as $$
    select jsonb_build_object(
        'assessment_version', r.assessment_version,
        'attempt_id', r.attempt_id,
        'user_id', r.user_id,
        'material_id', r.material_id,
        'origin', r.origin,
        'session_outcome_id', r.session_outcome_id,
        'status', r.status,
        'question_ids', r.question_ids,
        'total_questions', r.total_questions,
        'valid_response_count', r.valid_response_count,
        'correct_count', r.correct_count,
        'incorrect_count', r.incorrect_count,
        'omitted_count', r.omitted_count,
        'score_percent', case when r.score_percent is null then null else to_jsonb(trim_scale(r.score_percent)) end,
        'started_at', app_private.iso(r.started_at),
        'submitted_at', case when r.submitted_at is null then null else app_private.iso(r.submitted_at) end,
        'created_at', app_private.iso(r.created_at),
        'updated_at', app_private.iso(r.updated_at)
    )
$$;

create function app_private.quiz_response_json(r app_private.quiz_responses) returns jsonb
language sql stable set search_path = '' as $$
    select jsonb_build_object(
        'response_id', r.response_id,
        'attempt_id', r.attempt_id,
        'question_id', r.question_id,
        'user_id', r.user_id,
        'selected_option_id', r.selected_option_id,
        'validity', r.validity,
        'is_correct', r.is_correct,
        'graded_at', case when r.graded_at is null then null else app_private.iso(r.graded_at) end,
        'created_at', app_private.iso(r.created_at),
        'updated_at', app_private.iso(r.updated_at)
    )
$$;

-- 6. Public signed RPCs: create_quiz_attempt, save_quiz_response, submit_quiz_attempt
create function app_api.create_quiz_attempt(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'create_quiz_attempt', 'CreateQuizAttemptArguments');
    v_uid uuid;
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_args jsonb := p_request -> 'arguments';
    v_attempt_id uuid;
    v_material_id uuid;
    v_origin text;
    v_session_outcome_id uuid;
    v_qids jsonb;
    v_total integer;
    v_qid_text text;
    v_qstatus text;
    v_fp text;
    v_reply jsonb;
    v_attempt app_private.quiz_attempts;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key is required.');
    end if;

    v_origin := v_args ->> 'origin';
    if (v_origin = 'MANUAL' and v_args -> 'session_outcome_id' <> 'null'::jsonb)
       or (v_origin = 'SESSION_HANDOFF' and v_args -> 'session_outcome_id' = 'null'::jsonb) then
        return app_private.error_result(
            p_request,
            'INVALID_PARAMETER',
            'origin and session_outcome_id do not match the handoff contract.'
        );
    end if;

    v_fp := app_private.domain_fingerprint(v_uid, 'create_quiz_attempt', v_args);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'create_quiz_attempt', v_key, v_fp);
        if v_reply is not null then
            if v_reply ->> 'outcome' = 'COMMITTED' then
                return jsonb_set(v_reply, '{outcome}', '"READ"'::jsonb);
            end if;
            return v_reply;
        end if;

        perform app_private.lock_owner(v_uid, p_request);

        v_reply := app_private.idempotent_reply(p_request, v_uid, 'create_quiz_attempt', v_key, v_fp);
        if v_reply is not null then
            if v_reply ->> 'outcome' = 'COMMITTED' then
                return jsonb_set(v_reply, '{outcome}', '"READ"'::jsonb);
            end if;
            return v_reply;
        end if;

        v_attempt_id := (v_args ->> 'attempt_id')::uuid;
        v_material_id := (v_args ->> 'material_id')::uuid;
        v_session_outcome_id := case
            when v_args -> 'session_outcome_id' = 'null'::jsonb then null
            else (v_args ->> 'session_outcome_id')::uuid
        end;
        v_qids := v_args -> 'question_ids';
        v_total := jsonb_array_length(v_qids);

        if exists (select 1 from app_private.quiz_attempts where attempt_id = v_attempt_id) then
            return app_private.error_result(
                p_request,
                'IDEMPOTENCY_CONFLICT',
                'The attempt_id is already in use.'
            );
        end if;

        if not exists (
            select 1
            from app_private.materials m
            where m.material_id = v_material_id
              and m.user_id = v_uid
              and m.status = 'READY'
        ) then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Material not found.');
        end if;

        for v_qid_text in
            select value #>> '{}' from jsonb_array_elements(v_qids)
        loop
            select q.status
            into v_qstatus
            from app_private.question_drafts q
            where q.question_id = v_qid_text::uuid
              and q.user_id = v_uid
              and q.material_id = v_material_id;

            if not found then
                return app_private.error_result(
                    p_request,
                    'ENTITY_NOT_FOUND',
                    'Question not found for this material.'
                );
            end if;

            if v_qstatus <> 'VERIFIED' then
                return app_private.error_result(
                    p_request,
                    'STALE_ENTITY_VERSION',
                    'Only VERIFIED questions can be included in a quiz attempt.'
                );
            end if;
        end loop;

        insert into app_private.quiz_attempts (
            attempt_id,
            user_id,
            material_id,
            origin,
            session_outcome_id,
            status,
            question_ids,
            total_questions,
            valid_response_count,
            correct_count,
            incorrect_count,
            omitted_count,
            score_percent
        )
        values (
            v_attempt_id,
            v_uid,
            v_material_id,
            v_origin,
            v_session_outcome_id,
            'IN_PROGRESS',
            v_qids,
            v_total,
            0,
            0,
            0,
            v_total,
            null
        )
        returning * into v_attempt;

        v_result := app_private.ok_result(p_request, 'COMMITTED', app_private.quiz_attempt_json(v_attempt));
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
            'create_quiz_attempt',
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

create function app_api.save_quiz_response(p_request jsonb) returns jsonb
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

    v_fp := app_private.domain_fingerprint(v_uid, 'save_quiz_response', v_args);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'save_quiz_response', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;

        perform app_private.lock_owner(v_uid, p_request);

        v_reply := app_private.idempotent_reply(p_request, v_uid, 'save_quiz_response', v_key, v_fp);
        if v_reply is not null then
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

create function app_api.submit_quiz_attempt(p_request jsonb) returns jsonb
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
            return v_reply;
        end if;

        perform app_private.lock_owner(v_uid, p_request);

        v_reply := app_private.idempotent_reply(p_request, v_uid, 'submit_quiz_attempt', v_key, v_fp);
        if v_reply is not null then
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

-- 7. Function ownership and privilege lockdowns
alter function app_private.guard_quiz_attempt() owner to sf_rpc_owner;
alter function app_private.guard_quiz_response() owner to sf_rpc_owner;
alter function app_private.canonical_json(jsonb) owner to sf_rpc_owner;
alter function app_private.quiz_attempt_json(app_private.quiz_attempts) owner to sf_rpc_owner;
alter function app_private.quiz_response_json(app_private.quiz_responses) owner to sf_rpc_owner;

revoke all on function
    app_private.guard_quiz_attempt(),
    app_private.guard_quiz_response(),
    app_private.canonical_json(jsonb),
    app_private.quiz_attempt_json(app_private.quiz_attempts),
    app_private.quiz_response_json(app_private.quiz_responses)
from public, anon, authenticated;

do $$
declare
    v_name text;
begin
    foreach v_name in array array['create_quiz_attempt', 'save_quiz_response', 'submit_quiz_attempt'] loop
        execute format('alter function app_api.%I(jsonb) owner to sf_rpc_owner', v_name);
        execute format('revoke all on function app_api.%I(jsonb) from public, anon', v_name);
        execute format('grant execute on function app_api.%I(jsonb) to authenticated', v_name);
    end loop;
end $$;
