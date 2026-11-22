-- F3 M1 signed writes and owner-scoped polling over the shared material library.
create or replace function app_private.rpc_is_read(p_routine text) returns boolean
language sql immutable set search_path = '' as $$
    select p_routine in (
        'search_tasks', 'get_study_plan', 'list_time_windows', 'get_scheduling_context', 'lookup_operation_result',
        'get_workflow_context', 'get_workflow_continuation', 'get_ingestion_source',
        'get_assessment_material', 'search_material_chunks', 'list_questions', 'get_quiz_attempt_context',
        'get_topic_stats', 'get_learning_material', 'list_learning_materials'
    )
$$;

create function app_private.learning_material_json(m app_private.materials) returns jsonb
language sql stable set search_path = '' as $$
    select jsonb_build_object(
        'material_id', m.material_id, 'owner_id', m.user_id, 'course_label', m.course_label,
        'filename', m.filename, 'mime_type', m.mime_type, 'sha256', m.sha256, 'byte_size', m.size_bytes,
        'page_count', case when m.learning_status = 'READY' then m.page_count end,
        'status', case when expired then 'FAILED' else m.learning_status end,
        'error_code', case when expired then 'INDEX_TIMEOUT' else m.learning_error end,
        'created_at', app_private.iso(m.created_at)
    )
    from (select coalesce(m.learning_status = 'INDEXING' and m.learning_deadline <= statement_timestamp(), false) as expired) state
$$;

-- The caller holds the owner lock. Finish the original receipt and the status in the same transaction.
create function app_private.finish_learning_material(
    m app_private.materials, p_error text
) returns app_private.materials
language plpgsql set search_path = '' as $$
declare finished app_private.materials;
begin
    update app_private.materials
       set learning_status = case when p_error is null then 'READY' else 'FAILED' end,
           learning_error = p_error, learning_claim = null, learning_deadline = null
     where user_id = m.user_id and material_id = m.material_id and learning_claim = m.learning_claim
     returning * into strict finished;
    update app_private.learning_material_receipts
       set claim = null, response = app_private.learning_material_json(finished)
     where user_id = m.user_id and operation = 'upload' and claim = m.learning_claim;
    if not found then
        raise exception 'Missing material receipt' using errcode = '23514';
    end if;
    return finished;
end
$$;

create function app_api.reserve_learning_material(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'reserve_learning_material', 'ReserveLearningMaterialArguments');
    args jsonb := p_request -> 'arguments';
    uid uuid := app_private.current_uid();
    key text := p_request #>> '{execution_context,idempotency_key}';
    fingerprint text := args ->> 'fingerprint';
    receipt app_private.learning_material_receipts;
    material app_private.materials;
    claim_id uuid;
    claim_allowed boolean := coalesce((args ->> 'claim_allowed')::boolean, true);
    conversation uuid;
    snapshot jsonb;
    topic text := coalesce(args ->> 'course_label', 'Tài liệu học tập');
