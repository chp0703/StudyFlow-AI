-- WP2b-4 / migration 016: time windows (availability and busy), scheduling preferences and
-- window listing. The three writers need a backend approval for a PENDING_ACTION whose
-- presented command is exactly the command being executed.

create function app_private.default_policy() returns jsonb
language sql immutable set search_path = '' as $$
    select '{"min_block_minutes":25,"max_block_minutes":90,"allow_short_final_block":true,"max_daily_minutes":240,"break_minutes":10}'::jsonb
$$;

create function app_private.window_json(p_window app_private.time_windows) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('window_id', p_window.window_id, 'user_id', p_window.user_id, 'version', p_window.version,
        'kind', p_window.kind, 'label', p_window.label, 'recurrence', p_window.recurrence, 'timezone', p_window.timezone,
        'start_at', case when p_window.start_at is null then null else app_private.iso(p_window.start_at) end,
        'end_at', case when p_window.end_at is null then null else app_private.iso(p_window.end_at) end,
        'weekday', p_window.weekday, 'start_time', substr(p_window.start_time::text, 1, 5),
        'end_time', substr(p_window.end_time::text, 1, 5), 'valid_from', p_window.valid_from,
        'valid_until', p_window.valid_until,
        'archived_at', case when p_window.archived_at is null then null else app_private.iso(p_window.archived_at) end,
        'created_at', app_private.iso(p_window.created_at), 'updated_at', app_private.iso(p_window.updated_at))
$$;

-- Business rules JSON Schema cannot express: real time zone, whole minutes, one local day,
-- weekly ordering. Returns an ErrorResult or null.
create function app_private.validate_window(p_request jsonb, p_window jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_tz text := p_window ->> 'timezone';
    v_start timestamptz;
    v_end timestamptz;
    v_local_start timestamp;
    v_local_end timestamp;
begin
    if not exists (select 1 from pg_catalog.pg_timezone_names n where n.name = v_tz) then
        return app_private.field_error(p_request, 'INVALID_PARAMETER', 'Unknown time zone.', 'window.timezone');
    end if;
    if p_window ->> 'recurrence' = 'NONE' then
        v_start := (p_window ->> 'start_at')::timestamptz;
        v_end := (p_window ->> 'end_at')::timestamptz;
        if v_end <= v_start then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'The window must end after it starts.', 'window.end_at');
        end if;
        if extract(second from v_start) <> 0 or extract(second from v_end) <> 0 then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'Windows use whole minutes.', 'window.start_at');
        end if;
        v_local_start := v_start at time zone v_tz;
        v_local_end := v_end at time zone v_tz;
        if v_local_end::date <> v_local_start::date and v_local_end <> (v_local_start::date + 1)::timestamp then
            return app_private.field_error(p_request, 'INVALID_PARAMETER',
                'Split an interval that crosses midnight into two windows.', 'window.end_at');
        end if;
    else
        if (p_window ->> 'end_time')::time <= (p_window ->> 'start_time')::time then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'The window must end after it starts.', 'window.end_time');
        end if;
        if p_window ->> 'valid_until' is not null and (p_window ->> 'valid_until')::date <= (p_window ->> 'valid_from')::date then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'valid_until must be after valid_from.', 'window.valid_until');
        end if;
    end if;
    return null;
end $$;

-- Binding of the backend approval to its pending action; null when the context is unusable.
create function app_private.pending_binding(p_request jsonb) returns jsonb
language plpgsql immutable set search_path = '' as $$
declare
    v_ref jsonb := p_request #> '{execution_context,action_reference}';
    v_approval jsonb := p_request #> '{execution_context,approval_action}';
begin
    if jsonb_typeof(v_ref) is distinct from 'object' or jsonb_typeof(v_approval) is distinct from 'object'
       or v_approval ->> 'decision' <> 'APPROVE' or v_approval ->> 'target_type' <> 'PENDING_ACTION'
       or v_ref ->> 'target_type' <> 'PENDING_ACTION'
       or v_approval ->> 'target_id' <> v_ref ->> 'action_id' or v_ref ->> 'target_id' <> v_ref ->> 'action_id'
       or v_approval ->> 'target_version' <> v_ref ->> 'action_version'
       or v_ref ->> 'target_version' <> v_ref ->> 'action_version' then
        return null;
    end if;
    return jsonb_build_object('decision', 'APPROVE', 'action_id', v_ref -> 'action_id',
        'action_version', v_ref -> 'action_version', 'target_type', 'PENDING_ACTION',
        'target_id', v_ref -> 'action_id', 'target_version', v_ref -> 'action_version');
