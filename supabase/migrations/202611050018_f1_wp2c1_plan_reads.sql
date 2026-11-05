-- WP2c-1 / migration 018: read side of planning (get_scheduling_context, get_study_plan).
-- Both are read-only and owner scoped; plan writes arrive in the next stages.

create function app_private.plan_json(p_plan app_private.study_plans) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('plan_id', p_plan.plan_id, 'user_id', p_plan.user_id, 'version', p_plan.version,
        'previous_plan_id', p_plan.previous_plan_id, 'source_proposal_id', p_plan.source_proposal_id,
        'approved_at', app_private.iso(p_plan.approved_at), 'created_at', app_private.iso(p_plan.created_at))
$$;

create function app_private.block_json(p_block app_private.study_blocks) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('plan_id', p_block.plan_id, 'block_id', p_block.block_id, 'user_id', p_block.user_id,
        'task_id', p_block.task_id, 'start_at', app_private.iso(p_block.start_at), 'end_at', app_private.iso(p_block.end_at),
        'is_locked', p_block.is_locked, 'created_at', app_private.iso(p_block.created_at))
$$;

create function app_private.proposal_json(p_proposal app_private.plan_proposals) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('proposal_id', p_proposal.proposal_id, 'user_id', p_proposal.user_id,
        'version', p_proposal.version, 'status', p_proposal.status, 'base_plan_id', p_proposal.base_plan_id,
        'base_plan_version', p_proposal.base_plan_version, 'base_schedule_revision', p_proposal.base_schedule_revision,
        'generation_scope', p_proposal.generation_scope, 'payload', p_proposal.payload,
        'algorithm_version', p_proposal.algorithm_version, 'policy_snapshot', p_proposal.policy_snapshot,
        'generated_at', app_private.iso(p_proposal.generated_at), 'committed_plan_id', p_proposal.committed_plan_id,
        'created_at', app_private.iso(p_proposal.created_at), 'updated_at', app_private.iso(p_proposal.updated_at))
$$;

-- PlanView of one plan; a window keeps plan metadata whole and only filters the blocks (overlap rule).
create function app_private.plan_view_json(p_uid uuid, p_plan_id uuid, p_from timestamptz, p_to timestamptz) returns jsonb
language plpgsql stable set search_path = '' as $$
declare
    v_plan app_private.study_plans;
begin
    select * into v_plan from app_private.study_plans where user_id = p_uid and plan_id = p_plan_id;
    if not found then
        return jsonb_build_object('kind', 'PLAN_VIEW', 'plan', null, 'study_blocks', '[]'::jsonb);
    end if;
    return jsonb_build_object('kind', 'PLAN_VIEW', 'plan', app_private.plan_json(v_plan),
        'study_blocks', coalesce((select jsonb_agg(app_private.block_json(b) order by b.start_at, b.block_id)
            from app_private.study_blocks b
            where b.user_id = p_uid and b.plan_id = p_plan_id
              and (p_from is null or (b.start_at < p_to and b.end_at > p_from))), '[]'::jsonb));
end $$;

-- get_scheduling_context: one statement-consistent snapshot for the engine. It returns every task
-- and active window; the engine applies the generation scope. The base plan is never filtered.
create or replace function app_api.get_scheduling_context(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'get_scheduling_context', 'GetSchedulingSnapshotArguments');
    v_uid uuid;
    v_scope jsonb := p_request -> 'arguments' -> 'generation_scope';
    v_user app_private.user_profiles;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if (v_scope ->> 'end_at')::timestamptz <= (v_scope ->> 'start_at')::timestamptz then
        return app_private.field_error(p_request, 'INVALID_PARAMETER', 'The generation window must end after it starts.', 'generation_scope');
    end if;
    begin
        select * into v_user from app_private.user_profiles where user_id = v_uid;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The user context has not been initialized.');
        end if;
        if (select count(*) from app_private.academic_tasks
            where user_id = v_uid and task_id in (select value::uuid from jsonb_array_elements_text(v_scope -> 'task_ids')))
           <> jsonb_array_length(v_scope -> 'task_ids') then
            return app_private.field_error(p_request, 'ENTITY_NOT_FOUND', 'A selected task was not found.', 'generation_scope.task_ids');
        end if;
        return app_private.ok_result(p_request, 'READ', jsonb_build_object(
            'user', app_private.user_json(v_user),
            'tasks', coalesce((select jsonb_agg(app_private.task_json(t) order by t.deadline_at, t.task_id)
                from app_private.academic_tasks t where t.user_id = v_uid), '[]'::jsonb),
            'time_windows', coalesce((select jsonb_agg(app_private.window_json(w) order by w.created_at, w.window_id)
                from app_private.time_windows w where w.user_id = v_uid and w.archived_at is null), '[]'::jsonb),
            'base_plan', case when v_user.current_plan_id is null
                then jsonb_build_object('kind', 'PLAN_VIEW', 'plan', null, 'study_blocks', '[]'::jsonb)
                else app_private.plan_view_json(v_uid, v_user.current_plan_id, null, null) end,
            'schedule_revision', v_user.schedule_revision,
            'read_at', app_private.iso(clock_timestamp())));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- get_study_plan: CURRENT, HISTORY (by version) or PROPOSAL (by id, always the full payload).
create or replace function app_api.get_study_plan(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'get_study_plan', 'get_study_planArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_from timestamptz := (p_request -> 'arguments' ->> 'start_at')::timestamptz;
    v_to timestamptz := (p_request -> 'arguments' ->> 'end_at')::timestamptz;
    v_plan_id uuid;
    v_proposal app_private.plan_proposals;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_from is not null and v_to <= v_from then
        return app_private.field_error(p_request, 'INVALID_PARAMETER', 'The window must end after it starts.', 'end_at');
    end if;
    if v_args ->> 'view' = 'PROPOSAL' and v_from is not null then
        return app_private.field_error(p_request, 'INVALID_PARAMETER', 'A proposal view takes no time window.', 'start_at');
    end if;
    begin
        if v_args ->> 'view' = 'PROPOSAL' then
            select * into v_proposal from app_private.plan_proposals
            where user_id = v_uid and proposal_id = (v_args ->> 'proposal_id')::uuid;
            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The proposal was not found.');
            end if;
            return app_private.ok_result(p_request, 'READ', jsonb_build_object('kind', 'PROPOSAL_VIEW',
                'proposal', app_private.proposal_json(v_proposal)));
        elsif v_args ->> 'view' = 'HISTORY' then
            select plan_id into v_plan_id from app_private.study_plans
            where user_id = v_uid and version = (v_args ->> 'version')::bigint;
            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The plan version was not found.');
            end if;
        else
            select current_plan_id into v_plan_id from app_private.user_profiles where user_id = v_uid;
        end if;
        return app_private.ok_result(p_request, 'READ', app_private.plan_view_json(v_uid, v_plan_id, v_from, v_to));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.plan_json(app_private.study_plans) owner to sf_rpc_owner;
alter function app_private.block_json(app_private.study_blocks) owner to sf_rpc_owner;
alter function app_private.proposal_json(app_private.plan_proposals) owner to sf_rpc_owner;
alter function app_private.plan_view_json(uuid, uuid, timestamptz, timestamptz) owner to sf_rpc_owner;
revoke all on function app_private.plan_json(app_private.study_plans), app_private.block_json(app_private.study_blocks),
    app_private.proposal_json(app_private.plan_proposals),
    app_private.plan_view_json(uuid, uuid, timestamptz, timestamptz) from public, anon, authenticated;
