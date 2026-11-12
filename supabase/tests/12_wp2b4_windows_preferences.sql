-- WP2b-4: khung rảnh/bận, tùy chọn lập lịch và danh sách khung giờ; pgTAP local, có rollback.
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.q_canon(v jsonb) returns text language sql as $$ select app_private.canonical_json(v) $$;
create function pg_temp.q_req(op text, args jsonb, uid uuid, idem text, conv uuid, approval jsonb, ref jsonb) returns jsonb language sql as $$
 select jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','q12-request',
 'operation',op,'arguments',args,'attestation',null,'execution_context',jsonb_build_object(
 'conversation_id',conv,'idempotency_key',idem,'approval_action',approval,'action_reference',ref,
 'trusted_context',jsonb_build_object('request_id','q12-request','message_id','d1210000-0000-4000-8000-000000000004',
 'principal',jsonb_build_object('user_id',uid),'timezone','Asia/Ho_Chi_Minh','locale','vi-VN',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))))
$$;
create function pg_temp.q_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','q12-key','user_id',req#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.q_canon(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.q_canon(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','q12-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('12',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.q_call(op text, args jsonb, idem text default 'q12-default-key-0001', conv uuid default null,
 approval jsonb default null, ref jsonb default null, uid uuid default 'd1210000-0000-4000-8000-000000000001')
 returns jsonb language plpgsql as $$
