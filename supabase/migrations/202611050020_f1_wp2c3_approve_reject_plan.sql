-- WP2c-3 / migration 020: approve_study_plan and reject_study_plan. Approval is the only way a
-- proposal becomes the official plan: one atomic commit of approval, plan, blocks, current-plan
-- pointer, schedule_revision + 1, proposal status, action completion and idempotency record.

-- The approval and action reference come from the backend context and must name exactly this
-- proposal and version. Returns an ErrorResult or null.
create function app_private.plan_decision_guard(p_request jsonb, p_uid uuid, p_decision text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_args jsonb := p_request -> 'arguments';
    v_ctx jsonb := p_request -> 'execution_context';
    v_approval jsonb := v_ctx -> 'approval_action';
    v_ref jsonb := v_ctx -> 'action_reference';
begin
    if v_ctx ->> 'idempotency_key' is null or v_ctx ->> 'conversation_id' is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key and a conversation are required.');
    end if;
    if jsonb_typeof(v_approval) is distinct from 'object' or jsonb_typeof(v_ref) is distinct from 'object'
       or v_approval ->> 'decision' <> p_decision or v_approval ->> 'target_type' <> 'PLAN_PROPOSAL'
       or v_approval ->> 'user_id' <> p_uid::text or v_approval ->> 'target_id' <> v_args ->> 'proposal_id'
       or (v_approval ->> 'target_version')::bigint <> (v_args ->> 'expected_proposal_version')::bigint
       or v_ref ->> 'target_type' <> 'PLAN_PROPOSAL' or v_ref ->> 'target_id' <> v_args ->> 'proposal_id'
       or (v_ref ->> 'target_version')::bigint <> (v_args ->> 'expected_proposal_version')::bigint then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'A matching decision for this proposal version is required.');
    end if;
    if v_approval ->> 'source' = 'CHAT' and not exists (
           select 1 from app_private.source_messages m
           where m.user_id = p_uid and m.conversation_id = (v_ctx ->> 'conversation_id')::uuid and m.role = 'USER'
             and m.message_id = (v_approval ->> 'source_message_id')::uuid) then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'A chat decision needs a recorded user message.');
    end if;
    return null;
end $$;

-- Locks and validates the pending action behind a plan decision (must have been presented by the server).
create function app_private.plan_decision_action(p_request jsonb, p_uid uuid, p_proposal app_private.plan_proposals,
                                                 out o_action app_private.pending_actions, out o_error jsonb)
language plpgsql security definer set search_path = '' as $$
declare
    v_ref jsonb := p_request #> '{execution_context,action_reference}';
    p app_private.action_presentations;
begin
    select * into o_action from app_private.pending_actions
    where user_id = p_uid and action_id = (v_ref ->> 'action_id')::uuid for update;
    if not found or o_action.proposal_id is distinct from p_proposal.proposal_id
       or o_action.conversation_id <> (p_request #>> '{execution_context,conversation_id}')::uuid then
        o_error := app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The action for this proposal was not found.');
    elsif o_action.requires_review then
        o_error := app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED', 'The action must be reviewed before it can be decided.');
    elsif o_action.version <> (v_ref ->> 'action_version')::bigint
          or o_action.state not in ('AWAITING_CONFIRMATION', 'AWAITING_APPROVAL') then
        o_error := app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action changed since it was presented.');
    else
        select * into p from app_private.action_presentations
        where user_id = p_uid and action_id = o_action.action_id and action_version = o_action.version;
        if not found or p.target_type <> 'PLAN_PROPOSAL' or p.target_id <> p_proposal.proposal_id
           or p.target_version <> p_proposal.version
           or p.content_digest <> app_private.presentation_digest(o_action, 'PLAN_PROPOSAL', p_proposal.proposal_id,
                                                                  p_proposal.version, p.presentation) then
            o_error := app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'The decided content was not presented by the server.');
        end if;
    end if;
end $$;

