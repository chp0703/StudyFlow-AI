-- WP2b-1 / migration 013: shared wrapper helpers, signed bootstrap, source messages and
-- API receipt leases (ensure_user_context, record_source_message, claim/renew/release/complete).
-- Replaces four of the fail-closed stubs from migration 011; the rest stay fail-closed.

-- A receipt allocates stable message/action IDs at claim time, before the message or action
-- exists, so those columns cannot be foreign keys.
alter table app_private.api_request_receipts drop constraint fk_receipts_message_owner;
alter table app_private.api_request_receipts drop constraint fk_receipts_action_owner;

-- API timestamp format: UTC with microseconds.
create function app_private.iso(p_value timestamptz) returns text
language sql immutable set search_path = '' as $$
    select to_char(p_value at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
$$;

create function app_private.ok_result(p_request jsonb, p_outcome text, p_data jsonb,
                                      p_warnings jsonb default '[]'::jsonb) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('schema_version', '1.1',
        'request_id', coalesce(nullif(btrim(p_request ->> 'request_id'), ''), 'unknown'),
        'outcome', p_outcome, 'data', p_data, 'error', null, 'warnings', p_warnings)
$$;

-- Unexpected SQL failures never leak details: bad input is INVALID_PARAMETER, the rest INTERNAL_ERROR.
create function app_private.failure(p_request jsonb, p_sqlstate text) returns jsonb
language sql immutable set search_path = '' as $$
    select case when p_sqlstate in ('22023', '22P02', '22007', '22008')
        then app_private.error_result(p_request, 'INVALID_PARAMETER', 'The request contains an invalid value.')
        else app_private.error_result(p_request, 'INTERNAL_ERROR', 'The request could not be completed.') end
$$;

-- Common wrapper preamble: security verification, operation binding and exact shape checks.
-- Returns the ErrorResult to hand back, or null when the request may proceed.
create function app_private.precheck(p_request jsonb, p_routine text, p_arguments_def text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare v_error jsonb := app_private.security_error(p_request, p_routine);
begin
    if v_error is not null then
        return v_error;
    end if;
    if p_request ->> 'operation' is distinct from p_routine
       or not app_private.matches_contract('RpcEnvelope', p_request)
       or not app_private.matches_contract(p_arguments_def, p_request -> 'arguments') then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The request does not match the approved contract.');
    end if;
    return null;
end $$;

-- Creates the owner's profile when absent (trusted context defaults) and takes the owner row lock.
create function app_private.lock_owner(p_uid uuid, p_request jsonb, p_timezone text default null) returns void
language plpgsql security definer set search_path = '' as $$
declare
    v_tz text;
    v_locale text := coalesce(nullif(btrim(p_request #>> '{execution_context,trusted_context,locale}'), ''), 'vi');
begin
    select n.name into v_tz from pg_catalog.pg_timezone_names n
    where n.name = coalesce(p_timezone, p_request #>> '{execution_context,trusted_context,timezone}') limit 1;
    insert into app_private.user_profiles (user_id, timezone, locale, scheduling_policy)
    values (p_uid, coalesce(v_tz, 'Asia/Ho_Chi_Minh'), v_locale,
            '{"min_block_minutes":25,"max_block_minutes":90,"allow_short_final_block":true,"max_daily_minutes":240,"break_minutes":10}'::jsonb)
    on conflict (user_id) do nothing;
    perform 1 from app_private.user_profiles where user_id = p_uid for update;
end $$;

create function app_private.user_json(p_user app_private.user_profiles) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('user_id', p_user.user_id, 'timezone', p_user.timezone, 'locale', p_user.locale,
        'current_plan_id', p_user.current_plan_id, 'schedule_revision', p_user.schedule_revision,
        'scheduling_policy', p_user.scheduling_policy,
        'created_at', app_private.iso(p_user.created_at), 'updated_at', app_private.iso(p_user.updated_at))
$$;

create function app_private.receipt_json(p_receipt app_private.api_request_receipts) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('user_id', p_receipt.user_id, 'http_operation', p_receipt.http_operation,
        'idempotency_key', p_receipt.idempotency_key, 'request_fingerprint', p_receipt.request_fingerprint,
        'state', p_receipt.state, 'lease_version', p_receipt.lease_version,
        'lease_until', case when p_receipt.lease_until is null then null else app_private.iso(p_receipt.lease_until) end,
        'message_id', p_receipt.message_id, 'action_id', p_receipt.action_id,
        'http_status', p_receipt.http_status, 'response', p_receipt.response,
        'created_at', app_private.iso(p_receipt.created_at), 'updated_at', app_private.iso(p_receipt.updated_at))
$$;

-- ensure_user_context: signed bootstrap. Never overwrites or bumps an existing profile.
create or replace function app_api.ensure_user_context(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'ensure_user_context', 'EnsureUserContextArguments');
    v_uid uuid;
    v_user app_private.user_profiles;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into v_user from app_private.user_profiles where user_id = v_uid;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.user_json(v_user));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- record_source_message: persists the trusted original message (and its conversation) once.
create or replace function app_api.record_source_message(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'record_source_message', 'RecordSourceMessageArguments');
    v_uid uuid;
    v_msg jsonb := p_request #> '{arguments,message}';
    v_existing app_private.source_messages;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    -- The message must belong to the verified owner, the request conversation and the trusted message ID.
    if v_msg ->> 'user_id' is distinct from v_uid::text
       or v_msg ->> 'conversation_id' is distinct from p_request #>> '{execution_context,conversation_id}'
       or v_msg ->> 'message_id' is distinct from p_request #>> '{execution_context,trusted_context,message_id}' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER',
            'The message does not match the authenticated owner, conversation or trusted message.');
    end if;
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into v_existing from app_private.source_messages where message_id = (v_msg ->> 'message_id')::uuid;
        if found then
            if (v_existing.user_id, v_existing.conversation_id, v_existing.source, v_existing.role, v_existing.text,
                v_existing.received_at)
               is distinct from (v_uid, (v_msg ->> 'conversation_id')::uuid, v_msg ->> 'source', v_msg ->> 'role',
                                 v_msg ->> 'text', (v_msg ->> 'received_at')::timestamptz) then
                return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT',
                    'The message ID was already recorded with different content.');
            end if;
        else
            insert into app_private.conversation_records (user_id, conversation_id)
            values (v_uid, (v_msg ->> 'conversation_id')::uuid) on conflict do nothing;
            insert into app_private.source_messages (message_id, user_id, conversation_id, source, role, text, received_at)
            values ((v_msg ->> 'message_id')::uuid, v_uid, (v_msg ->> 'conversation_id')::uuid,
                    v_msg ->> 'source', v_msg ->> 'role', v_msg ->> 'text', (v_msg ->> 'received_at')::timestamptz)
            returning * into v_existing;
        end if;
        return app_private.ok_result(p_request, 'COMMITTED', jsonb_build_object(
            'message_id', v_existing.message_id, 'user_id', v_existing.user_id,
            'conversation_id', v_existing.conversation_id, 'source', v_existing.source, 'role', v_existing.role,
            'text', v_existing.text, 'received_at', app_private.iso(v_existing.received_at)));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- claim_api_receipt: first claim allocates stable IDs and a 120 s lease; a live lease is busy;
-- an expired one is reclaimed with a higher lease_version; a completed one replays.
create or replace function app_api.claim_api_receipt(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'claim_api_receipt', 'ClaimApiReceiptArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_now timestamptz := clock_timestamp();
    r app_private.api_request_receipts;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if p_request #>> '{execution_context,conversation_id}' is distinct from v_args ->> 'conversation_id' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The conversation does not match the request context.');
    end if;
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into r from app_private.api_request_receipts
        where user_id = v_uid and http_operation = v_args ->> 'http_operation'
          and idempotency_key = v_args ->> 'idempotency_key';
        if not found then
            insert into app_private.api_request_receipts
                (user_id, http_operation, idempotency_key, request_fingerprint, state, lease_version,
                 lease_until, message_id, action_id)
            values (v_uid, v_args ->> 'http_operation', v_args ->> 'idempotency_key',
                    v_args ->> 'request_fingerprint', 'IN_PROGRESS', 1, v_now + interval '120 seconds',
                    extensions.gen_random_uuid(),
                    case when v_args ->> 'http_operation' in ('send_message', 'prepare_action')
                         then extensions.gen_random_uuid() end)
            returning * into r;
        elsif r.request_fingerprint <> v_args ->> 'request_fingerprint' then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT',
                'The idempotency key was already used with a different request.');
        elsif r.state = 'IN_PROGRESS' then
            if r.lease_until > v_now then
                return app_private.error_result(p_request, 'SERVICE_UNAVAILABLE',
                    'The same request is still being processed.', true);
            end if;
            update app_private.api_request_receipts
            set lease_version = lease_version + 1, lease_until = v_now + interval '120 seconds'
            where user_id = r.user_id and http_operation = r.http_operation and idempotency_key = r.idempotency_key
            returning * into r;
        end if;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.receipt_json(r));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

create or replace function app_api.renew_api_receipt(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'renew_api_receipt', 'ApiReceiptLeaseArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_now timestamptz := clock_timestamp();
    r app_private.api_request_receipts;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into r from app_private.api_request_receipts
        where user_id = v_uid and http_operation = v_args ->> 'http_operation'
          and idempotency_key = v_args ->> 'idempotency_key';
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The API receipt was not found.');
        elsif r.request_fingerprint <> v_args ->> 'request_fingerprint' then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'The receipt belongs to a different request.');
        elsif r.state <> 'IN_PROGRESS' or r.lease_version <> (v_args ->> 'expected_lease_version')::bigint
              or r.lease_until <= v_now then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The receipt lease is no longer held.');
        end if;
        update app_private.api_request_receipts set lease_until = v_now + interval '120 seconds'
        where user_id = r.user_id and http_operation = r.http_operation and idempotency_key = r.idempotency_key
        returning * into r;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.receipt_json(r));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- release: hands the lease back immediately (retryable failure); the next claim reclaims it.
create or replace function app_api.release_api_receipt(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'release_api_receipt', 'ApiReceiptLeaseArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    r app_private.api_request_receipts;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into r from app_private.api_request_receipts
        where user_id = v_uid and http_operation = v_args ->> 'http_operation'
          and idempotency_key = v_args ->> 'idempotency_key';
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The API receipt was not found.');
        elsif r.request_fingerprint <> v_args ->> 'request_fingerprint' then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'The receipt belongs to a different request.');
        elsif r.state <> 'IN_PROGRESS' or r.lease_version <> (v_args ->> 'expected_lease_version')::bigint then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The receipt lease is no longer held.');
        end if;
        update app_private.api_request_receipts set lease_until = clock_timestamp()
        where user_id = r.user_id and http_operation = r.http_operation and idempotency_key = r.idempotency_key
        returning * into r;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.receipt_json(r));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- complete: only the current lease holder stores the terminal response. Transient 429/503
