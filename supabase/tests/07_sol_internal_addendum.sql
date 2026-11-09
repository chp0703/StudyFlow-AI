-- Nghiệm thu độc lập cho gói bổ sung 1.0.1 đã duyệt, schema logic 1.1.
-- A/B/C/D được duyệt rõ ngày 05/11/2026; test được viết
-- trước khi đồng bộ schema WP0 và SQL WP2, chủ động vẫn thất bại
-- trên baseline tám migration. Chạy: supabase test db
-- Rollback khóa giả lập, mọi fixture và thay đổi dữ liệu; không chạy trên cloud.
-- Bộ test độc lập, không dùng lại trạng thái pg_temp của test 06.
begin;
select no_plan();
set local search_path = public, extensions;
set local timezone = 'UTC';

select ok(exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 join pg_roles r on r.oid=p.proowner where n.nspname='app_api' and p.proname=e.name
 and p.pronargs=1 and p.proargtypes[0]='jsonb'::regtype
 and p.proargnames=array['p_request']::text[] and p.prorettype='jsonb'::regtype
 and p.prosecdef and r.rolname='sf_rpc_owner'
 and coalesce('search_path=""'=any(p.proconfig),false)
 and has_function_privilege('authenticated',p.oid,'EXECUTE')
 and not has_function_privilege('anon',p.oid,'EXECUTE')
 and not exists(select 1 from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
 where a.grantee=0 and a.privilege_type='EXECUTE')),
 e.name || ' has exact signature, restricted DEFINER owner/path and grants')
 from (values ('ensure_user_context'),('list_time_windows'),('get_workflow_context'),
 ('get_workflow_continuation'),('initialize_workflow_continuation'),
 ('checkpoint_workflow_continuation')) e(name);
select ok((select c.relrowsecurity and c.relforcerowsecurity from pg_class c
 join pg_namespace n on n.oid=c.relnamespace where n.nspname='app_private'
 and c.relname='workflow_continuations'),'continuations enable and force RLS');
