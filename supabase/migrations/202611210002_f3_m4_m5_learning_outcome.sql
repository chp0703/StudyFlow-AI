-- F3 M4 + M5: session summary -> pending save_session_outcome -> UI decision, plus 30-day retention purge.
-- A SessionOutcome is created only by decide_learning_session_outcome with an unmodified action reference.

alter table app_private.learning_session_receipts
    drop constraint learning_session_receipts_operation_check,
    add constraint learning_session_receipts_operation_check
        check (operation in ('create_session', 'add_turn', 'summary'));

grant delete on app_private.learning_session, app_private.learning_turn, app_private.learning_session_receipts
    to sf_rpc_owner;
grant insert on app_private.session_outcome to sf_rpc_owner;

create index ix_learning_session_expiry on app_private.learning_session (user_id, expires_at);

create function app_private.session_outcome_json(o app_private.session_outcome) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object(
        'outcome_id', o.outcome_id,
        'session_id', o.session_id,
        'owner_id', o.user_id,
        'summary', o.summary,
        'topics', to_jsonb(o.topics),
        'duration_minutes', o.duration_minutes,
        'confirmed_at', app_private.iso(o.confirmed_at)
    )
$$;

-- Stores the model draft (summary, topics) as a server-issued pending action. Duration comes from turn
-- timestamps, never from the model.
create function app_api.prepare_learning_summary(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'prepare_learning_summary', 'PrepareLearningSummaryArguments');
    args jsonb := p_request -> 'arguments';
    uid uuid := app_private.current_uid();
    key text := p_request #>> '{execution_context,idempotency_key}';
    v_session_id uuid := (args ->> 'session_id')::uuid;
    receipt app_private.learning_session_receipts;
    v_session app_private.learning_session;
    v_action app_private.pending_actions;
    v_first timestamptz;
    v_last timestamptz;
    v_draft jsonb;
    v_ref jsonb;
    v_data jsonb;
    v_now timestamptz := clock_timestamp();
begin
    if err is not null then return err; end if;
    if key is null or key !~ '^[A-Za-z0-9._:-]{16,128}$' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'A valid idempotency key is required.');
    end if;
    if (select count(distinct t) from jsonb_array_elements_text(args -> 'topics') t)
       <> jsonb_array_length(args -> 'topics') then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Topics must be unique.');
    end if;

    perform app_private.lock_owner(uid, p_request);

    select r.* into receipt from app_private.learning_session_receipts r
    where r.user_id = uid and r.operation = 'summary' and r.idempotency_key = key;
    if found then
        if receipt.fingerprint <> args ->> 'fingerprint' or receipt.session_id <> v_session_id then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'Summary key was used for a different request.');
        end if;
        return app_private.ok_result(p_request, 'DRAFTED', receipt.response || jsonb_build_object('replayed', true));
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
    if v_session.version <> (args ->> 'expected_session_version')::bigint then
        return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Phiên học đã thay đổi, hãy tạo lại bản tóm tắt.', true);
    end if;

    select min(t.created_at), max(t.created_at) into v_first, v_last
    from app_private.learning_turn t
    where t.user_id = uid and t.session_id = v_session_id;
    if v_first is null then
        err := app_private.error_result(p_request, 'TIME_CONFLICT', 'Phiên học chưa có lượt hỏi đáp để tóm tắt.');
        return jsonb_set(err, '{error,details}', '{"reason":"NO_TURNS"}'::jsonb);
    end if;

    v_draft := jsonb_build_object(
        'summary', args ->> 'summary',
        'topics', args -> 'topics',
        'duration_minutes', ceil(extract(epoch from (v_last - v_first)) / 60)::bigint
    );

    update app_private.learning_session
       set status = 'SUMMARY_PENDING', version = version + 1
     where user_id = uid and session_id = v_session_id
    returning * into v_session;

    insert into app_private.pending_actions (
        action_id, user_id, conversation_id, version, intent, state, requires_review, candidate_id, proposal_id,
        draft_arguments, missing_fields, ambiguities, depends_on_action_id, created_at, updated_at
    ) values (
        extensions.gen_random_uuid(), uid, v_session.conversation_id, 1, 'SAVE_SESSION_OUTCOME', 'AWAITING_APPROVAL',
        false, null, null,
        v_draft || jsonb_build_object('session_id', v_session_id, 'session_version', v_session.version),
        '[]'::jsonb, '[]'::jsonb, null, v_now, v_now
    ) returning * into v_action;

    err := app_private.store_presentation(p_request, uid, v_action, jsonb_build_object(
        'kind', 'ACTION_PRESENTATION', 'pending_action', app_private.pending_json(v_action), 'candidate', null,
        'proposal', null, 'normalized_command', null, 'effective_policy', null, 'schedule_confirmation', null
    ));
    if err is not null then
        raise exception 'store_presentation_failed: %', err::text;
    end if;

    v_ref := jsonb_build_object('action_id', v_action.action_id, 'action_version', v_action.version,
                                'target_type', 'PENDING_ACTION', 'target_id', v_action.action_id,
                                'target_version', v_action.version);
    v_data := jsonb_build_object('operation', 'save_session_outcome',
                                 'session', app_private.learning_session_json(v_session),
                                 'draft', v_draft, 'action_reference', v_ref);

    insert into app_private.learning_session_receipts(user_id, operation, idempotency_key, fingerprint, session_id, response)
    values (uid, 'summary', key, args ->> 'fingerprint', v_session_id, v_data);

    return app_private.ok_result(p_request, 'DRAFTED', v_data || jsonb_build_object('replayed', false));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

