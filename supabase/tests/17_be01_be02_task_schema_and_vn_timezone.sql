-- BE-01 & BE-02: schema công việc Planner đã phiên bản hóa và cố định múi giờ Việt Nam (Asia/Ho_Chi_Minh).
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.q_canon(v jsonb) returns text language sql as $$ select app_private.canonical_json(v) $$;
create function pg_temp.q_req(op text, args jsonb, uid uuid, idem text, msg uuid, approval jsonb, ref jsonb) returns jsonb language sql as $$
 select jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','q17-request',
 'operation',op,'arguments',args,'attestation',null,'execution_context',jsonb_build_object(
 'conversation_id','d1710000-0000-4000-8000-000000000003','idempotency_key',idem,'approval_action',approval,
 'action_reference',ref,'trusted_context',jsonb_build_object('request_id','q17-request','message_id',msg,
 'principal',jsonb_build_object('user_id',uid),'timezone','Asia/Ho_Chi_Minh','locale','vi-VN',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))))
$$;
create function pg_temp.q_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','q17-key','user_id',req#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.q_canon(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.q_canon(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','q17-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('17',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.q_call(op text, args jsonb, idem text default 'q17-default-key-0001',
 uid uuid default 'd1710000-0000-4000-8000-000000000001', msg uuid default 'd1710000-0000-4000-8000-000000000004',
 approval jsonb default null, ref jsonb default null) returns jsonb language plpgsql as $$