end $$;

-- Verifies the approval against the stored, presented action and consumes it: writes the
-- ApprovalAction and completes the action. Returns an ErrorResult (before any write) or null.
create function app_private.consume_pending_approval(p_request jsonb, p_uid uuid, p_operation text, p_intent text,
                                                     p_arguments jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_approval jsonb := p_request #> '{execution_context,approval_action}';
    v_ref jsonb := p_request #> '{execution_context,action_reference}';
    v_conv uuid := (p_request #>> '{execution_context,conversation_id}')::uuid;
    a app_private.pending_actions;
    p app_private.action_presentations;
begin
    if v_approval ->> 'user_id' <> p_uid::text then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'The approval belongs to another owner.');
    end if;
    if v_approval ->> 'source' = 'CHAT' and not exists (
           select 1 from app_private.source_messages m
           where m.user_id = p_uid and m.conversation_id = v_conv and m.role = 'USER'
             and m.message_id = (v_approval ->> 'source_message_id')::uuid) then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'A chat approval needs a recorded user message.');
    end if;
    select * into a from app_private.pending_actions
    where user_id = p_uid and action_id = (v_ref ->> 'action_id')::uuid for update;
    if not found or a.conversation_id <> v_conv or a.intent <> p_intent then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The action for this command was not found.');
    end if;
    if a.requires_review then
        return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED', 'The action must be reviewed before it can be approved.');
    end if;
    if a.version <> (v_ref ->> 'action_version')::bigint or a.state not in ('AWAITING_CONFIRMATION', 'AWAITING_APPROVAL') then
        return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action changed since it was presented.');
    end if;
    select * into p from app_private.action_presentations
    where user_id = p_uid and action_id = a.action_id and action_version = a.version;
    if not found or p.target_type <> 'PENDING_ACTION' or p.target_id <> a.action_id or p.target_version <> a.version
       or p.content_digest <> app_private.presentation_digest(a, 'PENDING_ACTION', a.action_id, a.version, p.presentation)
       or p.presentation -> 'normalized_command' is distinct from
          jsonb_build_object('schema_version', '1.1', 'operation', p_operation, 'arguments', p_arguments) then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'The approved command was not presented by the server.');
    end if;
    insert into app_private.approval_actions
        (approval_action_id, user_id, target_type, target_id, target_version, decision, source, source_message_id,
         pending_action_target_id)
    values ((v_approval ->> 'approval_action_id')::uuid, p_uid, 'PENDING_ACTION', a.action_id, a.version, 'APPROVE',
            v_approval ->> 'source', (v_approval ->> 'source_message_id')::uuid, a.action_id);
    update app_private.pending_actions set state = 'COMPLETED', version = version + 1 where action_id = a.action_id;
    return null;
end $$;

