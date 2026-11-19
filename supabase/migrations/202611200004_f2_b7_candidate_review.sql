create or replace function app_api.review_pending_action(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'review_pending_action', 'ReviewPendingActionArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_pres jsonb := p_request #> '{arguments,presentation}';
    a app_private.pending_actions;
    v_stored jsonb;
    c app_private.task_candidates;
    rec app_private.revision_recommendations;
    v_slots jsonb;
    v_missing jsonb;
    v_command jsonb;
    v_fp text;
    v_key text;
    v_reply jsonb;
    v_deadline timestamptz;
    v_patch jsonb;
    v_field text;
    v_conv_id uuid;
    v_msg_id text;
    v_precision text;
    v_date_text text;
    v_derived_deadline timestamptz;
    v_start_at timestamptz;
    v_avail_from timestamptz;
    v_sources jsonb;
    v_prev_pres jsonb;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();

    if v_args ? 'candidate_patch' then
        v_patch := v_args -> 'candidate_patch';
        if jsonb_typeof(v_patch) is distinct from 'object' then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'candidate_patch must be an object.');
        end if;

        v_key := nullif(p_request #>> '{execution_context,idempotency_key}', '');
        if v_key is null then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'idempotency_key is required when candidate_patch is provided.');
        end if;

        v_conv_id := nullif(p_request #>> '{execution_context,conversation_id}', '')::uuid;
        if v_conv_id is null or nullif(v_args ->> 'expected_candidate_version', '') is null then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'conversation_id and expected_candidate_version are required.');
        end if;

        v_fp := app_private.domain_fingerprint(
            v_uid,
            'review_pending_action',
            jsonb_build_object(
                'action_id', v_args -> 'action_id',
                'expected_action_version', v_args -> 'expected_action_version',
                'expected_candidate_version', v_args -> 'expected_candidate_version',
                'candidate_patch', v_patch,
                'conversation_id', v_conv_id
            )
        );

        v_reply := app_private.idempotent_reply(p_request, v_uid, 'review_pending_action', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;

        begin
            perform app_private.lock_owner(v_uid, p_request);

            v_reply := app_private.idempotent_reply(p_request, v_uid, 'review_pending_action', v_key, v_fp);
            if v_reply is not null then
                return v_reply;
            end if;

            select * into a
            from app_private.pending_actions
            where user_id = v_uid
              and conversation_id = v_conv_id
              and action_id = (v_args ->> 'action_id')::uuid
            for update;
            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The action was not found.');
            end if;
            if a.intent is distinct from 'CREATE_TASK' or a.candidate_id is null then
                return app_private.error_result(p_request, 'INVALID_PARAMETER', 'candidate_patch is only supported for CREATE_TASK actions with a candidate.');
            end if;

            select * into c
            from app_private.task_candidates
            where user_id = v_uid
              and conversation_id = v_conv_id
              and candidate_id = a.candidate_id
            for update;
            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The task candidate was not found.');
            end if;

            select * into rec
            from app_private.revision_recommendations
            where user_id = v_uid
              and conversation_id = v_conv_id
              and candidate_id = c.candidate_id
              and status = 'ACCEPTED'
            limit 1;
            if not found then
                return app_private.error_result(p_request, 'INVALID_PARAMETER', 'candidate_patch is restricted to accepted revision recommendations.');
            end if;

            if a.state not in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION')
               or a.version <> (v_args ->> 'expected_action_version')::bigint
               or c.version <> (v_args ->> 'expected_candidate_version')::bigint
               or c.status is distinct from 'DRAFT' then
                return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action or candidate changed since it was read.');
            end if;

            v_slots := coalesce(c.slots, '{}'::jsonb) || v_patch;
            if not app_private.matches_contract('CandidateTaskFields', v_slots) then
                return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Candidate fields do not match CandidateTaskFields.');
            end if;

            if (v_patch ? 'deadline_date')
               and jsonb_typeof(v_patch -> 'deadline_date') <> 'null'
               and nullif(v_slots ->> 'deadline_precision', '') is null then
                v_slots := jsonb_set(v_slots, '{deadline_precision}', '"DATE"'::jsonb, true);
            end if;

            if (v_patch ? 'deadline_at')
               and jsonb_typeof(v_patch -> 'deadline_at') <> 'null'
               and nullif(v_slots ->> 'deadline_precision', '') is null then
                v_slots := jsonb_set(v_slots, '{deadline_precision}', '"DATETIME"'::jsonb, true);
            end if;

            if (nullif(v_slots ->> 'deadline_date', '') is not null
                or nullif(v_slots ->> 'deadline_at', '') is not null
                or nullif(v_slots ->> 'deadline_precision', '') is not null)
               and nullif(v_slots ->> 'deadline_timezone', '') is null then
                v_slots := jsonb_set(v_slots, '{deadline_timezone}', '"Asia/Ho_Chi_Minh"'::jsonb, true);
            end if;

            v_precision := nullif(v_slots ->> 'deadline_precision', '');
            if v_precision = 'DATE' then
                v_date_text := nullif(v_slots ->> 'deadline_date', '');
                if v_date_text is not null then
                    v_derived_deadline := ((v_date_text::date + 1)::timestamp without time zone) at time zone 'Asia/Ho_Chi_Minh';
                    if (v_patch ? 'deadline_at') and jsonb_typeof(v_patch -> 'deadline_at') <> 'null' then
                        if (v_patch ->> 'deadline_at')::timestamptz is distinct from v_derived_deadline then
                            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Explicit deadline_at contradicts derived DATE deadline.');
                        end if;
                    end if;
                    v_slots := jsonb_set(v_slots, '{deadline_at}', to_jsonb(app_private.iso(v_derived_deadline)), true);
                end if;
            elsif v_precision = 'DATETIME' then
                if nullif(v_slots ->> 'deadline_date', '') is not null then
                    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'deadline_date is invalid when deadline_precision is DATETIME.');
                end if;
            end if;

            if not app_private.matches_contract('CandidateTaskFields', v_slots) then
                return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Normalized candidate fields do not match CandidateTaskFields.');
            end if;

            v_start_at := (nullif(v_slots ->> 'start_at', ''))::timestamptz;
            v_deadline := (nullif(v_slots ->> 'deadline_at', ''))::timestamptz;
            v_avail_from := (nullif(v_slots ->> 'available_from_at', ''))::timestamptz;

            if v_deadline is not null then
                if v_start_at is not null and v_start_at > v_deadline then
                    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'start_at cannot be after deadline_at.');
                end if;
                if v_avail_from is not null and v_avail_from > v_deadline then
                    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'available_from cannot be after deadline_at.');
                end if;
            end if;

            v_missing := '[]'::jsonb;
            if nullif(btrim(coalesce(v_slots ->> 'title', '')), '') is null then
                v_missing := v_missing || '["title"]'::jsonb;
            end if;
            if not (v_slots ? 'estimated_minutes') or jsonb_typeof(v_slots -> 'estimated_minutes') = 'null' then
                v_missing := v_missing || '["estimated_minutes"]'::jsonb;
            end if;
            if v_start_at is null then
                v_missing := v_missing || '["start_at"]'::jsonb;
            end if;
            if v_precision = 'DATE' then
                if nullif(v_slots ->> 'deadline_date', '') is null then
                    v_missing := v_missing || '["deadline_date"]'::jsonb;
                end if;
            elsif v_deadline is null then
                v_missing := v_missing || '["deadline_at"]'::jsonb;
            end if;

            select p.presentation into v_prev_pres
            from app_private.action_presentations p
            where p.user_id = v_uid
              and p.action_id = a.action_id
              and p.action_version = a.version;

            v_msg_id := nullif(p_request #>> '{execution_context,trusted_context,message_id}', '');
            v_sources := coalesce(c.field_sources, '{}'::jsonb);
            for v_field in select jsonb_object_keys(v_patch) loop
                v_sources := jsonb_set(
                    v_sources,
                    array[v_field],
                    jsonb_strip_nulls(jsonb_build_object(
                        'source', 'USER_MESSAGE',
                        'reference', v_msg_id
                    )),
                    true
                );
            end loop;

            update app_private.task_candidates
            set slots = v_slots,
                version = version + 1,
                field_sources = v_sources,
                updated_at = pg_catalog.now()
            where candidate_id = c.candidate_id
            returning * into c;

            update app_private.pending_actions
            set version = version + 1,
                requires_review = false,
                state = case
                    when jsonb_array_length(v_missing) > 0 then 'AWAITING_CLARIFICATION'
                    else 'AWAITING_CONFIRMATION'
                end,
                draft_arguments = jsonb_build_object('slots', v_slots),
                missing_fields = v_missing
            where action_id = a.action_id
            returning * into a;

            if jsonb_array_length(v_missing) > 0 then
                v_command := null;
            else
                v_command := jsonb_build_object(
                    'schema_version', '1.1',
                    'operation', 'confirm_task',
                    'arguments', jsonb_build_object(
                        'candidate_id', c.candidate_id,
                        'expected_candidate_version', c.version
                    )
                );
            end if;

            v_pres := coalesce(v_prev_pres, '{}'::jsonb) || jsonb_build_object(
                'pending_action', app_private.pending_json(a),
                'candidate', app_private.candidate_json(c),
                'normalized_command', v_command
            );

            v_error := app_private.store_presentation(p_request, v_uid, a, v_pres);
            if v_error is not null then
                raise exception using errcode = 'P0001', message = v_error #>> '{error,code}';
            end if;

            select p.presentation into v_stored
            from app_private.action_presentations p
            where p.user_id = v_uid
              and p.action_id = a.action_id
              and p.action_version = a.version;

            v_result := app_private.ok_result(p_request, 'COMMITTED', v_stored);

            insert into app_private.idempotency_records (
                user_id,
                operation,
                state,
                idempotency_key,
                request_fingerprint,
                result_reference_or_response,
                expires_at
            ) values (
                v_uid,
                'review_pending_action',
                'COMPLETED',
                v_key,
                v_fp,
                v_result,
                pg_catalog.now() + interval '7 days'
            );

            return v_result;
        exception
            when sqlstate 'P0001' then
                return app_private.error_result(
                    p_request,
                    case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_ENTITY_VERSION') then sqlerrm else 'INVALID_PARAMETER' end,
                    'The presentation does not match the stored target.'
                );
            when others then
                return app_private.failure(p_request, sqlstate);
        end;
    end if;

    v_error := app_private.pending_precheck(p_request, v_uid, v_pres -> 'pending_action');
    if v_error is not null then
        return v_error;
    end if;
    if v_pres #>> '{pending_action,action_id}' is distinct from v_args ->> 'action_id' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The presentation is for a different action.');
    end if;
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into a from app_private.pending_actions
        where user_id = v_uid and action_id = (v_args ->> 'action_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The action was not found.');
        end if;
        -- A retry after a lost response finds the review already applied one version ahead.
        if a.version = (v_args ->> 'expected_action_version')::bigint + 1 and not a.requires_review then
            select p.presentation into v_stored from app_private.action_presentations p
            where p.user_id = v_uid and p.action_id = a.action_id and p.action_version = a.version;
            if v_stored is not null then
                return app_private.ok_result(p_request, 'COMMITTED', v_stored);
            end if;
        end if;
        if a.version <> (v_args ->> 'expected_action_version')::bigint
           or a.state not in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL') then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action changed since it was read.');
        end if;
        if not a.requires_review then
            select p.presentation into v_stored from app_private.action_presentations p
            where p.user_id = v_uid and p.action_id = a.action_id and p.action_version = a.version;
            if v_stored is not null then
                return app_private.ok_result(p_request, 'COMMITTED', v_stored);
            end if;
        end if;
        update app_private.pending_actions set version = version + 1, requires_review = false
        where action_id = a.action_id returning * into a;
        v_error := app_private.store_presentation(p_request, v_uid, a, v_pres);
        if v_error is not null then
            raise exception using errcode = 'P0001', message = v_error #>> '{error,code}';
        end if;
        select p.presentation into v_stored from app_private.action_presentations p
        where p.user_id = v_uid and p.action_id = a.action_id and p.action_version = a.version;
        return app_private.ok_result(p_request, 'COMMITTED', v_stored);
    exception
        when sqlstate 'P0001' then
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_ENTITY_VERSION') then sqlerrm else 'INVALID_PARAMETER' end,
                'The presentation does not match the stored target.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_api.review_pending_action(jsonb) owner to sf_rpc_owner;
revoke all on function app_api.review_pending_action(jsonb) from public, anon;
grant execute on function app_api.review_pending_action(jsonb) to authenticated;
