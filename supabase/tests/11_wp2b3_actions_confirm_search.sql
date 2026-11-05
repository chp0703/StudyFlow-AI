-- WP2b-3: pending actions, presentations, task confirmation and search (local pgTAP, rolled back).
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.q_canon(v jsonb) returns text language sql as $$ select app_private.canonical_json(v) $$;
create function pg_temp.q_req(op text, args jsonb, uid uuid, idem text, msg uuid, approval jsonb, ref jsonb) returns jsonb language sql as $$
 select jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','q11-request',
 'operation',op,'arguments',args,'attestation',null,'execution_context',jsonb_build_object(
 'conversation_id','d1110000-0000-4000-8000-000000000003','idempotency_key',idem,'approval_action',approval,
 'action_reference',ref,'trusted_context',jsonb_build_object('request_id','q11-request','message_id',msg,
 'principal',jsonb_build_object('user_id',uid),'timezone','Asia/Ho_Chi_Minh','locale','vi-VN',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))))
$$;
create function pg_temp.q_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','q11-key','user_id',req#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.q_canon(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.q_canon(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','q11-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('11',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.q_call(op text, args jsonb, idem text default 'q11-default-key-0001',
 uid uuid default 'd1110000-0000-4000-8000-000000000001', msg uuid default 'd1110000-0000-4000-8000-000000000004',
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
create function pg_temp.q_is(res jsonb, code text) returns boolean language sql as $$
 select coalesce(res->>'outcome'='ERROR' and res#>>'{error,code}'=code and res->'data'='null'::jsonb,false) $$;
create function pg_temp.q_slots(title text, with_deadline boolean default true) returns jsonb language sql as $$
 select jsonb_build_object('slots',jsonb_build_object('title',title,'estimated_minutes',120,'priority','HIGH')
 || case when with_deadline then jsonb_build_object('deadline_precision','DATE','deadline_date','2026-11-06',
 'deadline_timezone','Asia/Ho_Chi_Minh') else '{}'::jsonb end) $$;
create function pg_temp.q_pres(candidate jsonb, action_id uuid, version bigint default 1) returns jsonb language sql as $$
 select jsonb_build_object('kind','ACTION_PRESENTATION','pending_action',jsonb_build_object('action_id',action_id,
 'user_id','d1110000-0000-4000-8000-000000000001','conversation_id','d1110000-0000-4000-8000-000000000003',
 'version',version,'intent','CREATE_TASK','state','AWAITING_CONFIRMATION','requires_review',false,
 'candidate_id',candidate->>'candidate_id','proposal_id',null,'draft_arguments','{}'::jsonb,'missing_fields','[]'::jsonb,
 'ambiguities','[]'::jsonb,'depends_on_action_id',null,'created_at','2026-11-05T01:00:00.000000Z',
 'updated_at','2026-11-05T01:00:00.000000Z'),'candidate',candidate,'proposal',null,'normalized_command',null,
 'effective_policy',null) $$;
create function pg_temp.q_ref(action_id uuid, action_version bigint, candidate jsonb) returns jsonb language sql as $$
 select jsonb_build_object('action_id',action_id,'action_version',action_version,'target_type','TASK_CANDIDATE',
 'target_id',candidate->>'candidate_id','target_version',(candidate->>'version')::bigint) $$;
create function pg_temp.q_appr(candidate jsonb, source text default 'UI', msg uuid default null) returns jsonb language sql as $$
 select jsonb_build_object('approval_action_id',extensions.gen_random_uuid(),'user_id','d1110000-0000-4000-8000-000000000001',
 'target_type','TASK_CANDIDATE','target_id',candidate->>'candidate_id','target_version',(candidate->>'version')::bigint,
 'decision','APPROVE','source',source,'source_message_id',msg,'created_at','2026-11-05T01:00:00.000000Z') $$;

insert into auth.users(id) values ('d1110000-0000-4000-8000-000000000001'),('d1110000-0000-4000-8000-000000000002');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('q11-key',decode(repeat('11',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');
select ok(pg_temp.q_call('record_source_message',jsonb_build_object('message',jsonb_build_object(
 'message_id','d1110000-0000-4000-8000-000000000004','user_id','d1110000-0000-4000-8000-000000000001',
 'conversation_id','d1110000-0000-4000-8000-000000000003','source','CHAT','role','USER','text','Tạo việc',
 'received_at','2026-11-05T01:02:03.000004Z')))->>'outcome'='COMMITTED','record the source message');
create temporary table q11(name text primary key, res jsonb);

-- Candidate A (complete) and its presented action.
insert into q11 values ('candA',pg_temp.q_call('create_task_candidate',pg_temp.q_slots('Ôn giải tích'),'q11-cand-a-0000001'));
create temporary table q11_ids as select 'd1110000-0000-4000-8000-0000000000a1'::uuid action_a,
 'd1110000-0000-4000-8000-0000000000b1'::uuid action_b;
insert into q11 select 'prepA',pg_temp.q_call('prepare_pending_action',jsonb_build_object(
 'presentation',pg_temp.q_pres(res->'data',(select action_a from q11_ids)),'expected_action_version',null),'q11-prep-a-00000001')
 from q11 where name='candA';
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,pending_action,version}'='1'
 and res#>>'{data,candidate,candidate_id}'=(select res#>>'{data,candidate_id}' from q11 where name='candA'),
 'prepare stores the action and returns the presentation') from q11 where name='prepA';
select is((select count(*) from app_private.pending_actions),1::bigint,'one pending action exists');
select is((select count(*) from app_private.action_presentations),1::bigint,'one presentation exists');
select ok((select p.target_type='TASK_CANDIDATE' and p.target_version=1 and p.content_digest ~ '^[a-f0-9]{64}$'
 from app_private.action_presentations p),'presentation binds target, version and a content digest');
insert into q11 select 'prepA2',pg_temp.q_call('prepare_pending_action',jsonb_build_object(
 'presentation',pg_temp.q_pres(res->'data',(select action_a from q11_ids)),'expected_action_version',null),'q11-prep-a-00000002')
 from q11 where name='candA';
select is(res->'data',(select res->'data' from q11 where name='prepA'),'a lost-response retry returns the stored presentation') from q11 where name='prepA2';
select is((select count(*) from app_private.action_presentations),1::bigint,'the retry added no presentation');

-- One awaiting action per conversation.
insert into q11 values ('candB',pg_temp.q_call('create_task_candidate',pg_temp.q_slots('Làm bài tập',false),'q11-cand-b-0000001'));
select ok(pg_temp.q_is(pg_temp.q_call('prepare_pending_action',jsonb_build_object(
 'presentation',pg_temp.q_pres((select res->'data' from q11 where name='candB'),(select action_b from q11_ids)),
 'expected_action_version',null),'q11-prep-b-00000001'),'ACTION_REVIEW_REQUIRED'),
 'a second awaiting action in the conversation is refused');
select is((select count(*) from app_private.pending_actions),1::bigint,'the refused action left no row');

-- Reload marks the action as needing review; review bumps the version once and is retry-safe.
update app_private.pending_actions set requires_review=true;
select ok(pg_temp.q_is(pg_temp.q_call('confirm_task',jsonb_build_object('candidate_id',(select res#>>'{data,candidate_id}' from q11 where name='candA'),
 'expected_candidate_version',1),'q11-confirm-0000001','d1110000-0000-4000-8000-000000000001','d1110000-0000-4000-8000-000000000004',
 pg_temp.q_appr((select res->'data' from q11 where name='candA')),
 pg_temp.q_ref((select action_a from q11_ids),1,(select res->'data' from q11 where name='candA'))),'ACTION_REVIEW_REQUIRED'),
 'approval is refused while the action requires review');
insert into q11 select 'rev',pg_temp.q_call('review_pending_action',jsonb_build_object('action_id',(select action_a from q11_ids),
 'expected_action_version',1,'presentation',pg_temp.q_pres(res->'data',(select action_a from q11_ids),2)),'q11-review-0000001')
 from q11 where name='candA';
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,pending_action,version}'='2' and res#>>'{data,pending_action,requires_review}'='false',
 'review clears requires_review and issues version 2') from q11 where name='rev';
select is(pg_temp.q_call('review_pending_action',jsonb_build_object('action_id',(select action_a from q11_ids),
 'expected_action_version',1,'presentation',pg_temp.q_pres((select res->'data' from q11 where name='candA'),(select action_a from q11_ids),2)),
 'q11-review-0000001')->'data',(select res->'data' from q11 where name='rev'),'retrying the review returns the issued reference');
select is((select version from app_private.pending_actions),2::bigint,'the retry did not review twice');
select ok(pg_temp.q_is(pg_temp.q_call('review_pending_action',jsonb_build_object('action_id',(select action_a from q11_ids),
 'expected_action_version',2,'presentation',jsonb_set(pg_temp.q_pres((select res->'data' from q11 where name='candA'),
 (select action_a from q11_ids),3),'{candidate,slots,title}','"Đã bị sửa"')),'q11-review-bad-0001'),'STALE_ENTITY_VERSION')
 or (select version from app_private.pending_actions)=2,'a review with edited candidate content is not applied');
select is((select count(*) from app_private.action_presentations),2::bigint,'each action version has one presentation');

-- confirm_task guards. Every refusal must leave all business state untouched.
create temporary table q11_before as select (select count(*) from app_private.academic_tasks) t,
 (select count(*) from app_private.approval_actions) a, (select schedule_revision from app_private.user_profiles
  where user_id='d1110000-0000-4000-8000-000000000001') r;
create function pg_temp.q_confirm(idem text, approval jsonb, ref jsonb, cv bigint default 1) returns jsonb language sql as $$
 select pg_temp.q_call('confirm_task',jsonb_build_object('candidate_id',(select res#>>'{data,candidate_id}' from q11 where name='candA'),
 'expected_candidate_version',cv),idem,'d1110000-0000-4000-8000-000000000001','d1110000-0000-4000-8000-000000000004',approval,ref) $$;
select ok(pg_temp.q_is(pg_temp.q_confirm('q11-confirm-0000002',null,null),'APPROVAL_REQUIRED'),'no approval context is refused');
select ok(pg_temp.q_is(pg_temp.q_confirm('q11-confirm-0000003',
 jsonb_set(pg_temp.q_appr((select res->'data' from q11 where name='candA')),'{target_version}','7'),
 pg_temp.q_ref((select action_a from q11_ids),2,(select res->'data' from q11 where name='candA'))),'APPROVAL_REQUIRED'),
 'an approval for another candidate version is refused');
select ok(pg_temp.q_is(pg_temp.q_confirm('q11-confirm-0000004',pg_temp.q_appr((select res->'data' from q11 where name='candA')),
 pg_temp.q_ref((select action_a from q11_ids),1,(select res->'data' from q11 where name='candA'))),'STALE_ENTITY_VERSION'),
 'a reference to an outdated action version is stale');
select ok(pg_temp.q_is(pg_temp.q_confirm('q11-confirm-0000005',
 pg_temp.q_appr((select res->'data' from q11 where name='candA'),'CHAT','d1110000-0000-4000-8000-000000000999'),
 pg_temp.q_ref((select action_a from q11_ids),2,(select res->'data' from q11 where name='candA'))),'APPROVAL_REQUIRED'),
 'a chat approval without a recorded user message is refused');
select ok(pg_temp.q_is(pg_temp.q_call('confirm_task',jsonb_build_object('candidate_id',(select res#>>'{data,candidate_id}' from q11 where name='candA'),
 'expected_candidate_version',1),'q11-confirm-0000006','d1110000-0000-4000-8000-000000000002','d1110000-0000-4000-8000-000000000004',
 pg_temp.q_appr((select res->'data' from q11 where name='candA')),
 pg_temp.q_ref((select action_a from q11_ids),2,(select res->'data' from q11 where name='candA'))),'APPROVAL_REQUIRED'),
 'a foreign owner cannot use this approval');
select ok((select count(*) from app_private.academic_tasks)=(select t from q11_before)
 and (select count(*) from app_private.approval_actions)=(select a from q11_before),'refused confirmations wrote nothing');

-- Atomicity: a failure after the approval insert rolls the whole confirmation back.
create function pg_temp.q_fail() returns trigger language plpgsql as $$
begin raise exception using errcode='XX000',message='Q11_INJECTED'; end $$;
create trigger q11_fail after insert on app_private.academic_tasks for each row execute function pg_temp.q_fail();
select ok(pg_temp.q_is(pg_temp.q_confirm('q11-confirm-0000007',pg_temp.q_appr((select res->'data' from q11 where name='candA')),
 pg_temp.q_ref((select action_a from q11_ids),2,(select res->'data' from q11 where name='candA'))),'INTERNAL_ERROR'),
 'an injected failure becomes INTERNAL_ERROR');
select ok((select count(*) from app_private.approval_actions)=(select a from q11_before)
 and (select status from app_private.task_candidates where candidate_id=(select (res#>>'{data,candidate_id}')::uuid from q11 where name='candA'))='DRAFT'
 and (select state from app_private.pending_actions where action_id=(select action_a from q11_ids))='AWAITING_CONFIRMATION'
 and (select schedule_revision from app_private.user_profiles where user_id='d1110000-0000-4000-8000-000000000001')=(select r from q11_before)
 and not exists(select 1 from app_private.idempotency_records where operation='confirm_task'),
 'the failed confirmation rolled back approval, candidate, action, revision and idempotency');
drop trigger q11_fail on app_private.academic_tasks;

-- Successful chat confirmation: one atomic commit with the DATE deadline cutoff.
insert into q11 select 'confirm',pg_temp.q_confirm('q11-confirm-0000008',
 pg_temp.q_appr(res->'data','CHAT','d1110000-0000-4000-8000-000000000004'),
 pg_temp.q_ref((select action_a from q11_ids),2,res->'data')) from q11 where name='candA';
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,status}'='TODO' and res#>>'{data,title}'='Ôn giải tích'
 and res#>>'{data,estimated_minutes}'='120' and res#>>'{data,remaining_minutes}'='120' and res#>>'{data,priority}'='HIGH',
 'confirmation creates a TODO task with remaining = estimated') from q11 where name='confirm';
select ok(res#>>'{data,deadline_date}'='2026-11-06' and res#>>'{data,deadline_precision}'='DATE'
 and res#>>'{data,deadline_at}'='2026-11-06T17:00:00.000000Z','a date-only deadline ends at the next local midnight') from q11 where name='confirm';
select ok((select count(*) from app_private.academic_tasks)=1 and (select count(*) from app_private.approval_actions)=1
 and (select source from app_private.approval_actions)='CHAT','one task and one approval were written');
select ok((select status='CONFIRMED' and confirmed_task_id is not null and version=2 from app_private.task_candidates
 where candidate_id=(select (res#>>'{data,candidate_id}')::uuid from q11 where name='candA'))
 and (select state='COMPLETED' from app_private.pending_actions where action_id=(select action_a from q11_ids)),
 'candidate is CONFIRMED with a backlink and the action is COMPLETED');
select is((select schedule_revision from app_private.user_profiles where user_id='d1110000-0000-4000-8000-000000000001'),
 (select r from q11_before)+1,'creating a task increments the schedule revision once');
-- Replay and later keys.
select is(pg_temp.q_confirm('q11-confirm-0000008',pg_temp.q_appr((select res->'data' from q11 where name='candA'),'CHAT',
 'd1110000-0000-4000-8000-000000000004'),pg_temp.q_ref((select action_a from q11_ids),2,(select res->'data' from q11 where name='candA')))->'data',
 (select res->'data' from q11 where name='confirm'),'retry with the same key returns the original task');
select ok((select count(*) from app_private.academic_tasks)=1 and (select count(*) from app_private.approval_actions)=1,
 'the retry created no second task or approval');
select ok(pg_temp.q_is(pg_temp.q_confirm('q11-confirm-0000009',pg_temp.q_appr((select res->'data' from q11 where name='candA')),
 pg_temp.q_ref((select action_a from q11_ids),2,(select res->'data' from q11 where name='candA'))),'STALE_ENTITY_VERSION'),
 'a new key after confirmation is stale, not a second task');

-- An incomplete candidate cannot be confirmed (no deadline).
insert into q11 select 'actB',pg_temp.q_call('prepare_pending_action',jsonb_build_object(
 'presentation',pg_temp.q_pres(res->'data',(select action_b from q11_ids)),'expected_action_version',null),'q11-prep-b-00000002')
 from q11 where name='candB';
select ok(res->>'outcome'='COMMITTED','candidate B is presented (the first action completed, freeing the conversation)') from q11 where name='actB';
select ok((select e->'error'->>'code'='MISSING_REQUIRED_FIELD' and e#>>'{error,field}'='deadline_precision' from (select pg_temp.q_call('confirm_task',
 jsonb_build_object('candidate_id',(select res#>>'{data,candidate_id}' from q11 where name='candB'),'expected_candidate_version',1),
 'q11-confirm-0000010','d1110000-0000-4000-8000-000000000001','d1110000-0000-4000-8000-000000000004',
 pg_temp.q_appr((select res->'data' from q11 where name='candB')),
 pg_temp.q_ref((select action_b from q11_ids),1,(select res->'data' from q11 where name='candB'))) e) x),
 'an incomplete candidate names the missing field');
-- Cancel rejects the draft without writing official data.
insert into q11 select 'cancel',pg_temp.q_call('cancel_pending_action',jsonb_build_object(
 'action_reference',pg_temp.q_ref((select action_b from q11_ids),1,res->'data'),'candidate_id',res#>>'{data,candidate_id}'),
 'q11-cancel-000000001') from q11 where name='candB';
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,state}'='CANCELLED','cancel moves the action to CANCELLED') from q11 where name='cancel';
select ok((select status from app_private.task_candidates where candidate_id=(select (res#>>'{data,candidate_id}')::uuid from q11 where name='candB'))='CANCELLED'
 and (select count(*) from app_private.academic_tasks)=1,'the draft candidate is CANCELLED and no task was written');
select is(pg_temp.q_call('cancel_pending_action',jsonb_build_object('action_reference',
 pg_temp.q_ref((select action_b from q11_ids),1,(select res->'data' from q11 where name='candB')),
 'candidate_id',(select res#>>'{data,candidate_id}' from q11 where name='candB')),'q11-cancel-000000001')->'data',
 (select res->'data' from q11 where name='cancel'),'retrying the cancel returns the cancelled action');

-- search_tasks: filters, keyset pagination and tamper-proof cursors.
insert into app_private.academic_tasks(task_id,user_id,candidate_id,title,course_label,deadline_at,deadline_precision,
 deadline_date,deadline_timezone,estimated_minutes,remaining_minutes,priority,status)
 select extensions.gen_random_uuid(),'d1110000-0000-4000-8000-000000000001',extensions.gen_random_uuid(),'Bài '||n,
 case when n=2 then 'Toán rời rạc' end,timestamptz '2026-11-10 00:00+00'+n*interval '1 day','DATETIME',null,'UTC',60,60,'NORMAL',
 case when n=3 then 'IN_PROGRESS' else 'TODO' end from generate_series(1,4) n;
create function pg_temp.q_search(q text, statuses jsonb, size int, cur text, uid uuid default 'd1110000-0000-4000-8000-000000000001')
 returns jsonb language sql as $$ select pg_temp.q_call('search_tasks',jsonb_build_object('query',q,'status_filter',statuses,
 'page_size',size,'cursor',cur),null,uid) $$;
insert into q11 values ('s1',pg_temp.q_search(null,'[]',2,null));
select ok(res->>'outcome'='READ' and jsonb_array_length(res#>'{data,items}')=2 and res#>>'{data,next_cursor}' is not null,
 'first page has two items and a cursor') from q11 where name='s1';
insert into q11 select 's2',pg_temp.q_search(null,'[]',2,res#>>'{data,next_cursor}') from q11 where name='s1';
select ok(jsonb_array_length(res#>'{data,items}')=2 and res#>>'{data,next_cursor}' is not null,'second page continues the order') from q11 where name='s2';
insert into q11 select 's3',pg_temp.q_search(null,'[]',2,res#>>'{data,next_cursor}') from q11 where name='s2';
select ok(jsonb_array_length(res#>'{data,items}')=1 and res#>'{data,next_cursor}'='null'::jsonb,'last page has the remainder and no cursor') from q11 where name='s3';
select is((select count(distinct i->>'task_id') from q11,jsonb_array_elements(res#>'{data,items}') i where name in ('s1','s2','s3')),
 5::bigint,'pages cover all five tasks without repeats');
select is(jsonb_array_length(pg_temp.q_search(null,'["IN_PROGRESS"]',10,null)#>'{data,items}'),1,'status filter applies');
select is(jsonb_array_length(pg_temp.q_search('rời rạc','[]',10,null)#>'{data,items}'),1,'query matches the course label');
select is(jsonb_array_length(pg_temp.q_search('100%','[]',10,null)#>'{data,items}'),0,'wildcard characters are matched literally');
select ok(pg_temp.q_is(pg_temp.q_search(null,'[]',2,'v1.tampered.deadbeef'),'INVALID_PARAMETER'),'a tampered cursor is rejected');
select ok(pg_temp.q_is(pg_temp.q_search(null,'["TODO"]',2,(select res#>>'{data,next_cursor}' from q11 where name='s1')),'INVALID_PARAMETER'),
 'a cursor cannot be reused with another filter');
select ok(pg_temp.q_is(pg_temp.q_search(null,'[]',2,(select res#>>'{data,next_cursor}' from q11 where name='s1'),
 'd1110000-0000-4000-8000-000000000002'),'INVALID_PARAMETER'),'a cursor cannot be used by another owner');
select is(jsonb_array_length(pg_temp.q_search(null,'[]',10,null,'d1110000-0000-4000-8000-000000000002')#>'{data,items}'),0,
 'another owner sees none of these tasks');
select * from finish();
rollback;
