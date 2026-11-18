-- F2 B3 + B4 pgTAP: RLS, immutability, UI-only verify guard, concurrency, and cursor security.
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.q_req(
    op text, args jsonb, uid uuid default 'd2030000-0000-4000-8000-000000000001',
    ikey text default 'f2-b3-child-key-0001', approval jsonb default null, aref jsonb default null
) returns jsonb language sql as $$
    select jsonb_build_object(
        'contract_version', '1.0.1', 'schema_version', '1.1', 'request_id', 'q-req',
        'operation', op, 'arguments', args, 'attestation', null,
        'execution_context', jsonb_build_object(
            'conversation_id', 'd2030000-0000-4000-8000-000000000003',
            'idempotency_key', ikey,
            'approval_action', approval,
            'action_reference', aref,
            'trusted_context', jsonb_build_object(
                'request_id', 'q-req', 'message_id', 'd2030000-0000-4000-8000-000000000004',
                'principal', jsonb_build_object('user_id', uid),
                'timezone', 'Asia/Ho_Chi_Minh', 'locale', 'vi-VN', 'received_at', app_private.iso(clock_timestamp())
            )
        )
    )
$$;

create function pg_temp.q_sign(req jsonb) returns jsonb language plpgsql as $$
declare stamp timestamptz := clock_timestamp(); body jsonb; payload text;
begin
    body := jsonb_build_object(
        'v', 1, 'key_id', 'q-key',
        'user_id', req #>> '{execution_context,trusted_context,principal,user_id}',
        'rpc', req ->> 'operation', 'request_id', req ->> 'request_id',
        'request_digest', encode(extensions.digest(convert_to(app_private.canonical_json(req - 'attestation'), 'UTF8'), 'sha256'), 'hex'),
        'issued_at', app_private.iso(stamp), 'expires_at', app_private.iso(stamp + interval '60 seconds')
    );
    payload := rtrim(translate(replace(encode(convert_to(app_private.canonical_json(body), 'UTF8'), 'base64'), E'\n', ''), '+/', '-_'), '=');
    return jsonb_set(req, '{attestation}', jsonb_build_object(
        'key_id', 'q-key', 'payload', payload,
        'signature', encode(extensions.hmac(convert_to(payload, 'UTF8'), decode(repeat('33', 32), 'hex'), 'sha256'), 'hex')
    ));
end $$;

create function pg_temp.q_call(
    op text, args jsonb, uid uuid default 'd2030000-0000-4000-8000-000000000001',
    ikey text default 'f2-b3-child-key-0001', approval jsonb default null, aref jsonb default null
) returns jsonb language plpgsql as $$
declare res jsonb; req jsonb := pg_temp.q_req(op, args, uid, ikey, approval, aref);
begin
    if not app_private.rpc_is_read(op) then req := pg_temp.q_sign(req); end if;
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
end $$;

insert into auth.users(id) values ('d2030000-0000-4000-8000-000000000001'), ('d2030000-0000-4000-8000-000000000002');
insert into app_private.rpc_attestation_keys(key_id, key_material, not_before, not_after)
values ('q-key', decode(repeat('33', 32), 'hex'), clock_timestamp() - interval '1 hour', clock_timestamp() + interval '1 hour');

select ok(not has_table_privilege('authenticated', 'app_private.question_drafts', 'SELECT'), 'no direct question reads');
select ok(not has_table_privilege('authenticated', 'app_private.question_draft_sources', 'INSERT'), 'no direct source writes');
select ok(not has_table_privilege('authenticated', 'app_private.question_draft_batch_items', 'INSERT'), 'no direct batch writes');
select ok((select relforcerowsecurity from pg_class where oid = 'app_private.question_drafts'::regclass), 'question_drafts FORCE RLS');
select ok((select relforcerowsecurity from pg_class where oid = 'app_private.question_draft_sources'::regclass), 'question_draft_sources FORCE RLS');
select ok((select relforcerowsecurity from pg_class where oid = 'app_private.question_draft_batch_items'::regclass), 'question_draft_batch_items FORCE RLS');
select ok(app_private.rpc_is_read('list_questions'), 'list_questions registered as read op');

select is(
    (pg_temp.q_call('store_assessment_material', jsonb_build_object(
        'conversation_id', 'd2030000-0000-4000-8000-000000000003',
        'material_id', 'd2030000-0000-4000-8000-000000000010',
        'filename', 'notes.md', 'mime_type', 'text/markdown', 'size_bytes', 200,
        'sha256', repeat('a', 64), 'page_count', 1,
        'char_count', length('Kỳ vọng E(X) là tổng giá trị nhân xác suất.'),
        'topics', jsonb_build_array('  Xác suất  '),
        'chunks', jsonb_build_array(jsonb_build_object(
            'chunk_id', 'd2030000-0000-4000-8000-000000000020',
            'material_id', 'd2030000-0000-4000-8000-000000000010',
            'user_id', 'd2030000-0000-4000-8000-000000000001',
            'page', 1, 'topic', '  Xác suất  ', 'chunk_index', 0,
            'text', 'Kỳ vọng E(X) là tổng giá trị nhân xác suất.',
            'created_at', '2026-11-16T08:00:00Z'
        ))
    )) ->> 'outcome'),
    'COMMITTED',
    'seed READY material for owner 1'
);