begin
    if err is not null then return err; end if;
    perform app_private.lock_owner(uid, p_request);
    select r.* into receipt from app_private.learning_material_receipts r
    where r.user_id = uid and r.operation = 'upload' and r.idempotency_key = key;
    if found then
        if receipt.fingerprint <> fingerprint then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'Upload key was used for a different request.');
        end if;
        if receipt.response is null then
            select m.* into strict material from app_private.materials m
            where m.user_id = uid and m.material_id = receipt.material_id;
            if material.learning_deadline > clock_timestamp() then
                return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'Upload is still indexing.', true);
            end if;
            material := app_private.finish_learning_material(material, 'INDEX_TIMEOUT');
            receipt.response := app_private.learning_material_json(material);
        end if;
        return app_private.ok_result(p_request, 'COMMITTED',
            jsonb_build_object('material', receipt.response, 'claim', null, 'replayed', true));
    end if;

    select m.* into material from app_private.materials m
    where m.user_id = uid and m.sha256 = args ->> 'sha256'
      and m.size_bytes <= 5242880 and m.page_count <= 50
      and (m.learning_status is not null or m.status = 'READY')
    order by (m.learning_status is not distinct from 'READY') desc,
             (m.learning_status is not null) desc, m.created_at, m.material_id
    limit 1;
    if material.learning_status = 'INDEXING' and material.learning_deadline <= clock_timestamp() then
        if not claim_allowed then
            return app_private.error_result(p_request, 'SERVICE_UNAVAILABLE', 'Material index worker is busy.', true);
        end if;
        material := app_private.finish_learning_material(material, 'INDEX_TIMEOUT');
    end if;
    if material.learning_status in ('UPLOADED','INDEXING','READY') or material.learning_error = 'INVALID_DOCUMENT' then
        snapshot := app_private.learning_material_json(material);
        insert into app_private.learning_material_receipts(user_id, operation, idempotency_key, fingerprint, material_id, response)
        values (uid, 'upload', key, fingerprint, material.material_id, snapshot);
        return app_private.ok_result(p_request, 'COMMITTED',
            jsonb_build_object('material', snapshot, 'claim', null, 'replayed', false));
    end if;
    if material.learning_status is null and (
        select count(*) from app_private.materials m where m.user_id = uid and m.learning_status is not null
    ) >= 20 then
        return app_private.error_result(p_request, 'TIME_CONFLICT', 'F3 material quota reached.');
    end if;

    if not claim_allowed then
        return app_private.error_result(p_request, 'SERVICE_UNAVAILABLE', 'Material index worker is busy.', true);
    end if;
    claim_id := gen_random_uuid();
    if material.material_id is null then
        conversation := gen_random_uuid();
        insert into app_private.conversation_records(user_id, conversation_id) values (uid, conversation);
        -- Assessment can see new F3 materials after the atomic publish below.
        insert into app_private.materials(user_id, conversation_id, material_id, filename, mime_type, size_bytes,
            sha256, page_count, char_count, topics, upload_fingerprint, course_label, learning_origin,
            learning_status, learning_claim, learning_deadline)
        values (uid, conversation, gen_random_uuid(), args ->> 'filename', args ->> 'mime_type',
            (args ->> 'byte_size')::integer, args ->> 'sha256', 1, 1, jsonb_build_array(topic),
            fingerprint, args ->> 'course_label', true, 'INDEXING', claim_id, clock_timestamp() + interval '120 seconds')
        returning * into material;
    else
        update app_private.materials m
           set course_label = case when m.learning_status is null then args ->> 'course_label' else m.course_label end,
               learning_status = 'INDEXING', learning_error = null, learning_claim = claim_id,
               learning_deadline = clock_timestamp() + interval '120 seconds'
         where m.user_id = uid and m.material_id = material.material_id returning m.* into material;
    end if;
    insert into app_private.learning_material_receipts(user_id, operation, idempotency_key, fingerprint, material_id, claim)
    values (uid, 'upload', key, fingerprint, material.material_id, claim_id);
    return app_private.ok_result(p_request, 'COMMITTED', jsonb_build_object(
        'material', app_private.learning_material_json(material), 'claim', claim_id, 'replayed', false));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

create function app_api.store_learning_material_chunks(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'store_learning_material_chunks', 'StoreLearningChunksArguments');
    args jsonb := p_request -> 'arguments';
    uid uuid := app_private.current_uid();
    material app_private.materials;
    item jsonb;
    page_number integer;
    ordinal integer;
    vector_value extensions.vector(384);
    page_count integer;
    matched_chunk uuid;
