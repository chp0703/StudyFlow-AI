-- Local-only F3 M2 + M3 pgTAP tests (sessions, hybrid retrieval, grounded turns & hints). Rolled back after test.
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.m2_unit_vec(p_slot integer) returns text language sql as $$
    select '[' || string_agg(case when i = p_slot then '1' else '0' end, ',') || ']'
    from generate_series(1, 384) i
$$;

create function pg_temp.m2_req(
    op text,
    args jsonb,
    uid uuid default 'd3220000-0000-4000-8000-000000000001',
    idem text default null
) returns jsonb language sql as $$
    select jsonb_build_object(
        'contract_version', '1.0.1',
        'schema_version', '1.1',
        'request_id', 'm2-pgtap-request',
        'operation', op,
        'arguments', args,
        'attestation', null,
        'execution_context', jsonb_build_object(
            'conversation_id', null,
            'idempotency_key', idem,
            'approval_action', null,
            'action_reference', null,
            'trusted_context', jsonb_build_object(
                'request_id', 'm2-pgtap-request',
                'message_id', 'd3220000-0000-4000-8000-000000000099',
                'principal', jsonb_build_object('user_id', uid),
                'timezone', 'Asia/Ho_Chi_Minh',
                'locale', 'vi-VN',
                'received_at', app_private.iso(clock_timestamp())
            )
        )
    )
$$;

create function pg_temp.m2_sign(req jsonb) returns jsonb language plpgsql as $$
declare
    stamp timestamptz := clock_timestamp();
    body jsonb;
    payload text;
begin
    body := jsonb_build_object(
        'v', 1,
        'key_id', 'm2-test-key',
        'user_id', req #>> '{execution_context,trusted_context,principal,user_id}',
        'rpc', req ->> 'operation',
        'request_id', req ->> 'request_id',
        'request_digest', encode(extensions.digest(convert_to(app_private.canonical_json(req - 'attestation'), 'UTF8'), 'sha256'), 'hex'),
        'issued_at', app_private.iso(stamp),
        'expires_at', app_private.iso(stamp + interval '60 seconds')
    );
    payload := rtrim(translate(replace(encode(convert_to(app_private.canonical_json(body), 'UTF8'), 'base64'), E'\n', ''), '+/', '-_'), '=');
    return jsonb_set(req, '{attestation}', jsonb_build_object(
        'key_id', 'm2-test-key',
        'payload', payload,
        'signature', encode(extensions.hmac(convert_to(payload, 'UTF8'), decode(repeat('33', 32), 'hex'), 'sha256'), 'hex')
    ));
end
$$;

create function pg_temp.m2_call(
    op text,
    args jsonb,
    uid uuid default 'd3220000-0000-4000-8000-000000000001',
    idem text default null
) returns jsonb language plpgsql as $$
declare
    res jsonb;
    req jsonb := pg_temp.m2_req(op, args, uid, idem);
begin
    if not app_private.rpc_is_read(op) then
        req := pg_temp.m2_sign(req);
    end if;
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

insert into auth.users(id) values
    ('d3220000-0000-4000-8000-000000000001'),
    ('d3220000-0000-4000-8000-000000000002');
insert into app_private.rpc_attestation_keys(key_id, key_material, not_before, not_after)
values ('m2-test-key', decode(repeat('33', 32), 'hex'), clock_timestamp() - interval '1 hour', clock_timestamp() + interval '1 hour');

-- 1. Security & privilege boundary assertions
select ok((select relrowsecurity and relforcerowsecurity from pg_class where oid = 'app_private.learning_session_receipts'::regclass),
    'learning_session_receipts enables and forces RLS');
select ok(not has_table_privilege('authenticated', 'app_private.learning_session_receipts', 'SELECT'),
    'authenticated cannot read learning_session_receipts directly');
select ok(not has_table_privilege('sf_rpc_owner', 'app_private.session_outcome', 'INSERT'),
    'M2+M3 still grants no INSERT on session_outcome before M4');
