-- F2 B7: evidence-backed revision recommendations and explicit UI decisions.
alter table app_private.api_request_receipts
    drop constraint if exists api_request_receipts_http_operation_check;
alter table app_private.api_request_receipts
    add constraint api_request_receipts_http_operation_check
        check (http_operation in (
            'send_message', 'prepare_action', 'review_action', 'submit_decision',
            'generate_question_drafts', 'create_revision_recommendation'
        ));

create table app_private.revision_recommendations (
    recommendation_id uuid primary key,
    user_id uuid not null,
    conversation_id uuid not null,
    material_id uuid not null,
    topic text not null check (length(btrim(topic)) between 1 and 120),
    priority numeric not null check (priority in (0.1, 0.5, 1)),
    suggested_minutes integer not null check (suggested_minutes between 15 and 240),
    reason_summary text not null check (length(btrim(reason_summary)) between 1 and 1000),
    evidence jsonb not null,
    confidence_limit jsonb not null,
    pending_action_id uuid not null,
    candidate_id uuid,
    status text not null default 'PROPOSED' check (status in ('PROPOSED', 'ACCEPTED', 'REJECTED')),
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    unique (user_id, recommendation_id),
    unique (user_id, pending_action_id),
    foreign key (user_id, material_id) references app_private.materials(user_id, material_id) on delete restrict,
    foreign key (user_id, pending_action_id) references app_private.pending_actions(user_id, action_id) on delete restrict
);

alter table app_private.revision_recommendations enable row level security;
alter table app_private.revision_recommendations force row level security;
revoke all on app_private.revision_recommendations from public, anon, authenticated;
grant select, insert, update on app_private.revision_recommendations to sf_rpc_owner;
create policy revision_recommendations_select on app_private.revision_recommendations
    for select to sf_rpc_owner using (user_id = app_private.current_uid());
create policy revision_recommendations_insert on app_private.revision_recommendations
    for insert to sf_rpc_owner with check (user_id = app_private.current_uid());
create policy revision_recommendations_update on app_private.revision_recommendations
    for update to sf_rpc_owner using (user_id = app_private.current_uid())
    with check (user_id = app_private.current_uid());

create function app_private.revision_recommendation_json(r app_private.revision_recommendations) returns jsonb
language sql stable set search_path = '' as $$
    select jsonb_build_object(
        'assessment_version', '1.0.0', 'recommendation_id', r.recommendation_id,
        'user_id', r.user_id, 'conversation_id', r.conversation_id, 'material_id', r.material_id,
        'topic', r.topic, 'priority', r.priority, 'suggested_minutes', r.suggested_minutes,
        'reason_summary', r.reason_summary, 'evidence', r.evidence,
        'confidence_limit', r.confidence_limit, 'pending_action_id', r.pending_action_id,
        'candidate_id', r.candidate_id, 'status', r.status,
        'created_at', app_private.iso(r.created_at), 'updated_at', app_private.iso(r.updated_at)
    )
$$;

create function app_private.guard_revision_recommendation() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
    if tg_op = 'DELETE' then
        raise exception using errcode = '42501', message = 'revision recommendations cannot be deleted';
    end if;
    if old.status <> 'PROPOSED'
       or (new.recommendation_id, new.user_id, new.conversation_id, new.material_id, new.topic,
           new.priority, new.suggested_minutes, new.reason_summary, new.evidence, new.confidence_limit,
           new.pending_action_id, new.candidate_id, new.created_at)
          is distinct from
          (old.recommendation_id, old.user_id, old.conversation_id, old.material_id, old.topic,
           old.priority, old.suggested_minutes, old.reason_summary, old.evidence, old.confidence_limit,
           old.pending_action_id, old.candidate_id, old.created_at)
       or new.status not in ('ACCEPTED', 'REJECTED') then
        raise exception using errcode = '42501', message = 'invalid revision recommendation transition';
    end if;
    return new;
end $$;

create trigger revision_recommendations_guard
before update or delete on app_private.revision_recommendations
for each row execute function app_private.guard_revision_recommendation();

