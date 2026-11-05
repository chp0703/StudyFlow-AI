-- WP2b-5: workflow context reads and continuation WAIT/ADVANCE rules (local pgTAP, rolled back).
-- Complements the 07 addendum, which covers initialize/read/ADVANCE-of-reads.
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.q_canon(v jsonb) returns text language sql as $$ select app_private.canonical_json(v) $$;
create function pg_temp.q_req(op text, args jsonb, idem text, conv uuid, msg uuid) returns jsonb language sql as $$
 select jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','q13-request',
 'operation',op,'arguments',args,'attestation',null,'execution_context',jsonb_build_object(
 'conversation_id',conv,'idempotency_key',idem,'approval_action',null,'action_reference',null,
 'trusted_context',jsonb_build_object('request_id','q13-request','message_id',msg,
 'principal',jsonb_build_object('user_id','d1310000-0000-4000-8000-000000000001'),'timezone','Asia/Ho_Chi_Minh','locale','vi-VN',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))))
$$;
create function pg_temp.q_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','q13-key','user_id',req#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.q_canon(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.q_canon(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','q13-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('13',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.q_call(op text, args jsonb, idem text default 'q13-default-key-0001',
 conv uuid default 'd1310000-0000-4000-8000-000000000003', msg uuid default 'd1310000-0000-4000-8000-000000000004')
 returns jsonb language plpgsql as $$
