-- Stage 03.3 local pgTAP smoke checks.
-- Run only with `supabase test db` against a local database. No remote target.

begin;
select plan(14);

select has_schema('app_private');
select has_schema('app_api');
select has_table('app_private', 'user_profiles');
select has_table('app_private', 'task_candidates');
select has_table('app_private', 'academic_tasks');
select has_table('app_private', 'time_windows');
select has_table('app_private', 'study_plans');
select has_table('app_private', 'study_blocks');
select has_table('app_private', 'plan_proposals');
select has_table('app_private', 'pending_actions');
select has_table('app_private', 'approval_actions');
select has_table('app_private', 'idempotency_records');
select has_table('app_private', 'chat_approval_attestations');
select has_index('app_private', 'study_blocks', 'ex_study_blocks_plan_time');

select * from finish();
rollback;
