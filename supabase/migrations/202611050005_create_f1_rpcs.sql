-- Stage 03.3 / commit 07: allow-listed F1 RPC boundary.
-- These functions are SECURITY INVOKER. Owner identity always comes from auth.uid().

create extension if not exists pgcrypto with schema extensions;

create or replace function app_private.owner_lock_key(p_user_id uuid)
returns bigint
language sql
immutable
strict
set search_path = ''
as $$
    select hashtextextended(p_user_id::text, 0)
$$;

create or replace function app_private.lock_owner(p_user_id uuid)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if p_user_id is null or auth.uid() is distinct from p_user_id then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;
    perform pg_advisory_xact_lock(app_private.owner_lock_key(p_user_id));
end;
$$;

create or replace function app_private.require_owner()
returns uuid
language plpgsql
security invoker
set search_path = ''
as $$
declare v_user uuid;
begin
    v_user := auth.uid();
    if v_user is null then
        raise exception using errcode = '28000', message = 'UNAUTHENTICATED';
    end if;
    if not exists (select 1 from app_private.user_profiles p where p.user_id = v_user) then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;
    return v_user;
end;
$$;

create or replace function app_api.create_task_candidate(
    p_conversation_id uuid,
    p_source_message_id uuid,
    p_slots jsonb,
    p_raw_expressions jsonb,
    p_field_sources jsonb,
    p_idempotency_key text,
    p_request_fingerprint text
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
    v_user uuid := app_private.require_owner();
    v_candidate uuid;
    v_existing app_private.idempotency_records%rowtype;
    v_result jsonb;
begin
    perform app_private.lock_owner(v_user);
    select * into v_existing from app_private.idempotency_records
    where user_id = v_user and operation = 'create_task_candidate' and idempotency_key = p_idempotency_key
    for update;
    if found then
        if v_existing.request_fingerprint <> p_request_fingerprint then
            raise exception using errcode = 'P0001', message = 'IDEMPOTENCY_CONFLICT';
        end if;
        return coalesce(v_existing.result_reference_or_response,
            jsonb_build_object('schema_version','1.1','state','IN_PROGRESS'));
    end if;
    v_candidate := extensions.gen_random_uuid();
    insert into app_private.idempotency_records
        (user_id, operation, idempotency_key, request_fingerprint, state, expires_at)
    values (v_user, 'create_task_candidate', p_idempotency_key, p_request_fingerprint,
            'IN_PROGRESS', clock_timestamp() + interval '24 hours');
    insert into app_private.task_candidates
        (candidate_id, user_id, conversation_id, slots, raw_expressions, field_sources, source_message_id)
    values (v_candidate, v_user, p_conversation_id, coalesce(p_slots,'{}'::jsonb),
            coalesce(p_raw_expressions,'{}'::jsonb), coalesce(p_field_sources,'{}'::jsonb), p_source_message_id);
    v_result := jsonb_build_object('schema_version','1.1','candidate_id',v_candidate,
                                   'version',1,'status','DRAFT');
    update app_private.idempotency_records
    set state = 'COMPLETED', result_reference_or_response = v_result
    where user_id = v_user and operation = 'create_task_candidate' and idempotency_key = p_idempotency_key;
    return v_result;
end;
$$;

create or replace function app_api.confirm_task(
    p_candidate_id uuid,
    p_expected_candidate_version integer,
    p_decision text,
    p_attestation_id uuid,
    p_idempotency_key text,
    p_request_fingerprint text
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
    v_user uuid := app_private.require_owner();
    v_candidate app_private.task_candidates%rowtype;
    v_existing app_private.idempotency_records%rowtype;
    v_task uuid;
    v_title text;
    v_result jsonb;
begin
    if p_attestation_id is not null then
        raise exception using errcode='P0001', message='APPROVAL_REQUIRED';
    end if;
    perform app_private.lock_owner(v_user);
    if p_idempotency_key is null or p_request_fingerprint is null then
        raise exception using errcode='P0001', message='INVALID_PARAMETER';
    end if;
    select * into v_existing from app_private.idempotency_records
    where user_id=v_user and operation='confirm_task' and idempotency_key=p_idempotency_key
    for update;
    if found then
        if v_existing.request_fingerprint <> p_request_fingerprint then
            raise exception using errcode='P0001', message='IDEMPOTENCY_CONFLICT';
        end if;
        return coalesce(v_existing.result_reference_or_response,
            jsonb_build_object('schema_version','1.1','state','IN_PROGRESS'));
    end if;
    insert into app_private.idempotency_records
        (user_id,operation,idempotency_key,request_fingerprint,state,expires_at)
    values(v_user,'confirm_task',p_idempotency_key,p_request_fingerprint,'IN_PROGRESS',clock_timestamp()+interval '24 hours');
    select * into v_candidate from app_private.task_candidates
    where candidate_id = p_candidate_id and user_id = v_user for update;
    if not found then raise exception using errcode='P0001', message='ENTITY_NOT_FOUND'; end if;
    if v_candidate.version <> p_expected_candidate_version or v_candidate.status <> 'DRAFT' then
        raise exception using errcode='P0001', message='STALE_ENTITY_VERSION';
    end if;
    if p_decision <> 'APPROVE' then
        update app_private.task_candidates set status='CANCELLED', version=version+1 where candidate_id=p_candidate_id;
        v_result := jsonb_build_object('schema_version','1.1','candidate_id',p_candidate_id,'status','CANCELLED');
        update app_private.idempotency_records set state='COMPLETED', result_reference_or_response=v_result
        where user_id=v_user and operation='confirm_task' and idempotency_key=p_idempotency_key;
        return v_result;
    end if;
    v_title := nullif(btrim(v_candidate.slots->>'title'),'');
    if v_title is null then raise exception using errcode='P0001', message='MISSING_REQUIRED_FIELD'; end if;
    v_task := extensions.gen_random_uuid();
    insert into app_private.academic_tasks
        (task_id,user_id,candidate_id,title,deadline_at,deadline_precision,deadline_date,deadline_timezone,estimated_minutes,remaining_minutes)
    values (v_task,v_user,p_candidate_id,v_title,
        (v_candidate.slots->>'deadline_at')::timestamptz,
            coalesce(v_candidate.slots->>'deadline_precision','DATETIME'),
            (v_candidate.slots->>'deadline_date')::date,
            coalesce(v_candidate.slots->>'deadline_timezone','UTC'),
            greatest(1,coalesce((v_candidate.slots->>'estimated_minutes')::bigint,1)),
            greatest(1,coalesce((v_candidate.slots->>'estimated_minutes')::bigint,1)));
    update app_private.task_candidates
    set status='CONFIRMED', confirmed_task_id=v_task, version=version+1
    where candidate_id=p_candidate_id and user_id=v_user;
    v_result := jsonb_build_object('schema_version','1.1','candidate_id',p_candidate_id,
                                   'task_id',v_task,'status','CONFIRMED');
    update app_private.idempotency_records set state='COMPLETED', result_reference_or_response=v_result
    where user_id=v_user and operation='confirm_task' and idempotency_key=p_idempotency_key;
    return v_result;
end;
$$;

create or replace function app_api.search_tasks(
    p_status_filter text[], p_query text, p_limit integer, p_cursor jsonb
)
returns jsonb
language plpgsql security invoker set search_path = ''
as $$
declare v_user uuid := app_private.require_owner(); v_rows jsonb;
begin
    select coalesce(jsonb_agg(to_jsonb(t) order by t.deadline_at), '[]'::jsonb) into v_rows
    from app_private.academic_tasks t
    where t.user_id=v_user
      and (p_status_filter is null or t.status = any(p_status_filter))
      and (p_query is null or t.title ilike '%' || p_query || '%')
    limit greatest(1, least(coalesce(p_limit,50),100));
    return jsonb_build_object('schema_version','1.1','tasks',v_rows);
end;
$$;

create or replace function app_api.read_scheduling_context(p_scope jsonb)
returns jsonb
language plpgsql security invoker set search_path = ''
as $$
declare v_user uuid := app_private.require_owner(); v_profile jsonb; v_tasks jsonb; v_windows jsonb;
begin
    select to_jsonb(p) into v_profile from app_private.user_profiles p where p.user_id=v_user;
    select coalesce(jsonb_agg(to_jsonb(t)), '[]'::jsonb) into v_tasks from app_private.academic_tasks t where t.user_id=v_user;
    select coalesce(jsonb_agg(to_jsonb(w)), '[]'::jsonb) into v_windows from app_private.time_windows w where w.user_id=v_user and w.archived_at is null;
    return jsonb_build_object('schema_version','1.1','profile',v_profile,'tasks',v_tasks,'time_windows',v_windows);
end;
$$;

create or replace function app_api.get_study_plan(
    p_view text, p_version integer, p_proposal_id uuid, p_start_at timestamptz, p_end_at timestamptz
)
returns jsonb
language plpgsql security invoker set search_path = ''
as $$
declare v_user uuid := app_private.require_owner(); v_plan uuid; v_blocks jsonb;
begin
    select current_plan_id into v_plan from app_private.user_profiles where user_id=v_user;
    select coalesce(jsonb_agg(to_jsonb(b) order by b.start_at),'[]'::jsonb) into v_blocks
    from app_private.study_blocks b
    where b.user_id=v_user and (v_plan is null or b.plan_id=v_plan)
      and (p_start_at is null or b.end_at > p_start_at)
      and (p_end_at is null or b.start_at < p_end_at);
    return jsonb_build_object('schema_version','1.1','plan_id',v_plan,'blocks',v_blocks);
end;
$$;

create or replace function app_private.upsert_time_window(
    p_kind text, p_operation text, p_window jsonb, p_window_id uuid,
    p_expected_version integer
)
returns jsonb
language plpgsql security invoker set search_path = ''
as $$
declare
    v_user uuid := auth.uid(); v_id uuid := coalesce(p_window_id, extensions.gen_random_uuid());
    v_version bigint := coalesce(p_expected_version, 0) + 1;
begin
    if v_user is null then raise exception using errcode='28000', message='UNAUTHENTICATED'; end if;
    perform app_private.lock_owner(v_user);
    if p_operation = 'UPDATE' then
        update app_private.time_windows set version=v_version, kind=p_kind,
            label=p_window->>'label', recurrence=coalesce(p_window->>'recurrence','NONE'),
            timezone=p_window->>'timezone', start_at=(p_window->>'start_at')::timestamptz,
            end_at=(p_window->>'end_at')::timestamptz,
            weekday=(p_window->>'weekday')::smallint, start_time=(p_window->>'start_time')::time,
            end_time=(p_window->>'end_time')::time, valid_from=(p_window->>'valid_from')::date,
            valid_until=(p_window->>'valid_until')::date
        where window_id=v_id and user_id=v_user and version=p_expected_version;
        if not found then raise exception using errcode='P0001', message='STALE_ENTITY_VERSION'; end if;
    else
        insert into app_private.time_windows
            (window_id,user_id,kind,label,recurrence,timezone,start_at,end_at,weekday,start_time,end_time,valid_from,valid_until)
        values (v_id,v_user,p_kind,p_window->>'label',coalesce(p_window->>'recurrence','NONE'),p_window->>'timezone',
                (p_window->>'start_at')::timestamptz,(p_window->>'end_at')::timestamptz,
                (p_window->>'weekday')::smallint,(p_window->>'start_time')::time,(p_window->>'end_time')::time,
                (p_window->>'valid_from')::date,(p_window->>'valid_until')::date);
    end if;
    return jsonb_build_object('schema_version','1.1','window_id',v_id,'version',v_version,'kind',p_kind);
end;
$$;

create or replace function app_api.set_availability(
    p_operation text, p_window jsonb, p_window_id uuid, p_expected_window_version integer,
    p_decision text, p_attestation_id uuid, p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
begin
    if p_attestation_id is not null then
        raise exception using errcode='P0001', message='APPROVAL_REQUIRED';
    end if;
    if p_decision <> 'APPROVE' then raise exception using errcode='P0001', message='APPROVAL_REQUIRED'; end if;
    return app_private.upsert_time_window('AVAILABILITY',p_operation,p_window,p_window_id,p_expected_window_version);
end;
$$;

create or replace function app_api.set_busy_interval(
    p_operation text, p_window jsonb, p_window_id uuid, p_expected_window_version integer,
    p_decision text, p_attestation_id uuid, p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
begin
    if p_attestation_id is not null then
        raise exception using errcode='P0001', message='APPROVAL_REQUIRED';
    end if;
    if p_decision <> 'APPROVE' then raise exception using errcode='P0001', message='APPROVAL_REQUIRED'; end if;
    return app_private.upsert_time_window('BUSY',p_operation,p_window,p_window_id,p_expected_window_version);
end;
$$;

create or replace function app_api.set_scheduling_preferences(
    p_policy_patch jsonb, p_expected_schedule_revision integer, p_decision text,
    p_attestation_id uuid, p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare v_user uuid := app_private.require_owner(); v_revision bigint;
begin
    if p_attestation_id is not null then
        raise exception using errcode='P0001', message='APPROVAL_REQUIRED';
    end if;
    if p_decision <> 'APPROVE' then raise exception using errcode='P0001', message='APPROVAL_REQUIRED'; end if;
    perform app_private.lock_owner(v_user);
    update app_private.user_profiles
    set scheduling_policy = scheduling_policy || coalesce(p_policy_patch,'{}'::jsonb),
        schedule_revision = schedule_revision + 1
    where user_id=v_user and schedule_revision=p_expected_schedule_revision
    returning schedule_revision into v_revision;
    if v_revision is null then raise exception using errcode='P0001', message='STALE_ENTITY_VERSION'; end if;
    return jsonb_build_object('schema_version','1.1','schedule_revision',v_revision,
                              'scheduling_policy',(select scheduling_policy from app_private.user_profiles where user_id=v_user));
end;
$$;

create or replace function app_api.persist_plan_proposal(
    p_scope jsonb, p_engine_result jsonb, p_expected_schedule_revision integer,
    p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare
    v_user uuid := app_private.require_owner(); v_id uuid := extensions.gen_random_uuid(); v_version bigint;
    v_revision bigint;
begin
    perform app_private.lock_owner(v_user);
    select schedule_revision into v_revision from app_private.user_profiles where user_id=v_user;
    if v_revision <> p_expected_schedule_revision then raise exception using errcode='P0001', message='STALE_PROPOSAL'; end if;
    -- Physical version is integer-compatible; reject non-numeric payload versions rather than coercing text.
    v_version := coalesce((p_engine_result->>'version')::bigint, 1);
    insert into app_private.plan_proposals
        (proposal_id,user_id,version,status,base_plan_id,base_plan_version,base_schedule_revision,
         generation_scope,payload,algorithm_version,policy_snapshot)
    select v_id,v_user, v_version, 'PROPOSED', p->>'base_plan_id',
           (p->>'base_plan_version')::bigint, p_expected_schedule_revision,
           coalesce(p_scope,'{}'::jsonb), p_engine_result,
           coalesce(p_engine_result->>'algorithm_version','f1'),
           coalesce(p_engine_result->'policy_snapshot','{}'::jsonb)
    from jsonb_build_object('base_plan_id',(select current_plan_id from app_private.user_profiles where user_id=v_user),
                            'base_plan_version',(select sp.version from app_private.study_plans sp join app_private.user_profiles up on up.current_plan_id=sp.plan_id where up.user_id=v_user)) p;
    return jsonb_build_object('schema_version','1.1','proposal_id',v_id,'version',v_version,'status','PROPOSED');
end;
$$;

create or replace function app_api.approve_study_plan(
    p_proposal_id uuid, p_expected_proposal_version integer, p_expected_plan_version integer,
    p_decision text, p_attestation_id uuid, p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare
    v_user uuid := app_private.require_owner(); v_prop app_private.plan_proposals%rowtype;
    v_plan uuid := extensions.gen_random_uuid(); v_version bigint; v_previous uuid; v_revision bigint; v_block jsonb;
begin
    if p_attestation_id is not null then
        raise exception using errcode='P0001', message='APPROVAL_REQUIRED';
    end if;
    if p_decision <> 'APPROVE' then raise exception using errcode='P0001', message='APPROVAL_REQUIRED'; end if;
    perform app_private.lock_owner(v_user);
    select * into v_prop from app_private.plan_proposals where proposal_id=p_proposal_id and user_id=v_user for update;
    if not found or v_prop.status <> 'PROPOSED' or v_prop.version <> p_expected_proposal_version then
        raise exception using errcode='P0001', message='STALE_PROPOSAL';
    end if;
    select current_plan_id, schedule_revision into v_previous, v_revision from app_private.user_profiles where user_id=v_user for update;
    if p_expected_plan_version is not null and v_previous is not null and
       (select version from app_private.study_plans where plan_id=v_previous) <> p_expected_plan_version then
        raise exception using errcode='P0001', message='STALE_PLAN_VERSION';
    end if;
    select coalesce(max(version),0)+1 into v_version from app_private.study_plans where user_id=v_user;
    insert into app_private.study_plans(plan_id,user_id,version,previous_plan_id,source_proposal_id)
    values(v_plan,v_user,v_version,v_previous,p_proposal_id);
    for v_block in select value from jsonb_array_elements(coalesce(v_prop.payload->'blocks','[]'::jsonb)) loop
        insert into app_private.study_blocks(plan_id,block_id,user_id,task_id,start_at,end_at,is_locked)
        values(v_plan,coalesce((v_block->>'block_id')::uuid,extensions.gen_random_uuid()),v_user,
               (v_block->>'task_id')::uuid,(v_block->>'start_at')::timestamptz,
               (v_block->>'end_at')::timestamptz,coalesce((v_block->>'is_locked')::boolean,false));
    end loop;
    update app_private.plan_proposals set status='APPROVED', committed_plan_id=v_plan where proposal_id=p_proposal_id;
    update app_private.user_profiles set current_plan_id=v_plan, schedule_revision=schedule_revision+1 where user_id=v_user;
    return jsonb_build_object('schema_version','1.1','plan_id',v_plan,'version',v_version,'schedule_revision',v_revision+1);
end;
$$;

create or replace function app_api.reject_study_plan(
    p_proposal_id uuid, p_expected_proposal_version integer, p_decision text,
    p_attestation_id uuid, p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare v_user uuid := app_private.require_owner();
begin
    if p_attestation_id is not null then
        raise exception using errcode='P0001', message='APPROVAL_REQUIRED';
    end if;
    perform app_private.lock_owner(v_user);
    update app_private.plan_proposals set status='REJECTED'
    where proposal_id=p_proposal_id and user_id=v_user and status='PROPOSED' and version=p_expected_proposal_version;
    if not found then raise exception using errcode='P0001', message='STALE_PROPOSAL'; end if;
    return jsonb_build_object('schema_version','1.1','proposal_id',p_proposal_id,'status','REJECTED');
end;
$$;

create or replace function app_api.issue_chat_approval_attestation(
    p_user_id uuid, p_conversation_id uuid, p_action_id uuid, p_action_version integer,
    p_target_type text, p_target_id uuid, p_target_version integer, p_decision text,
    p_source_message_id uuid, p_request_fingerprint text
)
returns jsonb
language plpgsql security invoker set search_path = ''
as $$
declare v_id uuid := extensions.gen_random_uuid(); v_expires timestamptz := clock_timestamp() + interval '5 minutes';
begin
    if current_user <> 'service_role' then raise exception using errcode='42501', message='FORBIDDEN'; end if;
    insert into app_private.chat_approval_attestations
      (attestation_id,user_id,conversation_id,action_id,action_version,target_type,target_id,target_version,decision,source_message_id,request_fingerprint,expires_at)
    values (v_id,p_user_id,p_conversation_id,p_action_id,p_action_version,p_target_type,p_target_id,p_target_version,p_decision,p_source_message_id,p_request_fingerprint,v_expires);
    return jsonb_build_object('schema_version','1.1','attestation_id',v_id,'expires_at',v_expires);
end;
$$;

revoke all on all functions in schema app_api from public;
grant execute on function app_private.owner_lock_key(uuid) to authenticated;
grant execute on function app_private.lock_owner(uuid) to authenticated;
grant execute on function app_private.require_owner() to authenticated;
grant execute on function app_private.upsert_time_window(text,text,jsonb,uuid,integer) to authenticated;
grant execute on function app_api.create_task_candidate(uuid,uuid,jsonb,jsonb,jsonb,text,text) to authenticated;
grant execute on function app_api.confirm_task(uuid,integer,text,uuid,text,text) to authenticated;
grant execute on function app_api.search_tasks(text[],text,integer,jsonb) to authenticated;
grant execute on function app_api.read_scheduling_context(jsonb) to authenticated;
grant execute on function app_api.get_study_plan(text,integer,uuid,timestamptz,timestamptz) to authenticated;
grant execute on function app_api.set_availability(text,jsonb,uuid,integer,text,uuid,text,text) to authenticated;
grant execute on function app_api.set_busy_interval(text,jsonb,uuid,integer,text,uuid,text,text) to authenticated;
grant execute on function app_api.set_scheduling_preferences(jsonb,integer,text,uuid,text,text) to authenticated;
grant execute on function app_api.persist_plan_proposal(jsonb,jsonb,integer,text,text) to authenticated;
grant execute on function app_api.approve_study_plan(uuid,integer,integer,text,uuid,text,text) to authenticated;
grant execute on function app_api.reject_study_plan(uuid,integer,text,uuid,text,text) to authenticated;
grant execute on function app_api.issue_chat_approval_attestation(uuid,uuid,uuid,integer,text,uuid,integer,text,uuid,text) to service_role;
