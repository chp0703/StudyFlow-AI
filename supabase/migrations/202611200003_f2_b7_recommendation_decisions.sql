create or replace function app_api.decide_revision_recommendation(p_request jsonb)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_err jsonb;
  v_uid uuid;
  v_args jsonb;
  v_context jsonb;
  v_recommendation_id_text text;
  v_recommendation_id uuid;
  v_decision text;
  v_conversation_id_text text;
  v_conversation_id uuid;
  v_idempotency_key text;
  v_approval jsonb;
  v_ref jsonb;
  v_ref_action_id uuid;
  v_ref_action_version bigint;
  v_approval_action_id uuid;
  v_decision_binding jsonb;
  v_fp_args jsonb;
  v_fingerprint text;
  v_replay jsonb;
  v_rec app_private.revision_recommendations%rowtype;
  v_updated_rec app_private.revision_recommendations%rowtype;
  v_action app_private.pending_actions%rowtype;
  v_updated_action app_private.pending_actions%rowtype;
  v_new_action app_private.pending_actions%rowtype;
  v_pres_row app_private.action_presentations%rowtype;
  v_orig_source_message_id uuid;
  v_now timestamptz := clock_timestamp();
  v_new_candidate_id uuid;
  v_new_action_id uuid;
  v_attempt_ids_text text;
  v_chunk_ids_text text;
  v_description text;
  v_slots jsonb;
  v_field_sources jsonb;
  v_candidate app_private.task_candidates%rowtype;
  v_presentation jsonb;
  v_store_err jsonb;
  v_final_presentation jsonb;
  v_result jsonb;
