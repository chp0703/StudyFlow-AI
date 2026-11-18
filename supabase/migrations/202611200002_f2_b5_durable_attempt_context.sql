-- B5 fix: load the exact durable attempt state needed for response validation and grading.
create or replace function app_private.rpc_is_read(p_routine text) returns boolean
language sql immutable set search_path = '' as $$
    select p_routine in (
        'search_tasks', 'get_study_plan', 'get_scheduling_context', 'lookup_operation_result',
        'list_time_windows', 'get_workflow_context', 'get_workflow_continuation',
        'get_ingestion_source', 'get_assessment_material', 'search_material_chunks',
        'list_questions', 'get_quiz_attempt_context', 'get_topic_stats'
    )
$$;

create function app_api.get_quiz_attempt_context(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'get_quiz_attempt_context', 'GetQuizAttemptContextArguments');
    v_uid uuid;
    v_attempt app_private.quiz_attempts;
    v_questions jsonb;
    v_responses jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        select * into v_attempt
        from app_private.quiz_attempts a
        where a.user_id = v_uid
          and a.attempt_id = (p_request #>> '{arguments,attempt_id}')::uuid;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Quiz attempt not found.');
        end if;

        select coalesce(jsonb_agg(app_private.question_json(q) order by x.ord), '[]'::jsonb)
        into v_questions
        from jsonb_array_elements_text(v_attempt.question_ids) with ordinality x(question_id, ord)
        join app_private.question_drafts q
          on q.user_id = v_uid
         and q.question_id = x.question_id::uuid
         and q.material_id = v_attempt.material_id;

        if jsonb_array_length(v_questions) <> v_attempt.total_questions then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'Attempt questions are no longer available.');
        end if;

        select coalesce(jsonb_agg(app_private.quiz_response_json(r) order by x.ord), '[]'::jsonb)
        into v_responses
        from jsonb_array_elements_text(v_attempt.question_ids) with ordinality x(question_id, ord)
        join app_private.quiz_responses r
          on r.user_id = v_uid
         and r.attempt_id = v_attempt.attempt_id
         and r.question_id = x.question_id::uuid;

        return app_private.ok_result(p_request, 'READ', jsonb_build_object(
            'attempt', app_private.quiz_attempt_json(v_attempt),
            'questions', v_questions,
            'responses', v_responses
        ));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.rpc_is_read(text) owner to sf_rpc_owner;
revoke all on function app_private.rpc_is_read(text) from public, anon, authenticated;
alter function app_api.get_quiz_attempt_context(jsonb) owner to sf_rpc_owner;
revoke all on function app_api.get_quiz_attempt_context(jsonb) from public, anon;
grant execute on function app_api.get_quiz_attempt_context(jsonb) to authenticated;
