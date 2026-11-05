-- WP2c-2: persist_plan_proposal (local pgTAP, rolled back).
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.q_canon(v jsonb) returns text language sql as $$ select app_private.canonical_json(v) $$;
create function pg_temp.q_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','q15-key','user_id',req#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.q_canon(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.q_canon(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','q15-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('15',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.q_call(op text, args jsonb, idem text default 'q15-default-key-0001', uid uuid default 'd1510000-0000-4000-8000-000000000001') returns jsonb
language plpgsql as $$
declare res jsonb; req jsonb := jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','q15-request',
 'operation',op,'arguments',args,'attestation',null,'execution_context',jsonb_build_object(
 'conversation_id',null,'idempotency_key',idem,'approval_action',null,'action_reference',null,
 'trusted_context',jsonb_build_object('request_id','q15-request','message_id','d1510000-0000-4000-8000-000000000004',
 'principal',jsonb_build_object('user_id',uid),'timezone','Asia/Ho_Chi_Minh','locale','vi-VN',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))));
begin
 if op not like 'get\_%' and op<>'lookup_operation_result' then req := pg_temp.q_sign(req); end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'role','authenticated')::text,true);
 perform set_config('request.jwt.claim.sub',uid::text,true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',op) into res using req;
 exception when others then res:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role; return res;
end $$;
create function pg_temp.q_is(res jsonb, code text) returns boolean language sql as $$
 select coalesce(res->>'outcome'='ERROR' and res#>>'{error,code}'=code and res->'data'='null'::jsonb,false) $$;

insert into auth.users(id) values ('d1510000-0000-4000-8000-000000000001'),('d1510000-0000-4000-8000-000000000002');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('q15-key',decode(repeat('15',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');
select ok(pg_temp.q_call('ensure_user_context','{}',null)->>'outcome'='COMMITTED','bootstrap the profile');
insert into app_private.user_profiles(user_id,timezone,locale,scheduling_policy)
 values ('d1510000-0000-4000-8000-000000000002','Asia/Ho_Chi_Minh','vi',app_private.default_policy());
insert into app_private.academic_tasks(task_id,user_id,candidate_id,title,deadline_at,deadline_precision,deadline_date,
 deadline_timezone,estimated_minutes,remaining_minutes) values
 ('d1510000-0000-4000-8000-0000000000a1','d1510000-0000-4000-8000-000000000001',extensions.gen_random_uuid(),'Bài tập',
  '2026-11-12T00:00:00Z','DATETIME',null,'UTC',120,120),
 ('d1510000-0000-4000-8000-0000000000a2','d1510000-0000-4000-8000-000000000002',extensions.gen_random_uuid(),'Của người khác',
  '2026-11-12T00:00:00Z','DATETIME',null,'UTC',60,60);

create function pg_temp.q_cmd(over jsonb default '{}') returns jsonb language sql as $$
 select jsonb_build_object('generation_scope',jsonb_build_object('start_at','2026-11-06T00:00:00.000000Z',
  'end_at','2026-11-13T00:00:00.000000Z','selection_mode','ALL_ELIGIBLE','task_ids','[]'::jsonb),'policy_overrides',over) $$;
-- Two disjoint one-hour blocks for task a1 unless overridden.
create function pg_temp.q_prop(pid text, blocks jsonb default null, rev int default 0, cmd jsonb default null,
 policy jsonb default null) returns jsonb language sql as $$
 select jsonb_build_object('proposal_id',pid,'user_id','d1510000-0000-4000-8000-000000000001','version',1,'status','PROPOSED',
  'base_plan_id',null,'base_plan_version',null,'base_schedule_revision',rev,
  'generation_scope',coalesce(cmd,pg_temp.q_cmd())->'generation_scope',
  'payload',jsonb_build_object('study_blocks',coalesce(blocks,jsonb_build_array(
    jsonb_build_object('block_id','d1510000-0000-4000-8000-0000000000e1','user_id','d1510000-0000-4000-8000-000000000001',
     'task_id','d1510000-0000-4000-8000-0000000000a1','start_at','2026-11-09T01:00:00.000000Z','end_at','2026-11-09T02:00:00.000000Z','is_locked',false),
    jsonb_build_object('block_id','d1510000-0000-4000-8000-0000000000e2','user_id','d1510000-0000-4000-8000-000000000001',
     'task_id','d1510000-0000-4000-8000-0000000000a1','start_at','2026-11-10T01:00:00.000000Z','end_at','2026-11-10T02:00:00.000000Z','is_locked',false))),
   'task_summaries','[]'::jsonb,'coverage','FULL','warnings','[]'::jsonb,
   'plan_diff','{"added":[],"moved":[],"removed":[],"unchanged":[]}'::jsonb),
  'algorithm_version','q15-1','policy_snapshot',coalesce(policy,app_private.default_policy()),
  'generated_at','2026-11-05T03:00:00.000000Z','committed_plan_id',null,
  'created_at','2026-11-05T03:00:00.000000Z','updated_at','2026-11-05T03:00:00.000000Z') $$;
create function pg_temp.q_persist(prop jsonb, cmd jsonb default null, idem text default 'q15-gen-key-000001') returns jsonb language sql as $$
 select pg_temp.q_call('persist_plan_proposal',jsonb_build_object('command_arguments',coalesce(cmd,pg_temp.q_cmd()),'proposal',prop),idem) $$;
create temporary table q15(name text primary key, res jsonb);
create temporary table q15_before as select (select count(*) from app_private.plan_proposals) p,(select count(*) from app_private.idempotency_records) i;

-- Rejections leave nothing behind.
select ok(pg_temp.q_is(pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c1'),pg_temp.q_cmd('{"max_block_minutes":60}')),'INVALID_PARAMETER'),
 'a proposal whose policy does not match the command overrides is rejected');
select ok(pg_temp.q_is(pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c1',null,0,null,'{"min_block_minutes":25,"max_block_minutes":45,"allow_short_final_block":true,"max_daily_minutes":240,"break_minutes":10}')),'INVALID_PARAMETER'),
 'a self-declared policy snapshot is not trusted');
select ok(pg_temp.q_is(pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c1',null,3)),'STALE_PROPOSAL'),
 'a proposal built on another schedule revision is stale');
select ok(pg_temp.q_is(pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c1','[{"block_id":"d1510000-0000-4000-8000-0000000000e1","user_id":"d1510000-0000-4000-8000-000000000002","task_id":"d1510000-0000-4000-8000-0000000000a1","start_at":"2026-11-09T01:00:00.000000Z","end_at":"2026-11-09T02:00:00.000000Z","is_locked":false}]')),'INVALID_PARAMETER'),
 'a block owned by someone else is rejected');
select ok(pg_temp.q_is(pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c1','[{"block_id":"d1510000-0000-4000-8000-0000000000e1","user_id":"d1510000-0000-4000-8000-000000000001","task_id":"d1510000-0000-4000-8000-0000000000a1","start_at":"2026-11-09T01:00:00.000000Z","end_at":"2026-11-09T02:00:00.000000Z","is_locked":false},{"block_id":"d1510000-0000-4000-8000-0000000000e2","user_id":"d1510000-0000-4000-8000-000000000001","task_id":"d1510000-0000-4000-8000-0000000000a1","start_at":"2026-11-09T01:30:00.000000Z","end_at":"2026-11-09T02:30:00.000000Z","is_locked":false}]')),'TIME_CONFLICT'),
 'overlapping blocks are a time conflict');
select ok(pg_temp.q_is(pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c1','[{"block_id":"d1510000-0000-4000-8000-0000000000e1","user_id":"d1510000-0000-4000-8000-000000000001","task_id":"d1510000-0000-4000-8000-0000000000a2","start_at":"2026-11-09T01:00:00.000000Z","end_at":"2026-11-09T02:00:00.000000Z","is_locked":false}]')),'ENTITY_NOT_FOUND'),
 'a block for another owner''s task is not found');
select ok(pg_temp.q_is(pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c1','[{"block_id":"d1510000-0000-4000-8000-0000000000e1","user_id":"d1510000-0000-4000-8000-000000000001","task_id":"d1510000-0000-4000-8000-0000000000a1","start_at":"2026-11-20T01:00:00.000000Z","end_at":"2026-11-20T02:00:00.000000Z","is_locked":false}]')),'INVALID_PARAMETER'),
 'a block outside the generation window is rejected');
select ok(pg_temp.q_is(pg_temp.q_call('persist_plan_proposal',jsonb_build_object('command_arguments',pg_temp.q_cmd(),
 'proposal',pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c1')),null),'INVALID_PARAMETER'),'a missing idempotency key is rejected');
select ok((select count(*) from app_private.plan_proposals)=(select p from q15_before)
 and (select count(*) from app_private.idempotency_records)=(select i from q15_before),'rejected proposals wrote no proposal or idempotency record');

-- Accepted, replayed and conflicting.
insert into q15 values ('p1',pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c1')));
select ok(app_private.matches_contract('generate_study_planResult',res) and res->>'outcome'='PROPOSED'
 and res#>>'{data,proposal_id}'='d1510000-0000-4000-8000-0000000000c1' and res#>>'{data,base_schedule_revision}'='0',
 'a valid proposal is stored and returned as PROPOSED') from q15 where name='p1';
select is((select schedule_revision from app_private.user_profiles where user_id='d1510000-0000-4000-8000-000000000001'),0::bigint,
 'persisting a proposal does not change the schedule revision');
select is(pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c2'))->'data',(select res->'data' from q15 where name='p1'),
 'a retry with new engine IDs replays the stored proposal');
select is((select count(*) from app_private.plan_proposals),1::bigint,'the retry stored no second proposal');
select ok(pg_temp.q_is(pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c3',null,0,
 jsonb_set(pg_temp.q_cmd(),'{generation_scope,end_at}','"2026-11-12T00:00:00.000000Z"')),
 jsonb_set(pg_temp.q_cmd(),'{generation_scope,end_at}','"2026-11-12T00:00:00.000000Z"')),'IDEMPOTENCY_CONFLICT'),
 'the same key with another command conflicts');
select ok(pg_temp.q_call('lookup_operation_result',jsonb_build_object('operation','generate_study_plan','idempotency_key','q15-gen-key-000001',
 'request_fingerprint',app_private.domain_fingerprint('d1510000-0000-4000-8000-000000000001','generate_study_plan',pg_temp.q_cmd())),null)
 #>>'{data,result,data,proposal_id}'='d1510000-0000-4000-8000-0000000000c1','lookup finds the stored generation result');
select ok(pg_temp.q_is(pg_temp.q_persist(pg_temp.q_prop('d1510000-0000-4000-8000-0000000000c1'),null,'q15-gen-key-000002'),'IDEMPOTENCY_CONFLICT'),
 'a new key cannot reuse a stored proposal ID');
select * from finish();
rollback;
