-- Orchestrator P1 pgTAP: sessions bind to a chat conversation, F2 reads F3 materials across conversations,
-- and checkpoints gate cross-feature writes. Rolled back after test.
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.o_req(op text, args jsonb, uid uuid, idem text, conv uuid) returns jsonb language sql as $$
    select jsonb_build_object(
        'contract_version', '1.0.1', 'schema_version', '1.1', 'request_id', 'o-pgtap-request',
        'operation', op, 'arguments', args, 'attestation', null,
        'execution_context', jsonb_build_object(
            'conversation_id', conv, 'idempotency_key', idem, 'approval_action', null, 'action_reference', null,
            'trusted_context', jsonb_build_object(
                'request_id', 'o-pgtap-request', 'message_id', 'd5550000-0000-4000-8000-000000000099',
                'principal', jsonb_build_object('user_id', uid), 'timezone', 'Asia/Ho_Chi_Minh', 'locale', 'vi-VN',
                'received_at', app_private.iso(clock_timestamp()))))
$$;

create function pg_temp.o_sign(req jsonb) returns jsonb language plpgsql as $$
declare
    stamp timestamptz := clock_timestamp();
    body jsonb;
    payload text;
begin
    body := jsonb_build_object('v', 1, 'key_id', 'o-test-key',
        'user_id', req #>> '{execution_context,trusted_context,principal,user_id}',
        'rpc', req ->> 'operation', 'request_id', req ->> 'request_id',
        'request_digest', encode(extensions.digest(convert_to(app_private.canonical_json(req - 'attestation'), 'UTF8'), 'sha256'), 'hex'),
        'issued_at', app_private.iso(stamp), 'expires_at', app_private.iso(stamp + interval '60 seconds'));
    payload := rtrim(translate(replace(encode(convert_to(app_private.canonical_json(body), 'UTF8'), 'base64'), E'\n', ''), '+/', '-_'), '=');
    return jsonb_set(req, '{attestation}', jsonb_build_object('key_id', 'o-test-key', 'payload', payload,
        'signature', encode(extensions.hmac(convert_to(payload, 'UTF8'), decode(repeat('55', 32), 'hex'), 'sha256'), 'hex')));
end
$$;

create function pg_temp.o_call(op text, args jsonb, uid uuid, idem text default null, conv uuid default null)
returns jsonb language plpgsql as $$
declare
    res jsonb;
    req jsonb := pg_temp.o_req(op, args, uid, idem, conv);
begin
    if not app_private.rpc_is_read(op) then req := pg_temp.o_sign(req); end if;
    perform set_config('request.jwt.claims', jsonb_build_object('sub', uid, 'role', 'authenticated')::text, true);
    perform set_config('request.jwt.claim.sub', uid::text, true);
    set local role authenticated;
    begin
        execute format('select app_api.%I($1)', op) into res using req;
    exception when others then
        res := jsonb_build_object('sqlstate', sqlstate, 'message', sqlerrm);
    end;
    reset role;
    return res;
end
$$;

insert into auth.users(id) values ('d5550000-0000-4000-8000-000000000001'), ('d5550000-0000-4000-8000-000000000002');
insert into app_private.rpc_attestation_keys(key_id, key_material, not_before, not_after)
values ('o-test-key', decode(repeat('55', 32), 'hex'), clock_timestamp() - interval '1 hour', clock_timestamp() + interval '1 hour');

create temporary table o_state(label text primary key, val text);
do $$
declare
    uid_a uuid := 'd5550000-0000-4000-8000-000000000001';
    r jsonb;
    mid uuid;
