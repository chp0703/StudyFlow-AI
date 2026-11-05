-- Stage 03.3 / commit 05: same-owner references and immutable-snapshot guards.

create unique index uq_task_candidates_user_candidate
    on app_private.task_candidates (user_id, candidate_id);
create unique index uq_academic_tasks_user_task
    on app_private.academic_tasks (user_id, task_id);
create unique index uq_study_plans_source_proposal
    on app_private.study_plans (source_proposal_id);
create unique index uq_plan_proposals_committed_plan
    on app_private.plan_proposals (committed_plan_id)
    where committed_plan_id is not null;

alter table app_private.user_profiles
    add constraint fk_profiles_current_plan_owner
    foreign key (user_id, current_plan_id)
    references app_private.study_plans (user_id, plan_id)
    deferrable initially deferred;

alter table app_private.task_candidates
    add constraint fk_candidates_confirmed_task_owner
    foreign key (user_id, confirmed_task_id)
    references app_private.academic_tasks (user_id, task_id)
    deferrable initially deferred;

alter table app_private.academic_tasks
    add constraint fk_tasks_candidate_owner
    foreign key (user_id, candidate_id)
    references app_private.task_candidates (user_id, candidate_id)
    deferrable initially deferred;

alter table app_private.study_plans
    add constraint fk_plans_previous_owner
    foreign key (user_id, previous_plan_id)
    references app_private.study_plans (user_id, plan_id)
    deferrable initially deferred;

alter table app_private.study_plans
    add constraint fk_plans_source_proposal_owner
    foreign key (user_id, source_proposal_id)
    references app_private.plan_proposals (user_id, proposal_id)
    deferrable initially deferred;

alter table app_private.plan_proposals
    add constraint fk_proposals_base_plan_owner
    foreign key (user_id, base_plan_id)
    references app_private.study_plans (user_id, plan_id)
    deferrable initially deferred;

alter table app_private.plan_proposals
    add constraint fk_proposals_committed_plan_owner
    foreign key (user_id, committed_plan_id)
    references app_private.study_plans (user_id, plan_id)
    deferrable initially deferred;

alter table app_private.study_blocks
    add constraint fk_blocks_plan_owner
    foreign key (user_id, plan_id)
    references app_private.study_plans (user_id, plan_id)
    deferrable initially deferred;

alter table app_private.study_blocks
    add constraint fk_blocks_task_owner
    foreign key (user_id, task_id)
    references app_private.academic_tasks (user_id, task_id)
    deferrable initially deferred;

alter table app_private.pending_actions
    add constraint fk_actions_candidate_owner
    foreign key (user_id, candidate_id)
    references app_private.task_candidates (user_id, candidate_id)
    deferrable initially deferred;

alter table app_private.pending_actions
    add constraint fk_actions_proposal_owner
    foreign key (user_id, proposal_id)
    references app_private.plan_proposals (user_id, proposal_id)
    deferrable initially deferred;

alter table app_private.pending_actions
    add constraint fk_actions_dependency_owner
    foreign key (user_id, depends_on_action_id)
    references app_private.pending_actions (user_id, action_id)
    deferrable initially deferred;

alter table app_private.approval_actions
    add constraint fk_approval_candidate_owner
    foreign key (user_id, candidate_target_id)
    references app_private.task_candidates (user_id, candidate_id)
    deferrable initially deferred;

alter table app_private.approval_actions
    add constraint fk_approval_pending_owner
    foreign key (user_id, pending_action_target_id)
    references app_private.pending_actions (user_id, action_id)
    deferrable initially deferred;

alter table app_private.approval_actions
    add constraint fk_approval_proposal_owner
    foreign key (user_id, proposal_target_id)
    references app_private.plan_proposals (user_id, proposal_id)
    deferrable initially deferred;

alter table app_private.chat_approval_attestations
    add constraint fk_attestation_action_owner
    foreign key (user_id, action_id)
    references app_private.pending_actions (user_id, action_id)
    deferrable initially deferred;

alter table app_private.idempotency_records
    add constraint idempotency_expiry_check check (expires_at > created_at);

alter table app_private.chat_approval_attestations
    add constraint chat_attestation_max_lifetime_check
    check (expires_at <= issued_at + interval '5 minutes');

alter table app_private.study_blocks
    add constraint ex_study_blocks_plan_time
    exclude using gist (
        plan_id with =,
        tstzrange(start_at, end_at, '[)') with &&
    );

create or replace function app_private.touch_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at := clock_timestamp();
    return new;
end;
$$;

create trigger trg_profiles_touch_updated_at
before update on app_private.user_profiles
for each row execute function app_private.touch_updated_at();
create trigger trg_candidates_touch_updated_at
before update on app_private.task_candidates
for each row execute function app_private.touch_updated_at();
create trigger trg_tasks_touch_updated_at
before update on app_private.academic_tasks
for each row execute function app_private.touch_updated_at();
create trigger trg_windows_touch_updated_at
before update on app_private.time_windows
for each row execute function app_private.touch_updated_at();
create trigger trg_proposals_touch_updated_at
before update on app_private.plan_proposals
for each row execute function app_private.touch_updated_at();
create trigger trg_actions_touch_updated_at
before update on app_private.pending_actions
for each row execute function app_private.touch_updated_at();
