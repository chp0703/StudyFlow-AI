-- F3 M2 + M3: learning sessions, hybrid retrieval (cosine + FTS via RRF), and grounded turns/hints.
create table app_private.learning_session_receipts (
    user_id uuid not null references app_private.user_profiles(user_id),
    operation text not null check (operation in ('create_session', 'add_turn')),
    idempotency_key text not null check (idempotency_key ~ '^[A-Za-z0-9._:-]{16,128}$'),
    fingerprint text not null check (fingerprint ~ '^[0-9a-f]{64}$'),
    session_id uuid not null,
    response jsonb not null,
    created_at timestamptz not null default clock_timestamp(),
    primary key (user_id, operation, idempotency_key)
);

alter table app_private.learning_session_receipts enable row level security;
alter table app_private.learning_session_receipts force row level security;
revoke all on app_private.learning_session_receipts from public, anon, authenticated;
create policy learning_session_receipts_owner on app_private.learning_session_receipts to sf_rpc_owner
    using (user_id = app_private.current_uid())
    with check (user_id = app_private.current_uid());

grant select, insert on app_private.learning_session_receipts to sf_rpc_owner;
grant insert, update on app_private.learning_session to sf_rpc_owner;
grant insert on app_private.learning_turn to sf_rpc_owner;

create index ix_learning_turn_session_ordinal
    on app_private.learning_turn (user_id, session_id, ordinal);
create index ix_material_chunks_learning_owner_mat
    on app_private.material_chunks (user_id, material_id, learning_ordinal)
    where learning_ordinal is not null;

create or replace function app_private.rpc_is_read(p_routine text) returns boolean
language sql immutable set search_path = '' as $$
    select p_routine in (
        'search_tasks', 'get_study_plan', 'list_time_windows', 'get_scheduling_context', 'lookup_operation_result',
        'get_workflow_context', 'get_workflow_continuation', 'get_ingestion_source',
        'get_assessment_material', 'search_material_chunks', 'list_questions', 'get_quiz_attempt_context',
        'get_topic_stats', 'get_learning_material', 'list_learning_materials',
        'get_learning_session', 'lookup_learning_turn_receipt', 'search_learning_material_chunks'
    )
$$;

create function app_private.learning_session_json(s app_private.learning_session) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object(
        'session_id', s.session_id,
        'owner_id', s.user_id,
        'conversation_id', s.conversation_id,
        'goal', s.goal,
        'material_ids', to_jsonb(s.material_ids),
        'planner_block_id', s.planner_block_id,
        'status', s.status,
        'version', s.version,
        'created_at', app_private.iso(s.created_at),
        'expires_at', app_private.iso(s.expires_at)
    )
$$;

create function app_private.learning_citations_json(p_uid uuid, p_citations jsonb) returns jsonb
language sql stable set search_path = '' as $$
    select coalesce(
        jsonb_agg(
            jsonb_build_object(
                'chunk_id', (c.item ->> 'chunk_id')::uuid,
                'material_id', (c.item ->> 'material_id')::uuid,
                'page', (c.item ->> 'page')::integer,
                'material_deleted', not exists (
                    select 1 from app_private.materials m
                    where m.user_id = p_uid and m.material_id = (c.item ->> 'material_id')::uuid
                )
            )
            order by c.ord
        ),
        '[]'::jsonb
    )
    from jsonb_array_elements(p_citations) with ordinality as c(item, ord)
$$;

create function app_private.learning_turn_json(t app_private.learning_turn) returns jsonb
language sql stable set search_path = '' as $$
    select jsonb_build_object(
        'turn_id', t.turn_id,
        'session_id', t.session_id,
        'owner_id', t.user_id,
        'ordinal', t.ordinal,
        'role', t.role,
        'kind', t.kind,
        'hint_level', t.hint_level,
        'content', t.content,
        'citations', app_private.learning_citations_json(t.user_id, t.citations),
        'supported', t.supported,
        'model', t.model,
        'prompt_version', t.prompt_version
    )
$$;