create function app_api.decide_learning_session_outcome(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'decide_learning_session_outcome', 'DecideLearningSessionOutcomeArguments');
    uid uuid := app_private.current_uid();
    v_decision text := p_request #>> '{arguments,decision}';
    v_ctx jsonb := p_request -> 'execution_context';
    v_key text := nullif(btrim(p_request #>> '{execution_context,idempotency_key}'), '');
    v_conversation uuid;
    v_approval jsonb := p_request #> '{execution_context,approval_action}';
    v_ref jsonb := p_request #> '{execution_context,action_reference}';
    v_fingerprint text;
    v_replay jsonb;
    v_action app_private.pending_actions;
    v_session app_private.learning_session;
    v_outcome app_private.session_outcome;
    v_data jsonb;
    v_result jsonb;
    v_now timestamptz := clock_timestamp();
begin
    if err is not null then return err; end if;
    if v_key is null or (v_ctx ->> 'conversation_id') is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Idempotency key and conversation are required.');
    end if;
    v_conversation := (v_ctx ->> 'conversation_id')::uuid;
    if jsonb_typeof(v_approval) is distinct from 'object' or jsonb_typeof(v_ref) is distinct from 'object'
       or (v_approval ->> 'source') is distinct from 'UI'
       or (v_approval -> 'source_message_id') is distinct from 'null'::jsonb
       or (v_approval ->> 'user_id') is distinct from uid::text
       or (v_approval ->> 'decision') is distinct from v_decision
       or (v_approval ->> 'target_type') is distinct from 'PENDING_ACTION'
       or (v_ref ->> 'target_type') is distinct from 'PENDING_ACTION'
       or (v_ref ->> 'action_id') !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
       or (v_ref ->> 'target_id') is distinct from (v_ref ->> 'action_id')
       or (v_approval ->> 'target_id') is distinct from (v_ref ->> 'action_id')
       or (v_ref ->> 'action_version') !~ '^[0-9]+$'
       or (v_ref ->> 'target_version') is distinct from (v_ref ->> 'action_version')
       or (v_approval ->> 'target_version') is distinct from (v_ref ->> 'action_version')
       or (v_approval ->> 'approval_action_id') !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'Valid UI approval_action and matching action_reference are required.');
    end if;

    v_fingerprint := app_private.domain_fingerprint(uid, 'decide_learning_session_outcome',
        jsonb_build_object('decision', v_decision),
        jsonb_build_object('decision', v_decision, 'action_id', v_ref ->> 'action_id',
                           'action_version', (v_ref ->> 'action_version')::bigint));
    v_replay := app_private.idempotent_reply(p_request, uid, 'decide_learning_session_outcome', v_key, v_fingerprint);
    if v_replay is not null then return v_replay; end if;

    perform app_private.lock_owner(uid, p_request);
    v_replay := app_private.idempotent_reply(p_request, uid, 'decide_learning_session_outcome', v_key, v_fingerprint);
    if v_replay is not null then return v_replay; end if;

    select a.* into v_action from app_private.pending_actions a
    where a.user_id = uid and a.action_id = (v_ref ->> 'action_id')::uuid
      and a.conversation_id = v_conversation and a.intent = 'SAVE_SESSION_OUTCOME'
    for update;
    if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Pending session outcome not found.');
    end if;
    if v_action.state <> 'AWAITING_APPROVAL' or v_action.version <> (v_ref ->> 'action_version')::bigint then
        return jsonb_set(app_private.error_result(p_request, 'STALE_ENTITY_VERSION',
            'Phiên đã thay đổi. Hãy tạo lại bản tóm tắt.'), '{error,field}', '"action_reference"');
    end if;

    select s.* into v_session from app_private.learning_session s
    where s.user_id = uid and s.session_id = (v_action.draft_arguments ->> 'session_id')::uuid
    for update;
    if not found or v_session.status <> 'SUMMARY_PENDING'
       or v_session.version <> (v_action.draft_arguments ->> 'session_version')::bigint then
        return jsonb_set(app_private.error_result(p_request, 'STALE_ENTITY_VERSION',
            'Phiên đã thay đổi. Hãy tạo lại bản tóm tắt.'), '{error,field}', '"action_reference"');
    end if;

    insert into app_private.approval_actions (
        approval_action_id, user_id, target_type, target_id, target_version, decision, source, source_message_id,
        pending_action_target_id, created_at
    ) values (
        (v_approval ->> 'approval_action_id')::uuid, uid, 'PENDING_ACTION', v_action.action_id, v_action.version,
        v_decision, 'UI', null, v_action.action_id, v_now
    );

    update app_private.pending_actions
       set state = case when v_decision = 'APPROVE' then 'COMPLETED' else 'CANCELLED' end,
           version = version + 1, updated_at = v_now
     where user_id = uid and action_id = v_action.action_id;

    update app_private.learning_session
       set status = case when v_decision = 'APPROVE' then 'CLOSED' else 'ACTIVE' end,
           version = version + 1
     where user_id = uid and session_id = v_session.session_id
    returning * into v_session;

    if v_decision = 'APPROVE' then
        insert into app_private.session_outcome (user_id, session_id, summary, topics, duration_minutes, confirmed_at)
        values (uid, v_session.session_id, v_action.draft_arguments ->> 'summary',
                array(select jsonb_array_elements_text(v_action.draft_arguments -> 'topics')),
                (v_action.draft_arguments ->> 'duration_minutes')::bigint, v_now)
        returning * into v_outcome;
    end if;

    v_data := jsonb_build_object(
        'operation', 'save_session_outcome', 'decision', v_decision,
        'session', app_private.learning_session_json(v_session),
        'session_outcome', case when v_decision = 'APPROVE' then app_private.session_outcome_json(v_outcome) else 'null'::jsonb end
    );
    v_result := app_private.ok_result(p_request, case when v_decision = 'APPROVE' then 'COMMITTED' else 'REJECTED' end, v_data);

    insert into app_private.idempotency_records (
        user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at
    ) values (
        uid, 'decide_learning_session_outcome', v_key, v_fingerprint, 'COMPLETED', v_result, v_now + interval '7 days'
    );
    return v_result;
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

-- Retention: an expired session loses its turns and turn receipts. A confirmed outcome keeps its session row
-- (CLOSED); a session without an outcome is removed entirely and its pending summary is cancelled.
-- shortcut: runs lazily for the caller only; add a scheduled sweep (pg_cron) if inactive users must be purged too.
create function app_api.purge_expired_learning(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'purge_expired_learning', 'PurgeExpiredLearningArguments');
    uid uuid := app_private.current_uid();
    v_expired uuid[];
    v_kept uuid[];
    v_now timestamptz := clock_timestamp();
begin
    if err is not null then return err; end if;
    perform app_private.lock_owner(uid, p_request);

    select coalesce(array_agg(s.session_id), '{}'),
           coalesce(array_agg(s.session_id) filter (
               where exists (select 1 from app_private.session_outcome o where o.user_id = uid and o.session_id = s.session_id)), '{}')
    into v_expired, v_kept
    from app_private.learning_session s
    where s.user_id = uid and s.expires_at <= v_now
      and (s.status <> 'CLOSED' or exists (select 1 from app_private.learning_turn t
                                           where t.user_id = uid and t.session_id = s.session_id));

    update app_private.pending_actions a
       set state = 'CANCELLED', version = a.version + 1, updated_at = v_now
     where a.user_id = uid and a.intent = 'SAVE_SESSION_OUTCOME' and a.state = 'AWAITING_APPROVAL'
       and (a.draft_arguments ->> 'session_id')::uuid = any(v_expired);
    delete from app_private.learning_session_receipts r where r.user_id = uid and r.session_id = any(v_expired);
    delete from app_private.learning_turn t where t.user_id = uid and t.session_id = any(v_expired);
    update app_private.learning_session s set status = 'CLOSED'
     where s.user_id = uid and s.session_id = any(v_kept) and s.status <> 'CLOSED';
    delete from app_private.learning_session s
     where s.user_id = uid and s.session_id = any(v_expired) and not (s.session_id = any(v_kept));

    return app_private.ok_result(p_request, 'COMMITTED', jsonb_build_object(
        'deleted_sessions', cardinality(v_expired) - cardinality(v_kept),
        'closed_sessions', cardinality(v_kept)));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

alter function app_private.session_outcome_json(app_private.session_outcome) owner to sf_rpc_owner;
revoke all on function app_private.session_outcome_json(app_private.session_outcome) from public, anon, authenticated;

do $$
declare routine text;
begin
    foreach routine in array array['prepare_learning_summary', 'decide_learning_session_outcome', 'purge_expired_learning'] loop
        execute format('alter function app_api.%I(jsonb) owner to sf_rpc_owner', routine);
        execute format('revoke all on function app_api.%I(jsonb) from public, anon', routine);
        execute format('grant execute on function app_api.%I(jsonb) to authenticated', routine);
    end loop;
end
$$;
