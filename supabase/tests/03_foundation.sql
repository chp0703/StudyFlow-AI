-- Stage 03.3 local pgTAP smoke checks.
-- Run only with `supabase test db` against a local database. No remote target.

begin;
select plan(14);

select has_schema('app_private');
select has_schema('app_api');
select has_table('app_private'::name, 'user_profiles'::name);
select has_table('app_private'::name, 'task_candidates'::name);
select has_table('app_private'::name, 'academic_tasks'::name);
select has_table('app_private'::name, 'time_windows'::name);
select has_table('app_private'::name, 'study_plans'::name);
select has_table('app_private'::name, 'study_blocks'::name);
select has_table('app_private'::name, 'plan_proposals'::name);
select has_table('app_private'::name, 'pending_actions'::name);
select has_table('app_private'::name, 'approval_actions'::name);
select has_table('app_private'::name, 'idempotency_records'::name);
select has_table('app_private'::name, 'chat_approval_attestations'::name);
select has_index(
    'app_private'::name,
    'study_blocks'::name,
    'ex_study_blocks_plan_time'::name
);

select * from finish();
rollback;
