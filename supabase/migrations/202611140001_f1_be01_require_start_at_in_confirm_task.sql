-- Require start_at in confirm_task instead of deriving it from deadline or available_from_at.

create or replace function app_api.confirm_task(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'confirm_task', 'confirm_taskArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_ctx jsonb := p_request -> 'execution_context';
    v_approval jsonb := v_ctx -> 'approval_action';
    v_ref jsonb := v_ctx -> 'action_reference';
    v_key text := v_ctx ->> 'idempotency_key';
    v_conv uuid := (v_ctx ->> 'conversation_id')::uuid;
    v_binding jsonb;
    v_fp text;
    v_reply jsonb;
    c app_private.task_candidates;
    a app_private.pending_actions;
    p app_private.action_presentations;
    t app_private.academic_tasks;
    v_slots jsonb;
    v_precision text;
    v_tz text;
    v_date date;
    v_start_at timestamptz;
    v_available_from timestamptz;
    v_deadline timestamptz;
    v_title text;
    v_minutes bigint;
    v_priority numeric;
    v_color text;
    v_missing text;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null or v_conv is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key and a conversation are required.');
    end if;
    if jsonb_typeof(v_approval) is distinct from 'object' or jsonb_typeof(v_ref) is distinct from 'object'
       or v_approval ->> 'decision' <> 'APPROVE' or v_approval ->> 'target_type' <> 'TASK_CANDIDATE'
       or v_approval ->> 'user_id' <> v_uid::text
       or v_approval ->> 'target_id' <> v_args ->> 'candidate_id'
       or (v_approval ->> 'target_version')::bigint <> (v_args ->> 'expected_candidate_version')::bigint
       or v_ref ->> 'target_type' <> 'TASK_CANDIDATE' or v_ref ->> 'target_id' <> v_args ->> 'candidate_id'
       or (v_ref ->> 'target_version')::bigint <> (v_args ->> 'expected_candidate_version')::bigint then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'A matching approval for this candidate version is required.');
    end if;
    v_binding := jsonb_build_object('decision', 'APPROVE', 'action_id', v_ref -> 'action_id',
        'action_version', v_ref -> 'action_version', 'target_type', 'TASK_CANDIDATE',
        'target_id', v_args -> 'candidate_id', 'target_version', v_args -> 'expected_candidate_version');
    v_fp := app_private.domain_fingerprint(v_uid, 'confirm_task', v_args, v_binding);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'confirm_task', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'confirm_task', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;

        if v_approval ->> 'source' = 'CHAT' and not exists (
               select 1 from app_private.source_messages m
               where m.user_id = v_uid and m.conversation_id = v_conv and m.role = 'USER'
                 and m.message_id = (v_approval ->> 'source_message_id')::uuid) then
            return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'A chat approval needs a recorded user message.');
        end if;

        select * into c from app_private.task_candidates
        where user_id = v_uid and candidate_id = (v_args ->> 'candidate_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The candidate was not found.');
        end if;
        if c.status <> 'DRAFT' or c.version <> (v_args ->> 'expected_candidate_version')::bigint then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The candidate changed since it was presented.');
        end if;
        select * into a from app_private.pending_actions
        where user_id = v_uid and action_id = (v_ref ->> 'action_id')::uuid for update;
        if not found or a.candidate_id is distinct from c.candidate_id or a.conversation_id <> v_conv then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The action for this candidate was not found.');
        end if;
        if a.requires_review then
            return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED', 'The action must be reviewed before it can be approved.');
        end if;
        if a.version <> (v_ref ->> 'action_version')::bigint or a.state <> 'AWAITING_CONFIRMATION' then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action changed since it was presented.');
        end if;
        select * into p from app_private.action_presentations
        where user_id = v_uid and action_id = a.action_id and action_version = a.version;
        if not found or p.target_type <> 'TASK_CANDIDATE' or p.target_id <> c.candidate_id or p.target_version <> c.version
           or p.content_digest <> app_private.presentation_digest(a, 'TASK_CANDIDATE', c.candidate_id, c.version, p.presentation) then
            return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'The approved content was not presented by the server.');
        end if;

        v_slots := c.slots;
        v_title := nullif(btrim(v_slots ->> 'title'), '');
        v_minutes := (v_slots ->> 'estimated_minutes')::bigint;
        v_start_at := (v_slots ->> 'start_at')::timestamptz;
        v_precision := coalesce(v_slots ->> 'deadline_precision', case when v_start_at is not null then 'DATETIME' end);
        v_tz := coalesce(v_slots ->> 'deadline_timezone', case when v_start_at is not null then 'Asia/Ho_Chi_Minh' end);

        v_missing := case
            when v_title is null then 'title'
            when v_minutes is null then 'estimated_minutes'
            when v_start_at is null then 'start_at'
            when v_tz is null then 'deadline_timezone'
            when v_precision = 'DATE' and v_slots ->> 'deadline_date' is null then 'deadline_date'
            when v_precision = 'DATETIME' and v_slots ->> 'deadline_at' is null and v_start_at is null then 'deadline_at'
        end;
        if v_missing is not null then
            return app_private.field_error(p_request, 'MISSING_REQUIRED_FIELD', 'The candidate is missing a required field.', v_missing);
        end if;
        if v_tz <> 'Asia/Ho_Chi_Minh' then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'Only Asia/Ho_Chi_Minh is supported.', 'deadline_timezone');
        end if;
        if v_precision = 'DATE' then
            v_date := (v_slots ->> 'deadline_date')::date;
            v_deadline := (v_date + 1)::timestamp at time zone v_tz;
            if v_slots ->> 'deadline_at' is not null and (v_slots ->> 'deadline_at')::timestamptz <> v_deadline then
                return app_private.field_error(p_request, 'INVALID_PARAMETER',
                    'A date-only deadline ends at the start of the next local day.', 'deadline_at');
            end if;
        else
            v_deadline := coalesce((v_slots ->> 'deadline_at')::timestamptz, v_start_at + (v_minutes * interval '1 minute'));
            if v_slots ->> 'deadline_date' is not null then
                return app_private.field_error(p_request, 'INVALID_PARAMETER', 'A date-time deadline has no deadline_date.', 'deadline_date');
            end if;
        end if;
        v_available_from := coalesce((v_slots ->> 'available_from_at')::timestamptz, v_start_at);
        if v_start_at > v_deadline then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'start_at is after the deadline.', 'start_at');
        end if;
        if v_available_from > v_deadline then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'available_from_at is after the deadline.', 'available_from_at');
        end if;

        if v_slots ? 'priority' and v_slots -> 'priority' <> 'null'::jsonb then
            if jsonb_typeof(v_slots -> 'priority') <> 'number' then
                return app_private.field_error(p_request, 'INVALID_PARAMETER', 'priority must be numeric.', 'priority');
            end if;
            v_priority := (v_slots ->> 'priority')::numeric;
            if v_priority not in (0.1, 0.5, 1) then
                return app_private.field_error(p_request, 'INVALID_PARAMETER', 'priority must be 0.1, 0.5 or 1.', 'priority');
            end if;
        else
            v_priority := 0.5;
        end if;

        v_color := coalesce(nullif(btrim(v_slots ->> 'color'), ''), '#596CF0');
        if v_color !~ '^#[0-9A-Fa-f]{6}$' then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'color must be a 6-digit hex color.', 'color');
        end if;

        insert into app_private.approval_actions
            (approval_action_id, user_id, target_type, target_id, target_version, decision, source, source_message_id,
             candidate_target_id)
        values ((v_approval ->> 'approval_action_id')::uuid, v_uid, 'TASK_CANDIDATE', c.candidate_id, c.version, 'APPROVE',
                v_approval ->> 'source', (v_approval ->> 'source_message_id')::uuid, c.candidate_id);
        insert into app_private.academic_tasks
            (task_id, user_id, candidate_id, title, description, start_at, available_from_at, deadline_at,
             deadline_precision, deadline_date, deadline_timezone, estimated_minutes, remaining_minutes, priority, color, status)
        values (extensions.gen_random_uuid(), v_uid, c.candidate_id, v_title, v_slots ->> 'description',
                v_start_at, v_available_from, v_deadline,
                v_precision, v_date, v_tz, v_minutes, v_minutes, v_priority, v_color, 'TODO')
        returning * into t;
        update app_private.task_candidates set status = 'CONFIRMED', confirmed_task_id = t.task_id, version = version + 1
        where candidate_id = c.candidate_id;
        update app_private.pending_actions set state = 'COMPLETED', version = version + 1 where action_id = a.action_id;
        update app_private.user_profiles set schedule_revision = schedule_revision + 1 where user_id = v_uid;
        v_result := app_private.ok_result(p_request, 'COMMITTED', app_private.task_json(t));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'confirm_task', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception
        when sqlstate 'P0001' then
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_ENTITY_VERSION') then sqlerrm else 'INVALID_PARAMETER' end,
                'The approval target is no longer valid.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;