create function pg_temp.q_draft(qid uuid, cid uuid default 'd2030000-0000-4000-8000-000000000020') returns jsonb language sql as $$
    select jsonb_build_object(
        'assessment_version', '1.0.0',
        'question_id', qid,
        'user_id', 'd2030000-0000-4000-8000-000000000001',
        'conversation_id', 'd2030000-0000-4000-8000-000000000003',
        'material_id', 'd2030000-0000-4000-8000-000000000010',
        'version', 1, 'topic', '  Xác suất  ', 'question_type', 'MCQ',
        'stem', 'Kỳ vọng E(X) là gì?',
        'options', jsonb_build_array(
            jsonb_build_object('option_id', 'A', 'text', 'Tổng có trọng số'),
            jsonb_build_object('option_id', 'B', 'text', 'Phương sai')
        ),
        'answer_key', 'A', 'explanation', 'Theo trang 1.',
        'source_chunk_ids', jsonb_build_array(cid),
        'status', 'DRAFT', 'model', 'deepseek-chat', 'prompt_version', 'f2-question-v1',
        'verified_at', null, 'created_at', '2026-11-16T08:01:00Z', 'updated_at', '2026-11-16T08:01:00Z'
    )
$$;

-- Rollback / zero partial write on second invalid draft (bad foreign chunk)
select is(
    pg_temp.q_call('create_question_drafts', jsonb_build_object(
        'conversation_id', 'd2030000-0000-4000-8000-000000000003',
        'material_id', 'd2030000-0000-4000-8000-000000000010',
        'action_id', 'd2030000-0000-4000-8000-000000000040',
        'drafts', jsonb_build_array(
            pg_temp.q_draft('d2030000-0000-4000-8000-000000000031'),
            pg_temp.q_draft('d2030000-0000-4000-8000-000000000032', 'd2030000-0000-4000-8000-000000000999')
        )
    )) #>> '{error,code}',
    'INVALID_PARAMETER',
    'rejects batch citing chunk outside target material/topic'
);
select is((select count(*) from app_private.question_drafts), 0::bigint, 'no partial question_drafts');
select is((select count(*) from app_private.pending_actions where action_id = 'd2030000-0000-4000-8000-000000000040'), 0::bigint, 'no partial pending_action');

-- Cross-user gets ENTITY_NOT_FOUND (404 same as missing)
select is(
    pg_temp.q_call('create_question_drafts', jsonb_build_object(
        'conversation_id', 'd2030000-0000-4000-8000-000000000003',
        'material_id', 'd2030000-0000-4000-8000-000000000010',
        'drafts', jsonb_build_array(jsonb_set(pg_temp.q_draft('d2030000-0000-4000-8000-000000000033'), '{user_id}', '"d2030000-0000-4000-8000-000000000002"'))
    ), 'd2030000-0000-4000-8000-000000000002') #>> '{error,code}',
    'ENTITY_NOT_FOUND',
    'cross-user material rejected with ENTITY_NOT_FOUND'
);

-- Create valid draft batch atomically
select is(
    pg_temp.q_call('create_question_drafts', jsonb_build_object(
        'conversation_id', 'd2030000-0000-4000-8000-000000000003',
        'material_id', 'd2030000-0000-4000-8000-000000000010',
        'action_id', 'd2030000-0000-4000-8000-000000000041',
        'generation_params', jsonb_build_object('topic', '  Xác suất  ', 'question_type', 'MCQ', 'count', 1),
        'drafts', jsonb_build_array(pg_temp.q_draft('d2030000-0000-4000-8000-000000000031'))
    ), 'd2030000-0000-4000-8000-000000000001', 'f2-b3-create-0000001') ->> 'outcome',
    'DRAFTED',
    'create_question_drafts commits batch and presentation atomically'
);

select is(
    (select presentation #>> '{question_drafts,source_chunks,0,text}'
     from app_private.action_presentations
     where action_id = 'd2030000-0000-4000-8000-000000000041' and action_version = 1),
    'Kỳ vọng E(X) là tổng giá trị nhân xác suất.',
    'presentation stores exact source chunk snapshot for verification review'
);

-- Chat approval is rejected
select is(
    pg_temp.q_call(
        'verify_question_drafts',
        jsonb_build_object(
            'conversation_id', 'd2030000-0000-4000-8000-000000000003',
            'action_id', 'd2030000-0000-4000-8000-000000000041',
            'expected_action_version', 1,
            'question_ids', jsonb_build_array('d2030000-0000-4000-8000-000000000031'),
            'decision', 'APPROVE'
        ),
        'd2030000-0000-4000-8000-000000000001',
        'f2-b4-chat-try-0001',
        jsonb_build_object(
            'approval_action_id', 'd2030000-0000-4000-8000-000000000050',
            'user_id', 'd2030000-0000-4000-8000-000000000001',
            'target_type', 'PENDING_ACTION',
            'target_id', 'd2030000-0000-4000-8000-000000000041',
            'target_version', 1,
            'decision', 'APPROVE',
            'source', 'CHAT',
            'source_message_id', 'd2030000-0000-4000-8000-000000000004',
            'created_at', '2026-11-16T08:02:00Z'
        ),
        jsonb_build_object(
            'action_id', 'd2030000-0000-4000-8000-000000000041',
            'action_version', 1,
            'target_type', 'PENDING_ACTION',
            'target_id', 'd2030000-0000-4000-8000-000000000041',
            'target_version', 1
        )
    ) #>> '{error,code}',
    'APPROVAL_REQUIRED',
    'CHAT approval rejected on F2 verification'
);