begin
  v_err := app_private.precheck(
    p_request,
    'decide_revision_recommendation',
    'DecideRevisionRecommendationArguments'
  );
  if v_err is not null then
    return v_err;
  end if;

  v_uid := app_private.current_uid();
  if v_uid is null then
    return app_private.error_result(p_request, 'UNAUTHENTICATED', 'Authenticated user is required.');
  end if;

  v_args := coalesce(p_request->'arguments', '{}'::jsonb);
  v_context := coalesce(p_request->'execution_context', '{}'::jsonb);

  v_recommendation_id_text := nullif(btrim(v_args->>'recommendation_id'), '');
  if v_recommendation_id_text is null
    or v_recommendation_id_text !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'recommendation_id must be a valid UUID.');
  end if;
  v_recommendation_id := v_recommendation_id_text::uuid;

  v_decision := v_args->>'decision';
  if v_decision is null or v_decision not in ('APPROVE', 'REJECT') then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'decision must be APPROVE or REJECT.');
  end if;

  v_conversation_id_text := nullif(btrim(v_context->>'conversation_id'), '');
  if v_conversation_id_text is null
    or v_conversation_id_text !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'execution_context.conversation_id is required.');
  end if;
  v_conversation_id := v_conversation_id_text::uuid;

  v_idempotency_key := nullif(btrim(v_context->>'idempotency_key'), '');
  if v_idempotency_key is null then
    return app_private.error_result(p_request, 'INVALID_PARAMETER', 'execution_context.idempotency_key is required.');
  end if;

  v_approval := v_context->'approval_action';
  v_ref := v_context->'action_reference';

  if jsonb_typeof(v_approval) is distinct from 'object'
    or jsonb_typeof(v_ref) is distinct from 'object' then
    return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'approval_action and action_reference are required.');
  end if;

  if (v_approval->>'source') is distinct from 'UI'
    or not (v_approval ? 'source_message_id')
    or (v_approval->'source_message_id') is distinct from 'null'::jsonb
    or (v_approval->>'user_id') is distinct from v_uid::text
    or (v_approval->>'decision') is distinct from v_decision
    or (v_approval->>'target_type') is distinct from 'PENDING_ACTION'
    or (v_ref->>'target_type') is distinct from 'PENDING_ACTION'
    or (v_ref->>'action_id') is null
    or (v_ref->>'action_id') !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    or (v_ref->>'target_id') is distinct from (v_ref->>'action_id')
    or (v_approval->>'target_id') is distinct from (v_ref->>'action_id')
    or (v_ref->>'action_version') is null
    or (v_ref->>'action_version') !~ '^[0-9]+$'
    or (v_ref->>'target_version') is distinct from (v_ref->>'action_version')
    or (v_approval->>'target_version') is distinct from (v_ref->>'action_version') then
    return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'Valid UI approval_action and matching action_reference are required.');
  end if;

  v_ref_action_id := (v_ref->>'action_id')::uuid;
  v_ref_action_version := (v_ref->>'action_version')::bigint;

  if nullif(btrim(v_approval->>'approval_action_id'), '') is not null then
    if (v_approval->>'approval_action_id') !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' then
      return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'approval_action_id must be a valid UUID.');
    end if;
    v_approval_action_id := (v_approval->>'approval_action_id')::uuid;
  else
    v_approval_action_id := extensions.gen_random_uuid();
  end if;

  v_decision_binding := jsonb_build_object(
    'decision', v_decision,
    'action_id', v_ref_action_id::text,
    'action_version', v_ref_action_version,
    'target_type', v_ref->>'target_type',
    'target_id', v_ref->>'target_id',
    'target_version', (v_ref->>'target_version')::bigint
  );

  v_fp_args := jsonb_build_object(
    'recommendation_id', v_recommendation_id::text,
    'decision', v_decision
  );

  v_fingerprint := app_private.domain_fingerprint(
    v_uid,
    'decide_revision_recommendation',
    v_fp_args,
    v_decision_binding
  );

  v_replay := app_private.idempotent_reply(
    p_request,
    v_uid,
    'decide_revision_recommendation',
    v_idempotency_key,
    v_fingerprint
  );
  if v_replay is not null then
    return v_replay;
  end if;

  begin
    perform app_private.lock_owner(v_uid, p_request);

    v_replay := app_private.idempotent_reply(
      p_request,
      v_uid,
      'decide_revision_recommendation',
      v_idempotency_key,
      v_fingerprint
    );
    if v_replay is not null then
      return v_replay;
    end if;

    select *
    into v_rec
    from app_private.revision_recommendations
    where recommendation_id = v_recommendation_id
      and user_id = v_uid
      and conversation_id = v_conversation_id
    for update;

    if not found then
      return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Revision recommendation not found.');
    end if;

    select *
    into v_action
    from app_private.pending_actions
    where action_id = v_rec.pending_action_id
      and user_id = v_uid
      and conversation_id = v_conversation_id
      and intent = 'ACCEPT_REVISION_RECOMMENDATION'
    for update;

    if not found then
      return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Pending action for revision recommendation not found.');
    end if;

    if v_action.requires_review is distinct from false then
      return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED', 'Pending action requires review before approval.');
    end if;

    if v_action.action_id is distinct from v_ref_action_id
      or v_action.version is distinct from v_ref_action_version
      or v_rec.status is distinct from 'PROPOSED'
      or v_action.state is distinct from 'AWAITING_APPROVAL' then
      return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Revision recommendation or pending action version/state is stale.');
    end if;

    select *
    into v_pres_row
    from app_private.action_presentations
    where user_id = v_uid
      and action_id = v_action.action_id
      and action_version = v_action.version;

    if not found then
      return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'Action presentation snapshot not found.');
    end if;

    if v_pres_row.target_type is distinct from 'PENDING_ACTION'
      or v_pres_row.target_id is distinct from v_action.action_id
      or v_pres_row.target_version is distinct from v_action.version
      or v_pres_row.content_digest is distinct from app_private.presentation_digest(
        v_action,
        'PENDING_ACTION',
        v_action.action_id,
        v_action.version,
        v_pres_row.presentation
      )
      or (v_pres_row.presentation->'revision_recommendation') is distinct from app_private.revision_json(v_rec)
      or (v_pres_row.presentation->'revision_source_chunks') is distinct from app_private.revision_source_chunks(v_uid, v_rec.evidence) then
      return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'Action presentation snapshot does not match current recommendation.');
    end if;

    if v_decision = 'APPROVE' then
      v_orig_source_message_id := v_pres_row.source_message_id;
      if v_orig_source_message_id is null then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Original source message not found.');
      end if;

      perform 1
      from app_private.source_messages
      where message_id = v_orig_source_message_id
        and user_id = v_uid
        and conversation_id = v_conversation_id;

      if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Original source message not found.');
      end if;
    end if;

    insert into app_private.approval_actions (
      approval_action_id,
      user_id,
      target_type,
      target_id,
      target_version,
      decision,
      source,
      source_message_id,
      pending_action_target_id,
      created_at
    )
    values (
      v_approval_action_id,
      v_uid,
      'PENDING_ACTION',
      v_action.action_id,
      v_action.version,
      v_decision,
      'UI',
      null,
      v_action.action_id,
      v_now
    );

    if v_decision = 'REJECT' then
      update app_private.revision_recommendations
      set status = 'REJECTED',
          updated_at = v_now
      where recommendation_id = v_rec.recommendation_id
        and user_id = v_uid
      returning * into v_updated_rec;

      update app_private.pending_actions
      set state = 'CANCELLED',
          version = v_action.version + 1,
          updated_at = v_now
      where action_id = v_action.action_id
        and user_id = v_uid
      returning * into v_updated_action;

      v_final_presentation := v_pres_row.presentation
        || jsonb_build_object(
          'pending_action', app_private.pending_json(v_updated_action),
          'revision_recommendation', app_private.revision_json(v_updated_rec)
        );
    else
      v_new_candidate_id := extensions.gen_random_uuid();
      v_new_action_id := extensions.gen_random_uuid();

      select coalesce(string_agg(distinct elem, ', '), '')
      into v_attempt_ids_text
      from (
        select jsonb_array_elements_text(
          case
            when jsonb_typeof(v_rec.evidence->'attempt_ids') = 'array' then v_rec.evidence->'attempt_ids'
            else '[]'::jsonb
          end
        ) as elem
      ) a
      where nullif(elem, '') is not null;

      select coalesce(string_agg(distinct elem, ', '), '')
      into v_chunk_ids_text
      from (
        select jsonb_array_elements_text(
          case
            when jsonb_typeof(v_rec.evidence->'chunk_ids') = 'array' then v_rec.evidence->'chunk_ids'
            else '[]'::jsonb
          end
        ) as elem
        union
        select item->>'chunk_id' as elem
        from jsonb_array_elements(
          case
            when jsonb_typeof(v_pres_row.presentation->'revision_source_chunks') = 'array'
              then v_pres_row.presentation->'revision_source_chunks'
            else '[]'::jsonb
          end
        ) as item
      ) c
      where nullif(elem, '') is not null;

      v_description := v_rec.reason_summary
        || E'\nrecommendation_id: ' || v_rec.recommendation_id::text
        || case when v_attempt_ids_text <> '' then E'\nattempt_ids: ' || v_attempt_ids_text else '' end
        || case when v_chunk_ids_text <> '' then E'\nchunk_ids: ' || v_chunk_ids_text else '' end;

      v_slots := jsonb_build_object(
        'title', 'Ôn tập: ' || v_rec.topic,
        'description', v_description,
        'estimated_minutes', v_rec.suggested_minutes,
        'priority', v_rec.priority
      );

      v_field_sources := jsonb_build_object(
        'title', jsonb_build_object('source', 'DERIVED', 'reference', v_rec.recommendation_id::text),
        'description', jsonb_build_object('source', 'DERIVED', 'reference', v_rec.recommendation_id::text),
        'estimated_minutes', jsonb_build_object('source', 'USER_MESSAGE', 'reference', v_orig_source_message_id::text),
        'priority', jsonb_build_object('source', 'USER_MESSAGE', 'reference', v_orig_source_message_id::text)
      );

      insert into app_private.task_candidates (
        candidate_id,
        user_id,
        conversation_id,
        version,
        status,
        slots,
        raw_expressions,
        field_sources,
        source_message_id,
        confirmed_task_id,
        created_at,
        updated_at
      )
      values (
        v_new_candidate_id,
        v_uid,
        v_conversation_id,
        1,
        'DRAFT',
        v_slots,
        '{}'::jsonb,
        v_field_sources,
        v_orig_source_message_id,
        null,
        v_now,
        v_now
      )
      returning * into v_candidate;

      update app_private.revision_recommendations
      set status = 'ACCEPTED',
          candidate_id = v_new_candidate_id,
          updated_at = v_now
      where recommendation_id = v_rec.recommendation_id
        and user_id = v_uid
      returning * into v_updated_rec;

      update app_private.pending_actions
      set state = 'COMPLETED',
          version = v_action.version + 1,
          updated_at = v_now
      where action_id = v_action.action_id
        and user_id = v_uid;

      insert into app_private.pending_actions (
        action_id,
        user_id,
        conversation_id,
        version,
        intent,
        state,
        requires_review,
        candidate_id,
        proposal_id,
        draft_arguments,
        missing_fields,
        ambiguities,
        depends_on_action_id,
        created_at,
        updated_at
      )
      values (
        v_new_action_id,
        v_uid,
        v_conversation_id,
        1,
        'CREATE_TASK',
        'AWAITING_CLARIFICATION',
        false,
        v_new_candidate_id,
        null,
        jsonb_build_object('slots', v_slots),
        '["start_at","deadline_at"]'::jsonb,
        '[]'::jsonb,
        v_action.action_id,
        v_now,
        v_now
      )
      returning * into v_new_action;

      v_presentation := jsonb_build_object(
        'kind', 'ACTION_PRESENTATION',
        'pending_action', app_private.pending_json(v_new_action),
        'candidate', app_private.candidate_json(v_candidate),
        'proposal', null,
        'normalized_command', null,
        'effective_policy', null,
        'schedule_confirmation', null,
        'revision_recommendation', app_private.revision_json(v_updated_rec),
        'revision_source_chunks', v_pres_row.presentation->'revision_source_chunks'
      );

      v_store_err := app_private.store_presentation(
        p_request,
        v_uid,
        v_new_action,
        v_presentation
      );
      if v_store_err is not null then
        raise exception 'store_presentation_failed: %', v_store_err::text;
      end if;

      select presentation
      into v_final_presentation
      from app_private.action_presentations
      where user_id = v_uid
        and action_id = v_new_action.action_id
        and action_version = v_new_action.version;

      if not found then
        raise exception 'stored_presentation_missing';
      end if;
    end if;

    v_result := app_private.ok_result(p_request, 'COMMITTED', v_final_presentation);

    insert into app_private.idempotency_records (
      user_id,
      operation,
      idempotency_key,
      request_fingerprint,
      state,
      result_reference_or_response,
      expires_at
    )
    values (
      v_uid,
      'decide_revision_recommendation',
      v_idempotency_key,
      v_fingerprint,
      'COMPLETED',
      v_result,
      v_now + interval '7 days'
    );

    return v_result;
  exception
    when others then
      return app_private.failure(p_request, sqlstate);
  end;
end;
$$;

alter function app_api.decide_revision_recommendation(jsonb) owner to sf_rpc_owner;
revoke all on function app_api.decide_revision_recommendation(jsonb) from public;
revoke all on function app_api.decide_revision_recommendation(jsonb) from anon;
grant execute on function app_api.decide_revision_recommendation(jsonb) to authenticated;

