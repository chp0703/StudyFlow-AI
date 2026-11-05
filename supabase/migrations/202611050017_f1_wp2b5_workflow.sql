-- WP2b-5 / migration 017: workflow reads and the durable continuation queue
-- (get_workflow_context, get_workflow_continuation, initialize_workflow_continuation,
-- checkpoint_workflow_continuation). Replaces the last four fail-closed stubs of this group.

create function app_private.message_json(p_message app_private.source_messages) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('message_id', p_message.message_id, 'user_id', p_message.user_id,
        'conversation_id', p_message.conversation_id, 'source', p_message.source, 'role', p_message.role,
        'text', p_message.text, 'received_at', app_private.iso(p_message.received_at))
$$;

create function app_private.continuation_json(p_row app_private.workflow_continuations) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('user_id', p_row.user_id, 'conversation_id', p_row.conversation_id,
        'source_message_id', p_row.source_message_id, 'origin_http_operation', p_row.origin_http_operation,
        'origin_idempotency_key', p_row.origin_idempotency_key,
        'origin_request_fingerprint', p_row.origin_request_fingerprint, 'version', p_row.version,
        'extraction', p_row.extraction, 'extraction_digest', p_row.extraction_digest,
        'depends_on', p_row.depends_on, 'cursor', p_row.cursor, 'awaiting_reference', p_row.awaiting_reference,
        'completed_steps', p_row.completed_steps,
        'created_at', app_private.iso(p_row.created_at), 'updated_at', app_private.iso(p_row.updated_at))
$$;

-- One pending action with the records a stateless caller needs to resume it.
-- Plan proposals arrive with WP2c, so no action can reference one yet.
create function app_private.workflow_action_json(p_action app_private.pending_actions) returns jsonb
language plpgsql stable set search_path = '' as $$
declare
    v_candidate app_private.task_candidates;
    v_pres app_private.action_presentations;
    v_source app_private.source_messages;
begin
    select * into v_candidate from app_private.task_candidates
    where user_id = p_action.user_id and candidate_id = p_action.candidate_id;
    select * into v_pres from app_private.action_presentations
    where user_id = p_action.user_id and action_id = p_action.action_id
    order by action_version desc limit 1;
    if v_pres.action_id is not null and v_pres.source_message_id is not null then
        select * into v_source from app_private.source_messages
        where user_id = p_action.user_id and message_id = v_pres.source_message_id;
    end if;
    return jsonb_build_object('pending_action', app_private.pending_json(p_action),
        'candidate', case when v_candidate.candidate_id is null then null else app_private.candidate_json(v_candidate) end,
        'proposal', null,
        'last_presentation', case when v_pres.action_id is null then null else jsonb_build_object(
            'user_id', v_pres.user_id, 'action_id', v_pres.action_id, 'action_version', v_pres.action_version,
            'target_type', v_pres.target_type, 'target_id', v_pres.target_id, 'target_version', v_pres.target_version,
            'content_digest', v_pres.content_digest, 'presentation', v_pres.presentation,
            'source_message_id', v_pres.source_message_id, 'created_at', app_private.iso(v_pres.created_at)) end,
        'presentation_source_message', case when v_source.message_id is null then null else app_private.message_json(v_source) end);
end $$;

-- The origin receipt must still be held: same request, same fencing version, lease not expired.
-- Returns the ErrorResult to hand back, or null when the lease is valid.
create function app_private.receipt_guard(p_request jsonb, p_uid uuid, p_binding jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    r app_private.api_request_receipts;
begin
    select * into r from app_private.api_request_receipts
    where user_id = p_uid and http_operation = p_binding ->> 'http_operation'
      and idempotency_key = p_binding ->> 'idempotency_key';
    if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The API receipt was not found.');
    elsif r.request_fingerprint <> p_binding ->> 'request_fingerprint' then
        return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'The receipt belongs to a different request.');
    elsif r.state <> 'IN_PROGRESS' or r.lease_version <> (p_binding ->> 'expected_lease_version')::bigint
          or r.lease_until <= clock_timestamp() then
        return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The receipt lease is no longer held.');
    end if;
    return null;
