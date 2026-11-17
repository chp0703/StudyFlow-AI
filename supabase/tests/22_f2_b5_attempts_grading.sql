-- F2 B5 pgTAP: quiz_attempts and quiz_responses tables, RLS, VERIFIED-only guard,
-- OMITTED/INVALID is_correct IS NULL invariant, and SUBMITTED immutability.

begin;
select no_plan();
set local search_path = public, extensions;
set local timezone = 'UTC';

-- 1. Schema, RLS, and privilege boundary checks
select ok(to_regclass('app_private.quiz_attempts') is not null, 'quiz_attempts table exists');
select ok(to_regclass('app_private.quiz_responses') is not null, 'quiz_responses table exists');

select ok(
    not exists (
        select 1
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'app_private'
          and c.relname in ('quiz_attempts', 'quiz_responses')
          and (not c.relrowsecurity or not c.relforcerowsecurity)
    ),
    'quiz_attempts and quiz_responses enable and force RLS'
);

select ok(
    not exists (
        select 1
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        cross join pg_roles r
        where n.nspname = 'app_private'
          and c.relname in ('quiz_attempts', 'quiz_responses')
          and r.rolname in ('anon', 'authenticated')
          and has_table_privilege(r.oid, c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
    ),
    'anon and authenticated have no direct privileges on quiz_attempts or quiz_responses'
);

-- 2. Seed local test fixtures (2 users, HMAC key, material, DRAFT + VERIFIED questions)
create function pg_temp.b5_seed() returns text
language plpgsql as $$
begin
    insert into auth.users(id) values
        ('b5000000-0000-4000-8000-000000000001'),
        ('b5000000-0000-4000-8000-000000000002');

    insert into app_private.rpc_attestation_keys (key_id, key_material, not_before, not_after)
    values (
        'b5-local-fixture-only',
        decode('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f', 'hex'),
        clock_timestamp() - interval '1 hour',
        clock_timestamp() + interval '1 hour'
    );
    return 'OK';
exception when others then
    return 'SQL_ERROR:' || sqlstate || ':' || sqlerrm;
end $$;

select is(pg_temp.b5_seed(), 'OK', 'seed local fixture users and HMAC key');

create function pg_temp.b5_request(
    p_operation text,
    p_arguments jsonb,
    p_owner uuid default 'b5000000-0000-4000-8000-000000000001',
    p_idem text default 'b5-idempotency-key-0001',
    p_conv uuid default 'b5000000-0000-4000-8000-000000000003',
    p_approval jsonb default null,
    p_action_ref jsonb default null
) returns jsonb
language sql as $$
    select jsonb_build_object(
        'contract_version', '1.0.1',
        'schema_version', '1.1',
        'request_id', 'b5-req-0001',
        'operation', p_operation,
        'arguments', p_arguments,
        'execution_context', jsonb_build_object(
            'conversation_id', p_conv,
            'idempotency_key', p_idem,
            'approval_action', p_approval,
            'action_reference', p_action_ref,
            'trusted_context', jsonb_build_object(
                'request_id', 'b5-req-0001',
                'message_id', 'b5000000-0000-4000-8000-000000000004',
                'principal', jsonb_build_object('user_id', p_owner),
                'received_at', app_private.iso(clock_timestamp()),
                'timezone', 'Asia/Ho_Chi_Minh',
                'locale', 'vi-VN'
            )
        ),
        'attestation', null
    )
$$;

create function pg_temp.b5_sign(p_request jsonb) returns jsonb
language plpgsql as $$
declare
    v_payload_json jsonb;
    v_payload text;
    v_stamp timestamptz := clock_timestamp();
begin
    v_payload_json := jsonb_build_object(
        'v', 1,
        'key_id', 'b5-local-fixture-only',
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
            'key_id', 'b5-local-fixture-only',
            'payload', v_payload,
            'signature', encode(
                extensions.hmac(
                    convert_to(v_payload, 'UTF8'),
                    decode('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f', 'hex'),
                    'sha256'
                ),
                'hex'
            )
        )
    );
end $$;