-- results are never cached as terminal (release the lease instead).
create or replace function app_api.complete_api_receipt(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'complete_api_receipt', 'CompleteApiReceiptArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    r app_private.api_request_receipts;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if (v_args ->> 'http_status')::bigint in (429, 503) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER',
            'Transient 429/503 results must release the receipt, not complete it.');
    end if;
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into r from app_private.api_request_receipts
        where user_id = v_uid and http_operation = v_args ->> 'http_operation'
          and idempotency_key = v_args ->> 'idempotency_key';
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The API receipt was not found.');
        elsif r.request_fingerprint <> v_args ->> 'request_fingerprint' then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'The receipt belongs to a different request.');
        elsif r.lease_version <> (v_args ->> 'expected_lease_version')::bigint then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The receipt lease is no longer held.');
        elsif r.state = 'COMPLETED' then
            if r.response is distinct from v_args -> 'response' or r.http_status <> (v_args ->> 'http_status')::bigint then
                return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'The receipt was completed with a different response.');
            end if;
        else
            update app_private.api_request_receipts
            set state = 'COMPLETED', lease_until = null, http_status = (v_args ->> 'http_status')::bigint,
                response = v_args -> 'response'
            where user_id = r.user_id and http_operation = r.http_operation and idempotency_key = r.idempotency_key
            returning * into r;
        end if;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.receipt_json(r));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- Ownership and grants for the helpers; only the wrappers (owned by sf_rpc_owner) call them.
alter function app_private.iso(timestamptz) owner to sf_rpc_owner;
alter function app_private.ok_result(jsonb, text, jsonb, jsonb) owner to sf_rpc_owner;
alter function app_private.failure(jsonb, text) owner to sf_rpc_owner;
alter function app_private.precheck(jsonb, text, text) owner to sf_rpc_owner;
alter function app_private.lock_owner(uuid, jsonb, text) owner to sf_rpc_owner;
alter function app_private.user_json(app_private.user_profiles) owner to sf_rpc_owner;
alter function app_private.receipt_json(app_private.api_request_receipts) owner to sf_rpc_owner;
revoke all on function app_private.iso(timestamptz), app_private.ok_result(jsonb, text, jsonb, jsonb),
    app_private.failure(jsonb, text), app_private.precheck(jsonb, text, text),
    app_private.lock_owner(uuid, jsonb, text), app_private.user_json(app_private.user_profiles),
    app_private.receipt_json(app_private.api_request_receipts) from public, anon, authenticated;