end $$;

create function app_private.step_key(p_api_key text, p_source uuid, p_index bigint) returns text
language sql immutable set search_path = '' as $$
    select encode(extensions.digest(convert_to(app_private.canonical_json(jsonb_build_object(
        'api_key', p_api_key, 'source_message_id', p_source::text, 'intent_index', p_index)), 'UTF8'), 'sha256'), 'hex')
$$;

-- get_workflow_context: read-only; never creates a conversation, action or message.
create or replace function app_api.get_workflow_context(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'get_workflow_context', 'GetWorkflowContextArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_conv uuid := (p_request -> 'arguments' ->> 'conversation_id')::uuid;
    v_active app_private.pending_actions;
    v_selected app_private.pending_actions;
    v_source app_private.source_messages;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        if not exists (select 1 from app_private.conversation_records where user_id = v_uid and conversation_id = v_conv) then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The conversation was not found.');
        end if;
        if v_args ->> 'message_id' is not null then
            select * into v_source from app_private.source_messages
            where user_id = v_uid and conversation_id = v_conv and message_id = (v_args ->> 'message_id')::uuid;
            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The message was not found.');
            end if;
        end if;
        if v_args ->> 'action_id' is not null then
            select * into v_selected from app_private.pending_actions
            where user_id = v_uid and conversation_id = v_conv and action_id = (v_args ->> 'action_id')::uuid;
            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The action was not found.');
            end if;
        end if;
        select * into v_active from app_private.pending_actions
        where user_id = v_uid and conversation_id = v_conv
          and state in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL');
        return app_private.ok_result(p_request, 'READ', jsonb_build_object(
            'conversation_id', v_conv,
            'active_action', case when v_active.action_id is null then null else app_private.workflow_action_json(v_active) end,
            'selected_action', case when v_selected.action_id is null then null else app_private.workflow_action_json(v_selected) end,
            'source_message', case when v_source.message_id is null then null else app_private.message_json(v_source) end,
            'read_at', app_private.iso(clock_timestamp())));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- get_workflow_continuation: exact lookup by source message (finished ones included) or the
-- conversation's single unfinished continuation. Never returns a finished one as "active".
create or replace function app_api.get_workflow_continuation(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'get_workflow_continuation', 'GetWorkflowContinuationArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    c app_private.workflow_continuations;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        if v_args ->> 'source_message_id' is not null then
            select * into c from app_private.workflow_continuations
            where user_id = v_uid and conversation_id = (v_args ->> 'conversation_id')::uuid
              and source_message_id = (v_args ->> 'source_message_id')::uuid;
        else
            select * into c from app_private.workflow_continuations
            where user_id = v_uid and conversation_id = (v_args ->> 'conversation_id')::uuid
              and cursor < jsonb_array_length(extraction -> 'intents');
        end if;
        return app_private.ok_result(p_request, 'READ', jsonb_build_object('continuation',
            case when c.source_message_id is null then null else app_private.continuation_json(c) end));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- initialize: first write wins; a replay returns the stored queue before comparing extractor output.
create or replace function app_api.initialize_workflow_continuation(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'initialize_workflow_continuation', 'InitializeWorkflowContinuationArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_binding jsonb := p_request -> 'arguments' -> 'receipt_binding';
    v_conv uuid;
    v_source uuid;
    v_receipt app_private.api_request_receipts;
    v_message app_private.source_messages;
    c app_private.workflow_continuations;
    v_count int;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    v_conv := (v_args ->> 'conversation_id')::uuid;
    v_source := (v_args ->> 'source_message_id')::uuid;
    v_count := jsonb_array_length(v_args #> '{extraction,intents}');
    -- depends_on lines up with the intents and only points at earlier steps.
    if v_args ->> 'conversation_id' is distinct from p_request #>> '{execution_context,conversation_id}'
       or jsonb_array_length(v_args -> 'depends_on') <> v_count
       or exists (select 1 from jsonb_array_elements(v_args -> 'depends_on') with ordinality t(v, i),
                  jsonb_array_elements_text(t.v) d where d::numeric >= t.i - 1) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER',
            'The conversation or dependency list does not match the extraction.');
    end if;
    begin
        perform app_private.lock_owner(v_uid, p_request);
        v_error := app_private.receipt_guard(p_request, v_uid, v_binding);
        if v_error is not null then
            return v_error;
        end if;
        select * into v_receipt from app_private.api_request_receipts
        where user_id = v_uid and http_operation = v_binding ->> 'http_operation'
          and idempotency_key = v_binding ->> 'idempotency_key';
        select * into v_message from app_private.source_messages
        where user_id = v_uid and conversation_id = v_conv and message_id = v_source and role = 'USER';
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The source message was not found.');
        end if;
        if v_receipt.message_id is distinct from v_source or v_binding ->> 'http_operation' not in ('send_message', 'prepare_action') then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The source message does not belong to the origin receipt.');
        end if;
        select * into c from app_private.workflow_continuations where user_id = v_uid and source_message_id = v_source;
        if found then
            if c.origin_http_operation <> v_binding ->> 'http_operation'
               or c.origin_idempotency_key <> v_binding ->> 'idempotency_key' then
                return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT',
                    'The source message already has a continuation from another request.');
            end if;
        else
            begin
                insert into app_private.workflow_continuations
                    (user_id, conversation_id, source_message_id, origin_http_operation, origin_idempotency_key,
                     origin_request_fingerprint, extraction, extraction_digest, depends_on)
                values (v_uid, v_conv, v_source, v_binding ->> 'http_operation', v_binding ->> 'idempotency_key',
                        v_binding ->> 'request_fingerprint', v_args -> 'extraction',
                        encode(extensions.digest(convert_to(app_private.canonical_json(v_args -> 'extraction'), 'UTF8'), 'sha256'), 'hex'),
                        v_args -> 'depends_on')
                returning * into c;
            exception when unique_violation then
                return app_private.error_result(p_request, 'STALE_ENTITY_VERSION',
                    'The conversation already has an unfinished workflow.');
            end;
        end if;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.continuation_json(c));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- checkpoint: compare-and-set on (version, cursor). WAIT parks on an existing awaiting action;
-- ADVANCE records the outcome of exactly the step at the cursor. Validation precedes any write.
create or replace function app_api.checkpoint_workflow_continuation(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'checkpoint_workflow_continuation', 'CheckpointWorkflowContinuationArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_out jsonb := p_request -> 'arguments' -> 'outcome';
    v_ref jsonb := p_request -> 'arguments' -> 'action_reference';
    v_exp_version bigint;
    v_exp_cursor bigint;
    c app_private.workflow_continuations;
    a app_private.pending_actions;
    v_count int;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_args ->> 'conversation_id' is distinct from p_request #>> '{execution_context,conversation_id}' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The conversation does not match the request context.');
    end if;
    v_exp_version := (v_args ->> 'expected_version')::bigint;
    v_exp_cursor := (v_args ->> 'expected_cursor')::bigint;
    begin
        perform app_private.lock_owner(v_uid, p_request);
        v_error := app_private.receipt_guard(p_request, v_uid, v_args -> 'receipt_binding');
        if v_error is not null then
            return v_error;
        end if;
        select * into c from app_private.workflow_continuations
        where user_id = v_uid and conversation_id = (v_args ->> 'conversation_id')::uuid
          and source_message_id = (v_args ->> 'source_message_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The workflow continuation was not found.');
        end if;
        v_count := jsonb_array_length(c.extraction -> 'intents');

        -- Replay of an already-applied identical checkpoint.
        if v_args ->> 'transition' = 'ADVANCE' and v_exp_cursor < c.cursor and v_exp_version < c.version
           and c.completed_steps -> v_exp_cursor::int = v_out then
            return app_private.ok_result(p_request, 'COMMITTED', app_private.continuation_json(c));
        end if;
        if v_args ->> 'transition' = 'WAIT' and v_exp_cursor = c.cursor and v_exp_version + 1 = c.version
           and c.awaiting_reference = v_ref then
            return app_private.ok_result(p_request, 'COMMITTED', app_private.continuation_json(c));
        end if;

        if c.version <> v_exp_version or c.cursor <> v_exp_cursor or c.cursor >= v_count then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The workflow continuation has moved on.');
        end if;

        if v_args ->> 'transition' = 'WAIT' then
            select * into a from app_private.pending_actions
            where user_id = v_uid and conversation_id = c.conversation_id and action_id = (v_ref ->> 'action_id')::uuid;
            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The awaited action was not found.');
            end if;
            if a.version <> (v_ref ->> 'action_version')::bigint
               or a.state not in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL') then
                return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The awaited action is not waiting for the user.');
            end if;
            if v_ref ->> 'target_id' not in (a.action_id::text, coalesce(a.candidate_id::text, ''), coalesce(a.proposal_id::text, '')) then
                return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The action reference does not match the action.');
            end if;
            update app_private.workflow_continuations
            set awaiting_reference = v_ref, version = version + 1
            where user_id = c.user_id and source_message_id = c.source_message_id returning * into c;
            return app_private.ok_result(p_request, 'COMMITTED', app_private.continuation_json(c));
        end if;

        -- ADVANCE
        if (v_out ->> 'intent_index')::bigint <> c.cursor
           or v_out ->> 'step_key' <> app_private.step_key(c.origin_idempotency_key, c.source_message_id, c.cursor) then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The outcome does not belong to the step at the cursor.');
        end if;
        -- A step whose dependency did not succeed can only be cancelled, and vice versa.
        if (v_out ->> 'disposition' = 'DEPENDENCY_CANCELLED') is distinct from exists (
               select 1 from jsonb_array_elements_text(c.depends_on -> c.cursor::int) d
               where c.completed_steps -> d::int ->> 'disposition' is distinct from 'SUCCEEDED') then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The outcome disposition contradicts the step dependencies.');
        end if;
        if c.awaiting_reference is not null then
            select * into a from app_private.pending_actions
            where user_id = v_uid and action_id = (c.awaiting_reference ->> 'action_id')::uuid;
            if a.state not in ('COMPLETED', 'CANCELLED') then
                return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The awaited action is not finished.');
            end if;
        end if;
        -- Approval-gated writes need a finished action as evidence; reads are trusted as attested.
        if v_out ->> 'disposition' = 'SUCCEEDED'
           and v_out ->> 'operation' in ('confirm_task', 'set_availability', 'set_busy_interval',
                                         'set_scheduling_preferences', 'approve_study_plan', 'reject_study_plan')
           and (c.awaiting_reference is null or a.state <> 'COMPLETED') then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The write result has no completed action behind it.');
        end if;
        update app_private.workflow_continuations
        set completed_steps = completed_steps || jsonb_build_array(v_out), cursor = cursor + 1,
            awaiting_reference = null, version = version + 1
        where user_id = c.user_id and source_message_id = c.source_message_id returning * into c;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.continuation_json(c));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.message_json(app_private.source_messages) owner to sf_rpc_owner;
alter function app_private.continuation_json(app_private.workflow_continuations) owner to sf_rpc_owner;
alter function app_private.workflow_action_json(app_private.pending_actions) owner to sf_rpc_owner;
alter function app_private.receipt_guard(jsonb, uuid, jsonb) owner to sf_rpc_owner;
alter function app_private.step_key(text, uuid, bigint) owner to sf_rpc_owner;
revoke all on function app_private.message_json(app_private.source_messages),
    app_private.continuation_json(app_private.workflow_continuations),
    app_private.workflow_action_json(app_private.pending_actions),
    app_private.receipt_guard(jsonb, uuid, jsonb), app_private.step_key(text, uuid, bigint)
    from public, anon, authenticated;
