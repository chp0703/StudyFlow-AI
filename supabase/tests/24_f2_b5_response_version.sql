-- F2 B5 durable response_version, trigger guards, get_quiz_attempt_context,
-- opt-in replay status (READ vs legacy COMMITTED), and submit expected_response_version checks.

begin;
select no_plan();
set local search_path = public, extensions;
set local timezone = 'UTC';

-- 1. Function boundary and schema column checks
select ok(
    exists (
        select 1
        from information_schema.columns
        where table_schema = 'app_private'
          and table_name = 'quiz_attempts'
          and column_name = 'response_version'
          and data_type = 'bigint'
          and is_nullable = 'NO'
    ),
    'quiz_attempts has non-null bigint response_version column'
);

select ok(
    app_private.rpc_is_read('get_quiz_attempt_context'),
    'get_quiz_attempt_context is classified as read-only'
);

select ok(
    (select prosecdef from pg_proc where oid = 'app_api.get_quiz_attempt_context(jsonb)'::regprocedure),
    'get_quiz_attempt_context is SECURITY DEFINER'
);

select ok(
    not has_function_privilege('anon', 'app_api.get_quiz_attempt_context(jsonb)', 'EXECUTE'),
    'anon cannot execute get_quiz_attempt_context'
);

select ok(
    has_function_privilege('authenticated', 'app_api.get_quiz_attempt_context(jsonb)', 'EXECUTE'),
    'authenticated can execute get_quiz_attempt_context'
);

-- 2. Self-contained local fixtures (2 users, HMAC key, READY material, 3 VERIFIED questions)
create function pg_temp.rv_seed() returns text
language plpgsql as $$
begin
    insert into auth.users(id) values
        ('b5240000-0000-4000-8000-000000000001'),
        ('b5240000-0000-4000-8000-000000000002');

    insert into app_private.rpc_attestation_keys (key_id, key_material, not_before, not_after)
    values (
        'b524-local-fixture-only',
        decode('101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f', 'hex'),
        clock_timestamp() - interval '1 hour',
        clock_timestamp() + interval '1 hour'
    );
    return 'OK';
exception when others then
    return 'SQL_ERROR:' || sqlstate || ':' || sqlerrm;
end $$;

select is(pg_temp.rv_seed(), 'OK', 'seed local fixture users and HMAC key');

create function pg_temp.rv_request(
    p_operation text,
    p_arguments jsonb,
    p_owner uuid default 'b5240000-0000-4000-8000-000000000001',
    p_idem text default 'b524-idempotency-key-0001',
    p_conv uuid default 'b5240000-0000-4000-8000-000000000003',
    p_approval jsonb default null,
    p_action_ref jsonb default null,
    p_req_id text default 'b524-req-0001'
) returns jsonb
language sql as $$
    select jsonb_build_object(
        'contract_version', '1.0.1',
        'schema_version', '1.1',
        'request_id', p_req_id,
        'operation', p_operation,
        'arguments', p_arguments,
        'execution_context', jsonb_build_object(
            'conversation_id', p_conv,
            'idempotency_key', p_idem,
            'approval_action', p_approval,
            'action_reference', p_action_ref,
            'trusted_context', jsonb_build_object(
                'request_id', p_req_id,
                'message_id', 'b5240000-0000-4000-8000-000000000004',
                'principal', jsonb_build_object('user_id', p_owner),
                'received_at', app_private.iso(clock_timestamp()),
                'timezone', 'Asia/Ho_Chi_Minh',
                'locale', 'vi-VN'
            )
        ),
        'attestation', null
    )
$$;

create function pg_temp.rv_sign(p_request jsonb) returns jsonb
language plpgsql as $$
declare
    v_payload_json jsonb;
    v_payload text;
    v_stamp timestamptz := clock_timestamp();
begin
    v_payload_json := jsonb_build_object(
        'v', 1,
        'key_id', 'b524-local-fixture-only',
        'user_id', p_request #>> '{execution_context,trusted_context,principal,user_id}',
        'rpc', p_request ->> 'operation',
        'request_id', p_request ->> 'request_id',
        'request_digest', encode(
            extensions.digest(convert_to(app_private.canonical_json(p_request - 'attestation'), 'UTF8'), 'sha256'),
            'hex'
        ),
        'issued_at', app_private.iso(v_stamp),
        'expires_at', app_private.iso(v_stamp + interval '60 seconds')
    );
    v_payload := rtrim(translate(replace(encode(convert_to(app_private.canonical_json(v_payload_json), 'UTF8'), 'base64'), E'\n', ''), '+/', '-_'), '=');
    return jsonb_set(
        p_request,
        '{attestation}',
        jsonb_build_object(
            'key_id', 'b524-local-fixture-only',
            'payload', v_payload,
            'signature', encode(
                extensions.hmac(
                    convert_to(v_payload, 'UTF8'),
                    decode('101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f', 'hex'),
                    'sha256'
                ),
                'hex'
            )
        )
    );