begin
    if err is not null then return err; end if;
    page_count := (args ->> 'page_count')::integer;
    perform app_private.lock_owner(uid, p_request);
    select m.* into material from app_private.materials m
    where m.user_id = uid and m.material_id = (args ->> 'material_id')::uuid;
    if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Material not found.');
    end if;
    if material.learning_claim is distinct from (args ->> 'claim')::uuid then
        return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Material index claim has changed.');
    end if;
    if material.learning_deadline <= clock_timestamp() then
        material := app_private.finish_learning_material(material, 'INDEX_TIMEOUT');
        return app_private.ok_result(p_request, 'COMMITTED', app_private.learning_material_json(material));
    end if;

    if material.status = 'READY' and material.page_count <> page_count then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Page count differs from the stored material.');
    end if;
    if exists (
        select 1 from jsonb_array_elements(args -> 'assessment_chunks') with ordinality as c(item, n)
        where (c.item ->> 'chunk_index')::integer <> c.n - 1 or (c.item ->> 'page')::integer > page_count
    ) or exists (
        select 1 from jsonb_array_elements(args -> 'learning_chunks') with ordinality as c(item, n)
        where (c.item ->> 'chunk_index')::integer <> c.n - 1 or (c.item ->> 'page')::integer > page_count
           or abs(extensions.vector_norm((c.item ->> 'embedding')::extensions.vector(384)) - 1) > 0.0001
    ) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Invalid material chunk ordering, page or embedding.');
    end if;
    if (select count(distinct c ->> 'page') from jsonb_array_elements(args -> 'learning_chunks') c) <> page_count
       or (select count(distinct c ->> 'page') from jsonb_array_elements(args -> 'assessment_chunks') c) <> page_count then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Material chunks must cover every extracted page.');
    end if;

    if material.learning_origin and material.status <> 'READY' then
        update app_private.materials m set page_count = (args ->> 'page_count')::integer,
                char_count = (args ->> 'char_count')::integer, updated_at = clock_timestamp()
         where m.user_id = uid and m.material_id = material.material_id;
        insert into app_private.material_chunks(chunk_id, material_id, user_id, page, topic, chunk_index, text, created_at)
        select gen_random_uuid(), material.material_id, uid, (c ->> 'page')::integer, material.topics ->> 0,
               (c ->> 'chunk_index')::integer, c ->> 'text', clock_timestamp()
        from jsonb_array_elements(args -> 'assessment_chunks') c;
    end if;

    for item in select value from jsonb_array_elements(args -> 'learning_chunks') loop
        page_number := (item ->> 'page')::integer;
        ordinal := (item ->> 'chunk_index')::integer;
        vector_value := (item ->> 'embedding')::extensions.vector(384);
        select c.chunk_id into matched_chunk from app_private.material_chunks c
        where c.user_id = uid and c.material_id = material.material_id and c.profile = 'assessment'
          and c.page = page_number and c.text = item ->> 'text' and c.learning_ordinal is null
        order by c.chunk_index limit 1;
        if matched_chunk is not null then
            update app_private.material_chunks c
               set learning_ordinal = ordinal, embedding = vector_value, embedding_model = 'intfloat/multilingual-e5-small'
             where c.user_id = uid and c.chunk_id = matched_chunk;
        else
            insert into app_private.material_chunks(chunk_id, material_id, user_id, page, topic, profile, chunk_index,
                text, created_at, learning_ordinal, embedding, embedding_model)
            values (gen_random_uuid(), material.material_id, uid, page_number, material.topics ->> 0, 'learning',
                ordinal, item ->> 'text', clock_timestamp(), ordinal, vector_value, 'intfloat/multilingual-e5-small');
        end if;
    end loop;
    if material.learning_origin and material.status <> 'READY' then
        update app_private.materials m set status = 'READY', updated_at = clock_timestamp()
        where m.user_id = uid and m.material_id = material.material_id;
    end if;
    material := app_private.finish_learning_material(material, null);
    return app_private.ok_result(p_request, 'COMMITTED', app_private.learning_material_json(material));
exception
    when data_exception then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Invalid material chunk or embedding.');
    when others then
        return app_private.failure(p_request, sqlstate);
end
$$;

create function app_api.fail_learning_material(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'fail_learning_material', 'FailLearningMaterialArguments');
    args jsonb := p_request -> 'arguments';
    uid uuid := app_private.current_uid();
    material app_private.materials;
begin
    if err is not null then return err; end if;
    perform app_private.lock_owner(uid, p_request);
    select m.* into material from app_private.materials m
    where m.user_id = uid and m.material_id = (args ->> 'material_id')::uuid;
    if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Material not found.');
    end if;
    if material.learning_claim is distinct from (args ->> 'claim')::uuid then
        return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Material index claim has changed.');
    end if;
    material := app_private.finish_learning_material(material, case
        when material.learning_deadline <= clock_timestamp() then 'INDEX_TIMEOUT' else args ->> 'error_code' end);
    return app_private.ok_result(p_request, 'COMMITTED', app_private.learning_material_json(material));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

create function app_api.get_learning_material(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'get_learning_material', 'LearningMaterialLookupArguments');
    snapshot jsonb;
