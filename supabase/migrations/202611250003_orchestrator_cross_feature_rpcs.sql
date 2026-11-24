-- Orchestrator P1: let chat reuse F3 learning materials and bind learning sessions to a chat conversation.
-- Bodies are the deployed definitions with the minimal edits noted per function; owners and grants are preserved by CREATE OR REPLACE.

-- F3 materials (learning_status READY) may back question drafts created in any of the owner's conversations.
CREATE OR REPLACE FUNCTION app_api.create_question_drafts(p_request jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
    v_error jsonb := app_private.precheck(p_request, 'create_question_drafts', 'CreateQuestionDraftsArguments');
    v_uid uuid;
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_conv uuid := (p_request #>> '{execution_context,conversation_id}')::uuid;
    v_args jsonb := p_request -> 'arguments';
    v_material_id uuid;
    v_action_id uuid;
    v_fp_input jsonb;
    v_fp text;
    v_reply jsonb;
    v_material app_private.materials;
    v_draft jsonb;
    v_opt_ids text[];
    v_distinct_opts int;
    v_opt_count int;
    v_chunk_count int;
    v_qid uuid;
    v_chunk_id uuid;
    v_idx int;
    v_src_idx int;
    v_qids jsonb := '[]'::jsonb;
    v_items jsonb := '[]'::jsonb;
    v_source_chunks jsonb := '[]'::jsonb;
    v_action app_private.pending_actions;
    v_pres jsonb;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null or v_conv is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key and conversation are required.');
    end if;
    if v_args ->> 'conversation_id' is distinct from v_conv::text then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Conversation does not match execution_context.');
    end if;
    v_material_id := (v_args ->> 'material_id')::uuid;
    if v_args ? 'generation_params' then
        v_fp_input := jsonb_build_object(
            'conversation_id', v_args -> 'conversation_id',
            'material_id', v_args -> 'material_id',
            'generation_params', v_args -> 'generation_params'
        );
    else
        v_fp_input := v_args;
    end if;
    v_fp := app_private.domain_fingerprint(v_uid, 'create_question_drafts', v_fp_input);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'create_question_drafts', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'create_question_drafts', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;

        select * into v_material from app_private.materials
        where material_id = v_material_id and user_id = v_uid and (conversation_id = v_conv or learning_status = 'READY') and status = 'READY';
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Material not found.');
        end if;

        if exists (
            select 1 from app_private.pending_actions x
            where x.user_id = v_uid and x.conversation_id = v_conv
              and x.state in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL')
        ) then
            return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED',
                'The conversation already has an awaiting action; review or cancel it first.');
        end if;

        -- Validate all draft invariants before writing any rows.
        for v_draft in select value from jsonb_array_elements(v_args -> 'drafts') loop
            if v_draft ->> 'user_id' is distinct from v_uid::text
               or v_draft ->> 'conversation_id' is distinct from v_conv::text
               or v_draft ->> 'material_id' is distinct from v_material_id::text
               or v_draft ->> 'status' is distinct from 'DRAFT'
               or (v_draft ->> 'version')::bigint is distinct from 1
               or (v_draft -> 'verified_at') is distinct from 'null'::jsonb then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'Draft metadata must match owner, conversation, material, and initial DRAFT state.');
            end if;
            if not (v_material.topics ? (v_draft ->> 'topic')) then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'Draft topic does not belong to the material.');
            end if;

            select array_agg(o ->> 'option_id' order by ord), count(distinct o ->> 'option_id'), count(*)
            into v_opt_ids, v_distinct_opts, v_opt_count
            from jsonb_array_elements(v_draft -> 'options') with ordinality as x(o, ord);
            if v_opt_count is null or v_opt_count not between 2 and 6 or v_distinct_opts <> v_opt_count then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'Question options must have 2 to 6 unique option_ids.');
            end if;
            if not ((v_draft ->> 'answer_key') = any(v_opt_ids)) then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'answer_key must match one of the question options.');
            end if;
            if v_draft ->> 'question_type' = 'TRUE_FALSE'
               and (v_opt_count <> 2 or not (v_opt_ids @> array['TRUE', 'FALSE'] and array['TRUE', 'FALSE'] @> v_opt_ids)) then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'TRUE_FALSE question must have exact option_ids TRUE and FALSE.');
            end if;

            select count(distinct c.chunk_id) into v_chunk_count
            from jsonb_array_elements_text(v_draft -> 'source_chunk_ids') s(cid)
            join app_private.material_chunks c
              on c.user_id = v_uid and c.material_id = v_material_id
             and c.chunk_id = s.cid::uuid and c.profile = 'assessment' and c.topic = v_draft ->> 'topic';
            if v_chunk_count <> jsonb_array_length(v_draft -> 'source_chunk_ids') then
                return app_private.error_result(p_request, 'INVALID_PARAMETER',
                    'Question source_chunk_ids must reference chunks of the target material and topic.');
            end if;
        end loop;

        v_action_id := coalesce((v_args ->> 'action_id')::uuid, extensions.gen_random_uuid());
        if exists (select 1 from app_private.pending_actions where user_id = v_uid and action_id = v_action_id) then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action already exists.');
        end if;

        for v_draft, v_idx in select value, ordinality - 1 from jsonb_array_elements(v_args -> 'drafts') with ordinality loop
            v_qid := (v_draft ->> 'question_id')::uuid;
            insert into app_private.question_drafts (
                question_id, user_id, conversation_id, material_id, assessment_version, version, topic,
                question_type, stem, options, answer_key, explanation, source_chunk_ids, status, model,
                prompt_version, verified_at
            ) values (
                v_qid, v_uid, v_conv, v_material_id, '1.0.0', 1, v_draft ->> 'topic',
                v_draft ->> 'question_type', v_draft ->> 'stem', v_draft -> 'options', v_draft ->> 'answer_key',
                v_draft ->> 'explanation', v_draft -> 'source_chunk_ids', 'DRAFT', v_draft ->> 'model',
                v_draft ->> 'prompt_version', null
            );
            for v_chunk_id, v_src_idx in
                select value::uuid, ordinality - 1 from jsonb_array_elements_text(v_draft -> 'source_chunk_ids') with ordinality
            loop
                insert into app_private.question_draft_sources (question_id, chunk_id, user_id, material_id, source_order)
                values (v_qid, v_chunk_id, v_uid, v_material_id, v_src_idx);
            end loop;
            v_qids := v_qids || jsonb_build_array(v_qid);
        end loop;

        insert into app_private.pending_actions (
            action_id, user_id, conversation_id, version, intent, state, requires_review, candidate_id,
            proposal_id, draft_arguments, missing_fields, ambiguities, depends_on_action_id
        ) values (
            v_action_id, v_uid, v_conv, 1, 'VERIFY_QUESTION_DRAFTS', 'AWAITING_APPROVAL', false, null,
            null, jsonb_build_object('material_id', v_material_id, 'question_ids', v_qids),
            '[]'::jsonb, '[]'::jsonb, null
        ) returning * into v_action;

        for v_qid, v_idx in select value::uuid, ordinality - 1 from jsonb_array_elements_text(v_qids) with ordinality loop
            insert into app_private.question_draft_batch_items (user_id, action_id, question_id, item_order)
            values (v_uid, v_action.action_id, v_qid, v_idx);
        end loop;

        select coalesce(jsonb_agg(app_private.question_json(q) order by bi.item_order), '[]'::jsonb)
        into v_items
        from app_private.question_draft_batch_items bi
        join app_private.question_drafts q on q.user_id = bi.user_id and q.question_id = bi.question_id
        where bi.user_id = v_uid and bi.action_id = v_action.action_id;

        v_source_chunks := app_private.question_batch_source_chunks(v_uid, v_action.action_id);
        v_pres := jsonb_build_object(
            'kind', 'ACTION_PRESENTATION',
            'pending_action', app_private.pending_json(v_action),
            'candidate', null,
            'proposal', null,
            'normalized_command', null,
            'effective_policy', null,
            'schedule_confirmation', null,
            'question_drafts', jsonb_build_object('items', v_items, 'source_chunks', v_source_chunks)
        );
        v_error := app_private.store_presentation(p_request, v_uid, v_action, v_pres);
        if v_error is not null then
            raise exception using errcode = 'P0001', message = v_error #>> '{error,code}';
        end if;

        v_result := app_private.ok_result(p_request, 'DRAFTED', jsonb_build_object('items', v_items, 'source_chunks', v_source_chunks));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'create_question_drafts', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception
        when sqlstate 'P0001' then
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_ENTITY_VERSION') then sqlerrm else 'INVALID_PARAMETER' end,
                'Unable to store question drafts batch.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $function$;

