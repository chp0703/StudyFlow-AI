-- Local-only BE-04 authorization, replay and extraction fencing. Synthetic data; rollback.
begin;
select no_plan();
set local search_path = public, extensions;
create function pg_temp.b4_canon(v jsonb) returns text language sql as $$ select app_private.canonical_json(v) $$;
create function pg_temp.b4_req(op text, args jsonb, conv uuid default 'd1940000-0000-4000-8000-000000000003',
 msg uuid default 'd1940000-0000-4000-8000-000000000004') returns jsonb language sql as $$
 select jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','b4-request',
 'operation',op,'arguments',args,'attestation',null,'execution_context',jsonb_build_object(
 'conversation_id',conv,'idempotency_key','b4-child-key-000001','approval_action',null,'action_reference',null,
 'trusted_context',jsonb_build_object('request_id','b4-request','message_id',msg,
 'principal',jsonb_build_object('user_id','d1940000-0000-4000-8000-000000000001'),
 'timezone','Asia/Ho_Chi_Minh','locale','vi-VN',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))))
$$;
create function pg_temp.b4_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','b4-key','user_id','d1940000-0000-4000-8000-000000000001',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.b4_canon(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.b4_canon(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','b4-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('19',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.b4_call(op text, args jsonb) returns jsonb language plpgsql as $$
declare res jsonb; signed jsonb := case when op='get_ingestion_source' then pg_temp.b4_req(op,args) else pg_temp.b4_sign(pg_temp.b4_req(op,args)) end;
begin
 perform set_config('request.jwt.claims','{"sub":"d1940000-0000-4000-8000-000000000001","role":"authenticated"}',true);
 perform set_config('request.jwt.claim.sub','d1940000-0000-4000-8000-000000000001',true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',op) into res using signed;
 exception when others then res:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role; return res;
end $$;

insert into auth.users(id) values ('d1940000-0000-4000-8000-000000000001');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('b4-key',decode(repeat('19',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');
create function pg_temp.b4_lookup() returns jsonb language sql as $$
 select '{"source_id":"d1940000-0000-4000-8000-000000000006","conversation_id":"d1940000-0000-4000-8000-000000000003"}'::jsonb $$;
create function pg_temp.b4_upload() returns jsonb language sql as $$
 select pg_temp.b4_lookup() || '{"filename":"tasks.txt","mime_type":"text/plain","content_base64":"aGk=","size_bytes":2,"sha256":"8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"}'::jsonb $$;
create function pg_temp.b4_complete(version bigint) returns jsonb language sql as $$
 select pg_temp.b4_lookup() || jsonb_build_object('expected_lease_version',version,'error_code',null,'extraction',
 '{"parser":"document-v1","model":"deepseek-flash","prompt_version":"be04-1","extracted_at":"2026-11-13T09:00:00Z","usage":{"input_tokens":10,"output_tokens":20},"intents":[{"intent":"CREATE_TASK","slots":{"title":"Homework"},"raw_expressions":{},"ambiguities":[]}]}'::jsonb) $$;
create temporary table b4(name text primary key,result jsonb);
select ok(not has_table_privilege('authenticated','app_private.ingestion_sources','SELECT'),'no direct source reads');
select ok(not has_table_privilege('authenticated','app_private.ingestion_sources','INSERT'),'no direct source writes');
select ok((select relforcerowsecurity from pg_class where oid='app_private.ingestion_sources'::regclass),'source FORCE RLS');
insert into b4 values('upload',pg_temp.b4_call('store_ingestion_source',pg_temp.b4_upload()));
select is(result->>'outcome','COMMITTED','upload stored') from b4 where name='upload';
select is(result#>>'{data,status}','UPLOADED','upload is a source, not a confirmed task') from b4 where name='upload';
select ok(not (result->'data' ? 'content_base64'),'public source excludes raw bytes') from b4 where name='upload';
select is(pg_temp.b4_call('store_ingestion_source',pg_temp.b4_upload())->>'outcome','READ','same upload ID replays');
select is(pg_temp.b4_call('store_ingestion_source',pg_temp.b4_upload()||'{"filename":"different.txt"}')#>>'{error,code}',
 'IDEMPOTENCY_CONFLICT','different upload conflicts');
select is(pg_temp.b4_call('get_ingestion_source',pg_temp.b4_lookup()||'{"conversation_id":"d1940000-0000-4000-8000-000000000099"}')#>>'{error,code}',
 'ENTITY_NOT_FOUND','foreign conversation cannot read source');
insert into b4 values('claim',pg_temp.b4_call('claim_source_extraction',pg_temp.b4_lookup()));
select is(result#>>'{data,source,lease_version}','1','fenced extraction lease') from b4 where name='claim';
select is(result#>>'{data,content_base64}','aGk=','internal claim reads bytes') from b4 where name='claim';
select is(pg_temp.b4_call('claim_source_extraction',pg_temp.b4_lookup())#>>'{error,code}','SERVICE_UNAVAILABLE','concurrent claim refused');
update app_private.ingestion_sources set lease_until=clock_timestamp()-interval '1 second' where source_id='d1940000-0000-4000-8000-000000000006';
select is(pg_temp.b4_call('claim_source_extraction',pg_temp.b4_lookup())#>>'{data,source,lease_version}','2','expired worker fenced');
select is(pg_temp.b4_call('complete_source_extraction',pg_temp.b4_complete(1))#>>'{error,code}','STALE_ENTITY_VERSION','old worker cannot finish');
insert into b4 values('done',pg_temp.b4_call('complete_source_extraction',pg_temp.b4_complete(2)));
select is(result#>>'{data,status}','READY','extraction saved') from b4 where name='done';
select ok((select content is null from app_private.ingestion_sources where source_id='d1940000-0000-4000-8000-000000000006'),'raw bytes cleared');
select ok(pg_temp.b4_call('claim_source_extraction',pg_temp.b4_lookup())#>'{data,content_base64}'='null'::jsonb,'READY result reused without paid call');
select is((select count(*) from app_private.academic_tasks where user_id='d1940000-0000-4000-8000-000000000001'),0::bigint,'no task created');
select is((select count(*) from app_private.time_windows where user_id='d1940000-0000-4000-8000-000000000001'),0::bigint,'no busy interval imported');
select ok(pg_temp.b4_call('record_source_message',jsonb_build_object('message',jsonb_build_object(
 'message_id','d1940000-0000-4000-8000-000000000004','user_id','d1940000-0000-4000-8000-000000000001',
 'conversation_id','d1940000-0000-4000-8000-000000000003','source','CHAT','role','USER','text','Use source','received_at',app_private.iso(clock_timestamp())),
 'source_ids',jsonb_build_array('d1940000-0000-4000-8000-000000000006')))->>'outcome'='COMMITTED','source lineage bound');
select is((select count(*) from app_private.message_source_links where user_id='d1940000-0000-4000-8000-000000000001'),1::bigint,'one message link');
-- A valid source with no tasks is still READY and binds to a chat message.
insert into b4 values('empty_upload',pg_temp.b4_call('store_ingestion_source',
 pg_temp.b4_upload()||'{"source_id":"d1940000-0000-4000-8000-000000000007"}'));
insert into b4 values('empty_claim',pg_temp.b4_call('claim_source_extraction',
 pg_temp.b4_lookup()||'{"source_id":"d1940000-0000-4000-8000-000000000007"}'));
insert into b4 values('empty_done',pg_temp.b4_call('complete_source_extraction',
 jsonb_set(pg_temp.b4_complete(1),'{extraction,intents}','[]')||'{"source_id":"d1940000-0000-4000-8000-000000000007"}'));
select is(result#>>'{data,status}','READY','empty extraction is successful') from b4 where name='empty_done';
select is(result#>'{data,extraction,intents}','[]'::jsonb,'empty intents preserved') from b4 where name='empty_done';
select ok((select content is null from app_private.ingestion_sources where source_id='d1940000-0000-4000-8000-000000000007'),
 'empty extraction also clears source bytes');
select * from finish();
rollback;
