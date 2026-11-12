-- WP2c-3: approve_study_plan và reject_study_plan; pgTAP local, có rollback.
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.q_canon(v jsonb) returns text language sql as $$ select app_private.canonical_json(v) $$;
create function pg_temp.q_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','q16-key','user_id',req#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.q_canon(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.q_canon(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','q16-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('16',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.q_run(req jsonb) returns jsonb language plpgsql as $$
declare res jsonb; uid text := req#>>'{execution_context,trusted_context,principal,user_id}';
begin
 req := pg_temp.q_sign(req);
 perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'role','authenticated')::text,true);
 perform set_config('request.jwt.claim.sub',uid,true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',req->>'operation') into res using req;
 exception when others then res:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role; return res;
end $$;
create function pg_temp.q_is(res jsonb, code text) returns boolean language sql as $$
 select coalesce(res->>'outcome'='ERROR' and res#>>'{error,code}'=code and res->'data'='null'::jsonb,false) $$;

create function pg_temp.pid(n int) returns uuid language sql as $$ select ('d1610000-0000-4000-8000-0000000000c'||n)::uuid $$;
create function pg_temp.aid(n int) returns uuid language sql as $$ select ('d1610000-0000-4000-8000-0000000000f'||n)::uuid $$;
create function pg_temp.cid(n int) returns uuid language sql as $$ select ('d1610000-0000-4000-8000-0000000000b'||n)::uuid $$;
create function pg_temp.uid() returns uuid language sql as $$ select 'd1610000-0000-4000-8000-000000000001'::uuid $$;
create function pg_temp.tid() returns uuid language sql as $$ select 'd1610000-0000-4000-8000-0000000000a1'::uuid $$;

-- Yêu cầu quyết định cho proposal n; wrong_ver cho phép test gửi phê duyệt sai version.
create function pg_temp.q_decide(op text, n int, idem text, expected_plan bigint default null, approval_ver bigint default 1,
 with_approval boolean default true) returns jsonb language sql as $$
 select pg_temp.q_run(jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','q16-request',
 'operation',op,
 'arguments',case when op='approve_study_plan' then jsonb_build_object('proposal_id',pg_temp.pid(n),'expected_proposal_version',1,'expected_plan_version',expected_plan)
  else jsonb_build_object('proposal_id',pg_temp.pid(n),'expected_proposal_version',1) end,
 'attestation',null,'execution_context',jsonb_build_object('conversation_id',pg_temp.cid(n),'idempotency_key',idem,
 'approval_action',case when with_approval then jsonb_build_object('approval_action_id',extensions.gen_random_uuid(),'user_id',pg_temp.uid(),
   'target_type','PLAN_PROPOSAL','target_id',pg_temp.pid(n),'target_version',approval_ver,
   'decision',case when op='approve_study_plan' then 'APPROVE' else 'REJECT' end,'source','UI','source_message_id',null,
   'created_at','2026-11-05T03:00:00.000000Z') end,
 'action_reference',jsonb_build_object('action_id',pg_temp.aid(n),'action_version',1,'target_type','PLAN_PROPOSAL',
   'target_id',pg_temp.pid(n),'target_version',approval_ver),
 'trusted_context',jsonb_build_object('request_id','q16-request','message_id','d1610000-0000-4000-8000-000000000004',
 'principal',jsonb_build_object('user_id',pg_temp.uid()),'timezone','Asia/Ho_Chi_Minh','locale','vi-VN',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))))) $$;