-- Same relaxation for revision recommendations.
CREATE OR REPLACE FUNCTION app_api.create_revision_recommendation(p_request jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  v_err jsonb;
  v_uid uuid;
  v_args jsonb;
  v_ctx jsonb;
  v_conv_id uuid;
  v_idem_key text;
  v_rec_id uuid;
  v_action_id uuid;
  v_mat_id uuid;
  v_topic text;
  v_minutes integer;
  v_priority numeric;
  v_fp text;
  v_saved jsonb;
  v_mat app_private.materials;
  v_valid_count integer := 0;
  v_error_count integer := 0;
  v_distinct_q_count integer := 0;
  v_attempt_ids jsonb := '[]'::jsonb;
  v_wrong_q_ids uuid[] := '{}'::uuid[];
  v_chunk_ids jsonb := '[]'::jsonb;
  v_total_source_count integer := 0;
  v_error_rate numeric;
  v_limitations jsonb := '[]'::jsonb;
  v_reason text;
  v_evidence jsonb;
  v_confidence jsonb;
  v_action app_private.pending_actions;
  v_rec app_private.revision_recommendations;
  v_sources jsonb;
  v_presentation jsonb;
  v_stored jsonb;
  v_result jsonb;
begin
  v_err := app_private.precheck(p_request, 'create_revision_recommendation', 'CreateRevisionRecommendationArguments');
  if v_err is not null then
    return v_err;
  end if;

  v_uid := app_private.current_uid();
  v_args := p_request -> 'arguments';
  v_ctx := p_request -> 'execution_context';

  v_idem_key := nullif(btrim(coalesce(v_ctx ->> 'idempotency_key', '')), '');
  if v_idem_key is null then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Thiếu idempotency_key.');
  end if;

  begin
    v_conv_id := (v_ctx ->> 'conversation_id')::uuid;
  exception when others then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'conversation_id không hợp lệ.');
  end;
  if v_conv_id is null then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Thiếu conversation_id.');
  end if;

  v_rec_id := (v_args ->> 'recommendation_id')::uuid;
  v_action_id := (v_args ->> 'pending_action_id')::uuid;
  v_mat_id := (v_args ->> 'material_id')::uuid;
  v_topic := v_args ->> 'topic';
  v_minutes := (v_args ->> 'suggested_minutes')::integer;
  v_priority := (v_args ->> 'priority')::numeric;

  v_fp := app_private.domain_fingerprint(
    v_uid,
    'create_revision_recommendation',
    jsonb_build_object(
      'conversation_id', v_conv_id,
      'material_id', v_mat_id,
      'topic', v_topic,
      'suggested_minutes', v_minutes,
      'priority', v_priority
    )
  );

  v_saved := app_private.idempotent_reply(p_request, v_uid, 'create_revision_recommendation', v_idem_key, v_fp);
  if v_saved is not null then
    return v_saved;
  end if;

  perform app_private.lock_owner(v_uid, p_request);

  v_saved := app_private.idempotent_reply(p_request, v_uid, 'create_revision_recommendation', v_idem_key, v_fp);
  if v_saved is not null then
    return v_saved;
  end if;

  select * into v_mat
  from app_private.materials m
  where m.user_id = v_uid
    and m.material_id = v_mat_id
    and (m.conversation_id = v_conv_id or m.learning_status = 'READY')
    and m.status = 'READY';

  if not found then
    return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Không tìm thấy tài liệu sẵn sàng trong cuộc trò chuyện này.');
  end if;

  if not (v_mat.topics ? v_topic) then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Chủ đề không thuộc tài liệu đã chọn.');
  end if;

  if exists (
    select 1
    from app_private.pending_actions pa
    where pa.user_id = v_uid
      and pa.conversation_id = v_conv_id
      and pa.state in ('AWAITING_APPROVAL', 'AWAITING_CONFIRMATION', 'AWAITING_CLARIFICATION')
  ) then
    return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED', 'Đang có hành động chờ xác nhận trong cuộc trò chuyện này.');
  end if;

  with eligible_attempts as (
    select qa.attempt_id, qa.submitted_at, qa.question_ids
    from app_private.quiz_attempts qa
    where qa.user_id = v_uid
      and qa.material_id = v_mat_id
      and qa.status = 'SUBMITTED'
      and exists (
        select 1
        from app_private.quiz_responses qr
        join app_private.question_drafts qd
          on qd.user_id = v_uid
         and qd.question_id = qr.question_id
        where qr.user_id = v_uid
          and qr.attempt_id = qa.attempt_id
          and qr.validity = 'VALID' and qr.graded_at is not null and qr.is_correct is not null
          and qd.material_id = v_mat_id
          and qd.topic = v_topic
          and qd.status = 'VERIFIED'
          and qa.question_ids ? qr.question_id::text
      )
    order by qa.submitted_at desc, qa.attempt_id desc
    limit 50
  ),
  eligible_responses as (
    select
      ea.attempt_id,
      ea.submitted_at,
      qr.question_id,
      qr.is_correct
    from eligible_attempts ea
    join app_private.quiz_responses qr
      on qr.user_id = v_uid
     and qr.attempt_id = ea.attempt_id
    join app_private.question_drafts qd
      on qd.user_id = v_uid
     and qd.question_id = qr.question_id
    where qr.validity = 'VALID' and qr.graded_at is not null and qr.is_correct is not null
      and qd.material_id = v_mat_id
      and qd.topic = v_topic
      and qd.status = 'VERIFIED'
      and ea.question_ids ? qr.question_id::text
  )
  select
    count(*)::integer,
    count(*) filter (where not er.is_correct)::integer,
    count(distinct er.question_id)::integer,
    coalesce((select jsonb_agg(ea.attempt_id order by ea.submitted_at desc, ea.attempt_id desc) from eligible_attempts ea), '[]'::jsonb),
    coalesce(array_agg(distinct er.question_id) filter (where not er.is_correct), '{}'::uuid[])
  into v_valid_count, v_error_count, v_distinct_q_count, v_attempt_ids, v_wrong_q_ids
  from eligible_responses er;

  if v_valid_count = 0 then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Chưa có dữ liệu làm bài hợp lệ cho chủ đề này.');
  end if;

  if v_error_count = 0 then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Chưa ghi nhận câu trả lời sai nào cho chủ đề này.');
  end if;

  with distinct_sources as (
    select distinct mc.chunk_id, mc.page, mc.chunk_index
    from app_private.question_draft_sources qds
    join app_private.material_chunks mc
      on mc.user_id = v_uid
     and mc.material_id = v_mat_id
     and mc.chunk_id = qds.chunk_id
    where qds.user_id = v_uid
      and qds.material_id = v_mat_id
      and qds.question_id = any(v_wrong_q_ids)
      and mc.topic = v_topic
  ),
  limited_sources as (
    select ds.chunk_id, ds.page, ds.chunk_index
    from distinct_sources ds
    order by ds.page asc, ds.chunk_index asc, ds.chunk_id asc
    limit 50
  )
  select
    (select count(*)::integer from distinct_sources),
    coalesce((select jsonb_agg(ls.chunk_id order by ls.page asc, ls.chunk_index asc, ls.chunk_id asc) from limited_sources ls), '[]'::jsonb)
  into v_total_source_count, v_chunk_ids;

  if v_total_source_count = 0 then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Không tìm thấy đoạn tài liệu nguồn liên quan đến các câu trả lời sai.');
  end if;

  v_error_rate := v_error_count::numeric / v_valid_count::numeric;

  v_evidence := jsonb_build_object(
    'valid_response_count', v_valid_count,
    'error_count', v_error_count,
    -- Store the wire float representation so Python review round trips preserve the snapshot.
    'error_rate', to_jsonb(v_error_count::double precision / v_valid_count::double precision),
    'chunk_ids', v_chunk_ids,
    'attempt_ids', v_attempt_ids
  );

  v_limitations := jsonb_build_array(
    'Chỉ tổng hợp tối đa 50 lượt làm bài gần nhất, không phản ánh toàn bộ lịch sử học tập.',
    format('Dựa trên %s lượt trả lời hợp lệ (%s lỗi) qua %s lượt làm bài.', v_valid_count, v_error_count, jsonb_array_length(v_attempt_ids)),
    'Chỉ phản ánh các đoạn tài liệu đã được kiểm tra, không đo lường toàn bộ mức độ thành thạo.'
  );

  if v_valid_count > v_distinct_q_count then
    v_limitations := v_limitations || jsonb_build_array('Có câu hỏi được lặp lại nhiều lần trong mẫu thống kê.');
  end if;

  if v_total_source_count > 50 then
    v_limitations := v_limitations || jsonb_build_array('Danh sách đoạn tài liệu nguồn đã được giới hạn tối đa 50 đoạn.');
  end if;

  v_confidence := jsonb_build_object(
    'level', 'LOW',
    'limitations', v_limitations
  );

  v_reason := format(
    'Ghi nhận %s/%s câu trả lời sai (%s%%) ở chủ đề "%s". Thời lượng %s phút và mức ưu tiên %s do người dùng chọn.',
    v_error_count,
    v_valid_count,
    round(v_error_rate * 100, 1),
    v_topic,
    v_minutes,
    v_priority
  );

  begin
    insert into app_private.pending_actions (
      action_id,
      user_id,
      conversation_id,
      intent,
      state,
      version,
      requires_review,
      draft_arguments,
      missing_fields,
      ambiguities,
      candidate_id,
      proposal_id,
      depends_on_action_id
    ) values (
      v_action_id,
      v_uid,
      v_conv_id,
      'ACCEPT_REVISION_RECOMMENDATION',
      'AWAITING_APPROVAL',
      1,
      false,
      jsonb_build_object('recommendation_id', v_rec_id),
      '[]'::jsonb,
      '[]'::jsonb,
      null,
      null,
      null
    ) returning * into v_action;

    insert into app_private.revision_recommendations (
      recommendation_id,
      user_id,
      material_id,
      conversation_id,
      pending_action_id,
      candidate_id,
      assessment_version,
      topic,
      suggested_minutes,
      priority,
      reason_summary,
      status,
      evidence,
      confidence_limit
    ) values (
      v_rec_id,
      v_uid,
      v_mat_id,
      v_conv_id,
      v_action_id,
      null,
      '1.0.0',
      v_topic,
      v_minutes,
      v_priority,
      v_reason,
      'PROPOSED',
      v_evidence,
      v_confidence
    ) returning * into v_rec;

    v_sources := app_private.revision_source_chunks(v_uid, v_rec.evidence);

    v_presentation := jsonb_build_object(
      'kind', 'ACTION_PRESENTATION',
      'pending_action', app_private.pending_json(v_action),
      'candidate', null,
      'proposal', null,
      'normalized_command', null,
      'effective_policy', null,
      'schedule_confirmation', null,
      'revision_recommendation', app_private.revision_json(v_rec),
      'revision_source_chunks', v_sources
    );

    v_err := app_private.store_presentation(p_request, v_uid, v_action, v_presentation);
    if v_err is not null then raise exception using errcode='P0001', message=v_err #>> '{error,code}'; end if;
    select presentation into v_stored from app_private.action_presentations where user_id=v_uid and action_id=v_action.action_id and action_version=v_action.version;
    v_result := app_private.ok_result(p_request, 'COMMITTED', v_stored);

    insert into app_private.idempotency_records (
      user_id,
      operation,
      idempotency_key,
      request_fingerprint,
      state,
      result_reference_or_response,
      expires_at
    ) values (
      v_uid,
      'create_revision_recommendation',
      v_idem_key,
      v_fp,
      'COMPLETED',
      v_result,
      now() + interval '7 days'
    );

    return v_result;
  exception when others then
    return app_private.failure(p_request, sqlstate);
  end;