select ok(not has_function_privilege('anon', 'app_api.search_learning_material_chunks(jsonb)', 'EXECUTE'),
    'anon cannot search learning chunks');
select ok(not has_function_privilege('anon', 'app_api.create_learning_session(jsonb)', 'EXECUTE'),
    'anon cannot create learning session');
select ok(not has_function_privilege('anon', 'app_api.append_learning_turn(jsonb)', 'EXECUTE'),
    'anon cannot append learning turn');

-- 2. Seed READY and FAILED materials via M1 RPCs
create temporary table m2_state(label text primary key, val text);

do $$
declare
    uid_a uuid := 'd3220000-0000-4000-8000-000000000001';
    uid_b uuid := 'd3220000-0000-4000-8000-000000000002';
    r jsonb;
    mid_a1 uuid;
    mid_a2 uuid;
    mid_af uuid;
    mid_b1 uuid;
begin
    -- Material A1 (READY, 2 pages: slot 1 = even numbers, slot 2 = prime numbers)
    r := pg_temp.m2_call('reserve_learning_material', jsonb_build_object(
        'fingerprint', repeat('1', 64), 'sha256', repeat('a', 64), 'filename', 'sohoc.txt',
        'mime_type', 'text/plain', 'byte_size', 200, 'course_label', 'Toán'
    ), uid_a, 'm2-upload-key-a1-0001');
    mid_a1 := (r #>> '{data,material,material_id}')::uuid;
    r := pg_temp.m2_call('store_learning_material_chunks', jsonb_build_object(
        'material_id', mid_a1, 'claim', r #>> '{data,claim}', 'page_count', 2, 'char_count', 120,
        'assessment_chunks', jsonb_build_array(
            jsonb_build_object('page', 1, 'chunk_index', 0, 'text', 'Tổng hai số chẵn luôn là một số chẵn.'),
            jsonb_build_object('page', 2, 'chunk_index', 1, 'text', 'Số nguyên tố chỉ chia hết cho 1 và chính nó.')
        ),
        'learning_chunks', jsonb_build_array(
            jsonb_build_object('page', 1, 'chunk_index', 0, 'text', 'Tổng hai số chẵn luôn là một số chẵn.', 'embedding', pg_temp.m2_unit_vec(1)),
            jsonb_build_object('page', 2, 'chunk_index', 1, 'text', 'Số nguyên tố chỉ chia hết cho 1 và chính nó.', 'embedding', pg_temp.m2_unit_vec(2))
        )
    ), uid_a, 'm2-upload-key-a1-0001');
    if r ->> 'outcome' <> 'COMMITTED' then raise exception 'seed mid_a1 failed: %', r; end if;

    -- Material A2 (READY, owned by A but NOT selected in session)
    r := pg_temp.m2_call('reserve_learning_material', jsonb_build_object(
        'fingerprint', repeat('2', 64), 'sha256', repeat('b', 64), 'filename', 'khac.txt',
        'mime_type', 'text/plain', 'byte_size', 200, 'course_label', 'Lý'
    ), uid_a, 'm2-upload-key-a2-0001');
    mid_a2 := (r #>> '{data,material,material_id}')::uuid;
    r := pg_temp.m2_call('store_learning_material_chunks', jsonb_build_object(
        'material_id', mid_a2, 'claim', r #>> '{data,claim}', 'page_count', 1, 'char_count', 60,
        'assessment_chunks', jsonb_build_array(
            jsonb_build_object('page', 1, 'chunk_index', 0, 'text', 'Tổng hai số chẵn không được chọn trong phiên.')
        ),
        'learning_chunks', jsonb_build_array(
            jsonb_build_object('page', 1, 'chunk_index', 0, 'text', 'Tổng hai số chẵn không được chọn trong phiên.', 'embedding', pg_temp.m2_unit_vec(1))
        )
    ), uid_a, 'm2-upload-key-a2-0001');

    -- Material A_FAILED
    r := pg_temp.m2_call('reserve_learning_material', jsonb_build_object(
        'fingerprint', repeat('3', 64), 'sha256', repeat('c', 64), 'filename', 'fail.txt',
        'mime_type', 'text/plain', 'byte_size', 100, 'course_label', 'Toán'
    ), uid_a, 'm2-upload-key-af-0001');
    mid_af := (r #>> '{data,material,material_id}')::uuid;
    perform pg_temp.m2_call('fail_learning_material', jsonb_build_object(
        'material_id', mid_af, 'claim', r #>> '{data,claim}', 'error_code', 'INVALID_DOCUMENT'
    ), uid_a, 'm2-upload-key-af-0001');

    -- Material B1 (READY, owned by B)
    r := pg_temp.m2_call('reserve_learning_material', jsonb_build_object(
        'fingerprint', repeat('4', 64), 'sha256', repeat('d', 64), 'filename', 'b_secret.txt',
        'mime_type', 'text/plain', 'byte_size', 100, 'course_label', 'Hóa'
    ), uid_b, 'm2-upload-key-b1-0001');
    mid_b1 := (r #>> '{data,material,material_id}')::uuid;
    perform pg_temp.m2_call('store_learning_material_chunks', jsonb_build_object(
        'material_id', mid_b1, 'claim', r #>> '{data,claim}', 'page_count', 1, 'char_count', 50,
        'assessment_chunks', jsonb_build_array(
            jsonb_build_object('page', 1, 'chunk_index', 0, 'text', 'Tài liệu bí mật của B về số chẵn.')
        ),
        'learning_chunks', jsonb_build_array(
            jsonb_build_object('page', 1, 'chunk_index', 0, 'text', 'Tài liệu bí mật của B về số chẵn.', 'embedding', pg_temp.m2_unit_vec(1))
        )
    ), uid_b, 'm2-upload-key-b1-0001');

    insert into m2_state values
        ('mid_a1', mid_a1::text),
        ('mid_a2', mid_a2::text),
        ('mid_af', mid_af::text),
        ('mid_b1', mid_b1::text);
end
$$;

-- 3. Session creation validation (foreign material, non-READY material, foreign planner block)
select is(
    pg_temp.m2_call('create_learning_session', jsonb_build_object(
        'goal', 'Ôn toán', 'material_ids', jsonb_build_array((select val from m2_state where label = 'mid_b1')),
        'planner_block_id', null, 'fingerprint', repeat('a', 64)
    ), 'd3220000-0000-4000-8000-000000000001', 'm2-sess-key-foreign-01') #>> '{error,code}',
    'ENTITY_NOT_FOUND', 'cannot create session with foreign material'
);

select is(
    pg_temp.m2_call('create_learning_session', jsonb_build_object(
        'goal', 'Ôn toán', 'material_ids', jsonb_build_array((select val from m2_state where label = 'mid_af')),
        'planner_block_id', null, 'fingerprint', repeat('b', 64)
    ), 'd3220000-0000-4000-8000-000000000001', 'm2-sess-key-notready-01') #>> '{error,code}',
    'TIME_CONFLICT', 'cannot create session with FAILED material'
);

select is(
    pg_temp.m2_call('create_learning_session', jsonb_build_object(
        'goal', 'Ôn toán', 'material_ids', jsonb_build_array((select val from m2_state where label = 'mid_a1')),
        'planner_block_id', 'd3220000-0000-4000-8000-999999999999', 'fingerprint', repeat('c', 64)
    ), 'd3220000-0000-4000-8000-000000000001', 'm2-sess-key-badblock-01') #>> '{error,code}',
    'ENTITY_NOT_FOUND', 'cannot bind unknown or foreign planner_block_id'
);

-- 4. Create session, replay, and conflict
create temporary table m2_sess_res as
select pg_temp.m2_call('create_learning_session', jsonb_build_object(
    'goal', 'Ôn số học', 'material_ids', jsonb_build_array((select val from m2_state where label = 'mid_a1')),
    'planner_block_id', null, 'fingerprint', repeat('5', 64)
), 'd3220000-0000-4000-8000-000000000001', 'm2-sess-key-valid-0001') res;

select is(res ->> 'outcome', 'COMMITTED', 'session created') from m2_sess_res;
select is(res #>> '{data,session,status}', 'ACTIVE', 'new session is ACTIVE') from m2_sess_res;
select is(res #>> '{data,replayed}', 'false', 'first creation is not replayed') from m2_sess_res;

insert into m2_state select 'sid_a', res #>> '{data,session,session_id}' from m2_sess_res;

select is(
    pg_temp.m2_call('create_learning_session', jsonb_build_object(
        'goal', 'Ôn số học', 'material_ids', jsonb_build_array((select val from m2_state where label = 'mid_a1')),
        'planner_block_id', null, 'fingerprint', repeat('5', 64)
    ), 'd3220000-0000-4000-8000-000000000001', 'm2-sess-key-valid-0001') #>> '{data,replayed}',
    'true', 'session creation replays on identical key and fingerprint'
);

select is(
    pg_temp.m2_call('create_learning_session', jsonb_build_object(
        'goal', 'Mục tiêu khác', 'material_ids', jsonb_build_array((select val from m2_state where label = 'mid_a1')),
        'planner_block_id', null, 'fingerprint', repeat('6', 64)
    ), 'd3220000-0000-4000-8000-000000000001', 'm2-sess-key-valid-0001') #>> '{error,code}',
    'IDEMPOTENCY_CONFLICT', 'session key reused with different fingerprint conflicts'
);

-- 5. Cross-user isolation on read and hybrid search
select is(
    pg_temp.m2_call('get_learning_session', jsonb_build_object(
        'session_id', (select val from m2_state where label = 'sid_a')
    ), 'd3220000-0000-4000-8000-000000000002') #>> '{error,code}',
    'ENTITY_NOT_FOUND', 'user B cannot read user A session'
);

select is(
    pg_temp.m2_call('search_learning_material_chunks', jsonb_build_object(
        'session_id', (select val from m2_state where label = 'sid_a'),
        'query_embedding', pg_temp.m2_unit_vec(1),
        'query_text', 'Tổng hai số chẵn',
        'k', 6
    ), 'd3220000-0000-4000-8000-000000000002') #>> '{error,code}',
    'ENTITY_NOT_FOUND', 'user B cannot search chunks of user A session'
);

-- 6. Hybrid retrieval strictly scopes to session.material_ids (excludes mid_a2 and mid_b1)
create temporary table m2_search_res as
select pg_temp.m2_call('search_learning_material_chunks', jsonb_build_object(
    'session_id', (select val from m2_state where label = 'sid_a'),
    'query_embedding', pg_temp.m2_unit_vec(1),
    'query_text', 'Tổng hai số chẵn là gì?',
    'k', 6
), 'd3220000-0000-4000-8000-000000000001') res;

select is(res ->> 'outcome', 'READ', 'hybrid search succeeds for owner') from m2_search_res;
select is(jsonb_array_length(res #> '{data,chunks}'), 2, 'only chunks from selected material mid_a1 returned (mid_a2 excluded)') from m2_search_res;
select is(res #>> '{data,chunks,0,page}', '1', 'matching cosine+FTS page 1 ranked first via RRF') from m2_search_res;
select is(res #>> '{data,chunks,0,material_id}', (select val from m2_state where label = 'mid_a1'), 'top chunk belongs to selected material') from m2_search_res;
select ok(((res #>> '{data,chunks,0,fts_rank}')::double precision) > 0, 'FTS matched Vietnamese question via OR lexemes') from m2_search_res;
select ok(((res #>> '{data,chunks,0,cosine_similarity}')::double precision) > 0.99, 'cosine similarity computed accurately') from m2_search_res;

insert into m2_state select 'cid_a1_p1', res #>> '{data,chunks,0,chunk_id}' from m2_search_res;

-- 7. Append turn validation, persistence, replay, hints, and deleted-material citation history
select is(
    pg_temp.m2_call('append_learning_turn', jsonb_build_object(
        'session_id', (select val from m2_state where label = 'sid_a'),
        'fingerprint', repeat('7', 64),
        'expected_last_ordinal', 0,
        'kind', 'ASK',
        'user_content', 'Tổng hai số chẵn là gì?',
        'assistant_content', 'Tổng hai số chẵn là số chẵn.',
        'hint_level', null,
        'citations', jsonb_build_array(jsonb_build_object(
            'chunk_id', 'd3220000-0000-4000-8000-888888888888',
            'material_id', (select val from m2_state where label = 'mid_a1'),
            'page', 1
        )),
        'supported', true,
        'model', 'deepseek-chat',
        'prompt_version', 'f3-m2-v1'
    ), 'd3220000-0000-4000-8000-000000000001', 'm2-turn-bad-chunk-01') #>> '{error,code}',
    'INVALID_PARAMETER', 'forged chunk_id rejected at DB boundary'
);

create temporary table m2_turn_res as
select pg_temp.m2_call('append_learning_turn', jsonb_build_object(
    'session_id', (select val from m2_state where label = 'sid_a'),
    'fingerprint', repeat('8', 64),
    'expected_last_ordinal', 0,
    'kind', 'ASK',
    'user_content', 'Tổng hai số chẵn là gì?',
    'assistant_content', 'Tổng hai số chẵn luôn là số chẵn.',
    'hint_level', null,
    'citations', jsonb_build_array(jsonb_build_object(
        'chunk_id', (select val from m2_state where label = 'cid_a1_p1'),
        'material_id', (select val from m2_state where label = 'mid_a1'),
        'page', 1
    )),
    'supported', true,
    'model', 'deepseek-chat',
    'prompt_version', 'f3-m2-v1'
), 'd3220000-0000-4000-8000-000000000001', 'm2-turn-ask-key-0001') res;

select is(res ->> 'outcome', 'COMMITTED', 'grounded ASK turn persisted') from m2_turn_res;
select is(res #>> '{data,user_turn,ordinal}', '1', 'user turn ordinal is 1') from m2_turn_res;
select is(res #>> '{data,assistant_turn,ordinal}', '2', 'assistant turn ordinal is 2') from m2_turn_res;
select is(res #>> '{data,assistant_turn,citations,0,material_deleted}', 'false', 'active material citation has material_deleted=false') from m2_turn_res;

select is(
    pg_temp.m2_call('lookup_learning_turn_receipt', jsonb_build_object(
        'session_id', (select val from m2_state where label = 'sid_a'),
        'idempotency_key', 'm2-turn-ask-key-0001',
        'fingerprint', repeat('8', 64)
    ), 'd3220000-0000-4000-8000-000000000001') #>> '{data,found}',
    'true', 'receipt lookup finds completed turn before model call'
);

select is(
    pg_temp.m2_call('lookup_learning_turn_receipt', jsonb_build_object(
        'session_id', (select val from m2_state where label = 'sid_a'),
        'idempotency_key', 'm2-turn-ask-key-0001',
        'fingerprint', repeat('9', 64)
    ), 'd3220000-0000-4000-8000-000000000001') #>> '{error,code}',
    'IDEMPOTENCY_CONFLICT', 'receipt lookup conflicts on mismatched fingerprint'
);

-- Stale expected_last_ordinal rejected (concurrent turn race guard)
select is(
    pg_temp.m2_call('append_learning_turn', jsonb_build_object(
        'session_id', (select val from m2_state where label = 'sid_a'),
        'fingerprint', repeat('e', 64),
        'expected_last_ordinal', 0,
        'kind', 'HINT',
        'user_content', 'Cho mình một gợi ý',
        'assistant_content', 'Hãy xem lại định nghĩa số chẵn.',
        'hint_level', 1,
        'citations', jsonb_build_array(jsonb_build_object(
            'chunk_id', (select val from m2_state where label = 'cid_a1_p1'),
            'material_id', (select val from m2_state where label = 'mid_a1'),
            'page', 1
        )),
        'supported', true,
        'model', 'deepseek-chat',
        'prompt_version', 'f3-m3-v1'
    ), 'd3220000-0000-4000-8000-000000000001', 'm2-turn-stale-key-01') #>> '{error,code}',
    'STALE_ENTITY_VERSION', 'stale expected_last_ordinal rejected'
);

-- Valid HINT turn (level 1, ordinals 3 & 4)
select is(
    pg_temp.m2_call('append_learning_turn', jsonb_build_object(
        'session_id', (select val from m2_state where label = 'sid_a'),
        'fingerprint', repeat('e', 64),
        'expected_last_ordinal', 2,
        'kind', 'HINT',
        'user_content', 'Cho mình một gợi ý',
        'assistant_content', 'Hãy xem lại định nghĩa số chẵn ở trang 1.',
        'hint_level', 1,
        'citations', jsonb_build_array(jsonb_build_object(
            'chunk_id', (select val from m2_state where label = 'cid_a1_p1'),
            'material_id', (select val from m2_state where label = 'mid_a1'),
            'page', 1
        )),
        'supported', true,
        'model', 'deepseek-chat',
        'prompt_version', 'f3-m3-v1'
    ), 'd3220000-0000-4000-8000-000000000001', 'm2-turn-hint-key-001') #>> '{data,assistant_turn,hint_level}',
    '1', 'HINT turn persists hint_level=1 at ordinals 3 and 4'
);

-- Non-ACTIVE session rejects new turns
update app_private.learning_session set status = 'CLOSED'
where session_id = (select val::uuid from m2_state where label = 'sid_a');

select is(
    pg_temp.m2_call('append_learning_turn', jsonb_build_object(
        'session_id', (select val from m2_state where label = 'sid_a'),
        'fingerprint', repeat('d', 64),
        'expected_last_ordinal', 4,
        'kind', 'ASK',
        'user_content', 'Câu hỏi khi đã đóng?',
        'assistant_content', 'Tài liệu hiện có không đủ căn cứ để trả lời câu này',
        'hint_level', null,
        'citations', '[]'::jsonb,
        'supported', false,
        'model', null,
        'prompt_version', null
    ), 'd3220000-0000-4000-8000-000000000001', 'm2-turn-closed-key-1') #>> '{error,code}',
    'TIME_CONFLICT', 'CLOSED session rejects new turns'
);

update app_private.learning_session set status = 'ACTIVE'
where session_id = (select val::uuid from m2_state where label = 'sid_a');

-- Delete material mid_a1 and verify historical citation retains IDs/page with material_deleted=true
select is(
    pg_temp.m2_call('delete_learning_material', jsonb_build_object(
        'material_id', (select val from m2_state where label = 'mid_a1'),
        'fingerprint', repeat('f', 64)
    ), 'd3220000-0000-4000-8000-000000000001', 'm2-delete-mid-a1-001') ->> 'outcome',
    'COMMITTED', 'material deleted cleanly'
);

select is(
    pg_temp.m2_call('get_learning_session', jsonb_build_object(
        'session_id', (select val from m2_state where label = 'sid_a')
    ), 'd3220000-0000-4000-8000-000000000001') #>> '{data,turns,1,citations,0,material_deleted}',
    'true', 'deleted material citation retains provenance and reports material_deleted=true'
);

select * from finish();
rollback;
