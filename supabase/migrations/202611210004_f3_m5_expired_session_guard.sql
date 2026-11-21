-- F3 M5: an expired session must not accept writes before the lazy purge removes it; otherwise a new turn
-- would extend expires_at and revive the old history. Body copied from 202611200013 plus the expiry guard.
create or replace function app_api.append_learning_turn(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'append_learning_turn', 'AppendLearningTurnArguments');
    args jsonb := p_request -> 'arguments';
    uid uuid := app_private.current_uid();
    key text := p_request #>> '{execution_context,idempotency_key}';
    v_session_id uuid;
    fingerprint text;
    receipt app_private.learning_session_receipts;
    v_session app_private.learning_session;
    v_last_ordinal bigint;
    v_kind text;
    v_hint_level integer;
    v_supported boolean;
    v_citations jsonb;
    v_item jsonb;
    v_cit_mat uuid;
    v_cit_chunk uuid;
    v_cit_page integer;
    v_user_turn app_private.learning_turn;
    v_assistant_turn app_private.learning_turn;
    v_pair jsonb;
begin
    if err is not null then return err; end if;
    if key is null or key !~ '^[A-Za-z0-9._:-]{16,128}$' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'A valid idempotency key is required.');
    end if;

    v_session_id := (args ->> 'session_id')::uuid;
    fingerprint := args ->> 'fingerprint';
    v_kind := args ->> 'kind';
    v_hint_level := (args ->> 'hint_level')::integer;
    v_supported := (args ->> 'supported')::boolean;
    v_citations := args -> 'citations';

    if (v_kind = 'ASK' and v_hint_level is not null)
       or (v_kind = 'HINT' and (v_hint_level is null or v_hint_level not between 1 and 3))
       or (v_supported and jsonb_array_length(v_citations) < 1)
       or (not v_supported and jsonb_array_length(v_citations) > 0) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Turn invariants violated.');
    end if;

    perform app_private.lock_owner(uid, p_request);

    select r.* into receipt from app_private.learning_session_receipts r
    where r.user_id = uid and r.operation = 'add_turn' and r.idempotency_key = key;
    if found then
        if receipt.fingerprint <> fingerprint or receipt.session_id <> v_session_id then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'Turn key was used for a different request.');
        end if;
        return app_private.ok_result(p_request, 'COMMITTED',
            receipt.response || jsonb_build_object('replayed', true));
    end if;

    select s.* into v_session from app_private.learning_session s
    where s.user_id = uid and s.session_id = v_session_id
    for update;
    if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Learning session not found.');
    end if;
    if v_session.status <> 'ACTIVE' then
        err := app_private.error_result(p_request, 'TIME_CONFLICT', 'Phiên học không còn ở trạng thái hoạt động.');
        return jsonb_set(err, '{error,details}', jsonb_build_object('status', v_session.status));
    end if;
    if v_session.expires_at <= clock_timestamp() then
        err := app_private.error_result(p_request, 'TIME_CONFLICT', 'Phiên học đã hết hạn lưu giữ.');
        return jsonb_set(err, '{error,details}', '{"reason":"SESSION_EXPIRED"}'::jsonb);
    end if;

    select coalesce(max(t.ordinal), 0) into v_last_ordinal
    from app_private.learning_turn t
    where t.user_id = uid and t.session_id = v_session_id;
    if v_last_ordinal <> (args ->> 'expected_last_ordinal')::bigint then
        return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Phiên học đã có lượt mới, hãy thử lại.', true);
    end if;

    -- Validate citations before any write: all cited materials must belong to this session and match indexed chunks.
    if (select count(distinct (c ->> 'chunk_id')::uuid) from jsonb_array_elements(v_citations) c)
       <> jsonb_array_length(v_citations) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Duplicate citation chunk_id.');
    end if;
    for v_item in select value from jsonb_array_elements(v_citations) loop
        v_cit_mat := (v_item ->> 'material_id')::uuid;
        v_cit_chunk := (v_item ->> 'chunk_id')::uuid;
        v_cit_page := (v_item ->> 'page')::integer;
        if not (v_cit_mat = any(v_session.material_ids)) then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Citation material is not in the session.');
        end if;
        if exists (select 1 from app_private.materials m where m.user_id = uid and m.material_id = v_cit_mat)
           and not exists (
               select 1 from app_private.material_chunks c
               where c.user_id = uid and c.material_id = v_cit_mat and c.chunk_id = v_cit_chunk
                 and c.page = v_cit_page and c.learning_ordinal is not null
           ) then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Citation chunk does not match indexed material.');
        end if;
    end loop;

    insert into app_private.learning_turn(
        user_id, session_id, ordinal, role, kind, hint_level, content, citations, supported, model, prompt_version
    ) values (
        uid, v_session_id, v_last_ordinal + 1, 'USER', v_kind, null, args ->> 'user_content',
        '[]'::jsonb, null, null, null
    ) returning * into v_user_turn;

    insert into app_private.learning_turn(
        user_id, session_id, ordinal, role, kind, hint_level, content, citations, supported, model, prompt_version
    ) values (
        uid, v_session_id, v_last_ordinal + 2, 'ASSISTANT', v_kind, v_hint_level, args ->> 'assistant_content',
        v_citations, v_supported, args ->> 'model', args ->> 'prompt_version'
    ) returning * into v_assistant_turn;

    update app_private.learning_session
       set version = version + 1,
           expires_at = greatest(expires_at, clock_timestamp() + interval '30 days')
     where user_id = uid and session_id = v_session_id;

    v_pair := jsonb_build_object(
        'user_turn', app_private.learning_turn_json(v_user_turn),
        'assistant_turn', app_private.learning_turn_json(v_assistant_turn)
    );

    insert into app_private.learning_session_receipts(user_id, operation, idempotency_key, fingerprint, session_id, response)
    values (uid, 'add_turn', key, fingerprint, v_session_id, v_pair);

    return app_private.ok_result(p_request, 'COMMITTED', v_pair || jsonb_build_object('replayed', false));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

alter function app_api.append_learning_turn(jsonb) owner to sf_rpc_owner;
revoke all on function app_api.append_learning_turn(jsonb) from public, anon;
grant execute on function app_api.append_learning_turn(jsonb) to authenticated;