end $$;

create function pg_temp.rv_call(
    p_routine text,
    p_request jsonb,
    p_jwt_user uuid default 'b5240000-0000-4000-8000-000000000001'
) returns jsonb
language plpgsql as $$
declare
    v_response jsonb;
begin
    perform set_config(
        'request.jwt.claims',
        jsonb_build_object('sub', p_jwt_user::text, 'role', 'authenticated')::text,
        true
    );
    perform set_config('request.jwt.claim.sub', p_jwt_user::text, true);
    set local role authenticated;
    begin
        execute format('select app_api.%I($1)', p_routine) into v_response using p_request;
    exception when others then
        v_response := jsonb_build_object('sqlstate', sqlstate, 'message', sqlerrm);
    end;
    reset role;
    return v_response;
end $$;

create function pg_temp.rv_draft(
    p_qid uuid,
    p_qtype text default 'MCQ',
    p_answer text default 'B'
) returns jsonb
language sql as $$
    select jsonb_build_object(
        'assessment_version', '1.0.0',
        'question_id', p_qid,
        'user_id', 'b5240000-0000-4000-8000-000000000001',
        'conversation_id', 'b5240000-0000-4000-8000-000000000003',
        'material_id', 'b5240000-0000-4000-8000-000000000101',
        'version', 1,
        'topic', 'Mạng máy tính',
        'question_type', p_qtype,
        'stem', 'Câu hỏi kiểm tra ' || p_qid::text || '?',
        'options', case
            when p_qtype = 'MCQ' then jsonb_build_array(
                jsonb_build_object('option_id', 'A', 'text', 'UDP'),
                jsonb_build_object('option_id', 'B', 'text', 'TCP'),
                jsonb_build_object('option_id', 'C', 'text', 'ICMP'),
                jsonb_build_object('option_id', 'D', 'text', 'ARP')
            )
            else jsonb_build_array(
                jsonb_build_object('option_id', 'TRUE', 'text', 'Đúng'),
                jsonb_build_object('option_id', 'FALSE', 'text', 'Sai')
            )
        end,
        'answer_key', p_answer,
        'explanation', 'Giải thích chuẩn theo trang 1.',
        'source_chunk_ids', jsonb_build_array('b5240000-0000-4000-8000-000000000201'),
        'status', 'DRAFT',
        'model', 'deepseek-chat',
        'prompt_version', 'f2-question-v1',
        'verified_at', null,
        'created_at', '2026-11-20T08:01:00.000000Z',
        'updated_at', '2026-11-20T08:01:00.000000Z'
    )
$$;

-- Store READY material via signed RPC (no READY guard bypass)
select is(
    (
        pg_temp.rv_call(
            'store_assessment_material',
            pg_temp.rv_sign(
                pg_temp.rv_request(
                    'store_assessment_material',
                    jsonb_build_object(
                        'material_id', 'b5240000-0000-4000-8000-000000000101',
                        'conversation_id', 'b5240000-0000-4000-8000-000000000003',
                        'filename', 'mang-rv.md',
                        'mime_type', 'text/markdown',
                        'size_bytes', 120,
                        'sha256', repeat('c', 64),
                        'page_count', 1,
                        'char_count', length('TCP truyền dữ liệu hướng kết nối, UDP truyền datagram không kết nối.'),
                        'topics', jsonb_build_array('Mạng máy tính'),
                        'chunks', jsonb_build_array(
                            jsonb_build_object(
                                'chunk_id', 'b5240000-0000-4000-8000-000000000201',
                                'material_id', 'b5240000-0000-4000-8000-000000000101',
                                'user_id', 'b5240000-0000-4000-8000-000000000001',
                                'page', 1,
                                'topic', 'Mạng máy tính',
                                'chunk_index', 0,
                                'text', 'TCP truyền dữ liệu hướng kết nối, UDP truyền datagram không kết nối.',
                                'created_at', '2026-11-20T08:00:00.000000Z'
                            )
                        )
                    ),
                    'b5240000-0000-4000-8000-000000000001',
                    'b524-mat-store-0001'
                )
            )
        ) ->> 'outcome'
    ),
    'COMMITTED',
    'store READY material for USER_A'
);

