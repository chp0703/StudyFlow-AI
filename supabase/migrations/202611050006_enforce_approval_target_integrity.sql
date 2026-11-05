-- Stage 03.3 Commit 13: validate polymorphic approval targets at the database boundary.

create or replace function app_private.validate_approval_action_target()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
declare
    v_version bigint;
    v_status text;
begin
    if tg_op = 'DELETE' then
        raise exception using errcode = '42501', message = 'APPROVAL_ACTION_IMMUTABLE';
    end if;
    if tg_op = 'UPDATE' then
        raise exception using errcode = '42501', message = 'APPROVAL_ACTION_IMMUTABLE';
    end if;
    if auth.uid() is distinct from new.user_id then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;

    if new.target_type = 'TASK_CANDIDATE' then
        select version, status into v_version, v_status
        from app_private.task_candidates
        where user_id = new.user_id and candidate_id = new.candidate_target_id;
        if not found then
            raise exception using errcode = 'P0001', message = 'ENTITY_NOT_FOUND';
        end if;
        if v_version <> new.target_version or v_status <> 'DRAFT' then
            raise exception using errcode = 'P0001', message = 'STALE_ENTITY_VERSION';
        end if;
    elsif new.target_type = 'PENDING_ACTION' then
        select version, state into v_version, v_status
        from app_private.pending_actions
        where user_id = new.user_id and action_id = new.pending_action_target_id;
        if not found then
            raise exception using errcode = 'P0001', message = 'ENTITY_NOT_FOUND';
        end if;
        if v_version <> new.target_version or v_status not in
            ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL') then
            raise exception using errcode = 'P0001', message = 'STALE_ENTITY_VERSION';
        end if;
    elsif new.target_type = 'PLAN_PROPOSAL' then
        select version, status into v_version, v_status
        from app_private.plan_proposals
        where user_id = new.user_id and proposal_id = new.proposal_target_id;
        if not found then
            raise exception using errcode = 'P0001', message = 'ENTITY_NOT_FOUND';
        end if;
        if v_version <> new.target_version or v_status <> 'PROPOSED' then
            raise exception using errcode = 'P0001', message = 'STALE_PROPOSAL';
        end if;
    else
        raise exception using errcode = 'P0001', message = 'INVALID_PARAMETER';
    end if;
    return new;
end;
$$;

drop trigger if exists trg_approval_action_validate on app_private.approval_actions;
create trigger trg_approval_action_validate
before insert or update on app_private.approval_actions
for each row execute function app_private.validate_approval_action_target();

drop trigger if exists trg_approval_action_no_delete on app_private.approval_actions;
create trigger trg_approval_action_no_delete
before delete on app_private.approval_actions
for each row execute function app_private.validate_approval_action_target();
