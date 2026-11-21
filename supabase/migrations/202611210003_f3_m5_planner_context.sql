-- F3 M5: read-only planner block context used to suggest a session goal. Never writes to the Planner.
create or replace function app_private.rpc_is_read(p_routine text) returns boolean
language sql immutable set search_path = '' as $$
    select p_routine in (
        'search_tasks', 'get_study_plan', 'list_time_windows', 'get_scheduling_context', 'lookup_operation_result',
        'get_workflow_context', 'get_workflow_continuation', 'get_ingestion_source',
        'get_assessment_material', 'search_material_chunks', 'list_questions', 'get_quiz_attempt_context',
        'get_topic_stats', 'get_learning_material', 'list_learning_materials',
        'get_learning_session', 'lookup_learning_turn_receipt', 'search_learning_material_chunks',
        'get_learning_planner_context'
    )
$$;

create function app_api.get_learning_planner_context(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    err jsonb := app_private.precheck(p_request, 'get_learning_planner_context', 'GetLearningPlannerContextArguments');
    uid uuid := app_private.current_uid();
    v_block app_private.study_blocks;
    v_task app_private.academic_tasks;
    v_title text;
begin
    if err is not null then return err; end if;
    -- block_id is unique per plan; the newest plan wins when a block id was carried over.
    select b.* into v_block from app_private.study_blocks b
    where b.user_id = uid and b.block_id = (p_request #>> '{arguments,block_id}')::uuid
    order by b.created_at desc limit 1;
    if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Planner block not found.');
    end if;
    select t.* into v_task from app_private.academic_tasks t where t.user_id = uid and t.task_id = v_block.task_id;
    if not found then
        return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'Planner task not found.');
    end if;
    v_title := left(btrim(v_task.title), 500);
    return app_private.ok_result(p_request, 'READ', jsonb_build_object(
        'block_id', v_block.block_id,
        'task_id', v_task.task_id,
        'task_title', v_title,
        'start_at', app_private.iso(v_block.start_at),
        'end_at', app_private.iso(v_block.end_at),
        'suggested_goal', v_title
    ));
exception when others then
    return app_private.failure(p_request, sqlstate);
end
$$;

alter function app_api.get_learning_planner_context(jsonb) owner to sf_rpc_owner;
revoke all on function app_api.get_learning_planner_context(jsonb) from public, anon;
grant execute on function app_api.get_learning_planner_context(jsonb) to authenticated;