create or replace function app_api.approve_study_plan(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'approve_study_plan', 'approve_study_planArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_ctx jsonb := p_request -> 'execution_context';
    v_approval jsonb := p_request #> '{execution_context,approval_action}';
    v_ref jsonb := p_request #> '{execution_context,action_reference}';
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_binding jsonb;
    v_fp text;
    v_reply jsonb;
    v_user app_private.user_profiles;
    v_cur app_private.study_plans;
    pr app_private.plan_proposals;
    d record;
    v_plan app_private.study_plans;
    v_result jsonb;
    v_max bigint;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    v_error := app_private.plan_decision_guard(p_request, v_uid, 'APPROVE');
    if v_error is not null then
        return v_error;
    end if;
    v_binding := jsonb_build_object('decision', 'APPROVE', 'action_id', v_ref -> 'action_id',
        'action_version', v_ref -> 'action_version', 'target_type', 'PLAN_PROPOSAL',
        'target_id', v_args -> 'proposal_id', 'target_version', v_args -> 'expected_proposal_version');
    v_fp := app_private.domain_fingerprint(v_uid, 'approve_study_plan', v_args, v_binding);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'approve_study_plan', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'approve_study_plan', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        select * into pr from app_private.plan_proposals
        where user_id = v_uid and proposal_id = (v_args ->> 'proposal_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The proposal was not found.');
        end if;
        if pr.status <> 'PROPOSED' or pr.version <> (v_args ->> 'expected_proposal_version')::bigint then
            return app_private.error_result(p_request, 'STALE_PROPOSAL', 'The proposal is no longer pending.');
        end if;
        select * into v_user from app_private.user_profiles where user_id = v_uid;
        select * into v_cur from app_private.study_plans where user_id = v_uid and plan_id = v_user.current_plan_id;
        -- A changed schedule makes the proposal permanently stale; the status survives this returned error.
        if pr.base_schedule_revision <> v_user.schedule_revision or pr.base_plan_id is distinct from v_user.current_plan_id then
            update app_private.plan_proposals set status = 'STALE' where proposal_id = pr.proposal_id;
            return app_private.error_result(p_request, 'STALE_PROPOSAL', 'The schedule changed after the proposal was generated.');
        end if;
        if (v_args ->> 'expected_plan_version')::bigint is distinct from v_cur.version then
            return app_private.error_result(p_request, 'STALE_PLAN_VERSION', 'The current plan version is not the expected one.');
        end if;
        select * into d from app_private.plan_decision_action(p_request, v_uid, pr);
        if d.o_error is not null then
            return d.o_error;
        end if;

        -- Re-validate every block against the tasks as they are now.
        v_max := (pr.policy_snapshot ->> 'max_block_minutes')::bigint;
        if exists (
            select 1 from jsonb_array_elements(pr.payload -> 'study_blocks') b
            left join app_private.academic_tasks t on t.user_id = v_uid and t.task_id = (b ->> 'task_id')::uuid
            where t.task_id is null or t.status not in ('TODO', 'IN_PROGRESS')
               or (b ->> 'end_at')::timestamptz > t.deadline_at
               or (t.available_from_at is not null and (b ->> 'start_at')::timestamptz < t.available_from_at)
               or extract(epoch from ((b ->> 'end_at')::timestamptz - (b ->> 'start_at')::timestamptz)) / 60 > v_max) then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'A proposed block no longer fits its task or the policy.');
        end if;

        insert into app_private.approval_actions
            (approval_action_id, user_id, target_type, target_id, target_version, decision, source, source_message_id,
             proposal_target_id)
        values ((v_approval ->> 'approval_action_id')::uuid, v_uid, 'PLAN_PROPOSAL', pr.proposal_id, pr.version, 'APPROVE',
                v_approval ->> 'source', (v_approval ->> 'source_message_id')::uuid, pr.proposal_id);
        insert into app_private.study_plans (plan_id, user_id, version, previous_plan_id, source_proposal_id)
        values (extensions.gen_random_uuid(), v_uid, coalesce(v_cur.version, 0) + 1, v_cur.plan_id, pr.proposal_id)
        returning * into v_plan;
        insert into app_private.study_blocks (plan_id, block_id, user_id, task_id, start_at, end_at, is_locked)
        select v_plan.plan_id, (b ->> 'block_id')::uuid, v_uid, (b ->> 'task_id')::uuid,
               (b ->> 'start_at')::timestamptz, (b ->> 'end_at')::timestamptz, (b ->> 'is_locked')::boolean
        from jsonb_array_elements(pr.payload -> 'study_blocks') b;
        update app_private.user_profiles
        set current_plan_id = v_plan.plan_id, schedule_revision = schedule_revision + 1 where user_id = v_uid;
        update app_private.plan_proposals set status = 'APPROVED', committed_plan_id = v_plan.plan_id
        where proposal_id = pr.proposal_id;
        update app_private.pending_actions set state = 'COMPLETED', version = version + 1 where action_id = (d.o_action).action_id;
        v_result := app_private.ok_result(p_request, 'COMMITTED', app_private.plan_json(v_plan));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'approve_study_plan', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception
        when sqlstate 'P0001' then
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_PROPOSAL') then sqlerrm else 'INVALID_PARAMETER' end,
                'The approval target is no longer valid.');
        when sqlstate '23P01' then
            return app_private.error_result(p_request, 'TIME_CONFLICT', 'The proposed blocks overlap.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;

create or replace function app_api.reject_study_plan(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'reject_study_plan', 'reject_study_planArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_approval jsonb := p_request #> '{execution_context,approval_action}';
    v_ref jsonb := p_request #> '{execution_context,action_reference}';
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_binding jsonb;
    v_fp text;
    v_reply jsonb;
    pr app_private.plan_proposals;
    d record;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    v_error := app_private.plan_decision_guard(p_request, v_uid, 'REJECT');
    if v_error is not null then
        return v_error;
    end if;
    v_binding := jsonb_build_object('decision', 'REJECT', 'action_id', v_ref -> 'action_id',
        'action_version', v_ref -> 'action_version', 'target_type', 'PLAN_PROPOSAL',
        'target_id', v_args -> 'proposal_id', 'target_version', v_args -> 'expected_proposal_version');
    v_fp := app_private.domain_fingerprint(v_uid, 'reject_study_plan', v_args, v_binding);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'reject_study_plan', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'reject_study_plan', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        select * into pr from app_private.plan_proposals
        where user_id = v_uid and proposal_id = (v_args ->> 'proposal_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The proposal was not found.');
        end if;
        if pr.status <> 'PROPOSED' or pr.version <> (v_args ->> 'expected_proposal_version')::bigint then
            return app_private.error_result(p_request, 'STALE_PROPOSAL', 'The proposal is no longer pending.');
        end if;
        select * into d from app_private.plan_decision_action(p_request, v_uid, pr);
        if d.o_error is not null then
            return d.o_error;
        end if;
        insert into app_private.approval_actions
            (approval_action_id, user_id, target_type, target_id, target_version, decision, source, source_message_id,
             proposal_target_id)
        values ((v_approval ->> 'approval_action_id')::uuid, v_uid, 'PLAN_PROPOSAL', pr.proposal_id, pr.version, 'REJECT',
                v_approval ->> 'source', (v_approval ->> 'source_message_id')::uuid, pr.proposal_id);
        update app_private.plan_proposals set status = 'REJECTED' where proposal_id = pr.proposal_id returning * into pr;
        update app_private.pending_actions set state = 'CANCELLED', version = version + 1 where action_id = (d.o_action).action_id;
        v_result := app_private.ok_result(p_request, 'REJECTED', app_private.proposal_json(pr));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'reject_study_plan', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception
        when sqlstate 'P0001' then
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_PROPOSAL') then sqlerrm else 'INVALID_PARAMETER' end,
                'The decision target is no longer valid.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.plan_decision_guard(jsonb, uuid, text) owner to sf_rpc_owner;
alter function app_private.plan_decision_action(jsonb, uuid, app_private.plan_proposals) owner to sf_rpc_owner;
revoke all on function app_private.plan_decision_guard(jsonb, uuid, text),
    app_private.plan_decision_action(jsonb, uuid, app_private.plan_proposals) from public, anon, authenticated;