insert into auth.users(id) values ('d1610000-0000-4000-8000-000000000001');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('q16-key',decode(repeat('16',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');
insert into app_private.user_profiles(user_id,timezone,locale,scheduling_policy)
 values (pg_temp.uid(),'Asia/Ho_Chi_Minh','vi',app_private.default_policy());
insert into app_private.academic_tasks(task_id,user_id,candidate_id,title,start_at,deadline_at,deadline_precision,deadline_date,
 deadline_timezone,estimated_minutes,remaining_minutes)
 values (pg_temp.tid(),pg_temp.uid(),extensions.gen_random_uuid(),'Bài tập','2026-11-06T00:00:00Z','2026-11-20T00:00:00Z','DATETIME',null,'Asia/Ho_Chi_Minh',600,600);

-- Proposal n: mỗi đề xuất có một action trong hội thoại riêng; block bắt đầu ngày 9+n.
create function pg_temp.q_seed(n int, rev bigint, base uuid, base_ver bigint, overlap boolean default false) returns void language plpgsql as $$
declare blocks jsonb; scope jsonb := '{"start_at":"2026-11-06T00:00:00.000000Z","end_at":"2026-11-19T00:00:00.000000Z","selection_mode":"ALL_ELIGIBLE","task_ids":[]}';
 act app_private.pending_actions; pres jsonb := '{"proposal":null,"normalized_command":null,"effective_policy":null}';
begin
 blocks := jsonb_build_array(jsonb_build_object('block_id',extensions.gen_random_uuid(),'user_id',pg_temp.uid(),'task_id',pg_temp.tid(),
   'start_at',to_char(timestamptz '2026-11-08 01:00+00'+n*interval '1 day','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
   'end_at',to_char(timestamptz '2026-11-08 02:00+00'+n*interval '1 day','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),'is_locked',false),
  jsonb_build_object('block_id',extensions.gen_random_uuid(),'user_id',pg_temp.uid(),'task_id',pg_temp.tid(),
   'start_at',to_char(timestamptz '2026-11-08 01:00+00'+n*interval '1 day'+case when overlap then interval '30 minutes' else interval '2 hours' end,'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
   'end_at',to_char(timestamptz '2026-11-08 02:00+00'+n*interval '1 day'+case when overlap then interval '30 minutes' else interval '2 hours' end,'YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),'is_locked',false));
 insert into app_private.plan_proposals(proposal_id,user_id,base_plan_id,base_plan_version,base_schedule_revision,generation_scope,payload,algorithm_version,policy_snapshot)
 values (pg_temp.pid(n),pg_temp.uid(),base,base_ver,rev,scope,jsonb_build_object('study_blocks',blocks,'task_summaries','[]'::jsonb,'coverage','FULL',
  'warnings','[]'::jsonb,'plan_diff','{"added":[],"moved":[],"removed":[],"unchanged":[]}'::jsonb),'q16-1',app_private.default_policy());
 insert into app_private.conversation_records(user_id,conversation_id) values (pg_temp.uid(),pg_temp.cid(n));
 insert into app_private.pending_actions(action_id,user_id,conversation_id,intent,state,proposal_id)
  values (pg_temp.aid(n),pg_temp.uid(),pg_temp.cid(n),'GENERATE_STUDY_PLAN','AWAITING_APPROVAL',pg_temp.pid(n)) returning * into act;
 insert into app_private.action_presentations(user_id,action_id,action_version,target_type,target_id,target_version,content_digest,presentation)
  values (pg_temp.uid(),act.action_id,act.version,'PLAN_PROPOSAL',pg_temp.pid(n),1,
   app_private.presentation_digest(act,'PLAN_PROPOSAL',pg_temp.pid(n),1,pres),pres);
end $$;
create function pg_temp.q_state() returns jsonb language sql as $$
 select jsonb_build_object('plans',(select count(*) from app_private.study_plans),'blocks',(select count(*) from app_private.study_blocks),
  'approvals',(select count(*) from app_private.approval_actions),'rev',(select schedule_revision from app_private.user_profiles where user_id=pg_temp.uid()),
  'idem',(select count(*) from app_private.idempotency_records)) $$;
create temporary table q16(name text primary key, res jsonb);

select pg_temp.q_seed(1,0,null,null);
select pg_temp.q_seed(2,0,null,null);
create temporary table q16_before as select pg_temp.q_state() s;
select ok(pg_temp.q_is(pg_temp.q_decide('approve_study_plan',1,'q16-approve-key-001',null,1,false),'APPROVAL_REQUIRED'),'approval needs a backend approval action');
select ok(pg_temp.q_is(pg_temp.q_decide('approve_study_plan',1,'q16-approve-key-001',null,7),'APPROVAL_REQUIRED'),'the approval must name the proposal version');
select is(pg_temp.q_state(),(select s from q16_before),'refused approvals wrote nothing');

insert into q16 values ('a1',pg_temp.q_decide('approve_study_plan',1,'q16-approve-key-001'));
select ok(app_private.matches_contract('approve_study_planResult',res) and res->>'outcome'='COMMITTED' and res#>>'{data,version}'='1'
 and res#>'{data,previous_plan_id}'='null'::jsonb and res#>>'{data,source_proposal_id}'=pg_temp.pid(1)::text,
 'approval commits plan version 1') from q16 where name='a1';
select ok((select count(*) from app_private.study_blocks where plan_id=(select (res#>>'{data,plan_id}')::uuid from q16 where name='a1'))=2
 and (select current_plan_id from app_private.user_profiles where user_id=pg_temp.uid())=(select (res#>>'{data,plan_id}')::uuid from q16 where name='a1')
 and (select schedule_revision from app_private.user_profiles where user_id=pg_temp.uid())=1,
 'blocks are stored, the plan is current and the schedule revision advanced');
select ok((select status from app_private.plan_proposals where proposal_id=pg_temp.pid(1))='APPROVED'
 and (select state from app_private.pending_actions where action_id=pg_temp.aid(1))='COMPLETED'
 and exists(select 1 from app_private.approval_actions where target_id=pg_temp.pid(1) and decision='APPROVE'),
 'proposal approved, action completed, approval recorded');
select is(pg_temp.q_decide('approve_study_plan',1,'q16-approve-key-001')->'data',(select res->'data' from q16 where name='a1'),'a retry replays the stored plan');
select is((select schedule_revision from app_private.user_profiles where user_id=pg_temp.uid()),1::bigint,'the replay did not advance the revision again');
select ok(pg_temp.q_is(pg_temp.q_decide('approve_study_plan',1,'q16-approve-key-002'),'STALE_PROPOSAL'),'another key cannot approve the same proposal twice');
select is((select count(*) from app_private.study_plans),1::bigint,'no second plan was created');

-- Đề xuất tạo trước lần phê duyệt đã thành STALE và giữ nguyên trạng thái đó.
select ok(pg_temp.q_is(pg_temp.q_decide('approve_study_plan',2,'q16-approve-key-003'),'STALE_PROPOSAL'),'a proposal based on an older revision is stale');
select is((select status from app_private.plan_proposals where proposal_id=pg_temp.pid(2)),'STALE','the stale status is durable');

-- Tính nguyên tử: block chồng lấn chưa bị phát hiện khi lưu đề xuất làm toàn bộ commit thất bại.
select pg_temp.q_seed(3,1,(select current_plan_id from app_private.user_profiles where user_id=pg_temp.uid()),1,true);
truncate q16_before; insert into q16_before select pg_temp.q_state();
select ok(pg_temp.q_is(pg_temp.q_decide('approve_study_plan',3,'q16-approve-key-004',1),'TIME_CONFLICT'),'overlapping blocks fail the commit');
select is(pg_temp.q_state(),(select s from q16_before),'a failed commit changed nothing');
select is((select status from app_private.plan_proposals where proposal_id=pg_temp.pid(3)),'PROPOSED','the proposal stays pending after a failed commit');

-- Từ chối.
select pg_temp.q_seed(4,1,(select current_plan_id from app_private.user_profiles where user_id=pg_temp.uid()),1);
insert into q16 values ('r1',pg_temp.q_decide('reject_study_plan',4,'q16-reject-key-0001'));
select ok(app_private.matches_contract('reject_study_planResult',res) and res->>'outcome'='REJECTED' and res#>>'{data,status}'='REJECTED',
 'rejection returns the rejected proposal') from q16 where name='r1';
select ok((select state from app_private.pending_actions where action_id=pg_temp.aid(4))='CANCELLED'
 and (select schedule_revision from app_private.user_profiles where user_id=pg_temp.uid())=1,'the action is cancelled and the revision is unchanged');
select is(pg_temp.q_decide('reject_study_plan',4,'q16-reject-key-0001')->'data',(select res->'data' from q16 where name='r1'),'a rejection retry replays');
select ok(pg_temp.q_is(pg_temp.q_decide('reject_study_plan',4,'q16-reject-key-0002'),'STALE_PROPOSAL'),'a settled proposal cannot be rejected again');

-- Phê duyệt thứ hai: bảo vệ version lịch, kiểm tra lại task rồi tạo version lịch 2.
select pg_temp.q_seed(5,1,(select current_plan_id from app_private.user_profiles where user_id=pg_temp.uid()),1);
select ok(pg_temp.q_is(pg_temp.q_decide('approve_study_plan',5,'q16-approve-key-005',9),'STALE_PLAN_VERSION'),'a wrong expected plan version is refused');
select is((select status from app_private.plan_proposals where proposal_id=pg_temp.pid(5)),'PROPOSED','the proposal stays pending after a version mismatch');
update app_private.academic_tasks set deadline_at='2026-11-10T00:00:00Z' where task_id=pg_temp.tid();
select ok(pg_temp.q_is(pg_temp.q_decide('approve_study_plan',5,'q16-approve-key-006',1),'INVALID_PARAMETER'),'a block past its task deadline is refused at approval');
update app_private.academic_tasks set deadline_at='2026-11-20T00:00:00Z' where task_id=pg_temp.tid();
insert into q16 values ('a2',pg_temp.q_decide('approve_study_plan',5,'q16-approve-key-007',1));
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,version}'='2' and res#>>'{data,previous_plan_id}'=(select res#>>'{data,plan_id}' from q16 where name='a1')
 and (select schedule_revision from app_private.user_profiles where user_id=pg_temp.uid())=2,
 'the next approval creates version 2 linked to version 1') from q16 where name='a2';
select is((select count(*) from app_private.study_blocks where plan_id=(select (res#>>'{data,plan_id}')::uuid from q16 where name='a1')),2::bigint,
 'the previous plan keeps its blocks as history');
select * from finish();
rollback;
