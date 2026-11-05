-- WP2b-2: task candidates, domain idempotency and lookup_operation_result (local pgTAP, rolled back).
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.q_canon(v jsonb) returns text language sql as $$ select app_private.canonical_json(v) $$;
create function pg_temp.q_req(op text, args jsonb, uid uuid, idem text, msg uuid) returns jsonb language sql as $$
 select jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','q10-request',
 'operation',op,'arguments',args,'attestation',null,'execution_context',jsonb_build_object(
 'conversation_id','d1010000-0000-4000-8000-000000000003','idempotency_key',idem,'approval_action',null,
 'action_reference',null,'trusted_context',jsonb_build_object('request_id','q10-request','message_id',msg,
 'principal',jsonb_build_object('user_id',uid),'timezone','Asia/Ho_Chi_Minh','locale','vi-VN',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))))
$$;
create function pg_temp.q_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','q10-key','user_id',req#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.q_canon(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.q_canon(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','q10-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('10',32),'hex'),'sha256'),'hex')));
end $$;
-- Reads carry no attestation; mutations are signed. Signing happens before the role switch.
create function pg_temp.q_call(op text, args jsonb, idem text default 'q10-default-key-0001',
 uid uuid default 'd1010000-0000-4000-8000-000000000001', msg uuid default 'd1010000-0000-4000-8000-000000000004')
 returns jsonb language plpgsql as $$
