-- B6 reads only durable graded responses. No cache, mastery label, or planner mutation.
create or replace function app_private.rpc_is_read(p_routine text) returns boolean
language sql immutable set search_path = '' as $$
    select p_routine in (
        'search_tasks', 'get_study_plan', 'get_scheduling_context', 'lookup_operation_result',
        'list_time_windows', 'get_workflow_context', 'get_workflow_continuation',
        'get_ingestion_source', 'get_assessment_material', 'search_material_chunks',
        'list_questions', 'get_topic_stats'
    )
$$;

create function app_api.get_topic_stats(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'get_topic_stats', 'GetTopicStatsArguments');
    v_uid uuid;
    v_material_id uuid;
    v_items jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    v_material_id := (p_request #>> '{arguments,material_id}')::uuid;
    begin
        if v_material_id is not null and not exists (
            select 1 from app_private.materials m
            where m.user_id = v_uid and m.material_id = v_material_id
        ) then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Material not found.');
        end if;

        with topics as (
            select distinct m.material_id, t.topic
            from app_private.materials m
            cross join lateral jsonb_array_elements_text(m.topics) t(topic)
            where m.user_id = v_uid and m.status = 'READY'
              and (v_material_id is null or m.material_id = v_material_id)
        ), graded as (
            select a.material_id, q.topic, count(*) as valid_count,
                   count(*) filter (where r.is_correct = false) as error_count,
                   max(a.submitted_at) as last_attempt_at
            from app_private.quiz_responses r
            join app_private.quiz_attempts a
              on a.user_id = r.user_id and a.attempt_id = r.attempt_id
            join app_private.question_drafts q
              on q.user_id = r.user_id and q.question_id = r.question_id
             and q.material_id = a.material_id
            where r.user_id = v_uid and a.status = 'SUBMITTED' and q.status = 'VERIFIED'
              and r.validity = 'VALID' and r.graded_at is not null and r.is_correct is not null
              and a.question_ids ? r.question_id::text
              and (v_material_id is null or a.material_id = v_material_id)
            group by a.material_id, q.topic
        )
        select coalesce(jsonb_agg(jsonb_build_object(
            'material_id', t.material_id, 'topic', t.topic,
            'status', case when coalesce(g.valid_count, 0) = 0 then 'INSUFFICIENT_DATA' else 'AVAILABLE' end,
            'valid_response_count', coalesce(g.valid_count, 0),
            'error_count', coalesce(g.error_count, 0),
            'error_rate', g.error_count::numeric / nullif(g.valid_count, 0),
            'last_attempt_at', app_private.iso(g.last_attempt_at)
        ) order by t.material_id, t.topic), '[]'::jsonb)
        into v_items
        from topics t left join graded g using (material_id, topic);

        return app_private.ok_result(p_request, 'READ', jsonb_build_object(
            'assessment_version', '1.0.0', 'material_id', v_material_id, 'items', v_items
        ));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.rpc_is_read(text) owner to sf_rpc_owner;
revoke all on function app_private.rpc_is_read(text) from public, anon, authenticated;
alter function app_api.get_topic_stats(jsonb) owner to sf_rpc_owner;
revoke all on function app_api.get_topic_stats(jsonb) from public, anon;
grant execute on function app_api.get_topic_stats(jsonb) to authenticated;