-- Shared body of set_availability / set_busy_interval (kind fixed by the caller).
create function app_private.set_window_body(p_request jsonb, p_operation text, p_intent text, p_kind text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_uid uuid := app_private.current_uid();
    v_args jsonb := p_request -> 'arguments';
    v_change text := v_args ->> 'change_type';
    v_w jsonb := v_args -> 'window';
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_conv uuid := (p_request #>> '{execution_context,conversation_id}')::uuid;
    v_binding jsonb := app_private.pending_binding(p_request);
    v_fp text;
    v_reply jsonb;
    v_error jsonb;
    t app_private.time_windows;
    v_result jsonb;
begin
    if v_key is null or v_conv is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key and a conversation are required.');
    end if;
    if v_binding is null then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'A matching approval for the pending action is required.');
    end if;
    v_fp := app_private.domain_fingerprint(v_uid, p_operation, v_args, v_binding);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, p_operation, v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, p_operation, v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        -- Validate and load everything first; the approval is consumed only when a write will follow.
        if v_change <> 'ADD' then
            select * into t from app_private.time_windows
            where user_id = v_uid and window_id = (v_args ->> 'window_id')::uuid and kind = p_kind for update;
            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The time window was not found.');
            end if;
            if t.archived_at is not null or t.version <> (v_args ->> 'expected_window_version')::bigint then
                return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The time window changed since it was read.');
            end if;
        end if;
        if v_change <> 'ARCHIVE' then
            v_error := app_private.validate_window(p_request, v_w);
            if v_error is not null then
                return v_error;
            end if;
        end if;
        v_error := app_private.consume_pending_approval(p_request, v_uid, p_operation, p_intent, v_args);
        if v_error is not null then
            return v_error;
        end if;
        if v_change = 'ADD' then
            insert into app_private.time_windows
                (window_id, user_id, kind, label, recurrence, timezone, start_at, end_at, weekday, start_time, end_time,
                 valid_from, valid_until)
            values (extensions.gen_random_uuid(), v_uid, p_kind, v_w ->> 'label', v_w ->> 'recurrence', v_w ->> 'timezone',
                    (v_w ->> 'start_at')::timestamptz, (v_w ->> 'end_at')::timestamptz, (v_w ->> 'weekday')::smallint,
                    (v_w ->> 'start_time')::time, (v_w ->> 'end_time')::time, (v_w ->> 'valid_from')::date,
                    (v_w ->> 'valid_until')::date)
            returning * into t;
        elsif v_change = 'UPDATE' then
            update app_private.time_windows
            set label = v_w ->> 'label', recurrence = v_w ->> 'recurrence', timezone = v_w ->> 'timezone',
                start_at = (v_w ->> 'start_at')::timestamptz, end_at = (v_w ->> 'end_at')::timestamptz,
                weekday = (v_w ->> 'weekday')::smallint, start_time = (v_w ->> 'start_time')::time,
                end_time = (v_w ->> 'end_time')::time, valid_from = (v_w ->> 'valid_from')::date,
                valid_until = (v_w ->> 'valid_until')::date, version = version + 1
            where window_id = t.window_id returning * into t;
        else
            update app_private.time_windows set archived_at = clock_timestamp(), version = version + 1
            where window_id = t.window_id returning * into t;
        end if;
        update app_private.user_profiles set schedule_revision = schedule_revision + 1 where user_id = v_uid;
        v_result := app_private.ok_result(p_request, 'COMMITTED', app_private.window_json(t));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, p_operation, v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
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

create or replace function app_api.set_availability(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v_error jsonb := app_private.precheck(p_request, 'set_availability', 'set_availabilityArguments');
begin
    return coalesce(v_error, app_private.set_window_body(p_request, 'set_availability', 'SET_AVAILABILITY', 'AVAILABILITY'));
end $$;

create or replace function app_api.set_busy_interval(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v_error jsonb := app_private.precheck(p_request, 'set_busy_interval', 'set_busy_intervalArguments');
begin
    return coalesce(v_error, app_private.set_window_body(p_request, 'set_busy_interval', 'SET_BUSY_INTERVAL', 'BUSY'));
end $$;

-- set_scheduling_preferences: merge a patch into the full stored policy; guarded by the schedule revision.
create or replace function app_api.set_scheduling_preferences(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'set_scheduling_preferences', 'set_scheduling_preferencesArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_conv uuid := (p_request #>> '{execution_context,conversation_id}')::uuid;
    v_binding jsonb := app_private.pending_binding(p_request);
    v_fp text;
    v_reply jsonb;
    u app_private.user_profiles;
    v_policy jsonb;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null or v_conv is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key and a conversation are required.');
    end if;
    if v_binding is null then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'A matching approval for the pending action is required.');
    end if;
    v_fp := app_private.domain_fingerprint(v_uid, 'set_scheduling_preferences', v_args, v_binding);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'set_scheduling_preferences', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'set_scheduling_preferences', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        select * into u from app_private.user_profiles where user_id = v_uid;
        if u.schedule_revision <> (v_args ->> 'expected_schedule_revision')::bigint then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The schedule changed since the preferences were read.');
        end if;
        v_policy := app_private.default_policy() || u.scheduling_policy || (v_args -> 'policy_patch');
        if (v_policy ->> 'min_block_minutes')::bigint < 1 or (v_policy ->> 'max_block_minutes')::bigint < (v_policy ->> 'min_block_minutes')::bigint
           or (v_policy ->> 'max_daily_minutes')::bigint < 1 or (v_policy ->> 'break_minutes')::bigint < 0 then
            return app_private.error_result(p_request, 'INVALID_PARAMETER',
                'The merged policy needs min>0, max>=min, daily>0 and break>=0.');
        end if;
        v_error := app_private.consume_pending_approval(p_request, v_uid, 'set_scheduling_preferences',
                                                        'SET_SCHEDULING_PREFERENCES', v_args);
        if v_error is not null then
            return v_error;
        end if;
        update app_private.user_profiles set scheduling_policy = v_policy, schedule_revision = schedule_revision + 1
        where user_id = v_uid returning * into u;
        v_result := app_private.ok_result(p_request, 'COMMITTED', jsonb_build_object(
            'scheduling_policy', u.scheduling_policy, 'schedule_revision', u.schedule_revision));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'set_scheduling_preferences', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
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

-- list_time_windows: read-only keyset listing on (created_at, window_id) with signed cursors.
create or replace function app_api.list_time_windows(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'list_time_windows', 'ListTimeWindowsArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_size int := (v_args ->> 'page_size')::int;
    v_filter jsonb;
    v_pos jsonb;
    v_items jsonb;
    v_more boolean;
    v_last_at text;
    v_last_id text;
    v_next text;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        v_filter := jsonb_build_object('k', v_args -> 'kind', 'a', v_args -> 'include_archived');
        if v_args ->> 'cursor' is not null then
            v_pos := app_private.cursor_decode(v_uid, v_filter, v_args ->> 'cursor');
        end if;
        with page as (
            select x as w, row_number() over (order by x.created_at, x.window_id) rn
            from app_private.time_windows x
            where x.user_id = v_uid
              and (v_args ->> 'kind' is null or x.kind = v_args ->> 'kind')
              and ((v_args ->> 'include_archived')::boolean or x.archived_at is null)
              and (v_pos is null or (x.created_at, x.window_id) > ((v_pos ->> 0)::timestamptz, (v_pos ->> 1)::uuid))
            order by x.created_at, x.window_id limit v_size + 1
        )
        select coalesce(jsonb_agg(app_private.window_json(p.w) order by p.rn) filter (where p.rn <= v_size), '[]'::jsonb),
               max(p.rn) > v_size,
               max(app_private.iso((p.w).created_at)) filter (where p.rn = v_size),
               max(((p.w).window_id)::text) filter (where p.rn = v_size)
        into v_items, v_more, v_last_at, v_last_id from page p;
        if v_more then
            v_next := app_private.cursor_encode(v_uid, v_filter, jsonb_build_array(v_last_at, v_last_id));
        end if;
        return app_private.ok_result(p_request, 'READ', jsonb_build_object('items', v_items, 'next_cursor', v_next));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.default_policy() owner to sf_rpc_owner;
alter function app_private.window_json(app_private.time_windows) owner to sf_rpc_owner;
alter function app_private.validate_window(jsonb, jsonb) owner to sf_rpc_owner;
alter function app_private.pending_binding(jsonb) owner to sf_rpc_owner;
alter function app_private.consume_pending_approval(jsonb, uuid, text, text, jsonb) owner to sf_rpc_owner;
alter function app_private.set_window_body(jsonb, text, text, text) owner to sf_rpc_owner;
revoke all on function app_private.default_policy(), app_private.window_json(app_private.time_windows),
    app_private.validate_window(jsonb, jsonb), app_private.pending_binding(jsonb),
    app_private.consume_pending_approval(jsonb, uuid, text, text, jsonb),
    app_private.set_window_body(jsonb, text, text, text) from public, anon, authenticated;