end;
$function$;

-- Same relaxation for the material read used before generating drafts.
CREATE OR REPLACE FUNCTION app_api.get_assessment_material(p_request jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare e jsonb := app_private.precheck(p_request,'get_assessment_material','MaterialLookupArguments');
 a jsonb := p_request->'arguments'; r app_private.materials;
begin
 if e is not null then return e; end if;
 select * into r from app_private.materials where material_id=(a->>'material_id')::uuid
  and user_id=app_private.current_uid() and (conversation_id=(a->>'conversation_id')::uuid or learning_status='READY')
  and (not learning_origin or status='READY');
 if not found then return app_private.error_result(p_request,'ENTITY_NOT_FOUND','Material not found.'); end if;
 return app_private.ok_result(p_request,'READ',app_private.material_detail(r));
end $function$;

-- Optional conversation_id binds the session (and its summary pending action) to the caller's chat conversation.
CREATE OR REPLACE FUNCTION app_api.create_learning_session(p_request jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
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

    v_conversation := coalesce((args ->> 'conversation_id')::uuid, gen_random_uuid());
    v_now := clock_timestamp();
    insert into app_private.conversation_records(user_id, conversation_id) values (uid, v_conversation) on conflict do nothing;
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
$function$;

-- Cross-feature writes also need a COMPLETED action behind a SUCCEEDED step.
CREATE OR REPLACE FUNCTION app_api.checkpoint_workflow_continuation(p_request jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
    v_error jsonb := app_private.precheck(p_request, 'checkpoint_workflow_continuation', 'CheckpointWorkflowContinuationArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_out jsonb := p_request -> 'arguments' -> 'outcome';
    v_ref jsonb := p_request -> 'arguments' -> 'action_reference';
    v_exp_version bigint;
    v_exp_cursor bigint;
    c app_private.workflow_continuations;
    a app_private.pending_actions;
    v_count int;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_args ->> 'conversation_id' is distinct from p_request #>> '{execution_context,conversation_id}' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The conversation does not match the request context.');
    end if;
    v_exp_version := (v_args ->> 'expected_version')::bigint;
    v_exp_cursor := (v_args ->> 'expected_cursor')::bigint;
    begin
        perform app_private.lock_owner(v_uid, p_request);
        v_error := app_private.receipt_guard(p_request, v_uid, v_args -> 'receipt_binding');
        if v_error is not null then
            return v_error;
        end if;
        select * into c from app_private.workflow_continuations
        where user_id = v_uid and conversation_id = (v_args ->> 'conversation_id')::uuid
          and source_message_id = (v_args ->> 'source_message_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The workflow continuation was not found.');
        end if;
        v_count := jsonb_array_length(c.extraction -> 'intents');

        -- Replay of an already-applied identical checkpoint.
        if v_args ->> 'transition' = 'ADVANCE' and v_exp_cursor < c.cursor and v_exp_version < c.version
           and c.completed_steps -> v_exp_cursor::int = v_out then
            return app_private.ok_result(p_request, 'COMMITTED', app_private.continuation_json(c));
        end if;
        if v_args ->> 'transition' = 'WAIT' and v_exp_cursor = c.cursor and v_exp_version + 1 = c.version
           and c.awaiting_reference = v_ref then
            return app_private.ok_result(p_request, 'COMMITTED', app_private.continuation_json(c));
        end if;

        if c.version <> v_exp_version or c.cursor <> v_exp_cursor or c.cursor >= v_count then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The workflow continuation has moved on.');
        end if;

        if v_args ->> 'transition' = 'WAIT' then
            select * into a from app_private.pending_actions
            where user_id = v_uid and conversation_id = c.conversation_id and action_id = (v_ref ->> 'action_id')::uuid;
            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The awaited action was not found.');
            end if;
            if a.version <> (v_ref ->> 'action_version')::bigint
               or a.state not in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL') then
                return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The awaited action is not waiting for the user.');
            end if;
            if v_ref ->> 'target_id' not in (a.action_id::text, coalesce(a.candidate_id::text, ''), coalesce(a.proposal_id::text, '')) then
                return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The action reference does not match the action.');
            end if;
            update app_private.workflow_continuations
            set awaiting_reference = v_ref, version = version + 1
            where user_id = c.user_id and source_message_id = c.source_message_id returning * into c;
            return app_private.ok_result(p_request, 'COMMITTED', app_private.continuation_json(c));
        end if;

        -- ADVANCE
        if (v_out ->> 'intent_index')::bigint <> c.cursor
           or v_out ->> 'step_key' <> app_private.step_key(c.origin_idempotency_key, c.source_message_id, c.cursor) then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The outcome does not belong to the step at the cursor.');
        end if;
        -- A step whose dependency did not succeed can only be cancelled, and vice versa.
        if (v_out ->> 'disposition' = 'DEPENDENCY_CANCELLED') is distinct from exists (
               select 1 from jsonb_array_elements_text(c.depends_on -> c.cursor::int) d
               where c.completed_steps -> d::int ->> 'disposition' is distinct from 'SUCCEEDED') then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The outcome disposition contradicts the step dependencies.');
        end if;
        if c.awaiting_reference is not null then
            select * into a from app_private.pending_actions
            where user_id = v_uid and action_id = (c.awaiting_reference ->> 'action_id')::uuid;
            if a.state not in ('COMPLETED', 'CANCELLED') then
                return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The awaited action is not finished.');
            end if;
        end if;
        -- Approval-gated writes need a finished action as evidence; reads are trusted as attested.
        if v_out ->> 'disposition' = 'SUCCEEDED'
           and v_out ->> 'operation' in ('confirm_task', 'set_availability', 'set_busy_interval',
                                         'set_scheduling_preferences', 'approve_study_plan', 'reject_study_plan',
                                         'verify_question_drafts', 'decide_revision_recommendation',
                                         'decide_learning_session_outcome')
           and (c.awaiting_reference is null or a.state <> 'COMPLETED') then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The write result has no completed action behind it.');
        end if;
        update app_private.workflow_continuations
        set completed_steps = completed_steps || jsonb_build_array(v_out), cursor = cursor + 1,
            awaiting_reference = null, version = version + 1
        where user_id = c.user_id and source_message_id = c.source_message_id returning * into c;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.continuation_json(c));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $function$;