create function app_api.create_learning_session(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'create_learning_session', 'CreateLearningSessionArguments');
    args jsonb := p_request -> 'arguments';
    uid uuid := app_private.current_uid();
    key text := p_request #>> '{execution_context,idempotency_key}';
    fingerprint text := args ->> 'fingerprint';
    receipt app_private.learning_session_receipts;
    v_material_ids uuid[];
    v_distinct_count integer;
    v_owned_count integer;
    v_ready_count integer;
    v_block_id uuid;
    v_conversation uuid;
    v_now timestamptz;
    v_session app_private.learning_session;
    v_snapshot jsonb;
begin
    if err is not null then return err; end if;
    if key is null or key !~ '^[A-Za-z0-9._:-]{16,128}$' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'A valid idempotency key is required.');
    end if;

    select array_agg(x.val::uuid order by x.ord), count(distinct x.val::uuid)
    into v_material_ids, v_distinct_count
    from jsonb_array_elements_text(args -> 'material_ids') with ordinality as x(val, ord);

    if v_material_ids is null or cardinality(v_material_ids) not between 1 and 5
       or v_distinct_count <> cardinality(v_material_ids) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Select between 1 and 5 unique materials.');
    end if;

    v_block_id := (args ->> 'planner_block_id')::uuid;

    perform app_private.lock_owner(uid, p_request);

    select r.* into receipt from app_private.learning_session_receipts r
    where r.user_id = uid and r.operation = 'create_session' and r.idempotency_key = key;
    if found then
        if receipt.fingerprint <> fingerprint then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'Session key was used for a different request.');
        end if;
        return app_private.ok_result(p_request, 'COMMITTED',
            jsonb_build_object('session', receipt.response, 'replayed', true));
    end if;

    select count(*), count(*) filter (where m.learning_status = 'READY')
    into v_owned_count, v_ready_count
    from app_private.materials m
    where m.user_id = uid and m.material_id = any(v_material_ids) and m.learning_status is not null;

    if v_owned_count <> cardinality(v_material_ids) then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Material not found.');
    end if;
    if v_ready_count <> cardinality(v_material_ids) then
        err := app_private.error_result(p_request, 'TIME_CONFLICT', 'Tài liệu chưa sẵn sàng để bắt đầu phiên học.');
        return jsonb_set(jsonb_set(err, '{error,details}', '{"reason":"MATERIAL_NOT_READY"}'::jsonb),
                         '{error,field}', '"material_ids"'::jsonb);
    end if;

    if v_block_id is not null and not exists (
        select 1 from app_private.study_blocks b where b.user_id = uid and b.block_id = v_block_id
    ) then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Planner block not found.');
    end if;

    v_conversation := gen_random_uuid();
    v_now := clock_timestamp();
    insert into app_private.conversation_records(user_id, conversation_id) values (uid, v_conversation);
    insert into app_private.learning_session(
        user_id, conversation_id, goal, material_ids, planner_block_id, status, version, created_at, expires_at
    ) values (
        uid, v_conversation, args ->> 'goal', v_material_ids, v_block_id, 'ACTIVE', 1, v_now, v_now + interval '30 days'
    ) returning * into v_session;

    v_snapshot := app_private.learning_session_json(v_session);
    insert into app_private.learning_session_receipts(user_id, operation, idempotency_key, fingerprint, session_id, response)
    values (uid, 'create_session', key, fingerprint, v_session.session_id, v_snapshot);

    return app_private.ok_result(p_request, 'COMMITTED',
        jsonb_build_object('session', v_snapshot, 'replayed', false));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

create function app_api.get_learning_session(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'get_learning_session', 'GetLearningSessionArguments');
    uid uuid := app_private.current_uid();
    v_session app_private.learning_session;
    v_turns jsonb;