begin
    if err is not null then return err; end if;
    select app_private.learning_material_json(m) into snapshot from app_private.materials m
    where m.user_id = app_private.current_uid() and m.learning_status is not null
      and m.material_id = (p_request #>> '{arguments,material_id}')::uuid;
    if not found then return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Material not found.'); end if;
    return app_private.ok_result(p_request, 'READ', snapshot);
end
$$;

create function app_api.list_learning_materials(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'list_learning_materials', 'ListLearningMaterialsArguments');
    args jsonb := p_request -> 'arguments';
    page_limit integer;
    before_at timestamptz;
    before_id uuid;
    result jsonb;
begin
    if err is not null then return err; end if;
    page_limit := (args ->> 'limit')::integer;
    before_at := (args ->> 'before_created_at')::timestamptz;
    before_id := (args ->> 'before_material_id')::uuid;
    if (before_at is null) <> (before_id is null) then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Incomplete material cursor.');
    end if;
    select jsonb_build_object(
        'materials', coalesce(jsonb_agg(s.snapshot order by s.created_at desc, s.material_id desc)
                              filter (where s.ordinal <= page_limit), '[]'::jsonb),
        'has_more', count(*) > page_limit
    ) into result
    from (
        select app_private.learning_material_json(m) as snapshot, m.created_at, m.material_id,
               row_number() over (order by m.created_at desc, m.material_id desc) as ordinal
        from app_private.materials m
        where m.user_id = app_private.current_uid() and m.learning_status is not null
          and (before_at is null or (m.created_at, m.material_id) < (before_at, before_id))
        order by m.created_at desc, m.material_id desc limit page_limit + 1
    ) s;
    return app_private.ok_result(p_request, 'READ', result);
end
$$;

create function app_api.delete_learning_material(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'delete_learning_material', 'DeleteLearningMaterialArguments');
    args jsonb := p_request -> 'arguments';
    uid uuid := app_private.current_uid();
    key text := p_request #>> '{execution_context,idempotency_key}';
    fingerprint text := args ->> 'fingerprint';
    receipt app_private.learning_material_receipts;
    material app_private.materials;
    result jsonb;
begin
    if err is not null then return err; end if;
    perform app_private.lock_owner(uid, p_request);
    select r.* into receipt from app_private.learning_material_receipts r
    where r.user_id = uid and r.operation = 'delete' and r.idempotency_key = key;
    if found then
        if receipt.fingerprint <> fingerprint then
            return app_private.error_result(p_request, 'IDEMPOTENCY_CONFLICT', 'Delete key was used for a different request.');
        end if;
        if receipt.response ->> 'outcome' = 'ERROR' then
            return receipt.response || jsonb_build_object('request_id', p_request ->> 'request_id');
        end if;
        return app_private.ok_result(p_request, 'COMMITTED', receipt.response || jsonb_build_object('replayed', true));
    end if;
    select m.* into material from app_private.materials m
    where m.user_id = uid and m.material_id = (args ->> 'material_id')::uuid and m.learning_status is not null
    for update;
    if not found then return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Material not found.'); end if;
    if material.learning_status = 'INDEXING' then
        if material.learning_deadline > clock_timestamp() then
            return app_private.error_result(p_request, 'TIME_CONFLICT', 'Material is still indexing.', true);
        end if;
        material := app_private.finish_learning_material(material, 'INDEX_TIMEOUT');
    end if;
    begin
        delete from app_private.material_chunks c where c.user_id = uid and c.material_id = material.material_id;
        delete from app_private.materials m where m.user_id = uid and m.material_id = material.material_id;
        result := jsonb_build_object('material_id', material.material_id, 'deleted', true);
    exception when foreign_key_violation then
        err := app_private.error_result(p_request, 'TIME_CONFLICT', 'Tài liệu đang được Assessment sử dụng.');
        result := jsonb_set(jsonb_set(err, '{error,details}', '{"reason":"MATERIAL_IN_USE"}'::jsonb),
                            '{error,field}', '"material_id"'::jsonb);
    end;
    insert into app_private.learning_material_receipts(user_id, operation, idempotency_key, fingerprint, material_id, response)
    values (uid, 'delete', key, fingerprint, material.material_id, result);
    if result ->> 'outcome' = 'ERROR' then return result; end if;
    return app_private.ok_result(p_request, 'COMMITTED', result || jsonb_build_object('replayed', false));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

alter function app_private.learning_material_json(app_private.materials) owner to sf_rpc_owner;
alter function app_private.finish_learning_material(app_private.materials, text) owner to sf_rpc_owner;
revoke all on function app_private.learning_material_json(app_private.materials),
    app_private.finish_learning_material(app_private.materials, text) from public, anon, authenticated;
do $$
declare routine text;
begin
    foreach routine in array array['reserve_learning_material','store_learning_material_chunks',
        'fail_learning_material','get_learning_material','list_learning_materials','delete_learning_material'] loop
        execute format('alter function app_api.%I(jsonb) owner to sf_rpc_owner', routine);
        execute format('revoke all on function app_api.%I(jsonb) from public, anon', routine);
        execute format('grant execute on function app_api.%I(jsonb) to authenticated', routine);
    end loop;
end
$$;