declare res jsonb; req jsonb := pg_temp.q_req(op,args,uid,idem,msg);
begin
 if op not in ('lookup_operation_result') then req := pg_temp.q_sign(req); end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'role','authenticated')::text,true);
 perform set_config('request.jwt.claim.sub',uid::text,true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',op) into res using req;
 exception when others then res:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role; return res;
end $$;
create function pg_temp.q_is(res jsonb, code text) returns boolean language sql as $$
 select coalesce(res->>'outcome'='ERROR' and res#>>'{error,code}'=code and res->'data'='null'::jsonb,false) $$;
create function pg_temp.q_msg(uid uuid default 'd1010000-0000-4000-8000-000000000001') returns jsonb language sql as $$
 select jsonb_build_object('message',jsonb_build_object('message_id','d1010000-0000-4000-8000-000000000004',
 'user_id',uid,'conversation_id','d1010000-0000-4000-8000-000000000003','source','CHAT','role','USER',
 'text','Ôn toán','received_at','2026-11-05T01:02:03.000004Z')) $$;

insert into auth.users(id) values ('d1010000-0000-4000-8000-000000000001'),('d1010000-0000-4000-8000-000000000002');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('q10-key',decode(repeat('10',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');
create temporary table q10(name text primary key, res jsonb);

-- A candidate needs a recorded source message in its conversation.
insert into q10 values ('nosource',pg_temp.q_call('create_task_candidate','{"slots":{"title":"A"}}'));
select ok(pg_temp.q_is(res,'ENTITY_NOT_FOUND'),'creating a candidate before its source message is recorded fails') from q10 where name='nosource';
select ok(not exists(select 1 from app_private.task_candidates)
 and not exists(select 1 from app_private.idempotency_records),'the failed creation left no candidate or idempotency record');
select ok(pg_temp.q_call('record_source_message',pg_temp.q_msg())->>'outcome'='COMMITTED','record the source message');
select ok(pg_temp.q_is(pg_temp.q_call('create_task_candidate','{"slots":{"title":"A"}}',null),'INVALID_PARAMETER'),
 'a null idempotency key is rejected');

-- Create, then replay with a fresh request returns the identical candidate.
insert into q10 values ('c1',pg_temp.q_call('create_task_candidate',
 '{"slots":{"title":"Ôn giải tích","estimated_minutes":90,"priority":null}}','q10-candidate-key-01'));
select ok(res->>'outcome'='DRAFTED' and res#>>'{data,status}'='DRAFT' and res#>>'{data,version}'='1'
 and res#>>'{data,source_message_id}'='d1010000-0000-4000-8000-000000000004'
 and res#>>'{data,slots,title}'='Ôn giải tích' and res#>>'{data,confirmed_task_id}' is null,
 'candidate is a version-1 DRAFT bound to the source message') from q10 where name='c1';
select ok(res#>'{data,field_sources,title}'='{"source":"USER_MESSAGE","reference":"d1010000-0000-4000-8000-000000000004"}'::jsonb
 and not (res#>'{data,field_sources}' ? 'priority'),'provenance is recorded for supplied fields only') from q10 where name='c1';
insert into q10 values ('c1_again',pg_temp.q_call('create_task_candidate',
 '{"slots":{"title":"Ôn giải tích","estimated_minutes":90,"priority":null}}','q10-candidate-key-01'));
select is(res->'data',(select res->'data' from q10 where name='c1'),'replay returns the original candidate') from q10 where name='c1_again';
select is((select count(*) from app_private.task_candidates),1::bigint,'replay creates no second candidate');
select ok(pg_temp.q_is(pg_temp.q_call('create_task_candidate','{"slots":{"title":"Khác"}}','q10-candidate-key-01'),
 'IDEMPOTENCY_CONFLICT'),'same key with a different body conflicts');
select is((select schedule_revision from app_private.user_profiles where user_id='d1010000-0000-4000-8000-000000000001'),
 0::bigint,'drafting does not change the schedule revision');

-- lookup_operation_result: found, absent, conflicting.
insert into q10 values ('l1',pg_temp.q_call('lookup_operation_result',jsonb_build_object('operation','create_task_candidate',
 'idempotency_key','q10-candidate-key-01','request_fingerprint',app_private.domain_fingerprint(
 'd1010000-0000-4000-8000-000000000001','create_task_candidate','{"slots":{"title":"Ôn giải tích","estimated_minutes":90,"priority":null}}'))));
select ok(res->>'outcome'='READ' and res#>>'{data,result,outcome}'='DRAFTED'
 and res#>>'{data,result,data,candidate_id}'=(select res#>>'{data,candidate_id}' from q10 where name='c1')
 ,'lookup returns the stored result') from q10 where name='l1';
select ok(pg_temp.q_call('lookup_operation_result',jsonb_build_object('operation','create_task_candidate',
 'idempotency_key','q10-unknown-key-0001','request_fingerprint',repeat('c',64)))#>'{data,result}'='null'::jsonb,
 'lookup of an unknown key returns null');
select ok(pg_temp.q_is(pg_temp.q_call('lookup_operation_result',jsonb_build_object('operation','create_task_candidate',
 'idempotency_key','q10-candidate-key-01','request_fingerprint',repeat('c',64))),'IDEMPOTENCY_CONFLICT'),
 'lookup with another fingerprint conflicts');
select ok(exists(select 1 from app_private.idempotency_records where idempotency_key='q10-candidate-key-01' and state='COMPLETED'
 and expires_at>=created_at+interval '7 days'-interval '1 second'),'domain record is completed and retained 7 days');

-- update_candidate_draft: versioned edit, replay-safe, owner scoped.
create function pg_temp.q_upd(version bigint, title text) returns jsonb language sql as $$
 select jsonb_build_object('candidate_id',(select res#>>'{data,candidate_id}' from q10 where name='c1'),
 'expected_candidate_version',version,'slots',jsonb_build_object('title',title),
 'raw_expressions','{}'::jsonb,'field_sources','{}'::jsonb) $$;
insert into q10 values ('u1',pg_temp.q_call('update_candidate_draft',pg_temp.q_upd(1,'Ôn giải tích chương 2')));
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,version}'='2' and res#>>'{data,slots,title}'='Ôn giải tích chương 2',
 'an edit bumps the version') from q10 where name='u1';
select is(pg_temp.q_call('update_candidate_draft',pg_temp.q_upd(1,'Ôn giải tích chương 2'))->'data',
 (select res->'data' from q10 where name='u1'),'retrying the same edit after a lost response is a replay');
select ok(pg_temp.q_is(pg_temp.q_call('update_candidate_draft',pg_temp.q_upd(1,'Nội dung khác')),'STALE_ENTITY_VERSION'),
 'an outdated version with different content is stale');
select is((select version from app_private.task_candidates),2::bigint,'stale and replayed edits do not bump the version again');
select ok(pg_temp.q_is(pg_temp.q_call('update_candidate_draft',pg_temp.q_upd(2,'Của người khác'),'q10-default-key-0001',
 'd1010000-0000-4000-8000-000000000002'),'ENTITY_NOT_FOUND'),'another owner cannot see or edit the candidate');

-- Atomicity: an internal failure after the insert rolls back candidate, idempotency record and profile changes.
create function pg_temp.q_fail() returns trigger language plpgsql as $$
begin raise exception using errcode='XX000',message='Q10_INJECTED'; end $$;
create trigger q10_fail after insert on app_private.task_candidates for each row execute function pg_temp.q_fail();
create temporary table q10_before as select (select count(*) from app_private.task_candidates) c,
 (select count(*) from app_private.idempotency_records) i;
select ok(pg_temp.q_is(pg_temp.q_call('create_task_candidate','{"slots":{"title":"Lỗi"}}','q10-fail-key-000001'),'INTERNAL_ERROR')
 and (select count(*) from app_private.task_candidates)=(select c from q10_before)
 and (select count(*) from app_private.idempotency_records)=(select i from q10_before),
 'an injected failure becomes INTERNAL_ERROR and rolls everything back');
select * from finish();
rollback;