-- Create & verify Q1 (MCQ B), Q2 (TRUE_FALSE TRUE), Q3 (MCQ A)
select is(
    (
        pg_temp.rv_call(
            'create_question_drafts',
            pg_temp.rv_sign(
                pg_temp.rv_request(
                    'create_question_drafts',
                    jsonb_build_object(
                        'conversation_id', 'b5240000-0000-4000-8000-000000000003',
                        'material_id', 'b5240000-0000-4000-8000-000000000101',
                        'action_id', 'b5240000-0000-4000-8000-000000000401',
                        'generation_params', jsonb_build_object(
                            'topic', 'Mạng máy tính',
                            'question_type', 'MCQ',
                            'count', 3
                        ),
                        'drafts', jsonb_build_array(
                            pg_temp.rv_draft('b5240000-0000-4000-8000-000000000301', 'MCQ', 'B'),
                            pg_temp.rv_draft('b5240000-0000-4000-8000-000000000302', 'TRUE_FALSE', 'TRUE'),
                            pg_temp.rv_draft('b5240000-0000-4000-8000-000000000303', 'MCQ', 'A')
                        )
                    ),
                    'b5240000-0000-4000-8000-000000000001',
                    'b524-drafts-create-0001'
                )
            )
        ) ->> 'outcome'
    ),
    'DRAFTED',
    'create 3 question drafts for USER_A'
);

select is(
    (
        pg_temp.rv_call(
            'verify_question_drafts',
            pg_temp.rv_sign(
                pg_temp.rv_request(
                    'verify_question_drafts',
                    jsonb_build_object(
                        'conversation_id', 'b5240000-0000-4000-8000-000000000003',
                        'action_id', 'b5240000-0000-4000-8000-000000000401',
                        'expected_action_version', 1,
                        'question_ids', jsonb_build_array(
                            'b5240000-0000-4000-8000-000000000301',
                            'b5240000-0000-4000-8000-000000000302',
                            'b5240000-0000-4000-8000-000000000303'
                        ),
                        'decision', 'APPROVE'
                    ),
                    'b5240000-0000-4000-8000-000000000001',
                    'b524-drafts-verify-0001',
                    'b5240000-0000-4000-8000-000000000003',
                    jsonb_build_object(
                        'approval_action_id', 'b5240000-0000-4000-8000-000000000411',
                        'user_id', 'b5240000-0000-4000-8000-000000000001',
                        'target_type', 'PENDING_ACTION',
                        'target_id', 'b5240000-0000-4000-8000-000000000401',
                        'target_version', 1,
                        'decision', 'APPROVE',
                        'source', 'UI',
                        'source_message_id', null,
                        'created_at', '2026-11-20T08:05:00.000000Z'
                    ),
                    jsonb_build_object(
                        'action_id', 'b5240000-0000-4000-8000-000000000401',
                        'action_version', 1,
                        'target_type', 'PENDING_ACTION',
                        'target_id', 'b5240000-0000-4000-8000-000000000401',
                        'target_version', 1
                    )
                )
            )
        ) ->> 'outcome'
    ),
    'COMMITTED',
    'verify Q1, Q2, Q3 through explicit UI decision'
);

-- 3. Historical-compatible data shape & response_version default = 0
insert into app_private.quiz_attempts (
    attempt_id,
    user_id,
    material_id,
    origin,
    session_outcome_id,
    status,
    question_ids,
    total_questions,
    valid_response_count,
    correct_count,
    incorrect_count,
    omitted_count,
    score_percent
) values (
    'b5240000-0000-4000-8000-000000000599',
    'b5240000-0000-4000-8000-000000000001',
    'b5240000-0000-4000-8000-000000000101',
    'MANUAL',
    null,
    'IN_PROGRESS',
    '["b5240000-0000-4000-8000-000000000301"]'::jsonb,
    1,
    0,
    0,
    0,
    1,
    null
);

select is(
    (select response_version from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000599'),
    0::bigint,
    'historical-compatible insert omitting response_version defaults to 0'
);

select is(
    (
        pg_temp.rv_call(
            'get_quiz_attempt_context',
            pg_temp.rv_request(
                'get_quiz_attempt_context',
                jsonb_build_object('attempt_id', 'b5240000-0000-4000-8000-000000000599')
            )
        ) #>> '{data,response_version}'
    )::bigint,
    0::bigint,
    'get_quiz_attempt_context reports response_version 0 on historical-shaped row'
);

select throws_ok(
    $$update app_private.quiz_attempts set response_version = -1 where attempt_id = 'b5240000-0000-4000-8000-000000000599'$$,
    '23514',
    null,
    'negative response_version is rejected by check/trigger'
);

-- Create attempt A1 via signed RPC (historical-compatible payload)
create temporary table rv_create_a1 as
select pg_temp.rv_call(
    'create_quiz_attempt',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'create_quiz_attempt',
            jsonb_build_object(
                'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                'material_id', 'b5240000-0000-4000-8000-000000000101',
                'question_ids', jsonb_build_array(
                    'b5240000-0000-4000-8000-000000000301',
                    'b5240000-0000-4000-8000-000000000302',
                    'b5240000-0000-4000-8000-000000000303'
                ),
                'origin', 'MANUAL',
                'session_outcome_id', null
            ),
            'b5240000-0000-4000-8000-000000000001',
            'b524-attempt-create-0001'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_create_a1), 'COMMITTED', 'create_quiz_attempt A1 succeeds');