begin
    if err is not null then return err; end if;
    select s.* into v_session from app_private.learning_session s
    where s.user_id = uid and s.session_id = (p_request #>> '{arguments,session_id}')::uuid;
    if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Learning session not found.');
    end if;
    select coalesce(jsonb_agg(app_private.learning_turn_json(t) order by t.ordinal asc), '[]'::jsonb)
    into v_turns
    from app_private.learning_turn t
    where t.user_id = uid and t.session_id = v_session.session_id;
    return app_private.ok_result(p_request, 'READ', jsonb_build_object(
        'session', app_private.learning_session_json(v_session),
        'turns', v_turns
    ));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

create function app_api.lookup_learning_turn_receipt(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'lookup_learning_turn_receipt', 'LookupLearningTurnReceiptArguments');
    args jsonb := p_request -> 'arguments';
    uid uuid := app_private.current_uid();
    receipt app_private.learning_session_receipts;
begin
    if err is not null then return err; end if;
    select r.* into receipt from app_private.learning_session_receipts r
    where r.user_id = uid and r.operation = 'add_turn' and r.idempotency_key = args ->> 'idempotency_key';
    if not found then
        return app_private.ok_result(p_request, 'READ', jsonb_build_object('found', false, 'data', null));
    end if;
    if receipt.fingerprint <> args ->> 'fingerprint'
       or receipt.session_id <> (args ->> 'session_id')::uuid then
        return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'Turn key was used for a different request.');
    end if;
    return app_private.ok_result(p_request, 'READ', jsonb_build_object('found', true, 'data', receipt.response));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

create function app_api.search_learning_material_chunks(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'search_learning_material_chunks', 'SearchLearningMaterialChunksArguments');
    args jsonb := p_request -> 'arguments';
    uid uuid := app_private.current_uid();
    v_session app_private.learning_session;
    v_emb extensions.vector(384);
    v_k integer;
    v_pool integer;
    v_query_text text;
    v_fts_query tsquery := null;
    v_tok text;
    v_part tsquery;
    v_chunks jsonb;
begin
    if err is not null then return err; end if;
    select s.* into v_session from app_private.learning_session s
    where s.user_id = uid and s.session_id = (args ->> 'session_id')::uuid;
    if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Learning session not found.');
    end if;

    v_emb := (args ->> 'query_embedding')::extensions.vector(384);
    if abs(extensions.vector_norm(v_emb) - 1) > 0.0001 then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Query embedding must be L2-normalized.');
    end if;

    v_k := (args ->> 'k')::integer;
    v_pool := greatest(v_k * 3, 20);
    v_query_text := args ->> 'query_text';

    for v_tok in
        select distinct tok
        from unnest(tsvector_to_array(to_tsvector('simple'::regconfig, v_query_text))) as tok
        where length(tok) >= 2
        order by tok
        limit 32
    loop
        v_part := plainto_tsquery('simple'::regconfig, v_tok);
        if v_part is not null and v_part::text <> '' then
            v_fts_query := case when v_fts_query is null then v_part else v_fts_query || v_part end;
        end if;
    end loop;
    if v_fts_query is null then
        v_fts_query := plainto_tsquery('simple'::regconfig, v_query_text);
        if v_fts_query::text = '' then
            v_fts_query := null;
        end if;
    end if;

    with eligible as (
        select c.chunk_id, c.material_id, c.page, c.learning_ordinal, c.text, c.embedding, c.search_vector
        from app_private.material_chunks c
        join app_private.materials m
          on m.user_id = c.user_id and m.material_id = c.material_id
        where c.user_id = uid
          and c.material_id = any(v_session.material_ids)
          and c.learning_ordinal is not null
          and c.embedding is not null
          and m.learning_status = 'READY'
    ),
    dense as (
        select e.chunk_id,
               row_number() over (
                   order by e.embedding operator(extensions.<=>) v_emb asc, e.material_id, e.learning_ordinal
               ) as r_dense
        from eligible e
        order by e.embedding operator(extensions.<=>) v_emb asc, e.material_id, e.learning_ordinal
        limit v_pool
    ),
    lexical as (
        select e.chunk_id,
               ts_rank_cd(e.search_vector, v_fts_query)::double precision as fts_rank,
               row_number() over (
                   order by ts_rank_cd(e.search_vector, v_fts_query) desc, e.material_id, e.learning_ordinal
               ) as r_fts
        from eligible e
        where v_fts_query is not null and e.search_vector @@ v_fts_query
        order by ts_rank_cd(e.search_vector, v_fts_query) desc, e.material_id, e.learning_ordinal
        limit v_pool
    ),
    fused as (
        select coalesce(d.chunk_id, l.chunk_id) as chunk_id,
               coalesce(1.0::double precision / (60.0 + d.r_dense), 0.0::double precision)
               + coalesce(1.0::double precision / (60.0 + l.r_fts), 0.0::double precision) as rrf_score,
               coalesce(l.fts_rank, 0.0::double precision) as fts_rank
        from dense d
        full outer join lexical l on l.chunk_id = d.chunk_id
    ),
    ranked as (
        select e.chunk_id,
               e.material_id,
               e.page,
               (e.learning_ordinal + 1)::bigint as ordinal,
               e.text,
               least(1.0::double precision,
                     greatest(-1.0::double precision, 1.0 - (e.embedding operator(extensions.<=>) v_emb))) as cosine_similarity,
               f.fts_rank,
               f.rrf_score
        from fused f
        join eligible e on e.chunk_id = f.chunk_id
        order by f.rrf_score desc, cosine_similarity desc, e.material_id, e.learning_ordinal
        limit v_k
    )
    select coalesce(
        jsonb_agg(
            jsonb_build_object(
                'chunk_id', r.chunk_id,
                'material_id', r.material_id,
                'page', r.page,
                'ordinal', r.ordinal,
                'text', r.text,
                'cosine_similarity', r.cosine_similarity,
                'fts_rank', r.fts_rank,
                'rrf_score', r.rrf_score
            )
            order by r.rrf_score desc, r.cosine_similarity desc, r.material_id, r.ordinal
        ),
        '[]'::jsonb
    )
    into v_chunks
    from ranked r;

    return app_private.ok_result(p_request, 'READ', jsonb_build_object(
        'session_id', v_session.session_id,
        'chunks', v_chunks
    ));