create function pg_temp.b5_call(
    p_routine text,
    p_request jsonb,
    p_jwt_user uuid default 'b5000000-0000-4000-8000-000000000001'
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

create function pg_temp.b5_draft(
    p_qid uuid,
    p_qtype text default 'MCQ',
    p_answer text default 'B'
) returns jsonb
language sql as $$
    select jsonb_build_object(
        'assessment_version', '1.0.0',
        'question_id', p_qid,
        'user_id', 'b5000000-0000-4000-8000-000000000001',
        'conversation_id', 'b5000000-0000-4000-8000-000000000003',
        'material_id', 'b5000000-0000-4000-8000-000000000101',
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
        'source_chunk_ids', jsonb_build_array('b5000000-0000-4000-8000-000000000201'),
        'status', 'DRAFT',
        'model', 'deepseek-chat',
        'prompt_version', 'f2-question-v1',
        'verified_at', null,
        'created_at', '2026-11-18T08:01:00.000000Z',
        'updated_at', '2026-11-18T08:01:00.000000Z'
    )
$$;

-- Store material & verify questions for USER_A
select is(
    (
        pg_temp.b5_call(
            'store_assessment_material',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'store_assessment_material',
                    jsonb_build_object(
                        'material_id', 'b5000000-0000-4000-8000-000000000101',
                        'conversation_id', 'b5000000-0000-4000-8000-000000000003',
                        'filename', 'mang.md',
                        'mime_type', 'text/markdown',
                        'size_bytes', 120,
                        'sha256', repeat('a', 64),
                        'page_count', 1,
                        'char_count', length('TCP truyền dữ liệu hướng kết nối, UDP truyền datagram không kết nối.'),
                        'topics', jsonb_build_array('Mạng máy tính'),
                        'chunks', jsonb_build_array(
                            jsonb_build_object(
                                'chunk_id', 'b5000000-0000-4000-8000-000000000201',
                                'material_id', 'b5000000-0000-4000-8000-000000000101',
                                'user_id', 'b5000000-0000-4000-8000-000000000001',
                                'page', 1,
                                'topic', 'Mạng máy tính',
                                'chunk_index', 0,
                                'text', 'TCP truyền dữ liệu hướng kết nối, UDP truyền datagram không kết nối.',
                                'created_at', '2026-11-18T08:00:00.000000Z'
                            )
                        )
                    ),
                    'b5000000-0000-4000-8000-000000000001',
                    'b5-mat-store-0001'
                )
            )
        ) ->> 'outcome'
    ),
    'COMMITTED',
    'store READY material for USER_A'
);

-- Create 3 drafts (Q1, Q2, Q3) in batch 1 and verify Q1, Q2, Q3
select is(
    (
        pg_temp.b5_call(
            'create_question_drafts',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'create_question_drafts',
                    jsonb_build_object(
                        'conversation_id', 'b5000000-0000-4000-8000-000000000003',
                        'material_id', 'b5000000-0000-4000-8000-000000000101',
                        'action_id', 'b5000000-0000-4000-8000-000000000401',
                        'generation_params', jsonb_build_object(
                            'topic', 'Mạng máy tính',
                            'question_type', 'MCQ',
                            'count', 3
                        ),
                        'drafts', jsonb_build_array(
                            pg_temp.b5_draft('b5000000-0000-4000-8000-000000000301', 'MCQ', 'B'),
                            pg_temp.b5_draft('b5000000-0000-4000-8000-000000000302', 'TRUE_FALSE', 'TRUE'),
                            pg_temp.b5_draft('b5000000-0000-4000-8000-000000000303', 'MCQ', 'A')
                        )
                    ),
                    'b5000000-0000-4000-8000-000000000001',
                    'b5-drafts-create-0001'
                )
            )
        ) ->> 'outcome'
    ),
    'DRAFTED',
    'create 3 question drafts for USER_A'
);