select ok(
    (select not (response -> 'data' ? 'response_version') from rv_create_a1),
    'QuizAttempt public JSON keeps historical shape without response_version'
);
select is(
    (select response_version from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    0::bigint,
    'new QuizAttempt A1 starts with response_version = 0'
);

-- 4. get_quiz_attempt_context owner check & initial response_version
create temporary table rv_ctx_0 as
select pg_temp.rv_call(
    'get_quiz_attempt_context',
    pg_temp.rv_request(
        'get_quiz_attempt_context',
        jsonb_build_object('attempt_id', 'b5240000-0000-4000-8000-000000000501')
    )
) as response;

select is((select response ->> 'outcome' from rv_ctx_0), 'READ', 'owner get_quiz_attempt_context returns READ');
select is((select (response #>> '{data,response_version}')::bigint from rv_ctx_0), 0::bigint, 'initial context response_version is 0');
select is((select jsonb_array_length(response #> '{data,questions}') from rv_ctx_0), 3, 'context returns all 3 attempt questions');
select is((select jsonb_array_length(response #> '{data,responses}') from rv_ctx_0), 0, 'initial context has 0 saved responses');

select is(
    pg_temp.rv_call(
        'get_quiz_attempt_context',
        pg_temp.rv_request(
            'get_quiz_attempt_context',
            jsonb_build_object('attempt_id', 'b5240000-0000-4000-8000-000000000501'),
            'b5240000-0000-4000-8000-000000000002'
        ),
        'b5240000-0000-4000-8000-000000000002'
    ) #>> '{error,code}',
    'ENTITY_NOT_FOUND',
    'cross-user get_quiz_attempt_context fails closed with ENTITY_NOT_FOUND'
);

select is(
    pg_temp.rv_call(
        'get_quiz_attempt_context',
        pg_temp.rv_request(
            'get_quiz_attempt_context',
            jsonb_build_object('attempt_id', 'b5240000-0000-4000-8000-000000009999')
        )
    ) #>> '{error,code}',
    'ENTITY_NOT_FOUND',
    'nonexistent attempt get_quiz_attempt_context returns ENTITY_NOT_FOUND'
);

-- 5. Direct version jump / extra mutation trigger guards on quiz_attempts
select throws_ok(
    $$update app_private.quiz_attempts set response_version = response_version + 2 where attempt_id = 'b5240000-0000-4000-8000-000000000501'$$,
    '23514',
    null,
    'direct response_version jump (+2) is rejected'
);

select throws_ok(
    $$update app_private.quiz_attempts
      set response_version = response_version + 1,
          status = 'SUBMITTED',
          submitted_at = clock_timestamp()
      where attempt_id = 'b5240000-0000-4000-8000-000000000501'$$,
    '23514',
    null,
    'extra status/submission mutation paired with response_version increment is rejected'
);

-- 6. Signed save_quiz_response: legacy caller (no include_replay_status) new + COMMITTED replay + conflict
create temporary table rv_save_legacy_1 as
select pg_temp.rv_call(
    'save_quiz_response',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'save_quiz_response',
            jsonb_build_object(
                'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                'question_id', 'b5240000-0000-4000-8000-000000000301',
                'selected_option_id', 'B',
                'validity', 'VALID'
            ),
            'b5240000-0000-4000-8000-000000000001',
            'b524-save-legacy-0001',
            p_req_id => 'b524-req-save-legacy-1'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_save_legacy_1), 'COMMITTED', 'legacy save without include_replay_status returns COMMITTED');
select ok((select not (response -> 'data' ? 'response_version') from rv_save_legacy_1), 'QuizResponse public JSON does not expose response_version');
select is(
    (select response_version from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    1::bigint,
    'legacy save increments response_version from 0 to 1'
);

-- Legacy replay with same key and omitted optional bool must still return COMMITTED and NOT bump version
create temporary table rv_save_legacy_replay as
select pg_temp.rv_call(
    'save_quiz_response',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'save_quiz_response',
            jsonb_build_object(
                'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                'question_id', 'b5240000-0000-4000-8000-000000000301',
                'selected_option_id', 'B',
                'validity', 'VALID'
            ),
            'b5240000-0000-4000-8000-000000000001',
            'b524-save-legacy-0001',
            p_req_id => 'b524-req-save-legacy-2'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_save_legacy_replay), 'COMMITTED', 'legacy replay without include_replay_status preserves COMMITTED outcome');
select is((select response ->> 'request_id' from rv_save_legacy_replay), 'b524-req-save-legacy-2', 'legacy replay echoes current request_id');
select is(
    (select response -> 'data' from rv_save_legacy_replay),
    (select response -> 'data' from rv_save_legacy_1),
    'legacy replay returns identical data'
);
select is(
    (select response_version from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    1::bigint,
    'legacy save replay increments response_version exactly once'
);

-- Direct decrement rejected once version > 0
select throws_ok(
    $$update app_private.quiz_attempts set response_version = response_version - 1 where attempt_id = 'b5240000-0000-4000-8000-000000000501'$$,
    '23514',
    null,
    'direct response_version decrement is rejected'
);

-- 7. Signed save_quiz_response: opt-in include_replay_status=true new + READ replay + conflict
create temporary table rv_save_optin_1 as
select pg_temp.rv_call(
    'save_quiz_response',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'save_quiz_response',
            jsonb_build_object(
                'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                'question_id', 'b5240000-0000-4000-8000-000000000302',
                'selected_option_id', 'TRUE',
                'validity', 'VALID',
                'include_replay_status', true
            ),
            'b5240000-0000-4000-8000-000000000001',
            'b524-save-optin-0001',
            p_req_id => 'b524-req-save-optin-1'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_save_optin_1), 'COMMITTED', 'opt-in new save returns COMMITTED');
select is(
    (select response_version from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    2::bigint,
    'opt-in new save increments response_version to 2'
);

create temporary table rv_save_optin_replay as
select pg_temp.rv_call(
    'save_quiz_response',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'save_quiz_response',
            jsonb_build_object(
                'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                'question_id', 'b5240000-0000-4000-8000-000000000302',
                'selected_option_id', 'TRUE',
                'validity', 'VALID',
                'include_replay_status', true
            ),
            'b5240000-0000-4000-8000-000000000001',
            'b524-save-optin-0001',
            p_req_id => 'b524-req-save-optin-2'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_save_optin_replay), 'READ', 'opt-in save replay returns READ');
select is((select response ->> 'request_id' from rv_save_optin_replay), 'b524-req-save-optin-2', 'opt-in save replay echoes current request_id');
select is(
    (select response -> 'data' from rv_save_optin_replay),
    (select response -> 'data' from rv_save_optin_1),
    'opt-in save replay returns identical data'
);
select is(
    (select response_version from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    2::bigint,
    'opt-in save replay increments response_version exactly once'
);

-- Same key with modified selected_option_id -> IDEMPOTENCY_CONFLICT and version unchanged
select is(
    pg_temp.rv_call(
        'save_quiz_response',
        pg_temp.rv_sign(
            pg_temp.rv_request(
                'save_quiz_response',
                jsonb_build_object(
                    'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                    'question_id', 'b5240000-0000-4000-8000-000000000302',
                    'selected_option_id', 'FALSE',
                    'validity', 'VALID',
                    'include_replay_status', true
                ),
                'b5240000-0000-4000-8000-000000000001',
                'b524-save-optin-0001'
            )
        )
    ) #>> '{error,code}',
    'IDEMPOTENCY_CONFLICT',
    'save_quiz_response with same key and different answer returns IDEMPOTENCY_CONFLICT'
);

-- Update Q1 to 'A' (incorrect; answer_key is 'B') with new key -> response_version becomes 3
select is(
    pg_temp.rv_call(
        'save_quiz_response',
        pg_temp.rv_sign(
            pg_temp.rv_request(
                'save_quiz_response',
                jsonb_build_object(
                    'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                    'question_id', 'b5240000-0000-4000-8000-000000000301',
                    'selected_option_id', 'A',
                    'validity', 'VALID',
                    'include_replay_status', true
                ),
                'b5240000-0000-4000-8000-000000000001',
                'b524-save-update-0001'
            )
        )
    ) ->> 'outcome',
    'COMMITTED',
    'updating Q1 with new key returns COMMITTED'
);

select is(
    (
        pg_temp.rv_call(
            'get_quiz_attempt_context',
            pg_temp.rv_request(
                'get_quiz_attempt_context',
                jsonb_build_object('attempt_id', 'b5240000-0000-4000-8000-000000000501')
            )
        ) #>> '{data,response_version}'
    )::bigint,
    3::bigint,
    'get_quiz_attempt_context reflects response_version 3 after 3 unique saves'
);

-- Helper to build graded submit payload for A1 using current saved response IDs
create function pg_temp.rv_a1_submit_args(
    p_expected_version bigint,
    p_include_replay boolean
) returns jsonb
language sql as $$
    with saved as (
        select question_id, response_id, created_at
        from app_private.quiz_responses
        where attempt_id = 'b5240000-0000-4000-8000-000000000501'
    )
    select jsonb_build_object(
        'attempt_id', 'b5240000-0000-4000-8000-000000000501',
        'graded_responses', jsonb_build_array(
            jsonb_build_object(
                'response_id', (select response_id from saved where question_id = 'b5240000-0000-4000-8000-000000000301'),
                'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                'question_id', 'b5240000-0000-4000-8000-000000000301',
                'user_id', 'b5240000-0000-4000-8000-000000000001',
                'selected_option_id', 'A',
                'validity', 'VALID',
                'is_correct', false,
                'graded_at', '2026-11-20T08:30:00.000000Z',
                'created_at', app_private.iso((select created_at from saved where question_id = 'b5240000-0000-4000-8000-000000000301')),
                'updated_at', '2026-11-20T08:30:00.000000Z'
            ),
            jsonb_build_object(
                'response_id', (select response_id from saved where question_id = 'b5240000-0000-4000-8000-000000000302'),
                'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                'question_id', 'b5240000-0000-4000-8000-000000000302',
                'user_id', 'b5240000-0000-4000-8000-000000000001',
                'selected_option_id', 'TRUE',
                'validity', 'VALID',
                'is_correct', true,
                'graded_at', '2026-11-20T08:30:00.000000Z',
                'created_at', app_private.iso((select created_at from saved where question_id = 'b5240000-0000-4000-8000-000000000302')),
                'updated_at', '2026-11-20T08:30:00.000000Z'
            ),
            jsonb_build_object(
                'response_id', 'b5240000-0000-4000-8000-000000000603',
                'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                'question_id', 'b5240000-0000-4000-8000-000000000303',
                'user_id', 'b5240000-0000-4000-8000-000000000001',
                'selected_option_id', null,
                'validity', 'OMITTED',
                'is_correct', null,
                'graded_at', '2026-11-20T08:30:00.000000Z',
                'created_at', '2026-11-20T08:30:00.000000Z',
                'updated_at', '2026-11-20T08:30:00.000000Z'
            )
        ),
        'valid_response_count', 2,
        'correct_count', 1,
        'incorrect_count', 1,
        'omitted_count', 1,
        'score_percent', 50,
        'submitted_at', '2026-11-20T08:30:00.000000Z',
        'expected_response_version', p_expected_version,
        'include_replay_status', p_include_replay
    )
$$;

-- 8. Signed submit with stale expected_response_version -> ERROR STALE_ENTITY_VERSION, field expected_response_version, zero point writes
create temporary table rv_submit_stale as
select pg_temp.rv_call(
    'submit_quiz_attempt',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'submit_quiz_attempt',
            pg_temp.rv_a1_submit_args(2, true),
            'b5240000-0000-4000-8000-000000000001',
            'b524-submit-stale-0001'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_submit_stale), 'ERROR', 'stale expected_response_version returns ERROR');
select is((select response #>> '{error,code}' from rv_submit_stale), 'STALE_ENTITY_VERSION', 'stale expected_response_version returns STALE_ENTITY_VERSION');
select is((select response #>> '{error,field}' from rv_submit_stale), 'expected_response_version', 'stale expected_response_version reports field expected_response_version');
select is((select response -> 'data' from rv_submit_stale), 'null'::jsonb, 'stale submit error returns data=null');

select is(
    (select status from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    'IN_PROGRESS',
    'stale submit performs no point write to quiz_attempts.status'
);
select is(
    (select submitted_at from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    null::timestamptz,
    'stale submit leaves submitted_at null'
);
select is(
    (select response_version from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    3::bigint,
    'stale submit preserves response_version = 3'
);
select is(
    (select count(*) from app_private.quiz_responses where attempt_id = 'b5240000-0000-4000-8000-000000000501' and (graded_at is not null or is_correct is not null)),
    0::bigint,
    'stale submit writes no graded_at or is_correct to quiz_responses'
);
select is(
    (select count(*) from app_private.quiz_responses where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    2::bigint,
    'stale submit does not insert omitted Q3 response row'
);

-- 9. Signed submit with matching expected_response_version = 3 + opt-in READ replay + SUBMITTED immutability
create temporary table rv_submit_match as
select pg_temp.rv_call(
    'submit_quiz_attempt',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'submit_quiz_attempt',
            pg_temp.rv_a1_submit_args(3, true),
            'b5240000-0000-4000-8000-000000000001',
            'b524-submit-optin-0001',
            p_req_id => 'b524-req-submit-optin-1'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_submit_match), 'COMMITTED', 'matching expected_response_version submit commits');
select is((select response #>> '{data,attempt,status}' from rv_submit_match), 'SUBMITTED', 'submitted attempt status is SUBMITTED');
select is((select (response #>> '{data,attempt,score_percent}')::integer from rv_submit_match), 50, 'submitted attempt score reflects updated answer');
select ok((select not ((response #> '{data,attempt}') ? 'response_version') from rv_submit_match), 'submitted QuizAttempt public JSON excludes response_version');
select is(
    (select response_version from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    3::bigint,
    'submit preserves response_version = 3'
);
select is(
    (
        pg_temp.rv_call(
            'get_quiz_attempt_context',
            pg_temp.rv_request(
                'get_quiz_attempt_context',
                jsonb_build_object('attempt_id', 'b5240000-0000-4000-8000-000000000501')
            )
        ) #>> '{data,response_version}'
    )::bigint,
    3::bigint,
    'get_quiz_attempt_context preserves response_version = 3 after submission'
);

-- Opt-in replay after submission returns READ with identical data
create temporary table rv_submit_optin_replay as
select pg_temp.rv_call(
    'submit_quiz_attempt',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'submit_quiz_attempt',
            pg_temp.rv_a1_submit_args(3, true),
            'b5240000-0000-4000-8000-000000000001',
            'b524-submit-optin-0001',
            p_req_id => 'b524-req-submit-optin-2'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_submit_optin_replay), 'READ', 'opt-in submit replay after submission returns READ');
select is((select response ->> 'request_id' from rv_submit_optin_replay), 'b524-req-submit-optin-2', 'opt-in submit replay echoes current request_id');
select is(
    (select response -> 'data' from rv_submit_optin_replay),
    (select response -> 'data' from rv_submit_match),
    'opt-in submit replay returns identical data'
);
select is(
    (select response_version from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'),
    3::bigint,
    'opt-in submit replay preserves response_version = 3'
);

-- SUBMITTED immutability checks (trigger + late RPC)
select throws_ok(
    $$update app_private.quiz_attempts set response_version = 4 where attempt_id = 'b5240000-0000-4000-8000-000000000501'$$,
    '23514',
    null,
    'SUBMITTED quiz_attempt blocks response_version update'
);
select throws_ok(
    $$delete from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000501'$$,
    '23514',
    null,
    'SUBMITTED quiz_attempt cannot be deleted'
);
select throws_ok(
    $$update app_private.quiz_responses set selected_option_id = 'B' where attempt_id = 'b5240000-0000-4000-8000-000000000501' and question_id = 'b5240000-0000-4000-8000-000000000301'$$,
    '23514',
    null,
    'SUBMITTED quiz_response cannot be updated'
);
select throws_ok(
    $$delete from app_private.quiz_responses where attempt_id = 'b5240000-0000-4000-8000-000000000501'$$,
    '23514',
    null,
    'SUBMITTED quiz_response cannot be deleted'
);
select is(
    pg_temp.rv_call(
        'save_quiz_response',
        pg_temp.rv_sign(
            pg_temp.rv_request(
                'save_quiz_response',
                jsonb_build_object(
                    'attempt_id', 'b5240000-0000-4000-8000-000000000501',
                    'question_id', 'b5240000-0000-4000-8000-000000000303',
                    'selected_option_id', 'A',
                    'validity', 'VALID',
                    'include_replay_status', true
                ),
                'b5240000-0000-4000-8000-000000000001',
                'b524-save-after-submit-0001'
            )
        )
    ) #>> '{error,code}',
    'STALE_ENTITY_VERSION',
    'late save_quiz_response on SUBMITTED attempt fails with STALE_ENTITY_VERSION'
);

-- 10. Legacy submit_quiz_attempt (without expected_response_version or include_replay_status) -> COMMITTED replay
select is(
    pg_temp.rv_call(
        'create_quiz_attempt',
        pg_temp.rv_sign(
            pg_temp.rv_request(
                'create_quiz_attempt',
                jsonb_build_object(
                    'attempt_id', 'b5240000-0000-4000-8000-000000000502',
                    'material_id', 'b5240000-0000-4000-8000-000000000101',
                    'question_ids', jsonb_build_array('b5240000-0000-4000-8000-000000000301'),
                    'origin', 'MANUAL',
                    'session_outcome_id', null
                ),
                'b5240000-0000-4000-8000-000000000001',
                'b524-attempt-create-0002'
            )
        )
    ) ->> 'outcome',
    'COMMITTED',
    'create second attempt A2 for legacy submit replay test'
);

create temporary table rv_a2_save as
select pg_temp.rv_call(
    'save_quiz_response',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'save_quiz_response',
            jsonb_build_object(
                'attempt_id', 'b5240000-0000-4000-8000-000000000502',
                'question_id', 'b5240000-0000-4000-8000-000000000301',
                'selected_option_id', 'B',
                'validity', 'VALID'
            ),
            'b5240000-0000-4000-8000-000000000001',
            'b524-a2-save-0001'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_a2_save), 'COMMITTED', 'save A2 response succeeds');

create temporary table rv_submit_legacy_1 as
select pg_temp.rv_call(
    'submit_quiz_attempt',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'submit_quiz_attempt',
            jsonb_build_object(
                'attempt_id', 'b5240000-0000-4000-8000-000000000502',
                'graded_responses', jsonb_build_array(
                    jsonb_build_object(
                        'response_id', (select response #>> '{data,response_id}' from rv_a2_save),
                        'attempt_id', 'b5240000-0000-4000-8000-000000000502',
                        'question_id', 'b5240000-0000-4000-8000-000000000301',
                        'user_id', 'b5240000-0000-4000-8000-000000000001',
                        'selected_option_id', 'B',
                        'validity', 'VALID',
                        'is_correct', true,
                        'graded_at', '2026-11-20T08:40:00.000000Z',
                        'created_at', (select response #>> '{data,created_at}' from rv_a2_save),
                        'updated_at', '2026-11-20T08:40:00.000000Z'
                    )
                ),
                'valid_response_count', 1,
                'correct_count', 1,
                'incorrect_count', 0,
                'omitted_count', 0,
                'score_percent', 100,
                'submitted_at', '2026-11-20T08:40:00.000000Z'
            ),
            'b5240000-0000-4000-8000-000000000001',
            'b524-submit-legacy-0001',
            p_req_id => 'b524-req-submit-legacy-1'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_submit_legacy_1), 'COMMITTED', 'legacy submit without optional flags returns COMMITTED');

create temporary table rv_submit_legacy_replay as
select pg_temp.rv_call(
    'submit_quiz_attempt',
    pg_temp.rv_sign(
        pg_temp.rv_request(
            'submit_quiz_attempt',
            jsonb_build_object(
                'attempt_id', 'b5240000-0000-4000-8000-000000000502',
                'graded_responses', jsonb_build_array(
                    jsonb_build_object(
                        'response_id', (select response #>> '{data,response_id}' from rv_a2_save),
                        'attempt_id', 'b5240000-0000-4000-8000-000000000502',
                        'question_id', 'b5240000-0000-4000-8000-000000000301',
                        'user_id', 'b5240000-0000-4000-8000-000000000001',
                        'selected_option_id', 'B',
                        'validity', 'VALID',
                        'is_correct', true,
                        'graded_at', '2026-11-20T08:40:00.000000Z',
                        'created_at', (select response #>> '{data,created_at}' from rv_a2_save),
                        'updated_at', '2026-11-20T08:40:00.000000Z'
                    )
                ),
                'valid_response_count', 1,
                'correct_count', 1,
                'incorrect_count', 0,
                'omitted_count', 0,
                'score_percent', 100,
                'submitted_at', '2026-11-20T08:40:00.000000Z'
            ),
            'b5240000-0000-4000-8000-000000000001',
            'b524-submit-legacy-0001',
            p_req_id => 'b524-req-submit-legacy-2'
        )
    )
) as response;

select is((select response ->> 'outcome' from rv_submit_legacy_replay), 'COMMITTED', 'legacy submit replay without include_replay_status preserves COMMITTED');
select is((select response ->> 'request_id' from rv_submit_legacy_replay), 'b524-req-submit-legacy-2', 'legacy submit replay echoes current request_id');
select is(
    (select response -> 'data' from rv_submit_legacy_replay),
    (select response -> 'data' from rv_submit_legacy_1),
    'legacy submit replay returns identical data'
);
select is(
    (select response_version from app_private.quiz_attempts where attempt_id = 'b5240000-0000-4000-8000-000000000502'),
    1::bigint,
    'legacy submit replay preserves response_version = 1'
);

-- Submit idempotency conflict (same key with different attempt_id)
select is(
    pg_temp.rv_call(
        'submit_quiz_attempt',
        pg_temp.rv_sign(
            pg_temp.rv_request(
                'submit_quiz_attempt',
                pg_temp.rv_a1_submit_args(3, true),
                'b5240000-0000-4000-8000-000000000001',
                'b524-submit-legacy-0001'
            )
        )
    ) #>> '{error,code}',
    'IDEMPOTENCY_CONFLICT',
    'submit_quiz_attempt with same key and different attempt_id returns IDEMPOTENCY_CONFLICT'
);

select * from finish();
rollback;
