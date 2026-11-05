-- WP2c-4 / migration 021: window and policy changes warn when approved future blocks may be affected.
-- Conservative: every future block of the current plan is listed, because the change is not matched
-- against recurring windows here. The user (or a replan) decides what actually conflicts.

create function app_private.affected_blocks_warning(p_uid uuid, p_what text) returns jsonb
language sql stable security definer set search_path = '' as $$
    select coalesce((select jsonb_build_array(jsonb_build_object('code', 'APPROVED_BLOCKS_MAY_BE_AFFECTED',
        'message', 'This ' || p_what || ' change may affect approved study blocks; review or regenerate the plan.',
        'field', null, 'details', jsonb_build_object('plan_id', x.plan_id, 'block_ids', x.ids)))
        from (select b.plan_id, jsonb_agg(b.block_id order by b.start_at, b.block_id) ids
              from app_private.study_blocks b join app_private.user_profiles u
                on u.user_id = b.user_id and u.current_plan_id = b.plan_id
              where b.user_id = p_uid and b.end_at > clock_timestamp() group by b.plan_id) x), '[]'::jsonb)
$$;
alter function app_private.affected_blocks_warning(uuid, text) owner to sf_rpc_owner;
revoke all on function app_private.affected_blocks_warning(uuid, text) from public, anon, authenticated;

create or replace function app_private.set_window_body(p_request jsonb, p_operation text, p_intent text, p_kind text) returns jsonb
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
        v_result := app_private.ok_result(p_request, 'COMMITTED', app_private.window_json(t),
            case when (p_kind = 'AVAILABILITY' and v_change in ('UPDATE', 'ARCHIVE'))
                      or (p_kind = 'BUSY' and v_change in ('ADD', 'UPDATE'))
                 then app_private.affected_blocks_warning(v_uid, 'time window') else '[]'::jsonb end);
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
            'scheduling_policy', u.scheduling_policy, 'schedule_revision', u.schedule_revision),
            app_private.affected_blocks_warning(v_uid, 'scheduling policy'));
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