-- Verify Q1, Q2, Q3
select is(
    (
        pg_temp.b5_call(
            'verify_question_drafts',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'verify_question_drafts',
                    jsonb_build_object(
                        'conversation_id', 'b5000000-0000-4000-8000-000000000003',
                        'action_id', 'b5000000-0000-4000-8000-000000000401',
                        'expected_action_version', 1,
                        'question_ids', jsonb_build_array(
                            'b5000000-0000-4000-8000-000000000301',
                            'b5000000-0000-4000-8000-000000000302',
                            'b5000000-0000-4000-8000-000000000303'
                        ),
                        'decision', 'APPROVE'
                    ),
                    'b5000000-0000-4000-8000-000000000001',
                    'b5-drafts-verify-0001',
                    'b5000000-0000-4000-8000-000000000003',
                    jsonb_build_object(
                        'approval_action_id', 'b5000000-0000-4000-8000-000000000411',
                        'user_id', 'b5000000-0000-4000-8000-000000000001',
                        'target_type', 'PENDING_ACTION',
                        'target_id', 'b5000000-0000-4000-8000-000000000401',
                        'target_version', 1,
                        'decision', 'APPROVE',
                        'source', 'UI',
                        'source_message_id', null,
                        'created_at', '2026-11-18T08:05:00.000000Z'
                    ),
                    jsonb_build_object(
                        'action_id', 'b5000000-0000-4000-8000-000000000401',
                        'action_version', 1,
                        'target_type', 'PENDING_ACTION',
                        'target_id', 'b5000000-0000-4000-8000-000000000401',
                        'target_version', 1
                    )
                )
            )
        ) ->> 'outcome'
    ),
    'COMMITTED',
    'verify Q1, Q2, Q3 through explicit decision'
);

-- Create a second draft batch (Q4) that stays DRAFT
select is(
    (
        pg_temp.b5_call(
            'create_question_drafts',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'create_question_drafts',
                    jsonb_build_object(
                        'conversation_id', 'b5000000-0000-4000-8000-000000000003',
                        'material_id', 'b5000000-0000-4000-8000-000000000101',
                        'action_id', 'b5000000-0000-4000-8000-000000000402',
                        'generation_params', jsonb_build_object(
                            'topic', 'Mạng máy tính',
                            'question_type', 'MCQ',
                            'count', 1
                        ),
                        'drafts', jsonb_build_array(
                            pg_temp.b5_draft('b5000000-0000-4000-8000-000000000304', 'MCQ', 'B')
                        )
                    ),
                    'b5000000-0000-4000-8000-000000000001',
                    'b5-drafts-create-0002'
                )
            )
        ) ->> 'outcome'
    ),
    'DRAFTED',
    'create unverified DRAFT question Q4'
);

-- 3. Reject creating attempt with DRAFT question Q4
select is(
    (
        pg_temp.b5_call(
            'create_quiz_attempt',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'create_quiz_attempt',
                    jsonb_build_object(
                        'attempt_id', 'b5000000-0000-4000-8000-000000000500',
                        'material_id', 'b5000000-0000-4000-8000-000000000101',
                        'question_ids', jsonb_build_array(
                            'b5000000-0000-4000-8000-000000000301',
                            'b5000000-0000-4000-8000-000000000304'
                        ),
                        'origin', 'MANUAL',
                        'session_outcome_id', null
                    ),
                    'b5000000-0000-4000-8000-000000000001',
                    'b5-attempt-draft-reject-01'
                )
            )
        ) #>> '{error,code}'
    ),
    'STALE_ENTITY_VERSION',
    'create_quiz_attempt rejects DRAFT question with STALE_ENTITY_VERSION'
);

-- 4. Create MANUAL attempt with VERIFIED questions Q1, Q2, Q3
select is(
    (
        pg_temp.b5_call(
            'create_quiz_attempt',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'create_quiz_attempt',
                    jsonb_build_object(
                        'attempt_id', 'b5000000-0000-4000-8000-000000000501',
                        'material_id', 'b5000000-0000-4000-8000-000000000101',
                        'question_ids', jsonb_build_array(
                            'b5000000-0000-4000-8000-000000000301',
                            'b5000000-0000-4000-8000-000000000302',
                            'b5000000-0000-4000-8000-000000000303'
                        ),
                        'origin', 'MANUAL',
                        'session_outcome_id', null
                    ),
                    'b5000000-0000-4000-8000-000000000001',
                    'b5-attempt-create-0001'
                )
            )
        ) ->> 'outcome'
    ),
    'COMMITTED',
    'create_quiz_attempt succeeds with VERIFIED questions'
);

