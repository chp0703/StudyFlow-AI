-- Hàm kiểm tra schema contract WP2a từ gói được sinh tự động; chỉ dùng pgTAP local.
begin;
select plan(8);
set local search_path = public, extensions;

select ok(app_private.matches_contract('create_task_candidateArguments',
  '{"slots":{"title":"Ôn toán"}}'::jsonb),'valid arguments match the approved definition');
select ok(not app_private.matches_contract('create_task_candidateArguments',
  '{"slots":{"title":"x"},"owner":"someone"}'::jsonb),'unknown argument fields are rejected');
select ok(not app_private.matches_contract('create_task_candidateArguments',
  '{"slots":{"title":5}}'::jsonb),'wrong slot types are rejected');
select ok(not app_private.matches_contract('NoSuchDefinition','{}'::jsonb),
  'unknown definitions fail closed');
select ok(not app_private.matches_contract('RpcEnvelope','{"attestation":null}'::jsonb),
  'incomplete envelopes are rejected');
select is(length(app_private.contract_schema_digest()),64,'bundle records its source digest');
select ok(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  cross join pg_roles r where n.nspname='app_private' and p.proname in
  ('matches_contract','contract_defs','contract_schema_digest') and r.rolname in ('anon','authenticated')
  and has_function_privilege(r.oid,p.oid,'EXECUTE')),'clients cannot execute the validators');
select ok(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  join pg_roles r on r.oid=p.proowner where n.nspname='app_private' and p.proname in
  ('matches_contract','contract_defs','contract_schema_digest','canonical_json','verify_rpc_request',
   'current_uid','error_result','security_error') and r.rolname<>'sf_rpc_owner'),
  'WP2a helpers are owned by the RPC owner');
select * from finish();
rollback;