-- UI approval succeeds
select is(
    pg_temp.q_call(
        'verify_question_drafts',
        jsonb_build_object(
            'conversation_id', 'd2030000-0000-4000-8000-000000000003',
            'action_id', 'd2030000-0000-4000-8000-000000000041',
            'expected_action_version', 1,
            'question_ids', jsonb_build_array('d2030000-0000-4000-8000-000000000031'),
            'decision', 'APPROVE'
        ),
        'd2030000-0000-4000-8000-000000000001',
        'f2-b4-ui-approve-001',
        jsonb_build_object(
            'approval_action_id', 'd2030000-0000-4000-8000-000000000051',
            'user_id', 'd2030000-0000-4000-8000-000000000001',
            'target_type', 'PENDING_ACTION',
            'target_id', 'd2030000-0000-4000-8000-000000000041',
            'target_version', 1,
            'decision', 'APPROVE',
            'source', 'UI',
            'source_message_id', null,
            'created_at', '2026-11-16T08:03:00Z'
        ),
        jsonb_build_object(
            'action_id', 'd2030000-0000-4000-8000-000000000041',
            'action_version', 1,
            'target_type', 'PENDING_ACTION',
            'target_id', 'd2030000-0000-4000-8000-000000000041',
            'target_version', 1
        )
    ) ->> 'outcome',
    'COMMITTED',
    'UI APPROVE promotes question_drafts to VERIFIED'
);

-- Subsequent reject on already-decided batch fails with STALE_ENTITY_VERSION
select is(
    pg_temp.q_call(
        'verify_question_drafts',
        jsonb_build_object(
            'conversation_id', 'd2030000-0000-4000-8000-000000000003',
            'action_id', 'd2030000-0000-4000-8000-000000000041',
            'expected_action_version', 1,
            'question_ids', jsonb_build_array('d2030000-0000-4000-8000-000000000031'),
            'decision', 'REJECT'
        ),
        'd2030000-0000-4000-8000-000000000001',
        'f2-b4-ui-reject-002',
        jsonb_build_object(
            'approval_action_id', 'd2030000-0000-4000-8000-000000000052',
            'user_id', 'd2030000-0000-4000-8000-000000000001',
            'target_type', 'PENDING_ACTION',
            'target_id', 'd2030000-0000-4000-8000-000000000041',
            'target_version', 1,
            'decision', 'REJECT',
            'source', 'UI',
            'source_message_id', null,
            'created_at', '2026-11-16T08:04:00Z'
        ),
        jsonb_build_object(
            'action_id', 'd2030000-0000-4000-8000-000000000041',
            'action_version', 1,
            'target_type', 'PENDING_ACTION',
            'target_id', 'd2030000-0000-4000-8000-000000000041',
            'target_version', 1
        )
    ) #>> '{error,code}',
    'STALE_ENTITY_VERSION',
    'second concurrent/stale decision fails'
);

-- Immutability triggers block update and delete on VERIFIED question
select throws_ok(
    $$update app_private.question_drafts set stem = 'tampered' where question_id = 'd2030000-0000-4000-8000-000000000031'$$,
    '23514', null, 'VERIFIED question_draft cannot be updated'
);
select throws_ok(
    $$delete from app_private.question_drafts where question_id = 'd2030000-0000-4000-8000-000000000031'$$,
    '23514', null, 'question_draft cannot be deleted'
);

-- list_questions filters by owner & exact padded topic & rejects tampered cursor
select is(
    jsonb_array_length(pg_temp.q_call('list_questions', jsonb_build_object(
        'material_id', null, 'topic', '  Xác suất  ', 'status', 'VERIFIED', 'page_size', 10, 'cursor', null
    )) #> '{data,items}'),
    1,
    'owner sees VERIFIED question via exact padded topic filter in list_questions'
);
select is(
    jsonb_array_length(pg_temp.q_call('list_questions', jsonb_build_object(
        'material_id', null, 'topic', null, 'status', null, 'page_size', 10, 'cursor', null
    ), 'd2030000-0000-4000-8000-000000000002') #> '{data,items}'),
    0,
    'other user sees zero questions'
);
select is(
    pg_temp.q_call('list_questions', jsonb_build_object(
        'material_id', null, 'topic', null, 'status', null, 'page_size', 10, 'cursor', 'tampered'
    )) #>> '{error,code}',
    'INVALID_PARAMETER',
    'tampered cursor rejected'
);

select * from finish();
rollback;
