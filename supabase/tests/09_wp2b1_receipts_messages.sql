-- WP2b-1: khởi tạo có chữ ký, tin nhắn nguồn và lease API receipt; pgTAP local, có rollback.
-- Đồng hồ lease được dịch bằng quyền quản trị và ghi rõ; không chờ 120 giây thực ở đây.
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.q9_canon(v jsonb) returns text language sql as $$ select app_private.canonical_json(v) $$;
create function pg_temp.q9_req(op text, args jsonb, conv uuid default 'd0910000-0000-4000-8000-000000000003',
 msg uuid default 'd0910000-0000-4000-8000-000000000004') returns jsonb language sql as $$
 select jsonb_build_object('contract_version','1.0.1','schema_version','1.1','request_id','q9-request',
 'operation',op,'arguments',args,'attestation',null,'execution_context',jsonb_build_object(
 'conversation_id',conv,'idempotency_key','q9-child-key-000001','approval_action',null,'action_reference',null,
 'trusted_context',jsonb_build_object('request_id','q9-request','message_id',msg,
 'principal',jsonb_build_object('user_id','d0910000-0000-4000-8000-000000000001'),
 'timezone','Asia/Ho_Chi_Minh','locale','vi-VN',
 'received_at',to_char(clock_timestamp() at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'))))
$$;
create function pg_temp.q9_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz:=clock_timestamp(); body jsonb; payload text;
begin
 body:=jsonb_build_object('v',1,'key_id','q9-key','user_id','d0910000-0000-4000-8000-000000000001',
 'rpc',req->>'operation','request_id',req->>'request_id',
 'request_digest',encode(extensions.digest(convert_to(pg_temp.q9_canon(req-'attestation'),'UTF8'),'sha256'),'hex'),
 'issued_at',to_char(stamp at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'),
 'expires_at',to_char((stamp+interval '60 seconds') at time zone 'UTC','YYYY-MM-DD"T"HH24:MI:SS.US"Z"'));
 payload:=rtrim(translate(replace(encode(convert_to(pg_temp.q9_canon(body),'UTF8'),'base64'),E'\n',''),'+/','-_'),'=');
 return jsonb_set(req,'{attestation}',jsonb_build_object('key_id','q9-key','payload',payload,
 'signature',encode(extensions.hmac(convert_to(payload,'UTF8'),decode(repeat('09',32),'hex'),'sha256'),'hex')));
end $$;
create function pg_temp.q9_call(op text, args jsonb) returns jsonb language plpgsql as $$
declare res jsonb; signed jsonb := pg_temp.q9_sign(pg_temp.q9_req(op,args));
begin
 perform set_config('request.jwt.claims','{"sub":"d0910000-0000-4000-8000-000000000001","role":"authenticated"}',true);
 perform set_config('request.jwt.claim.sub','d0910000-0000-4000-8000-000000000001',true);
 set local role authenticated;
 begin execute format('select app_api.%I($1)',op) into res using signed;
 exception when others then res:=jsonb_build_object('sqlstate',sqlstate,'message',sqlerrm); end;
 reset role; return res;
end $$;
create function pg_temp.q9_receipt() returns jsonb language sql as $$
 select to_jsonb(r) from app_private.api_request_receipts r where r.idempotency_key='q9-origin-key-00001' $$;
create function pg_temp.q9_claim(key text default 'q9-origin-key-00001', fp text default null) returns jsonb language sql as $$
 select pg_temp.q9_call('claim_api_receipt',jsonb_build_object('http_operation','send_message','idempotency_key',key,
 'request_fingerprint',coalesce(fp,repeat('a',64)),'conversation_id','d0910000-0000-4000-8000-000000000003')) $$;
create function pg_temp.q9_lease_args(version bigint, extra jsonb default '{}') returns jsonb language sql as $$
 select jsonb_build_object('http_operation','send_message','idempotency_key','q9-origin-key-00001',
 'request_fingerprint',repeat('a',64),'expected_lease_version',version)||extra $$;
create function pg_temp.q9_is(res jsonb, code text) returns boolean language sql as $$
 select coalesce(res->>'outcome'='ERROR' and res#>>'{error,code}'=code and res->'data'='null'::jsonb,false) $$;
create function pg_temp.q9_reply(code text, retry boolean) returns jsonb language sql as $$
 select jsonb_build_object('schema_version','1.1','request_id','r','state','ERROR','message','x',
 'action_reference',null,'questions','[]'::jsonb,'result',null,'error',jsonb_build_object('code',code,
 'message','x','field',null,'details','{}'::jsonb,'retryable',retry)) $$;

insert into auth.users(id) values ('d0910000-0000-4000-8000-000000000001');
insert into app_private.rpc_attestation_keys(key_id,key_material,not_before,not_after)
 values ('q9-key',decode(repeat('09',32),'hex'),clock_timestamp()-interval '1 hour',clock_timestamp()+interval '1 hour');
create temporary table q9(name text primary key, res jsonb);

-- Claim đầu tiên: ID lưu bền vững và lease 120 giây tại version 1.
insert into q9 values ('c1',pg_temp.q9_claim());
select ok(res->>'outcome'='COMMITTED' and res#>>'{data,lease_version}'='1' and res#>>'{data,state}'='IN_PROGRESS'
 and res#>>'{data,message_id}' is not null and res#>>'{data,action_id}' is not null,'claim allocates IDs, version 1, IN_PROGRESS')
 from q9 where name='c1';
select ok((select r.lease_until-r.created_at between interval '119 seconds' and interval '121 seconds'
 from app_private.api_request_receipts r where idempotency_key='q9-origin-key-00001'),'initial lease is 120 seconds');
-- Lease còn hiệu lực báo bận và cho thử lại; đổi body cùng khóa gây xung đột. Cả hai không sửa trạng thái.
create temporary table q9_state as select pg_temp.q9_receipt() r;
select ok(pg_temp.q9_is(pg_temp.q9_claim(),'SERVICE_UNAVAILABLE')
 and (select (res#>>'{error,retryable}')::boolean from (select pg_temp.q9_claim() res) x),
 'live lease returns retryable SERVICE_UNAVAILABLE');
select ok(pg_temp.q9_is(pg_temp.q9_claim(fp=>repeat('b',64)),'IDEMPOTENCY_CONFLICT'),'different fingerprint conflicts');
select is(pg_temp.q9_receipt(),r,'busy and conflicting claims leave the receipt unchanged') from q9_state;

-- Dùng quyền quản trị cho lease hết hạn; worker B nhận lại version 2 với cùng ID ổn định.
update app_private.api_request_receipts set lease_until=clock_timestamp()-interval '1 second'
 where idempotency_key='q9-origin-key-00001';
insert into q9 values ('c2',pg_temp.q9_claim());
select ok(res#>>'{data,lease_version}'='2' and res#>>'{data,message_id}'=(select res#>>'{data,message_id}' from q9 where name='c1')
 and res#>>'{data,action_id}'=(select res#>>'{data,action_id}' from q9 where name='c1'),
 'reclaim bumps lease_version and reuses message/action IDs') from q9 where name='c2';

-- Worker A ở version 1 bị chặn khỏi mọi thao tác lease.
truncate q9_state; insert into q9_state select pg_temp.q9_receipt();
select ok(pg_temp.q9_is(pg_temp.q9_call('renew_api_receipt',pg_temp.q9_lease_args(1)),'STALE_ENTITY_VERSION'),'old worker cannot renew');
select ok(pg_temp.q9_is(pg_temp.q9_call('release_api_receipt',pg_temp.q9_lease_args(1)),'STALE_ENTITY_VERSION'),'old worker cannot release');
select ok(pg_temp.q9_is(pg_temp.q9_call('complete_api_receipt',pg_temp.q9_lease_args(1,jsonb_build_object('http_status',200,
 'response',pg_temp.q9_reply('INTERNAL_ERROR',false)))),'STALE_ENTITY_VERSION'),'old worker cannot complete');
select is(pg_temp.q9_receipt(),r,'fenced attempts leave worker B receipt unchanged') from q9_state;
select ok(pg_temp.q9_call('renew_api_receipt',pg_temp.q9_lease_args(2))->>'outcome'='COMMITTED','current worker can renew');

-- Kết quả tạm thời 503 không phải kết quả cuối; phản hồi hợp lệ hoàn tất một lần rồi phát lại.
select ok(pg_temp.q9_is(pg_temp.q9_call('complete_api_receipt',pg_temp.q9_lease_args(2,jsonb_build_object('http_status',503,
 'response',pg_temp.q9_reply('SERVICE_UNAVAILABLE',true)))),'INVALID_PARAMETER'),
 '503 cannot be completed as a terminal result');
insert into q9 values ('done',pg_temp.q9_call('complete_api_receipt',pg_temp.q9_lease_args(2,jsonb_build_object('http_status',200,
 'response',pg_temp.q9_reply('INTERNAL_ERROR',false)))));
select ok(res#>>'{data,state}'='COMPLETED' and res#>>'{data,http_status}'='200' and res#>'{data,lease_until}'='null'::jsonb,
 'current worker completes the receipt') from q9 where name='done';
select is(pg_temp.q9_claim()#>'{data,response}',(select res#>'{data,response}' from q9 where name='done'),
 'claim after completion replays the stored response');

-- Release: lỗi có thể thử lại trả lease để lần claim sau nhận quyền xử lý.
insert into q9 values ('r1',pg_temp.q9_claim('q9-release-key-0001'));
select ok(pg_temp.q9_call('release_api_receipt',jsonb_build_object('http_operation','send_message',
 'idempotency_key','q9-release-key-0001','request_fingerprint',repeat('a',64),'expected_lease_version',1))->>'outcome'='COMMITTED',
 'holder releases its lease');
select ok(pg_temp.q9_claim('q9-release-key-0001')#>>'{data,lease_version}'='2','claim after release reclaims at version 2');

-- Tin nhắn nguồn gắn với tin nhắn đáng tin cậy, hội thoại và chủ sở hữu; chỉ lưu một lần.
create function pg_temp.q9_msg(text_value text default 'Xin chào') returns jsonb language sql as $$
 select jsonb_build_object('message',jsonb_build_object('message_id','d0910000-0000-4000-8000-000000000004',
 'user_id','d0910000-0000-4000-8000-000000000001','conversation_id','d0910000-0000-4000-8000-000000000003',
 'source','CHAT','role','USER','text',text_value,'received_at','2026-11-05T01:02:03.000004Z')) $$;
select ok(pg_temp.q9_call('record_source_message',pg_temp.q9_msg())->>'outcome'='COMMITTED','source message is recorded');
select ok(pg_temp.q9_call('record_source_message',pg_temp.q9_msg())->>'outcome'='COMMITTED'
 and (select count(*) from app_private.source_messages)=1,'recording the same message again is idempotent');
select ok(pg_temp.q9_is(pg_temp.q9_call('record_source_message',pg_temp.q9_msg('Nội dung khác')),'IDEMPOTENCY_CONFLICT'),
 'same message ID with different content conflicts');
select ok(pg_temp.q9_is(pg_temp.q9_call('record_source_message',
 jsonb_set(pg_temp.q9_msg(),'{message,user_id}','"d0910000-0000-4000-8000-000000000002"')),'INVALID_PARAMETER'),
 'message owned by someone else is rejected');
select ok(pg_temp.q9_is(pg_temp.q9_call('record_source_message',
 jsonb_set(pg_temp.q9_msg(),'{message,conversation_id}','"d0910000-0000-4000-8000-000000000099"')),'INVALID_PARAMETER'),
 'message in a different conversation than the request is rejected');

-- Khởi tạo không ghi đè hồ sơ đã có.
create temporary table q9_profile as select to_jsonb(u) p from app_private.user_profiles u;
select ok(pg_temp.q9_call('ensure_user_context','{}')#>>'{data,timezone}'='Asia/Ho_Chi_Minh'
 and (select to_jsonb(u) from app_private.user_profiles u)=(select p from q9_profile),
 'repeat bootstrap leaves the existing profile untouched');
select * from finish();
rollback;
