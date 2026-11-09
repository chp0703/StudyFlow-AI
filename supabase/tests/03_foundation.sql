-- Nền tảng contract F1 đã duyệt, dùng pgTAP local.
-- Chỉ chạy `supabase test db` với database local, không dùng đích từ xa.

begin;
select plan(19);

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
select has_table('app_private'::name, 'conversation_records'::name);
select has_table('app_private'::name, 'source_messages'::name);
select has_table('app_private'::name, 'api_request_receipts'::name);
select has_table('app_private'::name, 'action_presentations'::name);
select has_table('app_private'::name, 'rpc_attestation_keys'::name);
select has_table('app_private'::name, 'workflow_continuations'::name);
select has_index(
    'app_private'::name,
    'study_blocks'::name,
    'ex_study_blocks_plan_time'::name
);

select * from finish();
rollback;