select ok(not exists(select 1 from pg_roles r cross join pg_class c
 join pg_namespace n on n.oid=c.relnamespace where r.rolname in ('anon','authenticated')
 and n.nspname='app_private' and c.relname='workflow_continuations'
 and has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')),
 'continuations have no direct client privileges');
select ok(exists(select 1 from pg_index i join pg_class t on t.oid=i.indrelid
 join pg_namespace n on n.oid=t.relnamespace where n.nspname='app_private'
 and t.relname='workflow_continuations' and i.indisunique and i.indpred is not null),
 'unfinished continuations have a partial unique guard');

-- Ghi lỗi hàm chưa định nghĩa/SQL thành khẳng định thất bại, không coi là
-- lỗi bảo mật công khai hợp lệ. Tách fixture quản trị khỏi lần gọi RPC.
create function pg_temp.q7_canonical(value jsonb) returns text language plpgsql as $$
declare result text;
begin execute 'select app_private.canonical_json($1)' into result using value; return result;
exception when others then return 'SQL_ERROR:'||sqlstate||':'||sqlerrm;
end $$;
create function pg_temp.q7_sign(request jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); payload text; body jsonb;
begin
 body:=jsonb_build_object('v',1,'key_id','sol07-local-only',
 'user_id',request#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',request->>'operation','request_id',request->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.q7_canonical(request-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.q7_canonical(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(request,'{attestation}',jsonb_build_object('key_id','sol07-local-only',
 'payload',payload,'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),
 decode(repeat('07',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.q7_request(operation text, arguments jsonb,
 signed boolean default false, idem text default null,
 owner_id uuid default 'd0710000-0000-4000-8000-000000000001',
 message_id uuid default 'd0710000-0000-4000-8000-000000000004')
 returns jsonb language plpgsql as $$
declare request jsonb;
begin
 request:=jsonb_build_object('contract_version','1.0.1','schema_version','1.1',
 'request_id','sol07-request','operation',operation,'arguments',arguments,'attestation',null,
 'execution_context',jsonb_build_object('conversation_id','d0710000-0000-4000-8000-000000000003',
 'idempotency_key',idem,'approval_action',null,'action_reference',null,
 'trusted_context',jsonb_build_object('request_id','sol07-request',
 'message_id',message_id,
 'principal',jsonb_build_object('user_id',owner_id),'timezone','Asia/Ho_Chi_Minh',
 'locale','vi-VN','received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))));
 if signed then return pg_temp.q7_sign(request); end if;
 return request;
end $$;
create function pg_temp.q7_call(request jsonb) returns jsonb language plpgsql as $$
declare result jsonb;
begin
 perform set_config('request.jwt.claims',
 '{"sub":"d0710000-0000-4000-8000-000000000001","role":"authenticated"}',true);
 perform set_config('request.jwt.claim.sub','d0710000-0000-4000-8000-000000000001',true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',request->>'operation') into result using request;
 exception when others then result:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role;
 return result;
end $$;
create function pg_temp.q7_error(result jsonb, codes text[]) returns boolean language sql as $$
 select coalesce(result->>'outcome'='ERROR' and result->'data'='null'::jsonb
 and result#>>'{error,code}'=any(codes) and result->>'schema_version'='1.1'
 and result->>'request_id'='sol07-request' and jsonb_typeof(result->'warnings')='array',false)
$$;
create function pg_temp.q7_snapshot() returns jsonb language plpgsql as $$
declare item record; value jsonb; result jsonb:='{}';
begin
 for item in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='app_private' and c.relkind in ('r','p') and c.relname<>'rpc_attestation_keys' loop
 execute format('select coalesce(jsonb_agg(v order by v::text),''[]''::jsonb) from (select to_jsonb(t) v from app_private.%I t) x',item.relname) into value;
 result:=result||jsonb_build_object(item.relname,value);
 end loop; return result;
end $$;
create function pg_temp.q7_seed() returns text language plpgsql as $$
begin
 insert into auth.users(id) values ('d0710000-0000-4000-8000-000000000001'),
 ('d0710000-0000-4000-8000-000000000002');
 execute $q$insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('sol07-local-only',decode(repeat('07',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour')$q$;
 return 'OK';
exception when others then return 'SQL_ERROR:'||sqlstate||':'||sqlerrm;
end $$;
select is(pg_temp.q7_seed(),'OK','seed only users and synthetic signing key');
create temporary table q7_results(name text primary key, result jsonb);
create temporary table q7_before as select pg_temp.q7_snapshot() value;

insert into q7_results values ('bootstrap_unsigned',pg_temp.q7_call(pg_temp.q7_request('ensure_user_context','{}')));
select ok(pg_temp.q7_error(result,array['FORBIDDEN','UNAUTHENTICATED']),
 'potential first-GET bootstrap always requires attestation') from q7_results where name='bootstrap_unsigned';
select is(pg_temp.q7_snapshot(),value,'unsigned bootstrap creates no profile or other rows') from q7_before;
insert into q7_results values ('bootstrap',pg_temp.q7_call(pg_temp.q7_request('ensure_user_context','{}',true)));
select ok(result->>'outcome'='COMMITTED' and result->'error'='null'::jsonb
 and result#>>'{data,user_id}'='d0710000-0000-4000-8000-000000000001'
 and result#>>'{data,schedule_revision}'='0','signed bootstrap with null idempotency key returns User/revision zero')
 from q7_results where name='bootstrap';
truncate q7_before; insert into q7_before select pg_temp.q7_snapshot();
insert into q7_results values ('bootstrap_again',pg_temp.q7_call(pg_temp.q7_request('ensure_user_context','{}',true)));
select is((select result->'data' from q7_results where name='bootstrap_again'),
 (select result->'data' from q7_results where name='bootstrap'),'existing profile returns unchanged including audit timestamps');
select is(pg_temp.q7_snapshot(),value,'repeat bootstrap mutates no existing state') from q7_before;
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_request('ensure_user_context',
 '{"user_id":"d0710000-0000-4000-8000-000000000002"}',true)),array['INVALID_PARAMETER']),
 'bootstrap rejects caller-selected owner even with valid backend signature');

insert into q7_results values ('windows_empty',pg_temp.q7_call(pg_temp.q7_request('list_time_windows',
 '{"kind":null,"include_archived":false,"page_size":50,"cursor":null}')));
select ok(result->>'outcome'='READ' and result#>'{data,items}'='[]'::jsonb
 and result#>'{data,next_cursor}'='null'::jsonb,'signed bootstrap enables ordinary read-only window listing')
 from q7_results where name='windows_empty';
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_request('list_time_windows',
 '{"kind":null,"include_archived":false,"page_size":50,"cursor":"tampered-cursor"}')),array['INVALID_PARAMETER']),
 'tampered opaque window cursor is an INVALID_PARAMETER');
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_request('get_workflow_context',
 '{"conversation_id":"d0710000-0000-4000-8000-000000000099","action_id":null,"message_id":null}')),
 array['ENTITY_NOT_FOUND']),'workflow read does not create an absent conversation');
select is(pg_temp.q7_snapshot(),value,'read/invalid owner fields do not mutate existing state') from q7_before;

-- Lấy receipt nguồn đang hiệu lực thật rồi lưu tin nhắn USER gốc đã được cấp ID
-- qua RPC đã duyệt. Không tự tạo receipt hay giả kết quả nhận lease thành công.
insert into q7_results values ('claim',pg_temp.q7_call(pg_temp.q7_request('claim_api_receipt',
 jsonb_build_object('http_operation','send_message','idempotency_key','sol07-origin-key-0001',
 'request_fingerprint',repeat('a',64),'conversation_id','d0710000-0000-4000-8000-000000000003'),
 true,'sol07-claim-child-0001')));
select ok(result->>'outcome'='COMMITTED' and result#>>'{data,lease_version}'='1'
 and result#>>'{data,message_id}' is not null,'origin claim allocates durable message identity and active lease')
 from q7_results where name='claim';
insert into q7_results select 'message',pg_temp.q7_call(pg_temp.q7_request('record_source_message',
 jsonb_build_object('message',jsonb_build_object('message_id',result#>>'{data,message_id}',
 'user_id','d0710000-0000-4000-8000-000000000001','conversation_id','d0710000-0000-4000-8000-000000000003',
 'source','CHAT','role','USER','text','Tìm alpha rồi beta',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))),true,'sol07-source-child-0001',
 'd0710000-0000-4000-8000-000000000001',(result#>>'{data,message_id}')::uuid))
 from q7_results where name='claim';
select is(result->>'outcome','COMMITTED','original receipt message is durably persisted') from q7_results where name='message';
insert into q7_results select 'workflow_load',pg_temp.q7_call(pg_temp.q7_request('get_workflow_context',
 jsonb_build_object('conversation_id','d0710000-0000-4000-8000-000000000003',
 'action_id',null,'message_id',result#>>'{data,message_id}'))) from q7_results where name='claim';
select ok(result->>'outcome'='READ' and result#>'{data,active_action}'='null'::jsonb
 and result#>'{data,selected_action}'='null'::jsonb
 and result#>>'{data,source_message,role}'='USER'
 and result#>>'{data,source_message,conversation_id}'='d0710000-0000-4000-8000-000000000003',
 'cold workflow read loads exact persisted source and null actions without creating an action')
 from q7_results where name='workflow_load';

create temporary table q7_requests(name text primary key, request jsonb);
insert into q7_requests select 'initialize',pg_temp.q7_request('initialize_workflow_continuation',
 jsonb_build_object('conversation_id','d0710000-0000-4000-8000-000000000003',
 'source_message_id',result#>>'{data,message_id}',
 'extraction','{"intents":[{"intent":"SEARCH_TASKS","slots":{"query":"alpha"},"raw_expressions":{},"ambiguities":[]},{"intent":"SEARCH_TASKS","slots":{"query":"beta"},"raw_expressions":{},"ambiguities":[]}]}'::jsonb,
 'depends_on','[[],[0]]'::jsonb,'receipt_binding',jsonb_build_object('http_operation','send_message',
 'idempotency_key','sol07-origin-key-0001','request_fingerprint',repeat('a',64),
 'expected_lease_version',(result#>>'{data,lease_version}')::bigint)),true,'sol07-initialize-child-0001',
 'd0710000-0000-4000-8000-000000000001',(result#>>'{data,message_id}')::uuid)
 from q7_results where name='claim';
truncate q7_before; insert into q7_before select pg_temp.q7_snapshot();
select ok(pg_temp.q7_error(pg_temp.q7_call(jsonb_set(request,'{attestation}','null')),
 array['FORBIDDEN','UNAUTHENTICATED']),'continuation initialization requires attestation') from q7_requests where name='initialize';
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(request,
 '{arguments,receipt_binding,expected_lease_version}','999'))),
 array['STALE_ENTITY_VERSION','IDEMPOTENCY_CONFLICT','FORBIDDEN']),
 'initializer cannot use an obsolete or invented receipt fencing version') from q7_requests where name='initialize';
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(request,
 '{arguments,receipt_binding,request_fingerprint}',to_jsonb(repeat('b',64))))),array['IDEMPOTENCY_CONFLICT']),
 'initializer binds exact origin receipt fingerprint') from q7_requests where name='initialize';
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(request,
 '{arguments,depends_on}','[[1],[]]'))),array['INVALID_PARAMETER']),
 'dependency cannot refer forward to a not-yet-processed step') from q7_requests where name='initialize';
select is(pg_temp.q7_snapshot(),value,'all failed initialization guards leave no continuation or side effects') from q7_before;
insert into q7_results select 'initialize',pg_temp.q7_call(request) from q7_requests where name='initialize';
select ok(result->'error'='null'::jsonb and result#>>'{data,version}'='1'
 and result#>>'{data,cursor}'='0' and result#>'{data,completed_steps}'='[]'::jsonb
 and result#>'{data,awaiting_reference}'='null'::jsonb,'first initialization stores immutable queue with version1/cursor0')
 from q7_results where name='initialize';
select is((select result#>>'{data,extraction_digest}' from q7_results where name='initialize'),
 (select encode(extensions.digest(convert_to(pg_temp.q7_canonical(request#>'{arguments,extraction}'),'UTF8'),'sha256'),'hex')
 from q7_requests where name='initialize'),'extraction digest is computed from canonical normalized extraction');
insert into q7_results select 'initialize_race_replay',pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(request,
 '{arguments,extraction,intents,0,slots,query}','"different extractor result"')))
 from q7_requests where name='initialize';
select is((select result->'data' from q7_results where name='initialize_race_replay'),
 (select result->'data' from q7_results where name='initialize'),
 'same source/origin replay returns first extraction before comparing duplicate extractor output');

-- Chỉ dịch đồng hồ lease vận hành tương ứng trong fixture quản trị;
-- kiểm tra quy tắc bảo vệ, không kiểm chứng hết hạn sau 120 giây thực.
create function pg_temp.q7_lease(expire boolean) returns text language plpgsql as $$
declare changed bigint;
begin
 execute $q$update app_private.api_request_receipts set lease_until=
 clock_timestamp()+case when $1 then -interval '1 second' else interval '120 seconds' end
 where user_id='d0710000-0000-4000-8000-000000000001'
 and http_operation='send_message' and idempotency_key='sol07-origin-key-0001'$q$ using expire;
 get diagnostics changed=row_count;
 return case when changed=1 then 'OK' else 'FIXTURE_ERROR:receipt count='||changed end;
exception when others then return 'SQL_ERROR:'||sqlstate||':'||sqlerrm;
end $$;
select is(pg_temp.q7_lease(true),'OK','administratively expire origin receipt lease for guard fixture');
truncate q7_before; insert into q7_before select pg_temp.q7_snapshot();
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(request)),
 array['STALE_ENTITY_VERSION','IDEMPOTENCY_CONFLICT','FORBIDDEN','SERVICE_UNAVAILABLE']),
 'even initialization replay cannot authorize work with an expired origin lease') from q7_requests where name='initialize';
select is(pg_temp.q7_snapshot(),value,'expired-origin initializer changes no queue or receipt state') from q7_before;
select is(pg_temp.q7_lease(false),'OK','restore operational origin lease for remaining CAS tests');

insert into q7_requests select 'load_exact',pg_temp.q7_request('get_workflow_continuation',
 jsonb_build_object('conversation_id','d0710000-0000-4000-8000-000000000003',
 'source_message_id',request#>>'{arguments,source_message_id}')) from q7_requests where name='initialize';
insert into q7_requests values ('load_active',pg_temp.q7_request('get_workflow_continuation',
 '{"conversation_id":"d0710000-0000-4000-8000-000000000003","source_message_id":null}'));
insert into q7_results select name,pg_temp.q7_call(request) from q7_requests where name in ('load_exact','load_active');
select is(result#>'{data,continuation}',(select result->'data' from q7_results where name='initialize'),
 name||' loads canonical durable queue without extraction') from q7_results where name in ('load_exact','load_active');
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_request('get_workflow_continuation',
 '{"conversation_id":"d0710000-0000-4000-8000-000000000003","source_message_id":null}',false,null,
 'd0710000-0000-4000-8000-000000000002')),array['FORBIDDEN','UNAUTHENTICATED']),
 'read principal cannot differ from authenticated owner');

-- ADVANCE hợp lệ cho bước đọc tức thì không cần tự tạo action/presentation.
-- Thiết kế đã duyệt tin kết quả đọc đúng schema có chứng thực; nhưng thao tác
-- ghi bên dưới phải chứng minh action kết thúc đã lưu bền vững và kết quả operation tương ứng.
insert into q7_requests select 'advance',pg_temp.q7_request('checkpoint_workflow_continuation',
 jsonb_build_object('conversation_id','d0710000-0000-4000-8000-000000000003',
 'source_message_id',request#>>'{arguments,source_message_id}',
 'expected_version',1,'expected_cursor',0,'transition','ADVANCE','action_reference',null,
 'receipt_binding',request#>'{arguments,receipt_binding}',
 'outcome',jsonb_build_object('intent_index',0,'step_key',encode(extensions.digest(convert_to(
 pg_temp.q7_canonical(jsonb_build_object('api_key','sol07-origin-key-0001',
 'source_message_id',request#>>'{arguments,source_message_id}','intent_index',0)),'UTF8'),'sha256'),'hex'),
 'operation','search_tasks','disposition','SUCCEEDED','error',null,
 'result',jsonb_build_object('schema_version','1.1','request_id','sol07-read-result',
 'outcome','READ','data',jsonb_build_object('items','[]'::jsonb,'next_cursor',null),
 'error',null,'warnings','[]'::jsonb))),true,'sol07-checkpoint-child-0001',
 'd0710000-0000-4000-8000-000000000001',(request#>>'{arguments,source_message_id}')::uuid)
 from q7_requests where name='initialize';
truncate q7_before; insert into q7_before select pg_temp.q7_snapshot();
select ok(pg_temp.q7_error(pg_temp.q7_call(jsonb_set(request,'{attestation}','null')),
 array['FORBIDDEN','UNAUTHENTICATED']),'checkpoint always requires attestation') from q7_requests where name='advance';
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(request,
 '{arguments,outcome,step_key}',to_jsonb(repeat('0',64))))),array['INVALID_PARAMETER','IDEMPOTENCY_CONFLICT']),
 'checkpoint rejects step key not derived from immutable origin/source/index') from q7_requests where name='advance';
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(request,
 '{arguments,expected_version}','999'))),array['STALE_ENTITY_VERSION','IDEMPOTENCY_CONFLICT']),
 'checkpoint compares expected version under owner lock') from q7_requests where name='advance';
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(request,
 '{arguments,expected_cursor}','1'))),array['STALE_ENTITY_VERSION','IDEMPOTENCY_CONFLICT']),
 'checkpoint cannot skip unfinished cursor step') from q7_requests where name='advance';
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(request,
 '{arguments,receipt_binding,expected_lease_version}','999'))),
 array['STALE_ENTITY_VERSION','IDEMPOTENCY_CONFLICT','FORBIDDEN']),
 'checkpoint independently enforces receipt fencing') from q7_requests where name='advance';
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(jsonb_set(jsonb_set(request,
 '{arguments,transition}','"WAIT"'),'{arguments,outcome}','null'),'{arguments,action_reference}',
 '{"action_id":"d0710000-0000-4000-8000-000000000099","action_version":1,"target_type":"PENDING_ACTION","target_id":"d0710000-0000-4000-8000-000000000099","target_version":1}'))),
 array['ENTITY_NOT_FOUND','INVALID_PARAMETER','STALE_ENTITY_VERSION']),
 'WAIT cannot manufacture an awaiting action/presentation from a reference') from q7_requests where name='advance';
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(request,
 '{arguments,outcome,operation}','"confirm_task"'))),array['INVALID_PARAMETER','IDEMPOTENCY_CONFLICT','FORBIDDEN']),
 'schema-valid read result cannot fabricate successful domain-write evidence') from q7_requests where name='advance';
