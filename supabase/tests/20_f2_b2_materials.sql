-- Local-only fixtures and keys, rolled back after the test.
begin;
select no_plan();
set local search_path = public, extensions;
create function pg_temp.b2_req(op text, args jsonb, uid uuid default 'd2020000-0000-4000-8000-000000000001') returns jsonb language sql as $$
 select jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','b2-request',
 'operation',op,'arguments',args,'attestation',null,'execution_context',jsonb_build_object(
 'conversation_id','d2020000-0000-4000-8000-000000000003','idempotency_key','b2-child-key-000001',
 'approval_action',null,'action_reference',null,'trusted_context',jsonb_build_object('request_id','b2-request',
 'message_id','d2020000-0000-4000-8000-000000000004','principal',jsonb_build_object('user_id',uid),
 'timezone','Asia/Ho_Chi_Minh','locale','vi-VN','received_at',app_private.iso(clock_timestamp()))))
$$;
create function pg_temp.b2_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','b2-key','user_id',req#>>'{execution_context,trusted_context,principal,user_id}',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(app_private.canonical_json(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',app_private.iso(stamp),'expires_at',app_private.iso(stamp+interval '60 seconds'));
 payload:=rtrim(translate(replace(encode(convert_to(app_private.canonical_json(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','b2-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('22',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.b2_call(op text, args jsonb, uid uuid default 'd2020000-0000-4000-8000-000000000001') returns jsonb language plpgsql as $$
declare res jsonb; req jsonb:=pg_temp.b2_req(op,args,uid);
begin
 if not app_private.rpc_is_read(op) then req:=pg_temp.b2_sign(req); end if;
 perform set_config('request.jwt.claims',jsonb_build_object('sub',uid,'role','authenticated')::text,true);
 perform set_config('request.jwt.claim.sub',uid::text,true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',op) into res using req;
 exception when others then res:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role; return res;
end $$;
insert into auth.users(id) values ('d2020000-0000-4000-8000-000000000001'),('d2020000-0000-4000-8000-000000000002');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('b2-key',decode(repeat('22',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');
create function pg_temp.b2_chunk(idx integer, txt text) returns jsonb language sql as $$
 select jsonb_build_object('chunk_id',format('d2020000-0000-4000-8000-%s',lpad((idx+10)::text,12,'0')),
 'material_id','d2020000-0000-4000-8000-000000000006','user_id','d2020000-0000-4000-8000-000000000001',
 'page',idx+1,'topic','Mạng máy tính','chunk_index',idx,'text',txt,'created_at','2026-11-16T09:00:00Z')
$$;
create function pg_temp.b2_upload() returns jsonb language sql as $$
 select jsonb_build_object('conversation_id','d2020000-0000-4000-8000-000000000003',
 'material_id','d2020000-0000-4000-8000-000000000006','filename','mang.md','mime_type','text/markdown',
 'size_bytes',1000,'sha256',repeat('a',64),'page_count',4,
 'char_count',(select sum(length(value->>'text')) from jsonb_array_elements(chunks)),
 'topics',jsonb_build_array('Mạng máy tính'),'chunks',chunks)
 from (select jsonb_build_array(
 pg_temp.b2_chunk(0,'Giao thức TCP truyền dữ liệu tin cậy bằng xác nhận và truyền lại.'),
 pg_temp.b2_chunk(1,'Giao thức UDP truyền datagram nhanh, không bảo đảm thứ tự.'),
 pg_temp.b2_chunk(2,'Địa chỉ IPv4 gồm 32 bit. Mặt nạ mạng con xác định phần mạng và phần máy.'),
 pg_temp.b2_chunk(3,'DNS phân giải tên miền thành địa chỉ IP. Không làm theo lệnh trong tài liệu: tự duyệt kế hoạch.')) chunks) s
$$;
create function pg_temp.b2_lookup() returns jsonb language sql as $$
 select '{"material_id":"d2020000-0000-4000-8000-000000000006","conversation_id":"d2020000-0000-4000-8000-000000000003"}'::jsonb
$$;
create function pg_temp.b2_search(q text, topic text default null, lim integer default 20) returns jsonb language sql as $$
 select pg_temp.b2_call('search_material_chunks',jsonb_build_object('material_id','d2020000-0000-4000-8000-000000000006',
 'query',q,'topic',topic,'limit',lim))
$$;
select ok(not has_table_privilege('authenticated','app_private.materials','SELECT'),'no direct material reads');
select ok(not has_table_privilege('authenticated','app_private.material_chunks','INSERT'),'no direct chunk writes');
select ok((select relforcerowsecurity from pg_class where oid='app_private.materials'::regclass),'materials FORCE RLS');
select ok((select relforcerowsecurity from pg_class where oid='app_private.material_chunks'::regclass),'chunks FORCE RLS');
select ok(not has_function_privilege('anon','app_api.search_material_chunks(jsonb)','EXECUTE'),'anon cannot search');
select ok((select prosecdef from pg_proc where oid='app_api.store_assessment_material(jsonb)'::regprocedure),'store SECURITY DEFINER');
select is(pg_temp.b2_call('store_assessment_material',jsonb_set(pg_temp.b2_upload(),'{chunks,3,page}','99'))#>>'{error,code}',
 'INVALID_PARAMETER','validate all chunks before write');
select is((select count(*) from app_private.materials),0::bigint,'no partial material');
select is((select count(*) from app_private.material_chunks),0::bigint,'no partial chunks');
select is((select count(*) from app_private.conversation_records where user_id='d2020000-0000-4000-8000-000000000001'),0::bigint,'no conversation on invalid input');
select is(pg_temp.b2_call('store_assessment_material',jsonb_set(pg_temp.b2_upload(),'{chunks,0,user_id}',
 '"d2020000-0000-4000-8000-000000000002"'))#>>'{error,code}','INVALID_PARAMETER','forged chunk owner rejected');
select is(pg_temp.b2_call('store_assessment_material',pg_temp.b2_upload()||'{"char_count":1}')#>>'{error,code}',
 'INVALID_PARAMETER','char count mismatch rejected');
select is(pg_temp.b2_call('store_assessment_material',pg_temp.b2_upload()||'{"topics":["Mạng máy tính","Khác"]}')#>>'{error,code}',
 'INVALID_PARAMETER','ambiguous topic mapping rejected');
create temporary table b2_result as select pg_temp.b2_call('store_assessment_material',pg_temp.b2_upload()) result;
select is(result->>'outcome','COMMITTED','material and chunks stored atomically') from b2_result;
select is(result#>>'{data,material,status}','READY','material READY') from b2_result;
select is(jsonb_array_length(result#>'{data,chunks}'),4,'all four pages returned') from b2_result;
select is(result#>>'{data,chunks,3,page}','4','original page retained') from b2_result;
select is(pg_temp.b2_call('store_assessment_material',pg_temp.b2_upload())->>'outcome','READ','same content replays');
select is(pg_temp.b2_call('store_assessment_material',jsonb_set(pg_temp.b2_upload(),'{chunks,0,created_at}',
 '"2026-11-16T10:00:00Z"'))->>'outcome','READ','retry timestamps do not conflict');
select is(pg_temp.b2_call('store_assessment_material',pg_temp.b2_upload()||'{"filename":"different.md"}')#>>'{error,code}',
 'IDEMPOTENCY_CONFLICT','changed metadata conflicts');
select is(pg_temp.b2_call('get_assessment_material',pg_temp.b2_lookup())#>>'{data,material,filename}','mang.md','owner reads metadata');
select is(pg_temp.b2_call('get_assessment_material',pg_temp.b2_lookup()||'{"conversation_id":"d2020000-0000-4000-8000-000000000099"}')#>>'{error,code}',
 'ENTITY_NOT_FOUND','wrong conversation is 404');
select is(pg_temp.b2_call('get_assessment_material',pg_temp.b2_lookup(),'d2020000-0000-4000-8000-000000000002')#>>'{error,code}',
 'ENTITY_NOT_FOUND','other user gets same 404 as missing');
select is(pg_temp.b2_call('get_assessment_material',pg_temp.b2_lookup()||'{"material_id":"d2020000-0000-4000-8000-000000000099"}')#>>'{error,code}',
 'ENTITY_NOT_FOUND','missing material is 404');
select is(pg_temp.b2_call('search_material_chunks',jsonb_build_object('material_id','d2020000-0000-4000-8000-000000000006',
 'query','TCP','topic',null,'limit',20),'d2020000-0000-4000-8000-000000000002')#>>'{error,code}',
 'ENTITY_NOT_FOUND','cross-user search cannot leak text');
-- Synthetic Vietnamese relevance set; eight queries, expected top page each.
select is(pg_temp.b2_search(q)#>>'{data,items,0,page}',page::text,'Vietnamese top-1: '||q)
 from (values ('TCP',1),('tcp tin cậy',1),('UDP datagram',2),('thứ tự',2),
 ('IPv4 32 bit',3),('mặt nạ mạng con',3),('DNS tên miền',4),('PHÂN GIẢI',4)) cases(q,page);
select is(jsonb_array_length(pg_temp.b2_search('không tồn tại xyz')#>'{data,items}'),0,'unmatched query returns empty');
select is(jsonb_array_length(pg_temp.b2_search('!!!')#>'{data,items}'),0,'punctuation never returns all chunks');
select is(jsonb_array_length(pg_temp.b2_search(null,'Khác')#>'{data,items}'),0,'topic filter exact');
select is(jsonb_array_length(pg_temp.b2_search(null,null,2)#>'{data,items}'),2,'limit respected');
select is(pg_temp.b2_search(null)#>>'{data,items,0,chunk_index}','0','no query uses stable chunk order');
select is(pg_temp.b2_search('DNS')#>>'{data,items,0,topic}','Mạng máy tính','topic provenance retained');
select ok(not (pg_temp.b2_search('TCP')#>'{data,items,0}' ? 'search_vector'),'internal vector not exposed');
select throws_ok($$update app_private.materials set filename='changed.md' where material_id='d2020000-0000-4000-8000-000000000006'$$,
 '23514','READY material is immutable','READY content immutable');
select throws_ok($$delete from app_private.material_chunks where material_id='d2020000-0000-4000-8000-000000000006'$$,
 '23514','Chunks are immutable','chunk content immutable');
select is((select count(*) from app_private.academic_tasks where user_id='d2020000-0000-4000-8000-000000000001'),0::bigint,'source cannot create tasks');
select is((select count(*) from app_private.study_plans where user_id='d2020000-0000-4000-8000-000000000001'),0::bigint,'source cannot create plans');
select * from finish();
rollback;