declare res jsonb; req jsonb := pg_temp.q_req(op,args,uid,idem,coalesce(conv,'d1210000-0000-4000-8000-000000000003'),approval,ref);
begin
 if op not in ('list_time_windows') then req := pg_temp.q_sign(req); end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'role','authenticated')::text,true);
 perform set_config('request.jwt.claim.sub',uid::text,true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',op) into res using req;
 exception when others then res:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role; return res;
end $$;
create function pg_temp.q_is(res jsonb, code text) returns boolean language sql as $$
 select coalesce(res->>'outcome'='ERROR' and res#>>'{error,code}'=code and res->'data'='null'::jsonb,false) $$;

-- Hiển thị command để duyệt qua prepare_pending_action trong hội thoại mới rồi thực thi
-- với phê duyệt UI tương ứng; có thể truyền arguments khác nội dung đã hiển thị để duyệt.
create function pg_temp.q_set(op text, intent text, args jsonb, idem text, run_args jsonb default null,
 approve boolean default true) returns jsonb language plpgsql as $$
declare conv uuid := extensions.gen_random_uuid(); act uuid := extensions.gen_random_uuid();
 prep jsonb; ref jsonb; appr jsonb;
begin
 prep := pg_temp.q_call('prepare_pending_action',jsonb_build_object('presentation',jsonb_build_object('kind','ACTION_PRESENTATION',
 'pending_action',jsonb_build_object('action_id',act,'user_id','d1210000-0000-4000-8000-000000000001','conversation_id',conv,
 'version',1,'intent',intent,'state','AWAITING_CONFIRMATION','requires_review',false,'candidate_id',null,'proposal_id',null,
 'draft_arguments','{}'::jsonb,'missing_fields','[]'::jsonb,'ambiguities','[]'::jsonb,'depends_on_action_id',null,
 'created_at','2026-11-05T01:00:00.000000Z','updated_at','2026-11-05T01:00:00.000000Z'),'candidate',null,'proposal',null,
 'normalized_command',jsonb_build_object('schema_version','1.1','operation',op,'arguments',args),'effective_policy',null),
 'expected_action_version',null),'q12-prep-'||act::text,conv);
 if prep->>'outcome' <> 'COMMITTED' then return prep; end if;
 insert into q12_last(k,action_id,conv) values (1, act, conv) on conflict (k) do update set action_id=excluded.action_id, conv=excluded.conv;
 ref := jsonb_build_object('action_id',act,'action_version',1,'target_type','PENDING_ACTION','target_id',act,'target_version',1);
 appr := jsonb_build_object('approval_action_id',extensions.gen_random_uuid(),'user_id','d1210000-0000-4000-8000-000000000001',
 'target_type','PENDING_ACTION','target_id',act,'target_version',1,'decision','APPROVE','source','UI','source_message_id',null,
 'created_at','2026-11-05T01:00:00.000000Z');
 if not approve then return pg_temp.q_call(op,coalesce(run_args,args),idem,conv); end if;
 return pg_temp.q_call(op,coalesce(run_args,args),idem,conv,appr,ref);
end $$;
create temporary table q12_last(k int primary key default 1, action_id uuid, conv uuid);
create function pg_temp.q_weekly(label text default 'Giờ học thứ Sáu', wd int default 5) returns jsonb language sql as $$
 select jsonb_build_object('kind','AVAILABILITY','label',label,'recurrence','WEEKLY','timezone','Asia/Ho_Chi_Minh',
 'start_at',null,'end_at',null,'weekday',wd,'start_time','09:00','end_time','24:00','valid_from','2026-11-05','valid_until',null) $$;
create function pg_temp.q_add(w jsonb) returns jsonb language sql as $$
 select jsonb_build_object('change_type','ADD','window_id',null,'expected_window_version',null,'window',w) $$;

insert into auth.users(id) values ('d1210000-0000-4000-8000-000000000001'),('d1210000-0000-4000-8000-000000000002');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('q12-key',decode(repeat('12',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');
create temporary table q12(name text primary key, res jsonb);
create temporary table q12_base as select (select count(*) from app_private.approval_actions) a;

-- ADD khung giờ rảnh lặp hằng tuần.
insert into q12 values ('w1',pg_temp.q_set('set_availability','SET_AVAILABILITY',pg_temp.q_add(pg_temp.q_weekly()),'q12-avail-add-00001'));
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,kind}'='AVAILABILITY' and res#>>'{data,version}'='1'
 and res#>>'{data,start_time}'='09:00' and res#>>'{data,end_time}'='24:00' and res#>>'{data,recurrence}'='WEEKLY'
 and res#>>'{data,weekday}'='5' and res#>'{data,archived_at}'='null'::jsonb,'availability is stored with 24:00 preserved') from q12 where name='w1';
select ok((select schedule_revision from app_private.user_profiles where user_id='d1210000-0000-4000-8000-000000000001')=1
 and (select count(*) from app_private.approval_actions)=(select a from q12_base)+1
 and (select state='COMPLETED' from app_private.pending_actions where action_id=(select action_id from q12_last)),
 'one approval, a completed action and revision 1');
select is((select target_type from app_private.approval_actions order by created_at desc limit 1),'PENDING_ACTION','the approval targets the pending action');
-- Phát lại: cùng khóa và arguments trả cùng khung giờ, không ghi thêm.
create temporary table q12_snap as select (select count(*) from app_private.time_windows) w,
 (select count(*) from app_private.approval_actions) a;
select is(pg_temp.q_call('set_availability',pg_temp.q_add(pg_temp.q_weekly()),'q12-avail-add-00001',(select conv from q12_last),
 jsonb_build_object('approval_action_id',extensions.gen_random_uuid(),'user_id','d1210000-0000-4000-8000-000000000001',
 'target_type','PENDING_ACTION','target_id',(select action_id from q12_last),'target_version',1,'decision','APPROVE','source','UI',
 'source_message_id',null,'created_at','2026-11-05T01:00:00.000000Z'),
 jsonb_build_object('action_id',(select action_id from q12_last),'action_version',1,'target_type','PENDING_ACTION',
 'target_id',(select action_id from q12_last),'target_version',1))->'data',(select res->'data' from q12 where name='w1'),
 'a retry with the same key returns the original window');
select ok((select count(*) from app_private.time_windows)=(select w from q12_snap)
 and (select count(*) from app_private.approval_actions)=(select a from q12_snap),'the retry wrote nothing');

-- Bảo vệ phê duyệt và nội dung hiển thị để duyệt.
truncate q12_snap; insert into q12_snap select (select count(*) from app_private.time_windows),(select count(*) from app_private.approval_actions);
select ok(pg_temp.q_is(pg_temp.q_call('set_availability',pg_temp.q_add(pg_temp.q_weekly('Khác')),'q12-avail-add-00002'),'APPROVAL_REQUIRED'),
 'no approval context is refused');
select ok(pg_temp.q_is(pg_temp.q_set('set_availability','SET_AVAILABILITY',pg_temp.q_add(pg_temp.q_weekly()),'q12-avail-add-00003',
 pg_temp.q_add(pg_temp.q_weekly('Đã đổi sau khi trình bày'))),'APPROVAL_REQUIRED'),'a command different from the presented one is refused');
select ok(pg_temp.q_set('set_busy_interval','SET_BUSY_INTERVAL',pg_temp.q_add(pg_temp.q_weekly()),'q12-busy-add-00001')->>'outcome'='ERROR',
 'an availability-kind window cannot be sent through the busy routine');
select ok((select count(*) from app_private.time_windows)=(select w from q12_snap)
 and (select count(*) from app_private.approval_actions)=(select a from q12_snap),'refused commands wrote nothing');

-- Kiểm tra ngữ nghĩa trước khi sử dụng phê duyệt.
select ok((select e->'error'->>'code'='INVALID_PARAMETER' and e#>>'{error,field}'='window.end_at' from (select pg_temp.q_set('set_busy_interval','SET_BUSY_INTERVAL',
 pg_temp.q_add(jsonb_build_object('kind','BUSY','label',null,'recurrence','NONE','timezone','Asia/Ho_Chi_Minh',
 'start_at','2026-11-06T09:00:00Z','end_at','2026-11-06T08:00:00Z','weekday',null,'start_time',null,'end_time',null,
 'valid_from',null,'valid_until',null)),'q12-busy-bad-00001') e) x),'an interval that ends before it starts is rejected');
select ok(exists(select 1 from app_private.pending_actions where action_id=(select action_id from q12_last) and state='AWAITING_CONFIRMATION'),
 'a rejected command leaves the action awaiting');
select ok((select e->'error'->>'code'='INVALID_PARAMETER' from (select pg_temp.q_set('set_busy_interval','SET_BUSY_INTERVAL',
 pg_temp.q_add(jsonb_build_object('kind','BUSY','label',null,'recurrence','NONE','timezone','Asia/Ho_Chi_Minh',
 'start_at','2026-11-06T15:00:00Z','end_at','2026-11-07T03:00:00Z','weekday',null,'start_time',null,'end_time',null,
 'valid_from',null,'valid_until',null)),'q12-busy-bad-00002') e) x),'an interval crossing local midnight must be split');
select ok((select e->'error'->>'code'='INVALID_PARAMETER' from (select pg_temp.q_set('set_busy_interval','SET_BUSY_INTERVAL',
 pg_temp.q_add(jsonb_build_object('kind','BUSY','label',null,'recurrence','NONE','timezone','Mars/Base',
 'start_at','2026-11-06T09:00:00Z','end_at','2026-11-06T10:00:00Z','weekday',null,'start_time',null,'end_time',null,
 'valid_from',null,'valid_until',null)),'q12-busy-bad-00003') e) x),'an unknown time zone is rejected');
select ok((select e->'error'->>'code'='INVALID_PARAMETER' from (select pg_temp.q_set('set_busy_interval','SET_BUSY_INTERVAL',
 pg_temp.q_add(jsonb_build_object('kind','BUSY','label',null,'recurrence','NONE','timezone','Asia/Ho_Chi_Minh',
 'start_at','2026-11-06T09:00:30Z','end_at','2026-11-06T10:00:00Z','weekday',null,'start_time',null,'end_time',null,
 'valid_from',null,'valid_until',null)),'q12-busy-bad-00004') e) x),'windows use whole minutes');

-- Tạo khoảng bận, sau đó UPDATE có kiểm soát version lạc quan rồi ARCHIVE.
insert into q12 values ('b1',pg_temp.q_set('set_busy_interval','SET_BUSY_INTERVAL',
 pg_temp.q_add(jsonb_build_object('kind','BUSY','label','Lớp thực hành','recurrence','NONE','timezone','Asia/Ho_Chi_Minh',
 'start_at','2026-11-06T09:00:00Z','end_at','2026-11-06T10:30:00Z','weekday',null,'start_time',null,'end_time',null,
 'valid_from',null,'valid_until',null)),'q12-busy-add-00002'));
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,kind}'='BUSY' and res#>>'{data,end_at}'='2026-11-06T10:30:00.000000Z',
 'a one-off busy interval is stored') from q12 where name='b1';