declare res jsonb; req jsonb := pg_temp.q_req(op,args,uid,idem,msg,approval,ref);
begin
 if op not in ('search_tasks') then req := pg_temp.q_sign(req); end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'role','authenticated')::text,true);
 perform set_config('request.jwt.claim.sub',uid::text,true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',op) into res using req;
 exception when others then res:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role; return res;
end $$;

-- 1. Kiểm tra danh mục cột và ràng buộc bảng academic_tasks, user_profiles, time_windows.
select hasnt_column('app_private'::name, 'academic_tasks'::name, 'course_label'::name,
 'course_label has been retired from academic_tasks');
select has_column('app_private'::name, 'academic_tasks'::name, 'start_at'::name,
 'academic_tasks has start_at column');
select has_column('app_private'::name, 'academic_tasks'::name, 'color'::name,
 'academic_tasks has color column');

-- 2. Kiểm tra validator contract SQL cho BE-01 và BE-02.
select ok(app_private.matches_contract('CandidateTaskFields',
 '{"title":"Ôn tập đại số","start_at":"2026-11-06T09:00:00+07:00","estimated_minutes":90,"priority":0.5,"color":"#596CF0","description":null}'::jsonb),
 'canonical BE-01 CandidateTaskFields is accepted');
select ok(not app_private.matches_contract('CandidateTaskFields',
 '{"title":"Ôn tập","course_label":"MATH101"}'::jsonb),
 'retired course_label is rejected by CandidateTaskFields');
select ok(not app_private.matches_contract('CandidateTaskFields',
 '{"title":"Ôn tập","priority":0.75}'::jsonb),
 'non-canonical priority weight is rejected');
select ok(not app_private.matches_contract('CandidateTaskFields',
 '{"title":"Ôn tập","color":"blue"}'::jsonb),
 'non-hex color is rejected');
select ok(not app_private.matches_contract('CandidateTaskFields',
 '{"title":"Ôn tập","deadline_timezone":"UTC"}'::jsonb),
 'non-Vietnam deadline_timezone is rejected');
select ok(not app_private.matches_contract('TimeWindowInput',
 '{"kind":"AVAILABILITY","label":null,"recurrence":"NONE","timezone":"UTC","start_at":"2026-11-06T09:00:00Z","end_at":"2026-11-06T10:00:00Z","weekday":null,"start_time":null,"end_time":null,"valid_from":null,"valid_until":null}'::jsonb),
 'non-Vietnam TimeWindowInput timezone is rejected');

-- 3. Kiểm tra canonical_json hỗ trợ trọng số ưu tiên 0.1 và 0.5 cho chữ ký RPC.
select is(app_private.canonical_json('{"priority":0.1,"title":"A"}'::jsonb), '{"priority":0.1,"title":"A"}',
 'canonical_json serializes priority 0.1');
select is(app_private.canonical_json('{"priority":0.5,"title":"A"}'::jsonb), '{"priority":0.5,"title":"A"}',
 'canonical_json serializes priority 0.5');

-- 4. Kiểm tra luồng tạo candidate -> chuẩn bị -> xác nhận công việc với start_at, priority=0.5, color='#FF5733'.
insert into auth.users(id) values ('d1710000-0000-4000-8000-000000000001');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('q17-key',decode(repeat('17',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');

select ok(pg_temp.q_call('record_source_message',jsonb_build_object('message',jsonb_build_object(
 'message_id','d1710000-0000-4000-8000-000000000004','user_id','d1710000-0000-4000-8000-000000000001',
 'conversation_id','d1710000-0000-4000-8000-000000000003','source','UI','role','USER','text','Tạo việc theo mẫu mới',
 'received_at','2026-11-05T01:02:03.000004Z')))->>'outcome'='COMMITTED','record source message');

create temporary table q17(name text primary key, res jsonb);
insert into q17 values ('cand',pg_temp.q_call('create_task_candidate',jsonb_build_object('slots',jsonb_build_object(
 'title','Giải đề thi thử','description','Chương 1 đến chương 3','start_at','2026-11-06T02:00:00.000000Z',
 'estimated_minutes',90,'priority',0.5,'color','#FF5733')),'q17-cand-key-000001'));

select ok(res->>'outcome'='DRAFTED' and res#>'{data,slots,priority}'='0.5'::jsonb
 and res#>>'{data,slots,color}'='#FF5733','candidate stores numeric priority 0.5 and hex color') from q17 where name='cand';

insert into q17 select 'prep',pg_temp.q_call('prepare_pending_action',jsonb_build_object(
 'presentation',jsonb_build_object('kind','ACTION_PRESENTATION','pending_action',jsonb_build_object(
  'action_id','d1710000-0000-4000-8000-0000000000a1','user_id','d1710000-0000-4000-8000-000000000001',
  'conversation_id','d1710000-0000-4000-8000-000000000003','version',1,'intent','CREATE_TASK',
  'state','AWAITING_CONFIRMATION','requires_review',false,'candidate_id',res#>>'{data,candidate_id}',
  'proposal_id',null,'draft_arguments','{}'::jsonb,'missing_fields','[]'::jsonb,'ambiguities','[]'::jsonb,
  'depends_on_action_id',null,'created_at','2026-11-05T01:00:00.000000Z','updated_at','2026-11-05T01:00:00.000000Z'),
  'candidate',res->'data','proposal',null,'normalized_command',null,'effective_policy',null,'schedule_confirmation',null),
 'expected_action_version',null),'q17-prep-key-000001') from q17 where name='cand';

insert into q17 select 'confirm',pg_temp.q_call('confirm_task',
 jsonb_build_object('candidate_id',res#>>'{data,candidate_id}','expected_candidate_version',1),
 'q17-confirm-key-001','d1710000-0000-4000-8000-000000000001','d1710000-0000-4000-8000-000000000004',
 jsonb_build_object('approval_action_id',extensions.gen_random_uuid(),'user_id','d1710000-0000-4000-8000-000000000001',
  'target_type','TASK_CANDIDATE','target_id',res#>>'{data,candidate_id}','target_version',1,
  'decision','APPROVE','source','UI','source_message_id',null,'created_at','2026-11-05T01:00:00.000000Z'),
 jsonb_build_object('action_id','d1710000-0000-4000-8000-0000000000a1','action_version',1,
  'target_type','TASK_CANDIDATE','target_id',res#>>'{data,candidate_id}','target_version',1))
 from q17 where name='cand';

select ok(res->>'outcome'='COMMITTED'
 and app_private.matches_contract('confirm_taskResult', res)
 and res#>>'{data,start_at}'='2026-11-06T02:00:00.000000Z'
 and res#>>'{data,available_from_at}'='2026-11-06T02:00:00.000000Z'
 and res#>>'{data,deadline_at}'='2026-11-06T03:30:00.000000Z'
 and res#>>'{data,deadline_precision}'='DATETIME'
 and res#>>'{data,deadline_timezone}'='Asia/Ho_Chi_Minh'
 and res#>>'{data,estimated_minutes}'='90'
 and res#>>'{data,remaining_minutes}'='90'
 and res#>'{data,priority}'='0.5'::jsonb
 and res#>>'{data,color}'='#FF5733'
 and res#>>'{data,status}'='TODO'
 and not (res->'data' ? 'course_label'),
 'confirm_task derives scheduling fields deterministically from canonical BE-01 task slots')
 from q17 where name='confirm';

-- 5. Kiểm tra confirm_task bắt buộc start_at ngay cả khi candidate đã có deadline.
insert into q17 values ('cand_no_start',pg_temp.q_call('create_task_candidate',jsonb_build_object('slots',jsonb_build_object(
 'title','Thiếu giờ bắt đầu','deadline_precision','DATE','deadline_date','2026-11-06',
 'deadline_timezone','Asia/Ho_Chi_Minh','estimated_minutes',60)),'q17-cand2-key-0001'));
insert into q17 select 'prep_no_start',pg_temp.q_call('prepare_pending_action',jsonb_build_object(
 'presentation',jsonb_build_object('kind','ACTION_PRESENTATION','pending_action',jsonb_build_object(
  'action_id','d1710000-0000-4000-8000-0000000000a2','user_id','d1710000-0000-4000-8000-000000000001',
  'conversation_id','d1710000-0000-4000-8000-000000000003','version',1,'intent','CREATE_TASK',
  'state','AWAITING_CONFIRMATION','requires_review',false,'candidate_id',res#>>'{data,candidate_id}',
  'proposal_id',null,'draft_arguments','{}'::jsonb,'missing_fields','[]'::jsonb,'ambiguities','[]'::jsonb,
  'depends_on_action_id',null,'created_at','2026-11-05T01:00:00.000000Z','updated_at','2026-11-05T01:00:00.000000Z'),
  'candidate',res->'data','proposal',null,'normalized_command',null,'effective_policy',null,'schedule_confirmation',null),
 'expected_action_version',null),'q17-prep2-key-0001') from q17 where name='cand_no_start';
select ok(
 res->>'outcome'='ERROR'
 and res#>>'{error,code}'='MISSING_REQUIRED_FIELD'
 and res#>>'{error,field}'='start_at',
 'confirm_task rejects deadline-only candidate without start_at')
from (
 select pg_temp.q_call('confirm_task',
  jsonb_build_object('candidate_id',res#>>'{data,candidate_id}','expected_candidate_version',1),
  'q17-conf2-key-0001','d1710000-0000-4000-8000-000000000001','d1710000-0000-4000-8000-000000000004',
  jsonb_build_object('approval_action_id',extensions.gen_random_uuid(),'user_id','d1710000-0000-4000-8000-000000000001',
   'target_type','TASK_CANDIDATE','target_id',res#>>'{data,candidate_id}','target_version',1,
   'decision','APPROVE','source','UI','source_message_id',null,'created_at','2026-11-05T01:00:00.000000Z'),
  jsonb_build_object('action_id','d1710000-0000-4000-8000-0000000000a2','action_version',1,
   'target_type','TASK_CANDIDATE','target_id',res#>>'{data,candidate_id}','target_version',1)) as res
 from q17 where name='cand_no_start'
) denied;

select * from finish();
rollback;
