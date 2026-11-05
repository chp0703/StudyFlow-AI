-- WP2a / migration 010: canonical JSON and the exact-request attestation verifier.
-- Helpers live in app_private, are owned by sf_rpc_owner and are never executable by clients.

-- Canonical JSON per contracts/README.md 6.2: object keys sorted by Unicode code point
-- (UTF-8 byte order), array order kept, compact, UTF-8 not escaped, safe integers only.
create function app_private.canonical_json(p_value jsonb) returns text
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
    return '{' || coalesce((select string_agg(to_jsonb(e.key)::text || ':' || app_private.canonical_json(e.value),
                                              ',' order by convert_to(e.key, 'UTF8'))
                            from jsonb_each(p_value) e), '') || '}';
end $$;

-- The verified JWT subject, read from the claims PostgREST sets per request. This mirrors
-- auth.uid() without needing sf_rpc_owner to have access to the auth schema.
create function app_private.current_uid() returns uuid
language sql stable set search_path = '' as $$
    select coalesce(
        nullif(current_setting('request.jwt.claim.sub', true), ''),
        nullif(nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub', '')
    )::uuid
$$;

-- Routines that only read; they carry no attestation. Everything else mutates.
create function app_private.rpc_is_read(p_routine text) returns boolean
language sql immutable set search_path = '' as $$
    select p_routine in ('search_tasks', 'get_study_plan', 'get_scheduling_context',
                         'lookup_operation_result', 'list_time_windows',
                         'get_workflow_context', 'get_workflow_continuation')
$$;

-- Verifies the authenticated owner and, for mutations, the HMAC attestation. Returns the
-- verified user id or raises 28000/UNAUTHENTICATED, 42501/FORBIDDEN (22023 for bad numbers).
create function app_private.verify_rpc_request(p_request jsonb, p_routine text) returns uuid
language plpgsql security definer set search_path = '' as $$
declare
    v_uid uuid := app_private.current_uid();
    v_principal text := p_request #>> '{execution_context,trusted_context,principal,user_id}';
    v_att jsonb := p_request -> 'attestation';
    v_key record;
    v_payload_b64 text;
    v_payload_text text;
    v_payload jsonb;
    v_raw json;
    v_expected text;
    v_nonce bytea := extensions.gen_random_bytes(32);
    v_issued timestamptz;
    v_expires timestamptz;
    v_now timestamptz := clock_timestamp();
begin
    if v_uid is null then
        raise exception using errcode = '28000', message = 'UNAUTHENTICATED';
    end if;
    if jsonb_typeof(p_request) is distinct from 'object'
       or p_request ->> 'contract_version' is distinct from '1.0.1'
       or p_request ->> 'schema_version' is distinct from '1.1'
       or v_principal is distinct from v_uid::text then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;

    if app_private.rpc_is_read(p_routine) then
        if v_att is distinct from 'null'::jsonb and v_att is not null then
            raise exception using errcode = '42501', message = 'FORBIDDEN';
        end if;
        return v_uid;
    end if;

    -- Mutations: exact attestation object, never a bare flag from the caller.
    if jsonb_typeof(v_att) is distinct from 'object'
       or (select array_agg(k order by k) from jsonb_object_keys(v_att) k)
          is distinct from array['key_id', 'payload', 'signature']
       or jsonb_typeof(v_att -> 'key_id') is distinct from 'string'
       or jsonb_typeof(v_att -> 'payload') is distinct from 'string'
       or (v_att ->> 'signature') !~ '^[a-f0-9]{64}$' then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;

    select k.key_id, k.key_material into v_key
    from app_private.rpc_attestation_keys k
    where k.key_id = v_att ->> 'key_id' and k.not_before <= v_now and k.not_after > v_now;
    if not found then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;

    -- The signature covers the ASCII base64url text, so verify it before decoding anything.
    v_payload_b64 := v_att ->> 'payload';
    v_expected := encode(extensions.hmac(convert_to(v_payload_b64, 'UTF8'), v_key.key_material, 'sha256'), 'hex');
    if extensions.hmac(convert_to(v_expected, 'UTF8'), v_nonce, 'sha256')
       is distinct from extensions.hmac(convert_to(v_att ->> 'signature', 'UTF8'), v_nonce, 'sha256') then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;

    begin
        if v_payload_b64 !~ '^[A-Za-z0-9_-]+$' then
            raise exception using errcode = '22023', message = 'bad payload';
        end if;
        v_payload_text := convert_from(
            decode(translate(v_payload_b64, '-_', '+/') || repeat('=', (4 - length(v_payload_b64) % 4) % 4), 'base64'),
            'UTF8');
        -- Duplicate keys vanish when coerced to jsonb, so inspect the raw JSON text first.
        v_raw := v_payload_text::json;
        if jsonb_typeof(v_raw::jsonb) is distinct from 'object'
           or (select count(*) <> count(distinct t.key) from json_each(v_raw) t) then
            raise exception using errcode = '22023', message = 'bad payload';
        end if;
        v_payload := v_raw::jsonb;
        v_issued := (v_payload ->> 'issued_at')::timestamptz;
        v_expires := (v_payload ->> 'expires_at')::timestamptz;
    exception when others then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end;

    if (select array_agg(k order by k) from jsonb_object_keys(v_payload) k)
           is distinct from array['expires_at', 'issued_at', 'key_id', 'request_digest',
                                  'request_id', 'rpc', 'user_id', 'v']
       or v_payload -> 'v' is distinct from '1'::jsonb
       or v_payload ->> 'key_id' is distinct from v_key.key_id
       or v_payload ->> 'user_id' is distinct from v_uid::text
       or v_payload ->> 'rpc' is distinct from p_routine
       or v_payload ->> 'request_id' is distinct from p_request ->> 'request_id'
       or v_payload ->> 'issued_at' !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$'
       or v_payload ->> 'expires_at' !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$'
       or v_expires is distinct from v_issued + interval '60 seconds'
       or v_issued > v_now + interval '5 seconds'
       or v_expires <= v_now then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;

    if v_payload ->> 'request_digest' is distinct from
       encode(extensions.digest(convert_to(app_private.canonical_json(p_request - 'attestation'), 'UTF8'),
                                'sha256'), 'hex') then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;
    return v_uid;
end $$;

-- Builds the declared ErrorResult envelope for a request.
create function app_private.error_result(p_request jsonb, p_code text, p_message text,
                                         p_retryable boolean default false) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object(
        'schema_version', '1.1',
        'request_id', coalesce(nullif(btrim(p_request ->> 'request_id'), ''), 'unknown'),
        'outcome', 'ERROR', 'data', null,
        'error', jsonb_build_object('code', p_code, 'message', p_message, 'field', null,
                                    'details', '{}'::jsonb, 'retryable', p_retryable),
        'warnings', '[]'::jsonb)
$$;

-- Runs the verifier and converts a security failure into the typed ErrorResult, or null.
create function app_private.security_error(p_request jsonb, p_routine text) returns jsonb
language plpgsql security definer set search_path = '' as $$
begin
    perform app_private.verify_rpc_request(p_request, p_routine);
    return null;
exception
    when sqlstate '28000' then
        return app_private.error_result(p_request, 'UNAUTHENTICATED', 'Authentication is required.');
    when sqlstate '42501' then
        return app_private.error_result(p_request, 'FORBIDDEN', 'The request is not authorized.');
    when sqlstate '22023' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The request contains an unsupported value.');
end $$;

alter function app_private.current_uid() owner to sf_rpc_owner;
alter function app_private.canonical_json(jsonb) owner to sf_rpc_owner;
alter function app_private.rpc_is_read(text) owner to sf_rpc_owner;
alter function app_private.verify_rpc_request(jsonb, text) owner to sf_rpc_owner;
alter function app_private.error_result(jsonb, text, text, boolean) owner to sf_rpc_owner;
alter function app_private.security_error(jsonb, text) owner to sf_rpc_owner;
revoke all on function app_private.current_uid(), app_private.canonical_json(jsonb), app_private.rpc_is_read(text),
    app_private.verify_rpc_request(jsonb, text), app_private.error_result(jsonb, text, text, boolean),
    app_private.security_error(jsonb, text) from public, anon, authenticated;