select is(pg_temp.q7_snapshot(),value,'failed checkpoint guards change no business, receipt or queue state') from q7_before;
insert into q7_results select 'advance',pg_temp.q7_call(request) from q7_requests where name='advance';
select ok(result->'error'='null'::jsonb and result#>>'{data,version}'='2'
 and result#>>'{data,cursor}'='1' and jsonb_array_length(result#>'{data,completed_steps}')=1
 and result#>>'{data,completed_steps,0,intent_index}'='0','immediate read advances contiguous prefix exactly once')
 from q7_results where name='advance';
insert into q7_results select 'advance_replay',pg_temp.q7_call(pg_temp.q7_sign(request)) from q7_requests where name='advance';
select is((select result->'data' from q7_results where name='advance_replay'),
 (select result->'data' from q7_results where name='advance'),'identical already-applied CAS replays without another version/cursor increment');
select is(pg_temp.q7_lease(true),'OK','expire origin lease before checkpoint replay');
truncate q7_before; insert into q7_before select pg_temp.q7_snapshot();
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(request)),
 array['STALE_ENTITY_VERSION','IDEMPOTENCY_CONFLICT','FORBIDDEN','SERVICE_UNAVAILABLE']),
 'an expired receipt cannot authorize a checkpoint, including duplicate CAS') from q7_requests where name='advance';
