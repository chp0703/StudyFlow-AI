-- WP2b-2 / migration 014: domain idempotency, create_task_candidate, update_candidate_draft
-- and lookup_operation_result. Candidates are drafts: they never change schedule_revision.

-- Fingerprint = SHA256(canonical {schema_version, user_id, operation, arguments, decision_binding}).
-- It never contains request_id, clocks, signatures or newly generated IDs.
create function app_private.domain_fingerprint(p_user uuid, p_operation text, p_arguments jsonb,
                                               p_binding jsonb default null) returns text
language sql immutable set search_path = '' as $$
    select encode(extensions.digest(convert_to(app_private.canonical_json(jsonb_build_object(
        'schema_version', '1.1', 'user_id', p_user, 'operation', p_operation,
        'arguments', p_arguments, 'decision_binding', p_binding)), 'UTF8'), 'sha256'), 'hex')
$$;

-- Replays a stored domain result for a new request, or reports a conflicting/busy key.
-- Returns null when there is no record for the key.
create function app_private.idempotent_reply(p_request jsonb, p_user uuid, p_operation text,
                                             p_key text, p_fingerprint text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare r app_private.idempotency_records;
begin
    select * into r from app_private.idempotency_records
    where user_id = p_user and operation = p_operation and idempotency_key = p_key;
    if not found then
        return null;
    elsif r.request_fingerprint <> p_fingerprint then
        return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT',
            'The idempotency key was already used with a different request.');
    elsif r.state <> 'COMPLETED' then
        return app_private.error_result(p_request, 'SERVICE_UNAVAILABLE', 'The same request is still being processed.', true);
    end if;
    return jsonb_set(r.result_reference_or_response, '{request_id}',
                     to_jsonb(coalesce(nullif(btrim(p_request ->> 'request_id'), ''), 'unknown')));
end $$;

create function app_private.candidate_json(p_candidate app_private.task_candidates) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('candidate_id', p_candidate.candidate_id, 'user_id', p_candidate.user_id,
        'conversation_id', p_candidate.conversation_id, 'version', p_candidate.version,
        'status', p_candidate.status, 'slots', p_candidate.slots, 'raw_expressions', p_candidate.raw_expressions,
        'field_sources', p_candidate.field_sources, 'source_message_id', p_candidate.source_message_id,
        'confirmed_task_id', p_candidate.confirmed_task_id,
        'created_at', app_private.iso(p_candidate.created_at), 'updated_at', app_private.iso(p_candidate.updated_at))
$$;

create or replace function app_api.create_task_candidate(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'create_task_candidate', 'create_task_candidateArguments');
    v_uid uuid;
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_conv uuid := (p_request #>> '{execution_context,conversation_id}')::uuid;
    v_msg uuid := (p_request #>> '{execution_context,trusted_context,message_id}')::uuid;
    v_slots jsonb := p_request #> '{arguments,slots}';
    v_fp text;
    v_reply jsonb;
    v_candidate app_private.task_candidates;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null or v_conv is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER',
            'An idempotency key and a conversation are required.', false);
    end if;
    v_fp := app_private.domain_fingerprint(v_uid, 'create_task_candidate', p_request -> 'arguments');
    begin
        -- Fast lookup, owner lock, then lookup again: a racing twin may have committed meanwhile.
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'create_task_candidate', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'create_task_candidate', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        if not exists (select 1 from app_private.source_messages
                       where message_id = v_msg and user_id = v_uid and conversation_id = v_conv) then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND',
                'The source message was not recorded for this conversation.');
        end if;
        insert into app_private.task_candidates
            (candidate_id, user_id, conversation_id, status, slots, raw_expressions, field_sources, source_message_id)
        values (extensions.gen_random_uuid(), v_uid, v_conv, 'DRAFT', v_slots, '{}'::jsonb,
                coalesce((select jsonb_object_agg(s.key, jsonb_build_object('source', 'USER_MESSAGE', 'reference', v_msg::text))
                          from jsonb_each(v_slots) s where s.value <> 'null'::jsonb), '{}'::jsonb), v_msg)
        returning * into v_candidate;
        v_result := app_private.ok_result(p_request, 'DRAFTED', app_private.candidate_json(v_candidate));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'create_task_candidate', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- update_candidate_draft: versioned edit of a DRAFT candidate. A retry that finds exactly the
-- requested content one version ahead is a replay, so a lost response never double-bumps.
create or replace function app_api.update_candidate_draft(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'update_candidate_draft', 'UpdateCandidateDraftArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    c app_private.task_candidates;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into c from app_private.task_candidates
        where user_id = v_uid and candidate_id = (v_args ->> 'candidate_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The candidate was not found.');
        end if;
        if c.version = (v_args ->> 'expected_candidate_version')::bigint + 1 and c.status = 'DRAFT'
           and (c.slots, c.raw_expressions, c.field_sources)
               is not distinct from (v_args -> 'slots', v_args -> 'raw_expressions', v_args -> 'field_sources') then
            return app_private.ok_result(p_request, 'COMMITTED', app_private.candidate_json(c));
        end if;
        if c.status <> 'DRAFT' or c.version <> (v_args ->> 'expected_candidate_version')::bigint then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The candidate changed since it was read.');
        end if;
        update app_private.task_candidates
        set slots = v_args -> 'slots', raw_expressions = v_args -> 'raw_expressions',
            field_sources = v_args -> 'field_sources', version = version + 1
        where candidate_id = c.candidate_id returning * into c;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.candidate_json(c));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- lookup_operation_result: read-only view of a stored domain result for the owner.
create or replace function app_api.lookup_operation_result(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'lookup_operation_result', 'LookupOperationResultArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_reply jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, v_args ->> 'operation',
                                                v_args ->> 'idempotency_key', v_args ->> 'request_fingerprint');
        if v_reply is not null and v_reply ->> 'outcome' = 'ERROR' and v_reply #>> '{error,code}' = 'IDEMPOTENCY_CONFLICT' then
            return v_reply;
        end if;
        if v_reply is not null and v_reply ->> 'outcome' = 'ERROR' then
            v_reply := null;
        end if;
        return app_private.ok_result(p_request, 'READ', jsonb_build_object('result', v_reply));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.domain_fingerprint(uuid, text, jsonb, jsonb) owner to sf_rpc_owner;
alter function app_private.idempotent_reply(jsonb, uuid, text, text, text) owner to sf_rpc_owner;
alter function app_private.candidate_json(app_private.task_candidates) owner to sf_rpc_owner;
revoke all on function app_private.domain_fingerprint(uuid, text, jsonb, jsonb),
    app_private.idempotent_reply(jsonb, uuid, text, text, text),
    app_private.candidate_json(app_private.task_candidates) from public, anon, authenticated;
