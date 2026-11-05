-- Stage 03.3 catalog-level integrity checks (local pgTAP only).

begin;
select plan(16);

select ok((select c.relrowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace
          where n.nspname='app_private' and c.relname='academic_tasks'), 'RLS enabled on academic_tasks');
select ok((select c.relforcerowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace
          where n.nspname='app_private' and c.relname='academic_tasks'), 'RLS forced on academic_tasks');
select ok(exists(select 1 from pg_constraint where conname='fk_profiles_current_plan_owner'), 'current plan same-owner FK');
select ok(exists(select 1 from pg_constraint where conname='fk_plans_source_proposal_owner'), 'source proposal same-owner FK');
select ok(exists(select 1 from pg_constraint where conname='fk_blocks_task_owner'), 'block task same-owner FK');
select ok(exists(select 1 from pg_constraint where conname='ex_study_blocks_plan_time'), 'snapshot overlap exclusion');
select ok(exists(select 1 from pg_indexes where schemaname='app_private' and indexname='ix_pending_awaiting_conversation'), 'awaiting action partial index');
select ok(exists(select 1 from pg_constraint where conname='idempotency_expiry_check'), 'idempotency expiry check');
select ok(exists(select 1 from pg_constraint where conname='chat_attestation_max_lifetime_check'), 'attestation lifetime check');
select ok(exists(select 1 from pg_policies where schemaname='app_private' and tablename='academic_tasks' and policyname='tasks_owner_select'), 'owner task policy');
select ok(not exists(select 1 from information_schema.role_table_grants where table_schema='app_private' and table_name='chat_approval_attestations' and grantee='authenticated'), 'attestation table not granted');
select has_function(
    'app_api'::name,
    'create_task_candidate'::name,
    ARRAY['uuid', 'uuid', 'jsonb', 'jsonb', 'jsonb', 'text', 'text']::name[],
    'candidate RPC exists'
);
select has_function(
    'app_api'::name,
    'approve_study_plan'::name,
    ARRAY['uuid', 'integer', 'integer', 'text', 'uuid', 'text', 'text']::name[],
    'approval RPC exists'
);
select has_function(
    'app_api'::name,
    'issue_chat_approval_attestation'::name,
    ARRAY['uuid', 'uuid', 'uuid', 'integer', 'text', 'uuid', 'integer', 'text', 'uuid', 'text']::name[],
    'attestation RPC exists'
);
select ok(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                     where n.nspname='app_api' and p.proname='issue_chat_approval_attestation'
                       and has_function_privilege('authenticated', p.oid, 'EXECUTE')), 'authenticated cannot issue attestations');
select ok((select count(*) from pg_constraint where conname like 'fk_%_owner') >= 8, 'composite owner FK coverage');

select * from finish();
rollback;