create function app_api.create_revision_recommendation(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'create_revision_recommendation', 'CreateRevisionRecommendationArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_conv uuid := (p_request #>> '{execution_context,conversation_id}')::uuid;
    v_material_id uuid := (v_args ->> 'material_id')::uuid;
    v_topic text := v_args ->> 'topic';
    v_fp text;
    v_reply jsonb;
    v_valid_count integer;
    v_error_count integer;
    v_attempt_ids jsonb;
    v_chunk_ids jsonb;
    v_evidence jsonb;
    v_confidence jsonb;
    v_action app_private.pending_actions;
    v_rec app_private.revision_recommendations;
    v_pres jsonb;
    v_result jsonb;
begin
    if v_error is not null then return v_error; end if;
    v_uid := app_private.current_uid();
    if v_key is null or v_conv is null or v_args ->> 'conversation_id' is distinct from v_conv::text then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key and matching conversation are required.');
    end if;
    v_fp := app_private.domain_fingerprint(v_uid, 'create_revision_recommendation', v_args);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'create_revision_recommendation', v_key, v_fp);
        if v_reply is not null then return v_reply; end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'create_revision_recommendation', v_key, v_fp);
        if v_reply is not null then return v_reply; end if;

        if not exists (
            select 1 from app_private.materials m where m.user_id = v_uid and m.material_id = v_material_id
              and m.conversation_id = v_conv and m.status = 'READY' and m.topics ? v_topic
        ) then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Material topic not found.');
        end if;
        if exists (
            select 1 from app_private.pending_actions p where p.user_id = v_uid
              and p.state in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL')
        ) then
            return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED', 'Another action is awaiting a decision.');
        end if;

        with graded as (
            select a.attempt_id, q.source_chunk_ids, r.is_correct
            from app_private.quiz_responses r
            join app_private.quiz_attempts a on a.user_id = r.user_id and a.attempt_id = r.attempt_id
            join app_private.question_drafts q on q.user_id = r.user_id and q.question_id = r.question_id
            where r.user_id = v_uid and a.material_id = v_material_id and a.status = 'SUBMITTED'
              and q.material_id = v_material_id and q.topic = v_topic and q.status = 'VERIFIED'
              and r.validity = 'VALID' and r.graded_at is not null and r.is_correct is not null
        )
        select count(*), count(*) filter (where is_correct = false),
               coalesce(jsonb_agg(distinct attempt_id), '[]'::jsonb)
        into v_valid_count, v_error_count, v_attempt_ids from graded;
        if v_valid_count = 0 or v_error_count = 0 then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'No observed errors are available for this topic.');
        end if;

        with wrong_chunks as (
            select distinct cid.value::uuid as chunk_id
            from app_private.quiz_responses r
            join app_private.quiz_attempts a on a.user_id = r.user_id and a.attempt_id = r.attempt_id
            join app_private.question_drafts q on q.user_id = r.user_id and q.question_id = r.question_id
            cross join lateral jsonb_array_elements_text(q.source_chunk_ids) cid(value)
            where r.user_id = v_uid and a.material_id = v_material_id and a.status = 'SUBMITTED'
              and q.material_id = v_material_id and q.topic = v_topic and q.status = 'VERIFIED'
              and r.validity = 'VALID' and r.graded_at is not null and r.is_correct = false
        )
        select coalesce(jsonb_agg(chunk_id), '[]'::jsonb) into v_chunk_ids from wrong_chunks;
        if jsonb_array_length(v_chunk_ids) = 0 then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'No source evidence is available for this topic.');
        end if;

        v_evidence := jsonb_build_object(
            'attempt_ids', v_attempt_ids, 'chunk_ids', v_chunk_ids,
            'valid_response_count', v_valid_count, 'error_count', v_error_count,
            'error_rate', round(v_error_count::numeric / v_valid_count::numeric, 6)
        );
        v_confidence := jsonb_build_object(
            'level', case when v_valid_count < 5 then 'LOW' when v_valid_count < 10 then 'MEDIUM' else 'HIGH' end,
            'limitations', jsonb_build_array(format('Dữ liệu hiện có gồm %s câu trả lời hợp lệ.', v_valid_count))
        );

        insert into app_private.pending_actions (
            action_id, user_id, conversation_id, version, intent, state, requires_review,
            candidate_id, proposal_id, draft_arguments, missing_fields, ambiguities, depends_on_action_id
        ) values (
            (v_args ->> 'action_id')::uuid, v_uid, v_conv, 1, 'REVIEW_REVISION_RECOMMENDATION',
            'AWAITING_APPROVAL', false, null, null,
            jsonb_build_object('recommendation_id', v_args -> 'recommendation_id', 'material_id', v_args -> 'material_id', 'topic', v_args -> 'topic'),
            '[]'::jsonb, '[]'::jsonb, null
        ) returning * into v_action;

        insert into app_private.revision_recommendations (
            recommendation_id, user_id, conversation_id, material_id, topic, priority, suggested_minutes,
            reason_summary, evidence, confidence_limit, pending_action_id, candidate_id, status
        ) values (
            (v_args ->> 'recommendation_id')::uuid, v_uid, v_conv, v_material_id, v_topic,
            (v_args ->> 'priority')::numeric, (v_args ->> 'suggested_minutes')::integer,
            format('Tỷ lệ sai của chủ đề "%s" là %s/%s câu trả lời hợp lệ.', v_topic, v_error_count, v_valid_count),
            v_evidence, v_confidence, v_action.action_id, null, 'PROPOSED'
        ) returning * into v_rec;

        v_pres := jsonb_build_object(
            'kind', 'ACTION_PRESENTATION', 'pending_action', app_private.pending_json(v_action),
            'candidate', null, 'proposal', null, 'normalized_command', null,
            'effective_policy', null, 'schedule_confirmation', null
        );
        v_error := app_private.store_presentation(p_request, v_uid, v_action, v_pres);
        if v_error is not null then
            raise exception using errcode = 'P0001', message = v_error #>> '{error,code}';
        end if;

        v_result := app_private.ok_result(p_request, 'PROPOSED', app_private.revision_recommendation_json(v_rec));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'create_revision_recommendation', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