select is(pg_temp.q7_snapshot(),value,'expired-receipt checkpoint changes no state') from q7_before;
select is(pg_temp.q7_lease(false),'OK','restore receipt lease after expired-checkpoint guard');
select ok(pg_temp.q7_error(pg_temp.q7_call(pg_temp.q7_sign(jsonb_set(request,
 '{arguments,outcome,disposition}','"DEPENDENCY_CANCELLED"'))),
 array['STALE_ENTITY_VERSION','IDEMPOTENCY_CONFLICT','INVALID_PARAMETER']),
 'old cursor cannot be overwritten with incompatible recorded outcome') from q7_requests where name='advance';

-- Chuyển step1 bằng khóa xác định riêng, rồi phân biệt tra chính xác bản đã xong
-- với tra bản đang hoạt động; không được chọn hàng đợi cũ gần nhất làm bản đang hoạt động.
insert into q7_requests select 'advance_last',pg_temp.q7_sign(jsonb_set(jsonb_set(jsonb_set(jsonb_set(jsonb_set(request,
 '{arguments,expected_version}','2'),'{arguments,expected_cursor}','1'),'{arguments,outcome,intent_index}','1'),
 '{arguments,outcome,step_key}',to_jsonb(encode(extensions.digest(convert_to(pg_temp.q7_canonical(
 jsonb_build_object('api_key','sol07-origin-key-0001','source_message_id',request#>>'{arguments,source_message_id}',
 'intent_index',1)),'UTF8'),'sha256'),'hex'))),'{execution_context,idempotency_key}','"sol07-checkpoint-child-0002"'))
 from q7_requests where name='advance';
