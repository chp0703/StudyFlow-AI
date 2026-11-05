-- Independent approved-contract acceptance suite (Sol).
-- Run: supabase test db supabase/tests/06_sol_rpc_boundary.sql
-- Requires a disposable local Supabase PostgreSQL 15 database with all migrations.
-- Every fixture, synthetic signing key, trigger and mutation is rolled back.
-- This file intentionally FAILS against the pre-contract eight-migration baseline.
-- It does not certify HTTP JWT validation, duplicate raw envelope keys, timing-safe
-- comparison, two-session locking, or production key provisioning.
begin;
select no_plan();
set local search_path = public, extensions;
set local timezone = 'UTC';

create temporary table sol_expected_rpc(name text primary key);
insert into sol_expected_rpc values
 ('create_task_candidate'), ('confirm_task'), ('search_tasks'),
 ('set_availability'), ('set_busy_interval'), ('set_scheduling_preferences'),
 ('get_study_plan'), ('approve_study_plan'), ('reject_study_plan'),
 ('get_scheduling_context'), ('persist_plan_proposal'),
 ('prepare_pending_action'), ('review_pending_action'), ('update_candidate_draft'),
 ('cancel_pending_action'), ('record_source_message'), ('claim_api_receipt'),
 ('complete_api_receipt'), ('lookup_operation_result'),
 ('renew_api_receipt'), ('release_api_receipt');

select ok(exists(select 1 from pg_roles where rolname='sf_rpc_owner'
 and not rolcanlogin and not rolsuper and not rolbypassrls),
 'RPC owner exists and is NOLOGIN NOSUPERUSER NOBYPASSRLS');
select ok(not exists(select 1 from pg_roles member cross join pg_roles parent
 where member.rolname in ('anon','authenticated') and parent.rolname='sf_rpc_owner'
 and pg_has_role(member.oid,parent.oid,'MEMBER')),
 'client roles cannot assume sf_rpc_owner');
select ok(not exists(select 1 from pg_roles r where r.rolname in ('anon','authenticated')
 and has_schema_privilege(r.oid,'app_private','USAGE')),
 'anon and authenticated have no private schema USAGE');
select ok(has_schema_privilege('authenticated','app_api','USAGE'),
 'authenticated can use public RPC schema');
select ok(not exists(select 1 from pg_roles r cross join pg_namespace n
 where r.rolname in ('anon','authenticated') and n.nspname in ('app_api','app_private')
 and has_schema_privilege(r.oid,n.oid,'CREATE')),
 'clients cannot install objects in either application schema');
select ok(not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
 cross join pg_roles r where n.nspname='app_private' and c.relkind in ('r','p')
 and r.rolname in ('anon','authenticated')
 and has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')),
 'client roles have no effective private table privileges');
select ok(not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
 join pg_attribute a on a.attrelid=c.oid cross join pg_roles r
 where n.nspname='app_private' and c.relkind in ('r','p') and a.attnum>0 and not a.attisdropped
 and r.rolname in ('anon','authenticated')
 and has_column_privilege(r.oid,c.oid,a.attnum,'SELECT,INSERT,UPDATE,REFERENCES')),
 'column grants cannot bypass the private table boundary');
select ok(not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
 cross join pg_roles r where n.nspname='app_private' and c.relkind='S'
 and r.rolname in ('anon','authenticated')
 and has_sequence_privilege(r.oid,c.oid,'SELECT,USAGE,UPDATE')),
 'client roles have no private sequence privileges');
select ok(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 cross join pg_roles r where n.nspname='app_private' and r.rolname in ('anon','authenticated')
 and has_function_privilege(r.oid,p.oid,'EXECUTE')),
 'client roles cannot execute any private helper, including old bypass helpers');
select ok(not exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='app_private' and c.relkind in ('r','p')
 and (not c.relrowsecurity or not c.relforcerowsecurity)),
 'every private table enables and forces RLS');

select ok(exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='app_api' and p.proname=e.name and p.pronargs=1
 and p.proargtypes[0]='jsonb'::regtype and p.proargnames=array['p_request']::text[]
 and p.prorettype='jsonb'::regtype), e.name || ' takes exactly p_request jsonb and returns jsonb')
 from sol_expected_rpc e order by e.name;
select ok(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='app_api' and
 (not exists(select 1 from sol_expected_rpc e where e.name=p.proname)
 or p.pronargs<>1 or p.proargtypes[0]<>'jsonb'::regtype
 or p.proargnames is distinct from array['p_request']::text[])),
 'old overloads, legacy issuer and unregistered public RPCs are removed');
