-- Stage 03.3 security/transaction catalog coverage.
-- These checks run in the local Supabase database; behavior requiring two
-- authenticated sessions is documented for integration coverage below.

begin;
select plan(18);

select ok(exists(select 1 from pg_trigger t join pg_class c on c.oid=t.tgrelid
                 join pg_namespace n on n.oid=c.relnamespace
                 where n.nspname='app_private' and c.relname='approval_actions'
                   and t.tgname='trg_approval_action_validate'), 'typed target validation trigger');
select ok(exists(select 1 from pg_trigger t join pg_class c on c.oid=t.tgrelid
                 join pg_namespace n on n.oid=c.relnamespace
                 where n.nspname='app_private' and c.relname='approval_actions'
                   and t.tgname='trg_approval_action_no_delete'), 'approval action immutability trigger');
select ok(exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                 where n.nspname='app_private' and p.proname='consume_chat_attestation' and p.prosecdef), 'private attestation helper is privileged');
select ok(not has_function_privilege('anon','app_private.consume_chat_attestation(uuid,uuid,text,uuid,bigint,text)','EXECUTE'), 'anon cannot consume attestations');
select ok(has_function_privilege('authenticated','app_private.consume_chat_attestation(uuid,uuid,text,uuid,bigint,text)','EXECUTE'), 'authenticated RPC path may invoke private helper');
select ok(has_function_privilege('service_role','app_api.issue_chat_approval_attestation(uuid,uuid,uuid,integer,text,uuid,integer,text,uuid,text)','EXECUTE'), 'service role may issue attestations');
select ok(not has_function_privilege('authenticated','app_api.issue_chat_approval_attestation(uuid,uuid,uuid,integer,text,uuid,integer,text,uuid,text)','EXECUTE'), 'authenticated cannot issue attestations');
select ok(exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                 where n.nspname='app_private' and p.proname='idempotency_begin'), 'idempotency begin helper');
select ok(exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
                 where n.nspname='app_private' and p.proname='idempotency_complete'), 'idempotency completion helper');
select ok(exists(select 1 from pg_constraint where conname='approval_actions_one_typed_target'), 'exactly one typed target constraint');
select ok(exists(select 1 from pg_constraint where conname='approval_actions_typed_target_check'), 'typed target correspondence constraint');
select ok(exists(select 1 from pg_constraint where conname='approval_actions_chat_source_check'), 'CHAT source-message constraint');
select ok((select c.relforcerowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace
           where n.nspname='app_private' and c.relname='chat_approval_attestations'), 'attestation RLS forced');
select ok(not exists(select 1 from information_schema.role_table_grants where table_schema='app_private'
                     and table_name='chat_approval_attestations' and grantee in ('anon','authenticated')), 'attestation table not table-granted');
select ok(exists(select 1 from pg_constraint where conname='chat_attestation_max_lifetime_check'), 'five-minute attestation bound');
select ok(exists(select 1 from pg_constraint c join pg_class t on t.oid=c.conrelid
                 join pg_namespace n on n.oid=t.relnamespace
                 where n.nspname='app_private' and t.relname='idempotency_records' and c.contype='p'), 'idempotency triple primary key');
select ok((select count(*) from pg_constraint where conname like 'fk_%_owner') >= 8, 'same-owner composite FK coverage');
select ok((select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
           where n.nspname='app_api' and p.proname in
           ('create_task_candidate','confirm_task','set_availability','set_busy_interval',
            'set_scheduling_preferences','persist_plan_proposal','approve_study_plan','reject_study_plan')) >= 8,
           'all mutation RPCs present');

select * from finish();
rollback;

-- Multi-session cases intentionally require authenticated fixtures and are run
-- by the backend integration suite: concurrent idempotency replay, concurrent
-- attestation consumption, cross-user RLS, stale proposal approval, rollback
-- after a failed block insert, and owner advisory-lock serialization.
