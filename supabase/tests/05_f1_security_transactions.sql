-- Approved F1 security catalog regression coverage.
-- Behavioral attestation, typed public failures, idempotency and rollback live
-- in 06_sol_rpc_boundary.sql. These checks do not claim two-session execution.
begin;
select no_plan();
set local search_path = public, extensions;

select ok(exists(select 1 from pg_trigger t join pg_class c on c.oid=t.tgrelid
 join pg_namespace n on n.oid=c.relnamespace where n.nspname='app_private'
 and c.relname='approval_actions' and t.tgname='trg_approval_action_validate'
 and not t.tgisinternal and t.tgenabled<>'D'),'typed approval target validation trigger');
select ok(exists(select 1 from pg_trigger t join pg_class c on c.oid=t.tgrelid
 join pg_namespace n on n.oid=c.relnamespace where n.nspname='app_private'
 and c.relname='approval_actions' and t.tgname='trg_approval_action_no_delete'
 and not t.tgisinternal and t.tgenabled<>'D'),'approval action immutability trigger');
select ok(exists(select 1 from pg_constraint c join pg_class t on t.oid=c.conrelid
 join pg_namespace n on n.oid=t.relnamespace where n.nspname='app_private'
 and t.relname='approval_actions' and c.conname=e.name and c.contype='c'),e.description)
 from (values
 ('approval_actions_one_typed_target','exactly one typed approval target constraint'),
 ('approval_actions_typed_target_check','typed approval target correspondence constraint'),
 ('approval_actions_chat_source_check','CHAT approval requires source message constraint')) e(name,description);

select ok(exists(select 1 from pg_roles where rolname='sf_rpc_owner'
 and not rolcanlogin and not rolsuper and not rolbypassrls),
 'SECURITY DEFINER owner cannot log in or bypass RLS');
select ok(not exists(select 1 from pg_roles client cross join pg_roles owner_role
 where client.rolname in ('authenticated','anon') and owner_role.rolname='sf_rpc_owner'
 and pg_has_role(client.oid,owner_role.oid,'MEMBER')),
 'client roles do not inherit RPC owner role');
select ok(not exists(select 1 from pg_roles r where r.rolname in ('authenticated','anon')
 and has_schema_privilege(r.oid,'app_private','USAGE')),
 'no client has private schema usage');
select ok(not exists(select 1 from pg_roles r cross join pg_class c
 join pg_namespace n on n.oid=c.relnamespace where r.rolname in ('authenticated','anon')
 and n.nspname='app_private' and c.relkind in ('r','p')
 and has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')),
 'no client has effective private table privileges');
select ok(not exists(select 1 from pg_roles r cross join pg_proc p
 join pg_namespace n on n.oid=p.pronamespace where r.rolname in ('authenticated','anon')
 and n.nspname='app_private' and has_function_privilege(r.oid,p.oid,'EXECUTE')),
 'no client can execute any private verifier, signing or bypass helper');
select ok(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='app_api' and p.proname in
 ('issue_chat_approval_attestation','read_scheduling_context')),
 'legacy issuer and legacy scheduling-context RPC are removed');

select ok(exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 join pg_roles r on r.oid=p.proowner where n.nspname='app_api' and p.proname=e.name
 and p.pronargs=1 and p.proargtypes[0]='jsonb'::regtype
 and p.proargnames=array['p_request']::text[] and p.prorettype='jsonb'::regtype
 and p.prosecdef and r.rolname='sf_rpc_owner'
 and coalesce('search_path=""'=any(p.proconfig),false)
 and has_function_privilege('authenticated',p.oid,'EXECUTE')
 and not has_function_privilege('anon',p.oid,'EXECUTE')),
 e.name || ' is an authenticated-only safe DEFINER p_request wrapper')
 from (values ('create_task_candidate'),('confirm_task'),('search_tasks'),
 ('set_availability'),('set_busy_interval'),('set_scheduling_preferences'),
 ('get_study_plan'),('approve_study_plan'),('reject_study_plan'),
 ('get_scheduling_context'),('persist_plan_proposal'),('prepare_pending_action'),
 ('review_pending_action'),('update_candidate_draft'),('cancel_pending_action'),
 ('record_source_message'),('claim_api_receipt'),('complete_api_receipt'),
 ('lookup_operation_result'),('renew_api_receipt'),('release_api_receipt')) e(name);
select ok(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='app_api' and (p.pronargs<>1 or p.proargtypes[0]<>'jsonb'::regtype
 or p.proargnames is distinct from array['p_request']::text[])),
 'no legacy multi-argument public overload survives');

select ok((select c.relrowsecurity and c.relforcerowsecurity
 from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='app_private' and c.relname=e.name),
 e.name || ' enables and forces RLS')
 from (values ('conversation_records'),('source_messages'),('api_request_receipts'),
 ('action_presentations'),('rpc_attestation_keys')) e(name);
select ok(exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
 join pg_roles r on r.rolname='sf_rpc_owner' where n.nspname='app_private'
 and c.relname='rpc_attestation_keys' and has_table_privilege(r.oid,c.oid,'SELECT')
 and not has_table_privilege(r.oid,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')),
 'RPC owner can verify with global keys but cannot rotate or delete them');
select ok(not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
 join pg_roles r on r.rolname='sf_rpc_owner' join pg_attribute a on a.attrelid=c.oid
 where n.nspname='app_private' and c.relname='rpc_attestation_keys'
 and a.attnum>0 and not a.attisdropped
 and has_column_privilege(r.oid,c.oid,a.attnum,'INSERT,UPDATE,REFERENCES')),
 'RPC owner has no column-level key-store write grants');
select ok(exists(select 1 from pg_policy p join pg_class c on c.oid=p.polrelid
 join pg_namespace n on n.oid=c.relnamespace join pg_roles r on r.rolname='sf_rpc_owner'
 where n.nspname='app_private' and c.relname='rpc_attestation_keys'
 and p.polcmd='r' and p.polroles=array[r.oid]),
 'global key store has a SELECT policy restricted to sf_rpc_owner');
select ok(not exists(select 1 from pg_policy p join pg_class c on c.oid=p.polrelid
 join pg_namespace n on n.oid=c.relnamespace where n.nspname='app_private'
 and c.relname='rpc_attestation_keys' and
 (0::oid=any(p.polroles) or exists(select 1 from pg_roles r
 where r.rolname in ('authenticated','anon') and r.oid=any(p.polroles)))),
 'global key store policies never admit PUBLIC or client roles');
select ok(to_regprocedure('app_private.canonical_json(jsonb)') is not null,
 'private canonical JSON implementation exists');
select ok(to_regprocedure('app_private.verify_rpc_request(jsonb,text)') is not null,
 'private exact-request verifier exists');

select * from finish();
rollback;

-- Still required separately: two-session owner-row-lock serialization and
-- concurrent idempotency, receipt lease fencing/reclaim, stale proposal approve,
-- cross-user read isolation, and failure halfway through a full plan snapshot.
-- Documentation alone is never passing evidence for these cases.