-- Create SESSION_HANDOFF attempt with plain UUID session_outcome_id
select is(
    (
        pg_temp.b5_call(
            'create_quiz_attempt',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'create_quiz_attempt',
                    jsonb_build_object(
                        'attempt_id', 'b5000000-0000-4000-8000-000000000502',
                        'material_id', 'b5000000-0000-4000-8000-000000000101',
                        'question_ids', jsonb_build_array('b5000000-0000-4000-8000-000000000301'),
                        'origin', 'SESSION_HANDOFF',
                        'session_outcome_id', 'b5000000-0000-4000-8000-000000000777'
                    ),
                    'b5000000-0000-4000-8000-000000000001',
                    'b5-attempt-create-0002'
                )
            )
        ) ->> 'outcome'
    ),
    'COMMITTED',
    'create_quiz_attempt supports SESSION_HANDOFF with plain UUID session_outcome_id'
);

-- 5. Cross-user access fails closed with ENTITY_NOT_FOUND
select is(
    (
        pg_temp.b5_call(
            'save_quiz_response',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'save_quiz_response',
                    jsonb_build_object(
                        'attempt_id', 'b5000000-0000-4000-8000-000000000501',
                        'question_id', 'b5000000-0000-4000-8000-000000000301',
                        'selected_option_id', 'B',
                        'validity', 'VALID'
                    ),
                    'b5000000-0000-4000-8000-000000000002',
                    'b5-cross-user-save-01'
                )
            ),
            'b5000000-0000-4000-8000-000000000002'
        ) #>> '{error,code}'
    ),
    'ENTITY_NOT_FOUND',
    'cross-user save_quiz_response fails closed with ENTITY_NOT_FOUND'
);

-- 6. Save responses for Q1 (VALID correct 'B') and Q2 (INVALID 'Z'), leaving Q3 OMITTED
select is(
    (
        pg_temp.b5_call(
            'save_quiz_response',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'save_quiz_response',
                    jsonb_build_object(
                        'attempt_id', 'b5000000-0000-4000-8000-000000000501',
                        'question_id', 'b5000000-0000-4000-8000-000000000301',
                        'selected_option_id', 'B',
                        'validity', 'VALID'
                    ),
                    'b5000000-0000-4000-8000-000000000001',
                    'b5-save-resp-0001'
                )
            )
        ) ->> 'outcome'
    ),
    'COMMITTED',
    'save_quiz_response persists VALID response for Q1'
);

select is(
    (
        pg_temp.b5_call(
            'save_quiz_response',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'save_quiz_response',
                    jsonb_build_object(
                        'attempt_id', 'b5000000-0000-4000-8000-000000000501',
                        'question_id', 'b5000000-0000-4000-8000-000000000302',
                        'selected_option_id', 'Z',
                        'validity', 'INVALID'
                    ),
                    'b5000000-0000-4000-8000-000000000001',
                    'b5-save-resp-0002'
                )
            )
        ) ->> 'outcome'
    ),
    'COMMITTED',
    'save_quiz_response persists INVALID response for Q2 with is_correct null'
);