exception
    when data_exception then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Invalid query embedding.');
    when others then
        return app_private.failure(p_request, sqlstate);
end
$$;

create function app_api.append_learning_turn(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'append_learning_turn', 'AppendLearningTurnArguments');
    args jsonb := p_request -> 'arguments';
    uid uuid := app_private.current_uid();
    key text := p_request #>> '{execution_context,idempotency_key}';
    v_session_id uuid := (args ->> 'session_id')::uuid;
    fingerprint text := args ->> 'fingerprint';
    receipt app_private.learning_session_receipts;
    v_session app_private.learning_session;
    v_last_ordinal bigint;
    v_kind text := args ->> 'kind';
    v_hint_level integer := (args ->> 'hint_level')::integer;
    v_supported boolean := (args ->> 'supported')::boolean;
    v_citations jsonb := args -> 'citations';
    v_item jsonb;
    v_cit_mat uuid;
    v_cit_chunk uuid;
    v_cit_page integer;
    v_user_turn app_private.learning_turn;
    v_assistant_turn app_private.learning_turn;
    v_pair jsonb;
begin
    if err is not null then return err; end if;
    if key is null or key !~ '^[A-Za-z0-9._:-]{16,128}$' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'A valid idempotency key is required.');
    end if;

    if (v_kind = 'ASK' and v_hint_level is not null)
       or (v_kind = 'HINT' and (v_hint_level is null or v_hint_level not between 1 and 3))
       or (v_supported and jsonb_array_length(v_citations) < 1)
       or (not v_supported and jsonb_array_length(v_citations) > 0) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Turn invariants violated.');
    end if;

    perform app_private.lock_owner(uid, p_request);

    select r.* into receipt from app_private.learning_session_receipts r
    where r.user_id = uid and r.operation = 'add_turn' and r.idempotency_key = key;
    if found then
        if receipt.fingerprint <> fingerprint or receipt.session_id <> v_session_id then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'Turn key was used for a different request.');
        end if;
        return app_private.ok_result(p_request, 'COMMITTED',
            receipt.response || jsonb_build_object('replayed', true));
    end if;

    select s.* into v_session from app_private.learning_session s
    where s.user_id = uid and s.session_id = v_session_id
    for update;
    if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Learning session not found.');
    end if;
    if v_session.status <> 'ACTIVE' then
        err := app_private.error_result(p_request, 'TIME_CONFLICT', 'Phiên học không còn ở trạng thái hoạt động.');
        return jsonb_set(err, '{error,details}', jsonb_build_object('status', v_session.status));
    end if;

    select coalesce(max(t.ordinal), 0) into v_last_ordinal
    from app_private.learning_turn t
    where t.user_id = uid and t.session_id = v_session_id;
    if v_last_ordinal <> (args ->> 'expected_last_ordinal')::bigint then
        return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Phiên học đã có lượt mới, hãy thử lại.', true);
    end if;

    -- Validate citations before any write: all cited materials must belong to this session and match indexed chunks.
    if (select count(distinct (c ->> 'chunk_id')::uuid) from jsonb_array_elements(v_citations) c)
       <> jsonb_array_length(v_citations) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Duplicate citation chunk_id.');
    end if;
    for v_item in select value from jsonb_array_elements(v_citations) loop
        v_cit_mat := (v_item ->> 'material_id')::uuid;
        v_cit_chunk := (v_item ->> 'chunk_id')::uuid;
        v_cit_page := (v_item ->> 'page')::integer;
        if not (v_cit_mat = any(v_session.material_ids)) then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Citation material is not in the session.');
        end if;
        if exists (select 1 from app_private.materials m where m.user_id = uid and m.material_id = v_cit_mat)
           and not exists (
               select 1 from app_private.material_chunks c
               where c.user_id = uid and c.material_id = v_cit_mat and c.chunk_id = v_cit_chunk
                 and c.page = v_cit_page and c.learning_ordinal is not null
           ) then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Citation chunk does not match indexed material.');
        end if;
    end loop;

    insert into app_private.learning_turn(
        user_id, session_id, ordinal, role, kind, hint_level, content, citations, supported, model, prompt_version
    ) values (
        uid, v_session_id, v_last_ordinal + 1, 'USER', v_kind, null, args ->> 'user_content',
        '[]'::jsonb, null, null, null
    ) returning * into v_user_turn;

    insert into app_private.learning_turn(
        user_id, session_id, ordinal, role, kind, hint_level, content, citations, supported, model, prompt_version
    ) values (
        uid, v_session_id, v_last_ordinal + 2, 'ASSISTANT', v_kind, v_hint_level, args ->> 'assistant_content',
        v_citations, v_supported, args ->> 'model', args ->> 'prompt_version'
    ) returning * into v_assistant_turn;

    update app_private.learning_session
       set version = version + 1,
           expires_at = greatest(expires_at, clock_timestamp() + interval '30 days')
     where user_id = uid and session_id = v_session_id;

    v_pair := jsonb_build_object(
        'user_turn', app_private.learning_turn_json(v_user_turn),
        'assistant_turn', app_private.learning_turn_json(v_assistant_turn)
    );

    insert into app_private.learning_session_receipts(user_id, operation, idempotency_key, fingerprint, session_id, response)
    values (uid, 'add_turn', key, fingerprint, v_session_id, v_pair);

    return app_private.ok_result(p_request, 'COMMITTED', v_pair || jsonb_build_object('replayed', false));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

alter function app_private.learning_session_json(app_private.learning_session) owner to sf_rpc_owner;
alter function app_private.learning_citations_json(uuid, jsonb) owner to sf_rpc_owner;
alter function app_private.learning_turn_json(app_private.learning_turn) owner to sf_rpc_owner;
revoke all on function app_private.learning_session_json(app_private.learning_session),
    app_private.learning_citations_json(uuid, jsonb),
    app_private.learning_turn_json(app_private.learning_turn) from public, anon, authenticated;

do $$
declare routine text;
begin
    foreach routine in array array[
        'create_learning_session',
        'get_learning_session',
        'lookup_learning_turn_receipt',
        'search_learning_material_chunks',
        'append_learning_turn'
    ] loop
        execute format('alter function app_api.%I(jsonb) owner to sf_rpc_owner', routine);
        execute format('revoke all on function app_api.%I(jsonb) from public, anon', routine);
        execute format('grant execute on function app_api.%I(jsonb) to authenticated', routine);
    end loop;
end
$$;
