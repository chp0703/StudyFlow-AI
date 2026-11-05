-- WP2c-2 / migration 019: persist_plan_proposal. Stores an engine-generated proposal after the database
-- re-checks everything it can without trusting the caller's self-description. It never changes
-- schedule_revision (a proposal is not a plan).

-- Business checks on a proposal payload. Returns an ErrorResult or null.
create function app_private.validate_proposal(p_request jsonb, p_uid uuid, p_proposal jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_scope jsonb := p_proposal -> 'generation_scope';
    v_blocks jsonb := p_proposal #> '{payload,study_blocks}';
    v_ids uuid[];
begin
    if exists (select 1 from jsonb_array_elements(v_blocks) b where b ->> 'user_id' <> p_uid::text) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'A proposed block belongs to another user.');
    end if;
    if exists (select 1 from jsonb_array_elements(v_blocks) b
               where (b ->> 'end_at')::timestamptz <= (b ->> 'start_at')::timestamptz
                  or (b ->> 'start_at')::timestamptz < (v_scope ->> 'start_at')::timestamptz
                  or (b ->> 'end_at')::timestamptz > (v_scope ->> 'end_at')::timestamptz) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'A proposed block is empty or outside the generation window.');
    end if;
    select array_agg((b ->> 'block_id')::uuid) into v_ids from jsonb_array_elements(v_blocks) b;
    if (select count(distinct x) from unnest(coalesce(v_ids, '{}')) x) <> coalesce(cardinality(v_ids), 0) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Proposed block IDs must be unique.');
    end if;
    -- Blocks of one user never overlap each other.
    if exists (select 1 from jsonb_array_elements(v_blocks) a, jsonb_array_elements(v_blocks) b
               where a ->> 'block_id' < b ->> 'block_id'
                 and (a ->> 'start_at')::timestamptz < (b ->> 'end_at')::timestamptz
                 and (b ->> 'start_at')::timestamptz < (a ->> 'end_at')::timestamptz) then
        return app_private.error_result(p_request, 'TIME_CONFLICT', 'Proposed blocks overlap.');
    end if;
    -- Every block (and summary) targets a task the owner has, inside the selection when one is given.
    if exists (select 1 from (select b ->> 'task_id' t from jsonb_array_elements(v_blocks) b
                              union select s ->> 'task_id' from jsonb_array_elements(p_proposal #> '{payload,task_summaries}') s) x
               where not exists (select 1 from app_private.academic_tasks k where k.user_id = p_uid and k.task_id::text = x.t)
                  or (v_scope ->> 'selection_mode' = 'SELECTED_TASKS' and not ((v_scope -> 'task_ids') ? x.t))) then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'A proposed task is not available to this user or scope.');
    end if;
    return null;
end $$;

create or replace function app_api.persist_plan_proposal(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'persist_plan_proposal', 'PersistProposalArguments');
    v_uid uuid;
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_cmd jsonb := p_request #> '{arguments,command_arguments}';
    v_prop jsonb := p_request #> '{arguments,proposal}';
    v_fp text;
    v_reply jsonb;
    v_user app_private.user_profiles;
    v_plan app_private.study_plans;
    v_row app_private.plan_proposals;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key is required.');
    end if;
    -- Only an unsettled proposal of this owner, bound to the command the caller originally sent.
    if v_prop ->> 'user_id' <> v_uid::text or v_prop ->> 'status' <> 'PROPOSED' or v_prop ->> 'committed_plan_id' is not null
       or v_prop -> 'generation_scope' <> v_cmd -> 'generation_scope'
       or (v_cmd #>> '{generation_scope,end_at}')::timestamptz <= (v_cmd #>> '{generation_scope,start_at}')::timestamptz then
        return app_private.error_result(p_request, 'INVALID_PARAMETER',
            'The proposal does not match its owner, status or generation command.');
    end if;
    -- Generation fingerprints only the original command, never IDs or clocks created by the engine.
    v_fp := app_private.domain_fingerprint(v_uid, 'generate_study_plan', v_cmd);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'generate_study_plan', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'generate_study_plan', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        select * into v_user from app_private.user_profiles where user_id = v_uid;
        if v_prop -> 'policy_snapshot' <> app_private.default_policy() || v_user.scheduling_policy || (v_cmd -> 'policy_overrides') then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The policy snapshot is not the effective policy.');
        end if;
        select * into v_plan from app_private.study_plans where user_id = v_uid and plan_id = v_user.current_plan_id;
        if (v_prop ->> 'base_schedule_revision')::bigint <> v_user.schedule_revision
           or (v_prop ->> 'base_plan_id')::uuid is distinct from v_user.current_plan_id
           or (v_prop ->> 'base_plan_version')::bigint is distinct from v_plan.version then
            return app_private.error_result(p_request, 'STALE_PROPOSAL', 'The schedule changed after the proposal was generated.');
        end if;
        v_error := app_private.validate_proposal(p_request, v_uid, v_prop);
        if v_error is not null then
            return v_error;
        end if;
        if exists (select 1 from app_private.plan_proposals where proposal_id = (v_prop ->> 'proposal_id')::uuid) then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'The proposal ID is already in use.');
        end if;
        insert into app_private.plan_proposals
            (proposal_id, user_id, version, status, base_plan_id, base_plan_version, base_schedule_revision,
             generation_scope, payload, algorithm_version, policy_snapshot, generated_at)
        values ((v_prop ->> 'proposal_id')::uuid, v_uid, 1, 'PROPOSED', v_user.current_plan_id, v_plan.version,
                v_user.schedule_revision, v_prop -> 'generation_scope', v_prop -> 'payload',
                v_prop ->> 'algorithm_version', v_prop -> 'policy_snapshot', (v_prop ->> 'generated_at')::timestamptz)
        returning * into v_row;
        v_result := app_private.ok_result(p_request, 'PROPOSED', app_private.proposal_json(v_row));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'generate_study_plan', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.validate_proposal(jsonb, uuid, jsonb) owner to sf_rpc_owner;
revoke all on function app_private.validate_proposal(jsonb, uuid, jsonb) from public, anon, authenticated;