select ok(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 join pg_roles r on r.oid=p.proowner where n.nspname='app_api'
 and (not p.prosecdef or r.rolname<>'sf_rpc_owner'
 or not coalesce('search_path=""'=any(p.proconfig),false))),
 'all public wrappers are DEFINER owned by sf_rpc_owner with empty search_path');
select ok(not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='app_api' and
 (not has_function_privilege('authenticated',p.oid,'EXECUTE')
 or has_function_privilege('anon',p.oid,'EXECUTE')
 or exists(select 1 from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
 where a.grantee=0 and a.privilege_type='EXECUTE'))),
 'only authenticated clients can execute public wrappers (including inherited PUBLIC grants)');
select ok(to_regprocedure('app_private.canonical_json(jsonb)') is not null,
 'agreed canonical_json(jsonb) interoperability helper exists');
select ok(to_regprocedure('app_private.verify_rpc_request(jsonb,text)') is not null,
 'agreed verify_rpc_request(jsonb,text) helper exists');
select ok(to_regclass('app_private.rpc_attestation_keys') is not null,
 'approved global private key store exists');

-- Capture failures as data so missing implementations are failed TAP assertions,
-- rather than aborted scripts or false-positive security rejections.
create function pg_temp.sol_canonical(value jsonb) returns text
language plpgsql as $$
declare result text;
begin
 execute 'select app_private.canonical_json($1)' into result using value;
 return result;
exception when others then return 'SQL_ERROR:' || sqlstate || ':' || sqlerrm;
end $$;

-- Golden bytes produced independently with UTF-8 + .NET SHA256/HMACSHA256.
-- U+E000 must sort BEFORE U+1F600 (UTF-16/locale sorting is incorrect).
create temporary table sol_golden(input jsonb, canonical text, digest text,
 payload text, signature text);
insert into sol_golden values (
 '{"😀":"astral","z":1,"nested":{"á":"Tiếng Việt 🧠","a":"line\nquote\"slash\\"},"":"bmp","a":[true,false,null,-9007199254740991,0,9007199254740991]}',
 '{"a":[true,false,null,-9007199254740991,0,9007199254740991],"nested":{"a":"line\nquote\"slash\\","á":"Tiếng Việt 🧠"},"z":1,"":"bmp","😀":"astral"}',
 '50cb56d0c888cfbac8125e353a939b34ea4569871bf70a539420b587024b3946',
 'eyJhIjpbdHJ1ZSxmYWxzZSxudWxsLC05MDA3MTk5MjU0NzQwOTkxLDAsOTAwNzE5OTI1NDc0MDk5MV0sIm5lc3RlZCI6eyJhIjoibGluZVxucXVvdGVcInNsYXNoXFwiLCLDoSI6IlRp4bq_bmcgVmnhu4d0IPCfp6AifSwieiI6MSwi7oCAIjoiYm1wIiwi8J-YgCI6ImFzdHJhbCJ9',
 '37af53662b952e7ca5dedb379d1a419f4427e324ee167ec9d821caac31134269');
select is(pg_temp.sol_canonical(input),canonical,
 'Unicode code point order, UTF-8, escaping, arrays, bool/null and safe integer golden bytes') from sol_golden;
select is(encode(extensions.digest(convert_to(pg_temp.sol_canonical(input),'UTF8'),'sha256'),'hex'),digest,
 'canonical SHA256 golden vector') from sol_golden;
select is(rtrim(translate(replace(encode(convert_to(canonical,'UTF8'),'base64'),E'\n',''),'+/','-_'),'='),payload,
 'unpadded base64url golden vector') from sol_golden;
select is(encode(extensions.hmac(convert_to(payload,'UTF8'),
 decode('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f','hex'),'sha256'),'hex'),signature,
 'HMAC signs ASCII base64url payload, not decoded JSON') from sol_golden;
select ok(pg_temp.sol_canonical(value) like 'SQL_ERROR:22023:%', label)
 from (values ('1.25'::jsonb,'fractional number is rejected'),
 ('1.0'::jsonb,'decimal lexical form is rejected'),
 ('9007199254740992'::jsonb,'integer above safe maximum is rejected'),
 ('-9007199254740992'::jsonb,'integer below safe minimum is rejected'),
 ('{"nested":[{"bad":0.5}]}'::jsonb,'numeric restrictions apply recursively')) v(value,label);