declare res jsonb; req jsonb := pg_temp.q_req(op,args,idem,conv,msg);
begin
 if op not like 'get\_%' then req := pg_temp.q_sign(req); end if;
 perform set_config('request.jwt.claims','{"sub":"d1310000-0000-4000-8000-000000000001","role":"authenticated"}',true);
 perform set_config('request.jwt.claim.sub','d1310000-0000-4000-8000-000000000001',true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',op) into res using req;
 exception when others then res:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role; return res;
end $$;
create function pg_temp.q_is(res jsonb, code text) returns boolean language sql as $$
 select coalesce(res->>'outcome'='ERROR' and res#>>'{error,code}'=code and res->'data'='null'::jsonb,false) $$;

insert into auth.users(id) values ('d1310000-0000-4000-8000-000000000001');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('q13-key',decode(repeat('13',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');

-- Origin: a claimed receipt and its recorded USER message, for two different conversations.
create function pg_temp.q_origin(conv uuid, key text) returns jsonb language plpgsql as $$
declare c jsonb; mid text;
begin
 c := pg_temp.q_call('claim_api_receipt',jsonb_build_object('http_operation','send_message','idempotency_key',key,
  'request_fingerprint',repeat('a',64),'conversation_id',conv),key||'-claim-0001',conv);
 mid := c#>>'{data,message_id}';
 perform pg_temp.q_call('record_source_message',jsonb_build_object('message',jsonb_build_object('message_id',mid,
  'user_id','d1310000-0000-4000-8000-000000000001','conversation_id',conv,'source','CHAT','role','USER','text','Làm hai việc',
  'received_at','2026-11-05T01:02:03.000004Z')),key||'-msg-00001',conv,mid::uuid);
 return jsonb_build_object('message_id',mid,'binding',jsonb_build_object('http_operation','send_message',
  'idempotency_key',key,'request_fingerprint',repeat('a',64),'expected_lease_version',c#>'{data,lease_version}'));
end $$;
create temporary table q13(name text primary key, res jsonb);
insert into q13 values ('o1',pg_temp.q_origin('d1310000-0000-4000-8000-000000000003','q13-origin-key-0001'));
insert into q13 values ('o2',pg_temp.q_origin('d1310000-0000-4000-8000-000000000013','q13-origin-key-0002'));

create function pg_temp.q_init(o text, conv uuid) returns jsonb language sql as $$
 select pg_temp.q_call('initialize_workflow_continuation',jsonb_build_object('conversation_id',conv,
  'source_message_id',res->>'message_id',
  'extraction','{"intents":[{"intent":"CREATE_TASK","slots":{},"raw_expressions":{},"ambiguities":[]},{"intent":"SEARCH_TASKS","slots":{"query":"x"},"raw_expressions":{},"ambiguities":[]}]}'::jsonb,
  'depends_on','[[],[0]]'::jsonb,'receipt_binding',res->'binding'),'q13-'||o||'-init-000001',conv,(res->>'message_id')::uuid)
 from q13 where name=o $$;
select ok(pg_temp.q_init('o1','d1310000-0000-4000-8000-000000000003')->>'outcome'='COMMITTED','initialize the first queue');
-- A second unfinished queue in the same conversation is refused.
insert into q13 values ('o3',pg_temp.q_origin('d1310000-0000-4000-8000-000000000003','q13-origin-key-0003'));
select ok(pg_temp.q_is(pg_temp.q_init('o3','d1310000-0000-4000-8000-000000000003'),'STALE_ENTITY_VERSION'),
 'a conversation holds at most one unfinished continuation');
select ok(pg_temp.q_init('o2','d1310000-0000-4000-8000-000000000013')->>'outcome'='COMMITTED','another conversation is independent');
select ok(pg_temp.q_is(pg_temp.q_call('initialize_workflow_continuation',jsonb_build_object('conversation_id',
 'd1310000-0000-4000-8000-000000000003','source_message_id',(select res->>'message_id' from q13 where name='o2'),
 'extraction','{"intents":[{"intent":"UNKNOWN","slots":{},"raw_expressions":{},"ambiguities":[]}]}'::jsonb,
 'depends_on','[[]]'::jsonb,'receipt_binding',(select res->'binding' from q13 where name='o1')),'q13-bad-init-00001'),
 'ENTITY_NOT_FOUND'),'a source message from another conversation is not found');

-- Workflow context: active, selected and message lookups.
insert into app_private.pending_actions(action_id,user_id,conversation_id,intent,state)
 values ('d1310000-0000-4000-8000-0000000000a1','d1310000-0000-4000-8000-000000000001','d1310000-0000-4000-8000-000000000003',
 'CREATE_TASK','AWAITING_CLARIFICATION');
insert into q13 values ('ctx',pg_temp.q_call('get_workflow_context',jsonb_build_object('conversation_id','d1310000-0000-4000-8000-000000000003',
 'action_id','d1310000-0000-4000-8000-0000000000a1','message_id',(select res->>'message_id' from q13 where name='o1'))));
select ok(res->>'outcome'='READ' and res#>>'{data,active_action,pending_action,action_id}'='d1310000-0000-4000-8000-0000000000a1'
 and res#>'{data,selected_action}'=res#>'{data,active_action}' and res#>>'{data,source_message,text}'='Làm hai việc'
 and res#>'{data,active_action,candidate}'='null'::jsonb and res#>'{data,active_action,last_presentation}'='null'::jsonb,
 'context returns the awaiting action, the selected action and the source message') from q13 where name='ctx';
select ok(pg_temp.q_is(pg_temp.q_call('get_workflow_context',jsonb_build_object('conversation_id','d1310000-0000-4000-8000-000000000003',
 'action_id','d1310000-0000-4000-8000-0000000000a9','message_id',null)),'ENTITY_NOT_FOUND'),'an unknown action is not found');
select ok(pg_temp.q_is(pg_temp.q_call('get_workflow_context',jsonb_build_object('conversation_id','d1310000-0000-4000-8000-000000000013',
 'action_id','d1310000-0000-4000-8000-0000000000a1','message_id',null)),'ENTITY_NOT_FOUND'),'an action from another conversation is not found');

-- WAIT then ADVANCE rules on the first queue.
create function pg_temp.q_cp(o text, args jsonb) returns jsonb language sql as $$
 select pg_temp.q_call('checkpoint_workflow_continuation',jsonb_build_object('conversation_id',
  'd1310000-0000-4000-8000-000000000003','source_message_id',res->>'message_id','receipt_binding',res->'binding') || args,
  'q13-cp-'||md5(args::text),'d1310000-0000-4000-8000-000000000003',(res->>'message_id')::uuid) from q13 where name='o1' $$;
create function pg_temp.q_step(i int) returns text language sql as $$
 select app_private.step_key('q13-origin-key-0001',(select (res->>'message_id')::uuid from q13 where name='o1'),i) $$;
create function pg_temp.q_ref(v bigint) returns jsonb language sql as $$
 select jsonb_build_object('action_id','d1310000-0000-4000-8000-0000000000a1','action_version',v,
  'target_type','PENDING_ACTION','target_id','d1310000-0000-4000-8000-0000000000a1','target_version',1) $$;
select ok(pg_temp.q_is(pg_temp.q_cp('o1',jsonb_build_object('expected_version',1,'expected_cursor',0,'transition','WAIT',
 'action_reference',pg_temp.q_ref(7),'outcome',null)),'STALE_ENTITY_VERSION'),'WAIT with an outdated action version is stale');
insert into q13 values ('w1',pg_temp.q_cp('o1',jsonb_build_object('expected_version',1,'expected_cursor',0,'transition','WAIT',
 'action_reference',pg_temp.q_ref(1),'outcome',null)));
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,version}'='2' and res#>>'{data,cursor}'='0'
 and res#>'{data,awaiting_reference}'=pg_temp.q_ref(1),'WAIT parks on the awaiting action without moving the cursor') from q13 where name='w1';
select is(pg_temp.q_cp('o1',jsonb_build_object('expected_version',1,'expected_cursor',0,'transition','WAIT',
 'action_reference',pg_temp.q_ref(1),'outcome',null))->'data',(select res->'data' from q13 where name='w1'),'a repeated WAIT is a replay');
create function pg_temp.q_out(i int, disp text, op text) returns jsonb language sql as $$
 select jsonb_build_object('intent_index',i,'step_key',pg_temp.q_step(i),'operation',op,'disposition',disp,'result',
  case when disp='SUCCEEDED' then jsonb_build_object('schema_version','1.1','request_id','q13-r','outcome','READ',
   'data',jsonb_build_object('items','[]'::jsonb,'next_cursor',null),'error',null,'warnings','[]'::jsonb) end,'error',null) $$;
select ok(pg_temp.q_is(pg_temp.q_cp('o1',jsonb_build_object('expected_version',2,'expected_cursor',0,'transition','ADVANCE',
 'action_reference',null,'outcome',pg_temp.q_out(0,'REJECTED',null))),'INVALID_PARAMETER'),
 'ADVANCE is refused while the awaited action is still open');
update app_private.pending_actions set state='CANCELLED' where action_id='d1310000-0000-4000-8000-0000000000a1';
select ok((pg_temp.q_cp('o1',jsonb_build_object('expected_version',2,'expected_cursor',0,'transition','ADVANCE',
 'action_reference',null,'outcome',pg_temp.q_out(0,'REJECTED',null)))#>>'{data,cursor}')='1','after cancellation the step records REJECTED and advances');
select ok(pg_temp.q_is(pg_temp.q_cp('o1',jsonb_build_object('expected_version',3,'expected_cursor',1,'transition','ADVANCE',
 'action_reference',null,'outcome',pg_temp.q_out(1,'SUCCEEDED','search_tasks'))),'INVALID_PARAMETER'),
 'a step cannot succeed when its dependency was rejected');
select ok(pg_temp.q_cp('o1',jsonb_build_object('expected_version',3,'expected_cursor',1,'transition','ADVANCE',
 'action_reference',null,'outcome',pg_temp.q_out(1,'DEPENDENCY_CANCELLED',null)))#>>'{data,cursor}'='2',
 'the dependent step is recorded as cancelled and the queue finishes');
select ok(pg_temp.q_is(pg_temp.q_cp('o1',jsonb_build_object('expected_version',4,'expected_cursor',2,'transition','ADVANCE',
 'action_reference',null,'outcome',pg_temp.q_out(1,'DEPENDENCY_CANCELLED',null))),'STALE_ENTITY_VERSION'),'a finished queue accepts no more steps');
select ok(pg_temp.q_call('get_workflow_continuation',jsonb_build_object('conversation_id','d1310000-0000-4000-8000-000000000003',
 'source_message_id',null))#>'{data,continuation}'='null'::jsonb,'the finished queue frees the conversation for a new one');
select ok(pg_temp.q_init('o3','d1310000-0000-4000-8000-000000000003')->>'outcome'='COMMITTED','a new queue can start after the old one finished');
select * from finish();
rollback;