create function pg_temp.q_upd(window_id text, version bigint, label text) returns jsonb language sql as $$
 select jsonb_build_object('change_type','UPDATE','window_id',window_id,'expected_window_version',version,
 'window',pg_temp.q_weekly(label)) $$;
insert into q12 select 'u1',pg_temp.q_set('set_availability','SET_AVAILABILITY',pg_temp.q_upd(res#>>'{data,window_id}',1,'Đã sửa'),'q12-avail-upd-00001')
 from q12 where name='w1';
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,version}'='2' and res#>>'{data,label}'='Đã sửa','an update bumps the window version') from q12 where name='u1';
select ok(pg_temp.q_is(pg_temp.q_set('set_availability','SET_AVAILABILITY',pg_temp.q_upd((select res#>>'{data,window_id}' from q12 where name='w1'),1,'Cũ'),
 'q12-avail-upd-00002'),'STALE_ENTITY_VERSION'),'an outdated window version is stale');
select ok(pg_temp.q_is(pg_temp.q_set('set_busy_interval','SET_BUSY_INTERVAL',jsonb_build_object('change_type','UPDATE',
 'window_id',(select res#>>'{data,window_id}' from q12 where name='w1'),'expected_window_version',2,'window',
 jsonb_set(pg_temp.q_weekly(),'{kind}','"BUSY"')),'q12-busy-upd-00001'),'ENTITY_NOT_FOUND'),'a window cannot be edited through the other kind''s routine');
insert into q12 select 'a1',pg_temp.q_set('set_availability','SET_AVAILABILITY',jsonb_build_object('change_type','ARCHIVE',
 'window_id',res#>>'{data,window_id}','expected_window_version',2,'window',null),'q12-avail-arc-00001') from q12 where name='u1';
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,archived_at}' is not null and res#>>'{data,version}'='3','archive soft-deletes with archived_at') from q12 where name='a1';
select ok((select count(*) from app_private.time_windows)=2,'archiving removes no row');

-- Danh sách: lọc kind, hiển thị bản lưu trữ, phân trang và cursor có chữ ký.
create function pg_temp.q_list(kind text, arch boolean, size int, cur text, uid uuid default 'd1210000-0000-4000-8000-000000000001')
 returns jsonb language sql as $$ select pg_temp.q_call('list_time_windows',jsonb_build_object('kind',kind,'include_archived',arch,
 'page_size',size,'cursor',cur),null,null,null,null,uid) $$;
select is(jsonb_array_length(pg_temp.q_list(null,false,50,null)#>'{data,items}'),1,'archived windows are hidden by default');
select is(jsonb_array_length(pg_temp.q_list(null,true,50,null)#>'{data,items}'),2,'include_archived shows them');
select is(jsonb_array_length(pg_temp.q_list('BUSY',true,50,null)#>'{data,items}'),1,'the kind filter applies');
insert into q12 values ('l1',pg_temp.q_list(null,true,1,null));
select ok(jsonb_array_length(res#>'{data,items}')=1 and res#>>'{data,next_cursor}' is not null,'page of one has a cursor') from q12 where name='l1';
select is(jsonb_array_length(pg_temp.q_list(null,true,1,(select res#>>'{data,next_cursor}' from q12 where name='l1'))#>'{data,items}'),1,
 'the next page returns the remaining window');
select ok(pg_temp.q_is(pg_temp.q_list(null,false,1,(select res#>>'{data,next_cursor}' from q12 where name='l1')),'INVALID_PARAMETER'),
 'a cursor cannot be reused with another filter');
select is(jsonb_array_length(pg_temp.q_list(null,true,50,null,'d1210000-0000-4000-8000-000000000002')#>'{data,items}'),0,
 'another owner sees none of these windows');

-- Tính nguyên tử: lỗi khi ghi phải rollback phê duyệt, action và revision.
create function pg_temp.q_fail() returns trigger language plpgsql as $$
begin raise exception using errcode='XX000',message='Q12_INJECTED'; end $$;
create trigger q12_fail after insert on app_private.time_windows for each row execute function pg_temp.q_fail();
truncate q12_snap; insert into q12_snap select (select count(*) from app_private.time_windows),(select count(*) from app_private.approval_actions);
create temporary table q12_rev as select schedule_revision r from app_private.user_profiles where user_id='d1210000-0000-4000-8000-000000000001';
insert into q12 values ('fail',pg_temp.q_set('set_availability','SET_AVAILABILITY',pg_temp.q_add(pg_temp.q_weekly('Lỗi')),'q12-avail-fail-0001'));
select ok(pg_temp.q_is(res,'INTERNAL_ERROR')
 and (select count(*) from app_private.approval_actions)=(select a from q12_snap)
 and (select state from app_private.pending_actions where action_id=(select action_id from q12_last))='AWAITING_CONFIRMATION'
 and (select schedule_revision from app_private.user_profiles where user_id='d1210000-0000-4000-8000-000000000001')=(select r from q12_rev),
 'an injected failure rolls back approval, action and revision') from q12 where name='fail';
drop trigger q12_fail on app_private.time_windows;

-- Tùy chọn lập lịch: hợp nhất, bảo vệ revision, kiểm tra hợp lệ và phát lại.
create function pg_temp.q_prefs(patch jsonb, rev bigint) returns jsonb language sql as $$
 select jsonb_build_object('policy_patch',patch,'expected_schedule_revision',rev) $$;
create function pg_temp.q_rev() returns bigint language sql as $$
 select schedule_revision from app_private.user_profiles where user_id='d1210000-0000-4000-8000-000000000001' $$;
insert into q12 values ('p1',pg_temp.q_set('set_scheduling_preferences','SET_SCHEDULING_PREFERENCES',
 pg_temp.q_prefs('{"min_block_minutes":120,"max_block_minutes":150,"max_daily_minutes":600,"break_minutes":0}',pg_temp.q_rev()),'q12-prefs-00000001'));
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,scheduling_policy,min_block_minutes}'='120'
 and res#>>'{data,scheduling_policy,allow_short_final_block}'='true' and res#>>'{data,scheduling_policy,break_minutes}'='0'
 and (res#>>'{data,schedule_revision}')::bigint=pg_temp.q_rev(),'the patch merges into the full stored policy and bumps the revision') from q12 where name='p1';
select is((select scheduling_policy from app_private.user_profiles where user_id='d1210000-0000-4000-8000-000000000001'),
 (select res#>'{data,scheduling_policy}' from q12 where name='p1'),'the merged policy is persisted');
select ok(pg_temp.q_is(pg_temp.q_set('set_scheduling_preferences','SET_SCHEDULING_PREFERENCES',
 pg_temp.q_prefs('{"break_minutes":5}',pg_temp.q_rev()-1),'q12-prefs-00000002'),'STALE_ENTITY_VERSION'),'an outdated schedule revision is stale');
select ok(pg_temp.q_is(pg_temp.q_set('set_scheduling_preferences','SET_SCHEDULING_PREFERENCES',
 pg_temp.q_prefs('{"max_block_minutes":60}',pg_temp.q_rev()),'q12-prefs-00000003'),'INVALID_PARAMETER'),'a merged policy with max below min is rejected');
select is(pg_temp.q_rev(),(select (res#>>'{data,schedule_revision}')::bigint from q12 where name='p1'),'rejected preferences do not change the revision');

-- WP2c-4: cảnh báo khi block tương lai đã duyệt có thể bị ảnh hưởng; không có cảnh báo nếu chưa có lịch.
select ok(res->'warnings'='[]'::jsonb,'no warning while no plan exists') from q12 where name='p1';
insert into app_private.academic_tasks(task_id,user_id,candidate_id,title,start_at,deadline_at,deadline_precision,deadline_date,
 deadline_timezone,estimated_minutes,remaining_minutes) values ('d1210000-0000-4000-8000-0000000000a1','d1210000-0000-4000-8000-000000000001',
 extensions.gen_random_uuid(),'Bài tập',clock_timestamp(),clock_timestamp()+interval '30 days','DATETIME',null,'Asia/Ho_Chi_Minh',120,120);
insert into app_private.plan_proposals(proposal_id,user_id,base_schedule_revision,generation_scope,payload,algorithm_version,policy_snapshot)
 values ('d1210000-0000-4000-8000-0000000000c1','d1210000-0000-4000-8000-000000000001',0,'{}','{}','q12-1','{}');
insert into app_private.study_plans(plan_id,user_id,version,source_proposal_id)
 values ('d1210000-0000-4000-8000-0000000000d1','d1210000-0000-4000-8000-000000000001',1,'d1210000-0000-4000-8000-0000000000c1');
insert into app_private.study_blocks(plan_id,block_id,user_id,task_id,start_at,end_at) values
 ('d1210000-0000-4000-8000-0000000000d1','d1210000-0000-4000-8000-0000000000e1','d1210000-0000-4000-8000-000000000001',
  'd1210000-0000-4000-8000-0000000000a1',clock_timestamp()+interval '2 days',clock_timestamp()+interval '2 days 1 hour'),
 ('d1210000-0000-4000-8000-0000000000d1','d1210000-0000-4000-8000-0000000000e2','d1210000-0000-4000-8000-000000000001',
  'd1210000-0000-4000-8000-0000000000a1',clock_timestamp()-interval '2 days',clock_timestamp()-interval '2 days'+interval '1 hour');
update app_private.user_profiles set current_plan_id='d1210000-0000-4000-8000-0000000000d1' where user_id='d1210000-0000-4000-8000-000000000001';
insert into q12 values ('w_busy',pg_temp.q_set('set_busy_interval','SET_BUSY_INTERVAL',
 pg_temp.q_add(jsonb_build_object('kind','BUSY','label','Việc mới','recurrence','NONE','timezone','Asia/Ho_Chi_Minh',
 'start_at','2026-11-07T09:00:00Z','end_at','2026-11-07T10:00:00Z','weekday',null,'start_time',null,'end_time',null,
 'valid_from',null,'valid_until',null)),'q12-busy-warn-0001'));
select ok(res->>'outcome'='COMMITTED' and res#>>'{warnings,0,code}'='APPROVED_BLOCKS_MAY_BE_AFFECTED'
 and res#>'{warnings,0,details,block_ids}'='["d1210000-0000-4000-8000-0000000000e1"]'::jsonb,
 'a new busy interval warns about future approved blocks only') from q12 where name='w_busy';
insert into q12 values ('w_avail',pg_temp.q_set('set_availability','SET_AVAILABILITY',pg_temp.q_add(pg_temp.q_weekly('Thêm giờ rảnh',3)),'q12-avail-warn-001'));
select ok(res->>'outcome'='COMMITTED' and res->'warnings'='[]'::jsonb,'adding availability cannot hurt approved blocks') from q12 where name='w_avail';
insert into q12 values ('w_pref',pg_temp.q_set('set_scheduling_preferences','SET_SCHEDULING_PREFERENCES',
 pg_temp.q_prefs('{"break_minutes":15}',pg_temp.q_rev()),'q12-prefs-warn-001'));
select ok(res->>'outcome'='COMMITTED' and res#>>'{warnings,0,code}'='APPROVED_BLOCKS_MAY_BE_AFFECTED','a policy change warns too') from q12 where name='w_pref';
select ok(app_private.matches_contract('set_busy_intervalResult',res) and app_private.matches_contract('set_scheduling_preferencesResult',(select res from q12 where name='w_pref')),
 'warning payloads stay contract-valid') from q12 where name='w_busy';
select * from finish();
rollback;