create function app_api.decide_revision_recommendation(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'decide_revision_recommendation', 'DecideRevisionRecommendationArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_approval jsonb := p_request #> '{execution_context,approval_action}';
    v_ref jsonb := p_request #> '{execution_context,action_reference}';
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_conv uuid := (p_request #>> '{execution_context,conversation_id}')::uuid;
    v_action_id uuid := (v_args ->> 'action_id')::uuid;
    v_expected bigint := (v_args ->> 'expected_action_version')::bigint;
    v_decision text := v_args ->> 'decision';
    v_binding jsonb;
    v_fp text;
    v_reply jsonb;
    v_action app_private.pending_actions;
    v_pres app_private.action_presentations;
    v_rec app_private.revision_recommendations;
    v_result jsonb;
begin
    if v_error is not null then return v_error; end if;
    v_uid := app_private.current_uid();
    if v_key is null or v_conv is null or v_args ->> 'conversation_id' is distinct from v_conv::text
       or jsonb_typeof(v_approval) is distinct from 'object' or jsonb_typeof(v_ref) is distinct from 'object'
       or v_approval ->> 'source' <> 'UI' or (v_approval -> 'source_message_id') is distinct from 'null'::jsonb
       or v_approval ->> 'user_id' is distinct from v_uid::text or v_approval ->> 'decision' is distinct from v_decision
       or v_approval ->> 'target_type' <> 'PENDING_ACTION' or v_approval ->> 'target_id' is distinct from v_action_id::text
       or (v_approval ->> 'target_version')::bigint is distinct from v_expected
       or v_ref ->> 'target_type' <> 'PENDING_ACTION' or v_ref ->> 'action_id' is distinct from v_action_id::text
       or (v_ref ->> 'action_version')::bigint is distinct from v_expected
       or v_ref ->> 'target_id' is distinct from v_action_id::text
       or (v_ref ->> 'target_version')::bigint is distinct from v_expected then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'An exact UI action reference is required.');
    end if;
    v_binding := jsonb_build_object(
        'decision', v_decision, 'action_id', v_ref -> 'action_id', 'action_version', v_ref -> 'action_version',
        'target_type', 'PENDING_ACTION', 'target_id', v_ref -> 'target_id', 'target_version', v_ref -> 'target_version'
    );
    v_fp := app_private.domain_fingerprint(v_uid, 'decide_revision_recommendation', v_args, v_binding);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'decide_revision_recommendation', v_key, v_fp);
        if v_reply is not null then return v_reply; end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'decide_revision_recommendation', v_key, v_fp);
        if v_reply is not null then return v_reply; end if;

        select * into v_action from app_private.pending_actions
        where user_id = v_uid and action_id = v_action_id and conversation_id = v_conv
          and intent = 'REVIEW_REVISION_RECOMMENDATION' for update;
        if not found then return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Pending action not found.'); end if;
        if v_action.requires_review then return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED', 'Action requires review.'); end if;
        if v_action.version <> v_expected or v_action.state <> 'AWAITING_APPROVAL' then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Pending action changed.');
        end if;
        select * into v_pres from app_private.action_presentations
        where user_id = v_uid and action_id = v_action_id and action_version = v_expected;
        if not found or v_pres.target_type <> 'PENDING_ACTION' or v_pres.target_id <> v_action_id
           or v_pres.target_version <> v_expected
           or v_pres.content_digest <> app_private.presentation_digest(
               v_action, 'PENDING_ACTION', v_action_id, v_expected, v_pres.presentation) then
            return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'Recommendation was not presented by the server.');
        end if;
        select * into v_rec from app_private.revision_recommendations
        where user_id = v_uid and recommendation_id = (v_args ->> 'recommendation_id')::uuid
          and pending_action_id = v_action_id for update;
        if not found then return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Recommendation not found.'); end if;
        if v_rec.status <> 'PROPOSED' then return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Recommendation changed.'); end if;

        insert into app_private.approval_actions
            (approval_action_id, user_id, target_type, target_id, target_version, decision, source,
             source_message_id, pending_action_target_id)
        values ((v_approval ->> 'approval_action_id')::uuid, v_uid, 'PENDING_ACTION', v_action_id,
                v_expected, v_decision, 'UI', null, v_action_id);
        update app_private.revision_recommendations
        set status = case when v_decision = 'APPROVE' then 'ACCEPTED' else 'REJECTED' end,
            updated_at = clock_timestamp()
        where user_id = v_uid and recommendation_id = v_rec.recommendation_id returning * into v_rec;
        update app_private.pending_actions
        set state = case when v_decision = 'APPROVE' then 'COMPLETED' else 'CANCELLED' end,
            version = version + 1, updated_at = clock_timestamp()
        where user_id = v_uid and action_id = v_action_id;

        v_result := app_private.ok_result(p_request, 'COMMITTED', app_private.revision_recommendation_json(v_rec));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'decide_revision_recommendation', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.revision_recommendation_json(app_private.revision_recommendations) owner to sf_rpc_owner;
alter function app_private.guard_revision_recommendation() owner to sf_rpc_owner;
revoke all on function app_private.revision_recommendation_json(app_private.revision_recommendations),
    app_private.guard_revision_recommendation() from public, anon, authenticated;
alter function app_api.create_revision_recommendation(jsonb) owner to sf_rpc_owner;
alter function app_api.decide_revision_recommendation(jsonb) owner to sf_rpc_owner;
revoke all on function app_api.create_revision_recommendation(jsonb),
    app_api.decide_revision_recommendation(jsonb) from public, anon;
grant execute on function app_api.create_revision_recommendation(jsonb),
    app_api.decide_revision_recommendation(jsonb) to authenticated;