-- 7. Submit and grade attempt 501 (1 VALID correct, 1 INVALID, 1 OMITTED -> valid_response_count=1, correct=1, incorrect=0, omitted=2, score_percent=100)
create temporary table b5_submit_res as
select pg_temp.b5_call(
    'submit_quiz_attempt',
    pg_temp.b5_sign(
        pg_temp.b5_request(
            'submit_quiz_attempt',
            jsonb_build_object(
                'attempt_id', 'b5000000-0000-4000-8000-000000000501',
                'graded_responses', jsonb_build_array(
                    jsonb_build_object(
                        'response_id', 'b5000000-0000-4000-8000-000000000601',
                        'attempt_id', 'b5000000-0000-4000-8000-000000000501',
                        'question_id', 'b5000000-0000-4000-8000-000000000301',
                        'user_id', 'b5000000-0000-4000-8000-000000000001',
                        'selected_option_id', 'B',
                        'validity', 'VALID',
                        'is_correct', true,
                        'graded_at', '2026-11-18T08:30:00.000000Z',
                        'created_at', '2026-11-18T08:20:00.000000Z',
                        'updated_at', '2026-11-18T08:30:00.000000Z'
                    ),
                    jsonb_build_object(
                        'response_id', 'b5000000-0000-4000-8000-000000000602',
                        'attempt_id', 'b5000000-0000-4000-8000-000000000501',
                        'question_id', 'b5000000-0000-4000-8000-000000000302',
                        'user_id', 'b5000000-0000-4000-8000-000000000001',
                        'selected_option_id', 'Z',
                        'validity', 'INVALID',
                        'is_correct', null,
                        'graded_at', '2026-11-18T08:30:00.000000Z',
                        'created_at', '2026-11-18T08:21:00.000000Z',
                        'updated_at', '2026-11-18T08:30:00.000000Z'
                    ),
                    jsonb_build_object(
                        'response_id', 'b5000000-0000-4000-8000-000000000603',
                        'attempt_id', 'b5000000-0000-4000-8000-000000000501',
                        'question_id', 'b5000000-0000-4000-8000-000000000303',
                        'user_id', 'b5000000-0000-4000-8000-000000000001',
                        'selected_option_id', null,
                        'validity', 'OMITTED',
                        'is_correct', null,
                        'graded_at', '2026-11-18T08:30:00.000000Z',
                        'created_at', '2026-11-18T08:30:00.000000Z',
                        'updated_at', '2026-11-18T08:30:00.000000Z'
                    )
                ),
                'valid_response_count', 1,
                'correct_count', 1,
                'incorrect_count', 0,
                'omitted_count', 2,
                'score_percent', 100,
                'submitted_at', '2026-11-18T08:30:00.000000Z'
            ),
            'b5000000-0000-4000-8000-000000000001',
            'b5-submit-attempt-0001'
        )
    )
) as response;

select is((select response ->> 'outcome' from b5_submit_res), 'COMMITTED', 'submit_quiz_attempt commits graded attempt');
select is((select response #>> '{data,attempt,status}' from b5_submit_res), 'SUBMITTED', 'attempt status is SUBMITTED');
select is((select (response #>> '{data,attempt,valid_response_count}')::integer from b5_submit_res), 1, 'valid_response_count excludes INVALID and OMITTED');
select is((select (response #>> '{data,attempt,omitted_count}')::integer from b5_submit_res), 2, 'omitted_count counts both OMITTED and INVALID excluded items');
select ok(
    not exists (
        select 1
        from app_private.quiz_responses r
        where r.attempt_id = 'b5000000-0000-4000-8000-000000000501'
          and r.validity in ('OMITTED', 'INVALID')
          and r.is_correct is not null
    ),
    'OMITTED and INVALID responses have is_correct IS NULL in DB'
);

-- 8. Immutability after SUBMITTED: save_quiz_response fails with STALE_ENTITY_VERSION
select is(
    (
        pg_temp.b5_call(
            'save_quiz_response',
            pg_temp.b5_sign(
                pg_temp.b5_request(
                    'save_quiz_response',
                    jsonb_build_object(
                        'attempt_id', 'b5000000-0000-4000-8000-000000000501',
                        'question_id', 'b5000000-0000-4000-8000-000000000303',
                        'selected_option_id', 'A',
                        'validity', 'VALID'
                    ),
                    'b5000000-0000-4000-8000-000000000001',
                    'b5-save-after-submit-01'
                )
            )
        ) #>> '{error,code}'
    ),
    'STALE_ENTITY_VERSION',
    'save_quiz_response on SUBMITTED attempt fails with STALE_ENTITY_VERSION'
);

select * from finish();
rollback;
