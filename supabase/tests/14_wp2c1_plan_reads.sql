-- WP2c-1: get_scheduling_context and get_study_plan (local pgTAP, rolled back).
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.q_canon(v jsonb) returns text language sql as $$ select app_private.canonical_json(v) $$;
create function pg_temp.q_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','q14-key','user_id',req#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.q_canon(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.q_canon(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','q14-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('14',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.q_call(op text, args jsonb, uid uuid default 'd1410000-0000-4000-8000-000000000001') returns jsonb
language plpgsql as $$
declare res jsonb; req jsonb := jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','q14-request',
 'operation',op,'arguments',args,'attestation',null,'execution_context',jsonb_build_object(
 'conversation_id',null,'idempotency_key',null,'approval_action',null,'action_reference',null,
 'trusted_context',jsonb_build_object('request_id','q14-request','message_id','d1410000-0000-4000-8000-000000000004',
 'principal',jsonb_build_object('user_id',uid),'timezone','Asia/Ho_Chi_Minh','locale','vi-VN',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))));
begin
 if op not like 'get\_%' then req := pg_temp.q_sign(req); end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'role','authenticated')::text,true);
 perform set_config('request.jwt.claim.sub',uid::text,true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',op) into res using req;
 exception when others then res:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role; return res;
end $$;
create function pg_temp.q_is(res jsonb, code text) returns boolean language sql as $$
 select coalesce(res->>'outcome'='ERROR' and res#>>'{error,code}'=code and res->'data'='null'::jsonb,false) $$;

insert into auth.users(id) values ('d1410000-0000-4000-8000-000000000001'),('d1410000-0000-4000-8000-000000000002');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('q14-key',decode(repeat('14',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');

create function pg_temp.q_scope(mode text, ids jsonb default '[]') returns jsonb language sql as $$
 select jsonb_build_object('generation_scope',jsonb_build_object('start_at','2026-11-06T00:00:00.000000Z',
  'end_at','2026-11-13T00:00:00.000000Z','selection_mode',mode,'task_ids',ids)) $$;

-- Before bootstrap there is no profile to read.
select ok(pg_temp.q_is(pg_temp.q_call('get_scheduling_context',pg_temp.q_scope('ALL_ELIGIBLE')),'ENTITY_NOT_FOUND'),
 'scheduling context needs an initialized user');
select ok(pg_temp.q_call('ensure_user_context','{}')->>'outcome'='COMMITTED','bootstrap the profile');
create temporary table q14(name text primary key, res jsonb);
insert into q14 values ('empty',pg_temp.q_call('get_scheduling_context',pg_temp.q_scope('ALL_ELIGIBLE')));
select ok(app_private.matches_contract('get_scheduling_contextInternalResult',res) and res#>>'{data,schedule_revision}'='0'
 and res#>'{data,tasks}'='[]'::jsonb and res#>'{data,base_plan,plan}'='null'::jsonb,
 'an empty snapshot is contract-valid with a null base plan') from q14 where name='empty';
select ok(pg_temp.q_is(pg_temp.q_call('get_scheduling_context',pg_temp.q_scope('SELECTED_TASKS',
 '["d1410000-0000-4000-8000-0000000000f1"]')),'ENTITY_NOT_FOUND'),'a selected task that does not exist is not found');
select ok(pg_temp.q_is(pg_temp.q_call('get_scheduling_context',jsonb_build_object('generation_scope',jsonb_build_object(
 'start_at','2026-11-13T00:00:00.000000Z','end_at','2026-11-06T00:00:00.000000Z','selection_mode','ALL_ELIGIBLE','task_ids','[]'))),
 'INVALID_PARAMETER'),'an inverted generation window is rejected');

insert into app_private.user_profiles(user_id,timezone,locale,scheduling_policy)
 values ('d1410000-0000-4000-8000-000000000002','Asia/Ho_Chi_Minh','vi',app_private.default_policy());
-- Seed a task, an active and an archived window, and an approved plan with two blocks.
insert into app_private.academic_tasks(task_id,user_id,candidate_id,title,deadline_at,deadline_precision,deadline_date,
 deadline_timezone,estimated_minutes,remaining_minutes) values
 ('d1410000-0000-4000-8000-0000000000a1','d1410000-0000-4000-8000-000000000001',extensions.gen_random_uuid(),'Bài tập',
  '2026-11-12T00:00:00Z','DATETIME',null,'UTC',120,120),
 ('d1410000-0000-4000-8000-0000000000a2','d1410000-0000-4000-8000-000000000002',extensions.gen_random_uuid(),'Của người khác',
  '2026-11-12T00:00:00Z','DATETIME',null,'UTC',60,60);
insert into app_private.time_windows(window_id,user_id,kind,recurrence,timezone,weekday,start_time,end_time,valid_from,archived_at)
 values ('d1410000-0000-4000-8000-0000000000b1','d1410000-0000-4000-8000-000000000001','AVAILABILITY','WEEKLY','Asia/Ho_Chi_Minh',1,'08:00','10:00','2026-11-01',null),
 ('d1410000-0000-4000-8000-0000000000b2','d1410000-0000-4000-8000-000000000001','AVAILABILITY','WEEKLY','Asia/Ho_Chi_Minh',2,'08:00','10:00','2026-11-01',clock_timestamp());
insert into app_private.plan_proposals(proposal_id,user_id,base_schedule_revision,generation_scope,payload,algorithm_version,policy_snapshot)
 values ('d1410000-0000-4000-8000-0000000000c1','d1410000-0000-4000-8000-000000000001',0,
 (pg_temp.q_scope('ALL_ELIGIBLE')->'generation_scope'),
 '{"study_blocks":[],"task_summaries":[],"coverage":"FULL","warnings":[],"plan_diff":{"added":[],"moved":[],"removed":[],"unchanged":[]}}',
 'q14-1',app_private.default_policy());
insert into app_private.study_plans(plan_id,user_id,version,source_proposal_id)
 values ('d1410000-0000-4000-8000-0000000000d1','d1410000-0000-4000-8000-000000000001',1,'d1410000-0000-4000-8000-0000000000c1');
insert into app_private.study_blocks(plan_id,block_id,user_id,task_id,start_at,end_at) values
 ('d1410000-0000-4000-8000-0000000000d1','d1410000-0000-4000-8000-0000000000e1','d1410000-0000-4000-8000-000000000001','d1410000-0000-4000-8000-0000000000a1','2026-11-09T01:00:00Z','2026-11-09T02:00:00Z'),
 ('d1410000-0000-4000-8000-0000000000d1','d1410000-0000-4000-8000-0000000000e2','d1410000-0000-4000-8000-000000000001','d1410000-0000-4000-8000-0000000000a1','2026-11-10T01:00:00Z','2026-11-10T02:00:00Z');
update app_private.user_profiles set current_plan_id='d1410000-0000-4000-8000-0000000000d1'
 where user_id='d1410000-0000-4000-8000-000000000001';

insert into q14 values ('ctx',pg_temp.q_call('get_scheduling_context',pg_temp.q_scope('SELECTED_TASKS','["d1410000-0000-4000-8000-0000000000a1"]')));
select ok(app_private.matches_contract('get_scheduling_contextInternalResult',res)
 and jsonb_array_length(res#>'{data,tasks}')=1 and res#>>'{data,tasks,0,title}'='Bài tập'
 and jsonb_array_length(res#>'{data,time_windows}')=1 and jsonb_array_length(res#>'{data,base_plan,study_blocks}')=2
 and res#>>'{data,base_plan,plan,version}'='1','snapshot holds only the owner tasks, active windows and the full base plan')
 from q14 where name='ctx';
select ok(pg_temp.q_is(pg_temp.q_call('get_scheduling_context',pg_temp.q_scope('SELECTED_TASKS',
 '["d1410000-0000-4000-8000-0000000000a2"]')),'ENTITY_NOT_FOUND'),'another owner''s task cannot be selected');

create function pg_temp.q_plan(v text, ver int, pid text, s text, e text) returns jsonb language sql as $$
 select pg_temp.q_call('get_study_plan',jsonb_build_object('view',v,'version',ver,'proposal_id',pid,'start_at',s,'end_at',e)) $$;
insert into q14 values ('cur',pg_temp.q_plan('CURRENT',null,null,null,null));
select ok(app_private.matches_contract('get_study_planResult',res) and res#>>'{data,kind}'='PLAN_VIEW'
 and jsonb_array_length(res#>'{data,study_blocks}')=2 and res#>>'{data,study_blocks,0,block_id}'='d1410000-0000-4000-8000-0000000000e1',
 'CURRENT returns the plan with its blocks in time order') from q14 where name='cur';
insert into q14 values ('win',pg_temp.q_plan('CURRENT',null,null,'2026-11-10T00:00:00.000000Z','2026-11-11T00:00:00.000000Z'));
select ok(jsonb_array_length(res#>'{data,study_blocks}')=1 and res#>>'{data,plan,version}'='1',
 'a time window filters blocks but keeps the plan metadata') from q14 where name='win';
select is(pg_temp.q_plan('HISTORY',1,null,null,null)->'data',(select res->'data' from q14 where name='cur'),'HISTORY by version matches');
select ok(pg_temp.q_is(pg_temp.q_plan('HISTORY',9,null,null,null),'ENTITY_NOT_FOUND'),'an unknown version is not found');
insert into q14 values ('prop',pg_temp.q_plan('PROPOSAL',null,'d1410000-0000-4000-8000-0000000000c1',null,null));
select ok(app_private.matches_contract('get_study_planResult',res) and res#>>'{data,kind}'='PROPOSAL_VIEW'
 and res#>>'{data,proposal,status}'='PROPOSED','PROPOSAL returns the full stored proposal') from q14 where name='prop';
select ok(pg_temp.q_is(pg_temp.q_plan('PROPOSAL',null,'d1410000-0000-4000-8000-0000000000c1','2026-11-10T00:00:00.000000Z','2026-11-11T00:00:00.000000Z'),
 'INVALID_PARAMETER'),'a proposal view rejects a time window');
select ok(pg_temp.q_is(pg_temp.q_call('get_study_plan',jsonb_build_object('view','PROPOSAL','version',null,
 'proposal_id','d1410000-0000-4000-8000-0000000000c1','start_at',null,'end_at',null),'d1410000-0000-4000-8000-000000000002'),
 'ENTITY_NOT_FOUND'),'another owner cannot see the proposal');
select ok(pg_temp.q_call('get_study_plan',jsonb_build_object('view','CURRENT','version',null,'proposal_id',null,
 'start_at',null,'end_at',null),'d1410000-0000-4000-8000-000000000002')#>'{data,plan}'='null'::jsonb
 or pg_temp.q_is(pg_temp.q_call('get_study_plan',jsonb_build_object('view','CURRENT','version',null,'proposal_id',null,
 'start_at',null,'end_at',null),'d1410000-0000-4000-8000-000000000002'),'ENTITY_NOT_FOUND') ,'another owner never sees this plan');
select * from finish();
rollback;
