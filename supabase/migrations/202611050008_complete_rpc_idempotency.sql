-- Stage 03.3 Commit 15: shared idempotency reservation/completion primitives.
-- The owner lock is acquired by each caller before this helper. A concurrent
-- retry therefore observes the committed result, while a rolled-back attempt
-- leaves no durable IN_PROGRESS row.

create or replace function app_private.idempotency_begin(
    p_user_id uuid,
    p_operation text,
    p_idempotency_key text,
    p_request_fingerprint text
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
    v_record app_private.idempotency_records%rowtype;
begin
    if p_idempotency_key is null or p_request_fingerprint is null then
        raise exception using errcode = 'P0001', message = 'INVALID_PARAMETER';
    end if;
    select * into v_record
    from app_private.idempotency_records
    where user_id = p_user_id and operation = p_operation and idempotency_key = p_idempotency_key
    for update;
    if found then
        if v_record.request_fingerprint <> p_request_fingerprint then
            raise exception using errcode = 'P0001', message = 'IDEMPOTENCY_CONFLICT';
        end if;
        return coalesce(v_record.result_reference_or_response,
            jsonb_build_object('schema_version','1.1','state','IN_PROGRESS'));
    end if;
    insert into app_private.idempotency_records
        (user_id,operation,idempotency_key,request_fingerprint,state,expires_at)
    values (p_user_id,p_operation,p_idempotency_key,p_request_fingerprint,
            'IN_PROGRESS',clock_timestamp()+interval '24 hours');
    return null;
end;
$$;

create or replace function app_private.idempotency_complete(
    p_user_id uuid,
    p_operation text,
    p_idempotency_key text,
    p_result jsonb
)
returns void
language plpgsql
security invoker
set search_path = ''
as $$
begin
    update app_private.idempotency_records
    set state='COMPLETED', result_reference_or_response=p_result
    where user_id=p_user_id and operation=p_operation and idempotency_key=p_idempotency_key;
    if not found then
        raise exception using errcode='P0001', message='INVALID_PARAMETER';
    end if;
end;
$$;

revoke all on function app_private.idempotency_begin(uuid,text,text,text) from public, anon;
revoke all on function app_private.idempotency_complete(uuid,text,text,jsonb) from public, anon;
grant execute on function app_private.idempotency_begin(uuid,text,text,text) to authenticated;
grant execute on function app_private.idempotency_complete(uuid,text,text,jsonb) to authenticated;

create or replace function app_api.set_availability(
    p_operation text, p_window jsonb, p_window_id uuid, p_expected_window_version integer,
    p_decision text, p_attestation_id uuid, p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare v_user uuid := app_private.require_owner(); v_replay jsonb; v_result jsonb;
begin
    perform app_private.lock_owner(v_user);
    v_replay := app_private.idempotency_begin(v_user,'set_availability',p_idempotency_key,p_request_fingerprint);
    if v_replay is not null then return v_replay; end if;
    if p_attestation_id is not null or p_decision <> 'APPROVE' then
        raise exception using errcode='P0001', message='APPROVAL_REQUIRED';
    end if;
    v_result := app_private.upsert_time_window('AVAILABILITY',p_operation,p_window,p_window_id,p_expected_window_version);
    perform app_private.idempotency_complete(v_user,'set_availability',p_idempotency_key,v_result);
    return v_result;
end;
$$;

create or replace function app_api.set_busy_interval(
    p_operation text, p_window jsonb, p_window_id uuid, p_expected_window_version integer,
    p_decision text, p_attestation_id uuid, p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare v_user uuid := app_private.require_owner(); v_replay jsonb; v_result jsonb;
begin
    perform app_private.lock_owner(v_user);
    v_replay := app_private.idempotency_begin(v_user,'set_busy_interval',p_idempotency_key,p_request_fingerprint);
    if v_replay is not null then return v_replay; end if;
    if p_attestation_id is not null or p_decision <> 'APPROVE' then
        raise exception using errcode='P0001', message='APPROVAL_REQUIRED';
    end if;
    v_result := app_private.upsert_time_window('BUSY',p_operation,p_window,p_window_id,p_expected_window_version);
    perform app_private.idempotency_complete(v_user,'set_busy_interval',p_idempotency_key,v_result);
    return v_result;
end;
$$;

create or replace function app_api.set_scheduling_preferences(
    p_policy_patch jsonb, p_expected_schedule_revision integer, p_decision text,
    p_attestation_id uuid, p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare v_user uuid := app_private.require_owner(); v_revision bigint; v_replay jsonb; v_result jsonb;
begin
    perform app_private.lock_owner(v_user);
    v_replay := app_private.idempotency_begin(v_user,'set_scheduling_preferences',p_idempotency_key,p_request_fingerprint);
    if v_replay is not null then return v_replay; end if;
    if p_attestation_id is not null or p_decision <> 'APPROVE' then
        raise exception using errcode='P0001', message='APPROVAL_REQUIRED';
    end if;
    update app_private.user_profiles
    set scheduling_policy=scheduling_policy || coalesce(p_policy_patch,'{}'::jsonb),
        schedule_revision=schedule_revision+1
    where user_id=v_user and schedule_revision=p_expected_schedule_revision
    returning schedule_revision into v_revision;
    if v_revision is null then raise exception using errcode='P0001', message='STALE_ENTITY_VERSION'; end if;
    v_result := jsonb_build_object('schema_version','1.1','schedule_revision',v_revision,
        'scheduling_policy',(select scheduling_policy from app_private.user_profiles where user_id=v_user));
    perform app_private.idempotency_complete(v_user,'set_scheduling_preferences',p_idempotency_key,v_result);
    return v_result;
end;
$$;

create or replace function app_api.persist_plan_proposal(
    p_scope jsonb, p_engine_result jsonb, p_expected_schedule_revision integer,
    p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare v_user uuid := app_private.require_owner(); v_replay jsonb; v_id uuid := extensions.gen_random_uuid();
    v_version bigint; v_revision bigint; v_result jsonb;
begin
    perform app_private.lock_owner(v_user);
    v_replay := app_private.idempotency_begin(v_user,'persist_plan_proposal',p_idempotency_key,p_request_fingerprint);
    if v_replay is not null then return v_replay; end if;
    select schedule_revision into v_revision from app_private.user_profiles where user_id=v_user;
    if v_revision <> p_expected_schedule_revision then raise exception using errcode='P0001', message='STALE_PROPOSAL'; end if;
    v_version := coalesce((p_engine_result->>'version')::bigint,1);
    insert into app_private.plan_proposals
        (proposal_id,user_id,version,status,base_plan_id,base_plan_version,base_schedule_revision,
         generation_scope,payload,algorithm_version,policy_snapshot)
    select v_id,v_user,v_version,'PROPOSED',p->>'base_plan_id',(p->>'base_plan_version')::bigint,
        p_expected_schedule_revision,coalesce(p_scope,'{}'::jsonb),p_engine_result,
        coalesce(p_engine_result->>'algorithm_version','f1'),coalesce(p_engine_result->'policy_snapshot','{}'::jsonb)
    from jsonb_build_object('base_plan_id',(select current_plan_id from app_private.user_profiles where user_id=v_user),
        'base_plan_version',(select sp.version from app_private.study_plans sp join app_private.user_profiles up on up.current_plan_id=sp.plan_id where up.user_id=v_user)) p;
    v_result := jsonb_build_object('schema_version','1.1','proposal_id',v_id,'version',v_version,'status','PROPOSED');
    perform app_private.idempotency_complete(v_user,'persist_plan_proposal',p_idempotency_key,v_result);
    return v_result;
end;
$$;

create or replace function app_api.approve_study_plan(
    p_proposal_id uuid, p_expected_proposal_version integer, p_expected_plan_version integer,
    p_decision text, p_attestation_id uuid, p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare
    v_user uuid := app_private.require_owner(); v_replay jsonb; v_result jsonb;
    v_prop app_private.plan_proposals%rowtype; v_plan uuid := extensions.gen_random_uuid();
    v_version bigint; v_previous uuid; v_revision bigint; v_block jsonb;
    v_approval jsonb; v_source text := 'UI'; v_source_message_id uuid;
begin
    perform app_private.lock_owner(v_user);
    v_replay := app_private.idempotency_begin(v_user,'approve_study_plan',p_idempotency_key,p_request_fingerprint);
    if v_replay is not null then return v_replay; end if;
    if p_decision <> 'APPROVE' then raise exception using errcode='P0001', message='APPROVAL_REQUIRED'; end if;
    select * into v_prop from app_private.plan_proposals
    where proposal_id=p_proposal_id and user_id=v_user for update;
    if not found or v_prop.status <> 'PROPOSED' or v_prop.version <> p_expected_proposal_version then
        raise exception using errcode='P0001', message='STALE_PROPOSAL';
    end if;
    if p_attestation_id is not null then
        v_approval := app_private.consume_chat_attestation(p_attestation_id,v_user,'PLAN_PROPOSAL',p_proposal_id,p_expected_proposal_version,p_decision);
        v_source := 'CHAT'; v_source_message_id := (v_approval->>'source_message_id')::uuid;
    end if;
    insert into app_private.approval_actions
        (approval_action_id,user_id,target_type,target_id,target_version,decision,source,source_message_id,proposal_target_id)
    values (extensions.gen_random_uuid(),v_user,'PLAN_PROPOSAL',p_proposal_id,p_expected_proposal_version,
            p_decision,v_source,v_source_message_id,p_proposal_id);
    select current_plan_id,schedule_revision into v_previous,v_revision
    from app_private.user_profiles where user_id=v_user for update;
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
    update app_private.plan_proposals set status='APPROVED',committed_plan_id=v_plan where proposal_id=p_proposal_id;
    update app_private.user_profiles set current_plan_id=v_plan,schedule_revision=schedule_revision+1 where user_id=v_user;
    v_result := jsonb_build_object('schema_version','1.1','plan_id',v_plan,'version',v_version,'schedule_revision',v_revision+1);
    perform app_private.idempotency_complete(v_user,'approve_study_plan',p_idempotency_key,v_result);
    return v_result;
end;
$$;

create or replace function app_api.reject_study_plan(
    p_proposal_id uuid, p_expected_proposal_version integer, p_decision text,
    p_attestation_id uuid, p_idempotency_key text, p_request_fingerprint text
)
returns jsonb language plpgsql security invoker set search_path = ''
as $$
declare v_user uuid := app_private.require_owner(); v_replay jsonb; v_result jsonb;
    v_approval jsonb; v_source text := 'UI'; v_source_message_id uuid;
begin
    perform app_private.lock_owner(v_user);
    v_replay := app_private.idempotency_begin(v_user,'reject_study_plan',p_idempotency_key,p_request_fingerprint);
    if v_replay is not null then return v_replay; end if;
    if p_decision <> 'REJECT' then raise exception using errcode='P0001', message='APPROVAL_REQUIRED'; end if;
    select 1 from app_private.plan_proposals
    where proposal_id=p_proposal_id and user_id=v_user and status='PROPOSED' and version=p_expected_proposal_version for update;
    if not found then raise exception using errcode='P0001', message='STALE_PROPOSAL'; end if;
    if p_attestation_id is not null then
        v_approval := app_private.consume_chat_attestation(p_attestation_id,v_user,'PLAN_PROPOSAL',p_proposal_id,p_expected_proposal_version,p_decision);
        v_source := 'CHAT'; v_source_message_id := (v_approval->>'source_message_id')::uuid;
    end if;
    insert into app_private.approval_actions
        (approval_action_id,user_id,target_type,target_id,target_version,decision,source,source_message_id,proposal_target_id)
    values (extensions.gen_random_uuid(),v_user,'PLAN_PROPOSAL',p_proposal_id,p_expected_proposal_version,
            p_decision,v_source,v_source_message_id,p_proposal_id);
    update app_private.plan_proposals set status='REJECTED' where proposal_id=p_proposal_id and user_id=v_user;
    v_result := jsonb_build_object('schema_version','1.1','proposal_id',p_proposal_id,'status','REJECTED');
    perform app_private.idempotency_complete(v_user,'reject_study_plan',p_idempotency_key,v_result);
    return v_result;
end;
$$;

grant execute on function app_api.set_availability(text,jsonb,uuid,integer,text,uuid,text,text) to authenticated;
grant execute on function app_api.set_busy_interval(text,jsonb,uuid,integer,text,uuid,text,text) to authenticated;
grant execute on function app_api.set_scheduling_preferences(jsonb,integer,text,uuid,text,text) to authenticated;
grant execute on function app_api.persist_plan_proposal(jsonb,jsonb,integer,text,text) to authenticated;
grant execute on function app_api.approve_study_plan(uuid,integer,integer,text,uuid,text,text) to authenticated;
grant execute on function app_api.reject_study_plan(uuid,integer,text,uuid,text,text) to authenticated;
