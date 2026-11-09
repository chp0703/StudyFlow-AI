-- Stage 03.3 / commit 06: database boundary for authenticated owner access.
-- app_private is intentionally absent from supabase/config.toml exposed schemas.

revoke all on schema app_private from public;
revoke all on schema app_api from public;
grant usage on schema app_private to authenticated;
grant usage on schema app_api to authenticated;

alter table app_private.user_profiles enable row level security;
alter table app_private.task_candidates enable row level security;
alter table app_private.academic_tasks enable row level security;
alter table app_private.time_windows enable row level security;
alter table app_private.study_plans enable row level security;
alter table app_private.study_blocks enable row level security;
alter table app_private.plan_proposals enable row level security;
alter table app_private.pending_actions enable row level security;
alter table app_private.approval_actions enable row level security;
alter table app_private.idempotency_records enable row level security;
alter table app_private.chat_approval_attestations enable row level security;

alter table app_private.user_profiles force row level security;
alter table app_private.task_candidates force row level security;
alter table app_private.academic_tasks force row level security;
alter table app_private.time_windows force row level security;
alter table app_private.study_plans force row level security;
alter table app_private.study_blocks force row level security;
alter table app_private.plan_proposals force row level security;
alter table app_private.pending_actions force row level security;
alter table app_private.approval_actions force row level security;
alter table app_private.idempotency_records force row level security;
alter table app_private.chat_approval_attestations force row level security;

create policy user_profiles_owner_select on app_private.user_profiles
    for select to authenticated using (user_id = auth.uid());
create policy user_profiles_owner_update on app_private.user_profiles
    for update to authenticated using (user_id = auth.uid())
    with check (user_id = auth.uid());

create policy candidates_owner_select on app_private.task_candidates
    for select to authenticated using (user_id = auth.uid());
create policy candidates_owner_insert on app_private.task_candidates
    for insert to authenticated with check (auth.uid() is not null and user_id = auth.uid());
create policy candidates_owner_update on app_private.task_candidates
    for update to authenticated using (user_id = auth.uid())
    with check (user_id = auth.uid());

create policy tasks_owner_select on app_private.academic_tasks
    for select to authenticated using (user_id = auth.uid());
create policy tasks_owner_insert on app_private.academic_tasks
    for insert to authenticated with check (auth.uid() is not null and user_id = auth.uid());

create policy windows_owner_select on app_private.time_windows
    for select to authenticated using (user_id = auth.uid());
create policy windows_owner_insert on app_private.time_windows
    for insert to authenticated with check (auth.uid() is not null and user_id = auth.uid());
create policy windows_owner_update on app_private.time_windows
    for update to authenticated using (user_id = auth.uid())
    with check (user_id = auth.uid());

create policy plans_owner_select on app_private.study_plans
    for select to authenticated using (user_id = auth.uid());
create policy plans_owner_insert on app_private.study_plans
    for insert to authenticated with check (auth.uid() is not null and user_id = auth.uid());

create policy blocks_owner_select on app_private.study_blocks
    for select to authenticated using (user_id = auth.uid());
create policy blocks_owner_insert on app_private.study_blocks
    for insert to authenticated with check (auth.uid() is not null and user_id = auth.uid());

create policy proposals_owner_select on app_private.plan_proposals
    for select to authenticated using (user_id = auth.uid());
create policy proposals_owner_insert on app_private.plan_proposals
    for insert to authenticated with check (auth.uid() is not null and user_id = auth.uid());
create policy proposals_owner_update on app_private.plan_proposals
    for update to authenticated using (user_id = auth.uid())
    with check (user_id = auth.uid());

create policy pending_owner_select on app_private.pending_actions
    for select to authenticated using (user_id = auth.uid());
create policy pending_owner_insert on app_private.pending_actions
    for insert to authenticated with check (auth.uid() is not null and user_id = auth.uid());
create policy pending_owner_update on app_private.pending_actions
    for update to authenticated using (user_id = auth.uid())
    with check (user_id = auth.uid());

create policy approvals_owner_select on app_private.approval_actions
    for select to authenticated using (user_id = auth.uid());
create policy approvals_owner_insert on app_private.approval_actions
    for insert to authenticated with check (auth.uid() is not null and user_id = auth.uid());

create policy idempotency_owner_select on app_private.idempotency_records
    for select to authenticated using (user_id = auth.uid());
create policy idempotency_owner_insert on app_private.idempotency_records
    for insert to authenticated with check (auth.uid() is not null and user_id = auth.uid());
create policy idempotency_owner_update on app_private.idempotency_records
    for update to authenticated using (user_id = auth.uid())
    with check (user_id = auth.uid());

revoke all on all tables in schema app_private from public;
revoke all on all sequences in schema app_private from public;
grant select, update on app_private.user_profiles to authenticated;
grant select, insert, update on app_private.task_candidates to authenticated;
grant select, insert on app_private.academic_tasks to authenticated;
grant select, insert, update on app_private.time_windows to authenticated;
grant select, insert on app_private.study_plans to authenticated;
grant select, insert on app_private.study_blocks to authenticated;
grant select, insert, update on app_private.plan_proposals to authenticated;
grant select, insert, update on app_private.pending_actions to authenticated;
grant select, insert on app_private.approval_actions to authenticated;
grant select, insert, update on app_private.idempotency_records to authenticated;
revoke all on app_private.chat_approval_attestations from authenticated, anon, public;

revoke all on all functions in schema app_api from public;
revoke all on all functions in schema app_private from public;