-- Test-only setup uses migration privileges, never production signing material.
-- Dynamic insert permits informative TAP failures on the old baseline.
create function pg_temp.sol_seed() returns text language plpgsql as $$
begin
 insert into auth.users(id) values
 ('d0610000-0000-4000-8000-000000000001'),
 ('d0610000-0000-4000-8000-000000000002');
 execute $q$insert into app_private.rpc_attestation_keys
 (key_id,key_material,not_before,not_after) values
 ('sol-local-fixture-only',decode('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f','hex'),
 clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour')$q$;
 return 'OK';
exception when others then return 'SQL_ERROR:' || sqlstate || ':' || sqlerrm;
end $$;
select is(pg_temp.sol_seed(),'OK','seed synthetic local-only key and two users');
select ok(not exists(select 1 from pg_roles r join pg_class c
 on c.oid=to_regclass('app_private.rpc_attestation_keys')
 where r.rolname='sf_rpc_owner' and
 (not has_table_privilege(r.oid,c.oid,'SELECT')
 or has_table_privilege(r.oid,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE'))),
 'RPC owner reads key store but cannot rotate or delete keys');

create function pg_temp.sol_request(operation text, arguments jsonb,
 owner_id uuid default 'd0610000-0000-4000-8000-000000000001',
 idem text default 'sol-candidate-idempotency-0001') returns jsonb language sql as $$
 select jsonb_build_object('contract_version','1.0.0','schema_version','1.1',
 'request_id','sol-request-0001','operation',operation,'arguments',arguments,
 'execution_context',jsonb_build_object(
 'conversation_id','d0610000-0000-4000-8000-000000000003',
 'idempotency_key',idem,'approval_action',null,'action_reference',null,
 'trusted_context',jsonb_build_object('request_id','sol-request-0001',
 'message_id','d0610000-0000-4000-8000-000000000004','principal',
 jsonb_build_object('user_id',owner_id),'received_at',
 to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'timezone','Asia/Ho_Chi_Minh','locale','vi-VN')),'attestation',null)
$$;
create function pg_temp.sol_sign(request jsonb, payload_patch jsonb default '{}')
 returns jsonb language plpgsql as $$
declare payload_json jsonb; payload text; stamp timestamptz := clock_timestamp();
begin
 payload_json := jsonb_build_object('v',1,'key_id','sol-local-fixture-only',
 'user_id',request#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',request->>'operation','request_id',request->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.sol_canonical(request-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"')) || payload_patch;
 payload := rtrim(translate(replace(encode(convert_to(pg_temp.sol_canonical(payload_json),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(request,'{attestation}',jsonb_build_object('key_id','sol-local-fixture-only',
 'payload',payload,'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),
 decode('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f','hex'),'sha256'),'hex')));
end $$;
create function pg_temp.sol_raw_attestation(request jsonb, payload_text text)
 returns jsonb language plpgsql as $$
declare payload text;
begin
 payload := rtrim(translate(replace(encode(convert_to(payload_text,'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(request,'{attestation}',jsonb_build_object('key_id','sol-local-fixture-only',
 'payload',payload,'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),
 decode('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f','hex'),'sha256'),'hex')));
end $$;
create function pg_temp.sol_call(routine text, request jsonb, verifier boolean default false)
 returns jsonb language plpgsql as $$
declare response jsonb; owner_id uuid;
begin
 perform set_config('request.jwt.claims',
 '{"sub":"d0610000-0000-4000-8000-000000000001","role":"authenticated"}',true);
 perform set_config('request.jwt.claim.sub','d0610000-0000-4000-8000-000000000001',true);
 if verifier then
   -- Invoke as migration owner: private verifier must not be exposed to clients.
   begin
     execute 'select app_private.verify_rpc_request($1,$2)' into owner_id using request,routine;
     return jsonb_build_object('verified_user',owner_id);
   exception when others then
     return jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm);
   end;
 end if;
 set local role authenticated;
 begin
   execute format('select app_api.%I($1)',routine) into response using request;
 exception when others then
   response := jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm);
 end;
 reset role;
 return response;
end $$;
create function pg_temp.sol_rejected(response jsonb) returns boolean language sql as $$
 select coalesce(response->>'outcome'='ERROR' and response->'data'='null'::jsonb
 and response#>>'{error,code}' in ('FORBIDDEN','UNAUTHENTICATED'),false)
$$;
create function pg_temp.sol_private_rejected(response jsonb) returns boolean language sql as $$
 select coalesce(response->>'sqlstate' in ('42501','28000')
 and response->>'message' in ('FORBIDDEN','UNAUTHENTICATED'),false)
$$;

-- Full logical snapshot detects changes to existing rows as well as inserts.
create function pg_temp.sol_snapshot() returns jsonb language plpgsql as $$
declare item record; rows jsonb; result jsonb := '{}';
begin
 for item in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='app_private' and c.relkind in ('r','p')
 and c.relname<>'rpc_attestation_keys' order by c.relname loop
   execute format('select coalesce(jsonb_agg(v order by v::text),''[]''::jsonb) from (select to_jsonb(t) v from app_private.%I t) x',item.relname) into rows;
   result := result || jsonb_build_object(item.relname,rows);
 end loop;
 return result;
end $$;
create temporary table sol_requests(name text primary key, request jsonb);
insert into sol_requests values ('valid',pg_temp.sol_sign(pg_temp.sol_request(
 'create_task_candidate','{"slots":{"title":"Ôn toán 🧠"}}')));
insert into sol_requests select 'missing',jsonb_set(request,'{attestation}','null') from sol_requests where name='valid';
insert into sol_requests select 'forged',jsonb_set(request,'{attestation,signature}',to_jsonb(repeat('0',64))) from sol_requests where name='valid';
insert into sol_requests select 'tampered',jsonb_set(request,'{arguments,slots,title}','"Changed after signing"') from sol_requests where name='valid';
insert into sol_requests select 'cross-owner',pg_temp.sol_sign(pg_temp.sol_request(
 'create_task_candidate','{"slots":{}}','d0610000-0000-4000-8000-000000000002'));
insert into sol_requests select 'wrong-rpc',pg_temp.sol_sign(request,jsonb_build_object('rpc','confirm_task')) from sol_requests where name='valid';
insert into sol_requests select 'wrong-request-id',pg_temp.sol_sign(request,'{"request_id":"another-request"}') from sol_requests where name='valid';
insert into sol_requests select 'unknown-payload-field',pg_temp.sol_sign(request,'{"unexpected":true}') from sol_requests where name='valid';
insert into sol_requests select 'wrong-key-id',jsonb_set(request,'{attestation,key_id}','"unknown-key"') from sol_requests where name='valid';
-- Raw duplicate keys must be checked BEFORE payload JSON is coerced to jsonb.
insert into sol_requests select 'duplicate-payload-key',pg_temp.sol_raw_attestation(request,
 '{"v":1,' || substring(convert_from(decode(translate(request#>>'{attestation,payload}','-_','+/') ||
 repeat('=',(4-length(request#>>'{attestation,payload}')%4)%4),'base64'),'UTF8') from 2))
 from sol_requests where name='valid';
insert into sol_requests select 'expired',pg_temp.sol_sign(request,jsonb_build_object(
 'issued_at',to_char((clock_timestamp()-interval '2 minutes') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((clock_timestamp()-interval '1 minute') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))) from sol_requests where name='valid';
insert into sol_requests select 'future',pg_temp.sol_sign(request,jsonb_build_object(
 'issued_at',to_char((clock_timestamp()+interval '20 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((clock_timestamp()+interval '80 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))) from sol_requests where name='valid';
insert into sol_requests select 'wrong-ttl',pg_temp.sol_sign(request,jsonb_build_object(
 'expires_at',to_char((clock_timestamp()+interval '5 minutes') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))) from sol_requests where name='valid';

create temporary table sol_before as select pg_temp.sol_snapshot() snapshot;
select is(pg_temp.sol_call('create_task_candidate',request,true)->>'verified_user',
 'd0610000-0000-4000-8000-000000000001','valid HMAC verifies exact authenticated user') from sol_requests where name='valid';
select ok(pg_temp.sol_private_rejected(pg_temp.sol_call('create_task_candidate',request,true)),
 'private verifier rejects ' || name || ' specifically as authentication/authorization failure')
 from sol_requests where name<>'valid' order by name;
select ok(pg_temp.sol_rejected(pg_temp.sol_call('create_task_candidate',request)),
 'public wrapper returns typed security ErrorResult for ' || name)
 from sol_requests where name in ('missing','forged','tampered','cross-owner') order by name;
select is(pg_temp.sol_snapshot(),snapshot,'invalid security requests leave all private business state unchanged') from sol_before;

-- Seed infrastructure through the actual attested RPC, rather than bypassing the
-- required source-message ownership link with a fabricated UUID.
create temporary table sol_results(name text primary key, response jsonb);
insert into sol_results select 'source',pg_temp.sol_call('record_source_message',
 pg_temp.sol_sign(pg_temp.sol_request('record_source_message',jsonb_build_object('message',
 jsonb_build_object('message_id','d0610000-0000-4000-8000-000000000004',
 'user_id','d0610000-0000-4000-8000-000000000001',
 'conversation_id','d0610000-0000-4000-8000-000000000003','source','UI','role','USER',
 'text','Ôn toán 🧠','received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))),
 'd0610000-0000-4000-8000-000000000001','sol-source-idempotency-00001')));
select ok(response->>'outcome'='COMMITTED' and response->'error'='null'::jsonb,
 'attested source-message RPC succeeds') from sol_results where name='source';
insert into sol_results select 'first',pg_temp.sol_call('create_task_candidate',request) from sol_requests where name='valid';
insert into sol_results select 'replay',pg_temp.sol_call('create_task_candidate',
 pg_temp.sol_sign(jsonb_set(jsonb_set(request,'{request_id}','"sol-retry-0002"'),
 '{execution_context,trusted_context,request_id}','"sol-retry-0002"')))
 from sol_requests where name='valid';
select is(response->>'outcome','DRAFTED','signed candidate creation returns approved ToolResult') from sol_results where name='first';
select is(response#>>'{data,user_id}','d0610000-0000-4000-8000-000000000001',
 'candidate result is owned by authenticated principal') from sol_results where name='first';
select is(response#>>'{data,source_message_id}','d0610000-0000-4000-8000-000000000004',
 'candidate result refers to persisted trusted source message') from sol_results where name='first';
select is(response#>>'{data,slots,title}','Ôn toán 🧠',
 'Unicode candidate slots survive DB and ToolResult serialization') from sol_results where name='first';
select is(response->>'outcome','DRAFTED','replay retains the successful operation outcome') from sol_results where name='replay';
select is((select response->'data' from sol_results where name='replay'),
 (select response->'data' from sol_results where name='first'),
 'freshly attested retry with same business key preserves original candidate and audit fields');
select is((select count(*) from app_private.task_candidates where user_id='d0610000-0000-4000-8000-000000000001'),
 1::bigint,'retry persists exactly one candidate');
select is((select count(*) from app_private.idempotency_records
 where user_id='d0610000-0000-4000-8000-000000000001' and operation='create_task_candidate'
 and idempotency_key='sol-candidate-idempotency-0001'),1::bigint,
 'candidate retry uses one durable domain idempotency record');
select ok(exists(select 1 from app_private.idempotency_records
 where user_id='d0610000-0000-4000-8000-000000000001' and operation='create_task_candidate'
 and idempotency_key='sol-candidate-idempotency-0001' and state='COMPLETED'
 and expires_at>=created_at+interval '7 days'-interval '1 second'),
 'completed domain replay is retained for seven days (one second clock tolerance)');
select is((select schedule_revision from app_private.user_profiles
 where user_id='d0610000-0000-4000-8000-000000000001'),0::bigint,
 'source-message and candidate drafts do not increase scheduling revision');
truncate sol_before;
insert into sol_before select pg_temp.sol_snapshot();
insert into sol_results select 'conflict',pg_temp.sol_call('create_task_candidate',
 pg_temp.sol_sign(jsonb_set(request,'{arguments,slots,title}','"Different business body"')))
 from sol_requests where name='valid';
select is(response#>>'{error,code}','IDEMPOTENCY_CONFLICT',
 'same key with changed signed arguments conflicts') from sol_results where name='conflict';
select is(pg_temp.sol_snapshot(),snapshot,
 'idempotency conflict leaves original result and all business state unchanged') from sol_before;

-- Inject failure after candidate insertion. A broken wrapper which catches SQL
-- errors outside the write subtransaction must not retain candidate/idempotency.
create function pg_temp.sol_fail_candidate() returns trigger language plpgsql as $$
-- Use an internal-error SQLSTATE: 23514 would legitimately be interpreted as
-- input constraint validation, making an INTERNAL_ERROR expectation ambiguous.
begin raise exception using errcode='XX000',message='SOL_TEST_INJECTED_FAILURE'; end $$;
create trigger sol_injected_failure after insert on app_private.task_candidates
 for each row execute function pg_temp.sol_fail_candidate();
truncate sol_before;
insert into sol_before select pg_temp.sol_snapshot();
insert into sol_results select 'rollback',pg_temp.sol_call('create_task_candidate',
 pg_temp.sol_sign(jsonb_set(request,'{execution_context,idempotency_key}','"sol-rollback-idempotency-0001"')))
 from sol_requests where name='valid';
select ok(response->>'outcome'='ERROR' and response->'data'='null'::jsonb
 and response#>>'{error,code}'='INTERNAL_ERROR',
 'injected database failure becomes typed INTERNAL_ERROR') from sol_results where name='rollback';
select is(pg_temp.sol_snapshot(),snapshot,
 'failed mutation atomically rolls back candidate, idempotency and profile changes') from sol_before;

select * from finish();
rollback;