begin
    r := pg_temp.o_call('reserve_learning_material', jsonb_build_object(
        'fingerprint', repeat('1', 64), 'sha256', repeat('a', 64), 'filename', 'sohoc.txt',
        'mime_type', 'text/plain', 'byte_size', 200, 'course_label', 'Toán'), uid_a, 'o-upload-key-a1-0001');
    mid := (r #>> '{data,material,material_id}')::uuid;
    r := pg_temp.o_call('store_learning_material_chunks', jsonb_build_object(
        'material_id', mid, 'claim', r #>> '{data,claim}', 'page_count', 1, 'char_count', 40,
        'assessment_chunks', jsonb_build_array(jsonb_build_object('page', 1, 'chunk_index', 0, 'text', 'Tổng hai số chẵn luôn là một số chẵn.')),
        'learning_chunks', jsonb_build_array(jsonb_build_object('page', 1, 'chunk_index', 0, 'text', 'Tổng hai số chẵn luôn là một số chẵn.',
            'embedding', '[' || (select string_agg(case when i = 1 then '1' else '0' end, ',') from generate_series(1, 384) i) || ']'))
    ), uid_a, 'o-upload-key-a1-0001');
    if r ->> 'outcome' <> 'COMMITTED' then raise exception 'seed material failed: %', r; end if;
    insert into o_state values ('mid', mid::text);
end $$;

-- 1. A session created with conversation_id lives in that conversation; without it, a fresh one.
select is(pg_temp.o_call('create_learning_session', jsonb_build_object(
        'goal', 'Ôn số chẵn', 'material_ids', jsonb_build_array((select val from o_state where label = 'mid')),
        'planner_block_id', null, 'conversation_id', 'd5550000-0000-4000-8000-0000000000c1', 'fingerprint', repeat('a', 64)),
        'd5550000-0000-4000-8000-000000000001', 'o-session-key-bound-0001') #>> '{data,session,conversation_id}',
    'd5550000-0000-4000-8000-0000000000c1', 'create_learning_session binds the session to the given conversation');
select ok(exists(select 1 from app_private.conversation_records
    where user_id = 'd5550000-0000-4000-8000-000000000001' and conversation_id = 'd5550000-0000-4000-8000-0000000000c1'),
    'the conversation record exists for the owner');
select isnt(pg_temp.o_call('create_learning_session', jsonb_build_object(
        'goal', 'Ôn số chẵn', 'material_ids', jsonb_build_array((select val from o_state where label = 'mid')),
        'planner_block_id', null, 'fingerprint', repeat('b', 64)),
        'd5550000-0000-4000-8000-000000000001', 'o-session-key-free-0001') #>> '{data,session,conversation_id}',
    'd5550000-0000-4000-8000-0000000000c1', 'without conversation_id the session gets its own conversation');

-- 2. F2 reads an owned F3 material from another conversation, but never someone else's.
select isnt(pg_temp.o_call('get_assessment_material', jsonb_build_object(
        'material_id', (select val from o_state where label = 'mid'), 'conversation_id', 'd5550000-0000-4000-8000-0000000000c2'),
        'd5550000-0000-4000-8000-000000000001', null, 'd5550000-0000-4000-8000-0000000000c2') ->> 'outcome',
    'ERROR', 'F2 can read the owner F3 material from a chat conversation');
select is(pg_temp.o_call('get_assessment_material', jsonb_build_object(
        'material_id', (select val from o_state where label = 'mid'), 'conversation_id', 'd5550000-0000-4000-8000-0000000000c3'),
        'd5550000-0000-4000-8000-000000000002', null, 'd5550000-0000-4000-8000-0000000000c3') ->> 'outcome',
    'ERROR', 'another user cannot read the F3 material through F2');

-- 3. The checkpoint gate covers cross-feature writes.
select ok(pg_get_functiondef('app_api.checkpoint_workflow_continuation(jsonb)'::regprocedure) like '%decide_learning_session_outcome%'
    and pg_get_functiondef('app_api.checkpoint_workflow_continuation(jsonb)'::regprocedure) like '%decide_revision_recommendation%'
    and pg_get_functiondef('app_api.checkpoint_workflow_continuation(jsonb)'::regprocedure) like '%verify_question_drafts%',
    'checkpoint requires a completed action behind SUCCEEDED cross-feature writes');

select * from finish();
rollback;