insert into q7_results select 'advance_last',pg_temp.q7_call(request) from q7_requests where name='advance_last';
select ok(result->'error'='null'::jsonb and result#>>'{data,cursor}'='2'
 and result#>>'{data,version}'='3','second immediate read completes the ordered queue') from q7_results where name='advance_last';
insert into q7_results select 'load_finished_'||name,pg_temp.q7_call(request)
 from q7_requests where name in ('load_exact','load_active');
select ok(result->>'outcome'='READ' and result#>'{data,continuation}'='null'::jsonb,
 'active lookup never resurrects a completed continuation') from q7_results where name='load_finished_load_active';
select is(result#>>'{data,continuation,cursor}','2','exact source lookup still recovers completed continuation')
 from q7_results where name='load_finished_load_exact';

select ok(not exists(select 1 from app_private.idempotency_records
 where user_id='d0710000-0000-4000-8000-000000000001' and operation in
 ('ensure_user_context','initialize_workflow_continuation','checkpoint_workflow_continuation')),
 'new helpers never add names to domain idempotency namespace');
select is((select schedule_revision from app_private.user_profiles
 where user_id='d0710000-0000-4000-8000-000000000001'),0::bigint,
 'bootstrap, queue initialization/read/checkpoint leave scheduling revision unchanged');
select * from finish();
rollback;
