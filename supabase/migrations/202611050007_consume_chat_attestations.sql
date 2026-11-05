-- Stage 03.3 Commit 14: atomic one-time CHAT attestation consumption.
-- This is the narrowly-scoped E-05 exception: the private helper is SECURITY
-- DEFINER only because authenticated invoker RPCs have no table privilege on
-- the attestation store. It has fixed search_path, explicit owner/target checks,
-- and is not exposed through PostgREST.

create or replace function app_private.consume_chat_attestation(
    p_attestation_id uuid,
    p_user_id uuid,
    p_target_type text,
    p_target_id uuid,
    p_target_version bigint,
    p_decision text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_att app_private.chat_approval_attestations%rowtype;
begin
    if auth.uid() is distinct from p_user_id then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;
    select * into v_att
    from app_private.chat_approval_attestations
    where attestation_id = p_attestation_id
    for update;
    if not found then
        raise exception using errcode = 'P0001', message = 'APPROVAL_REQUIRED';
    end if;
    if v_att.user_id <> p_user_id
       or v_att.target_type <> p_target_type
       or v_att.target_id <> p_target_id
       or v_att.target_version <> p_target_version
       or v_att.decision <> p_decision
       or v_att.expires_at <= clock_timestamp()
       or v_att.consumed_at is not null then
        raise exception using errcode = 'P0001', message = 'APPROVAL_REQUIRED';
    end if;
    update app_private.chat_approval_attestations
    set consumed_at = clock_timestamp()
    where attestation_id = p_attestation_id and consumed_at is null;
    if not found then
        raise exception using errcode = 'P0001', message = 'APPROVAL_REQUIRED';
    end if;
    return jsonb_build_object('source','CHAT','source_message_id',v_att.source_message_id,
                              'action_id',v_att.action_id,'action_version',v_att.action_version);
end;
$$;

revoke all on function app_private.consume_chat_attestation(uuid,uuid,text,uuid,bigint,text) from public, anon;
grant execute on function app_private.consume_chat_attestation(uuid,uuid,text,uuid,bigint,text) to authenticated;

create or replace function app_api.issue_chat_approval_attestation(
    p_user_id uuid, p_conversation_id uuid, p_action_id uuid, p_action_version integer,
    p_target_type text, p_target_id uuid, p_target_version integer, p_decision text,
    p_source_message_id uuid, p_request_fingerprint text
)
returns jsonb
language plpgsql security invoker set search_path = ''
as $$
declare
    v_id uuid := extensions.gen_random_uuid();
    v_expires timestamptz := clock_timestamp() + interval '5 minutes';
    v_version bigint; v_status text;
begin
    if current_user <> 'service_role' then raise exception using errcode='42501', message='FORBIDDEN'; end if;
    if p_decision not in ('APPROVE','REJECT') or p_target_type not in ('TASK_CANDIDATE','PENDING_ACTION','PLAN_PROPOSAL') then
        raise exception using errcode='P0001', message='INVALID_PARAMETER';
    end if;
    if not exists (
        select 1 from app_private.pending_actions
        where user_id=p_user_id and action_id=p_action_id and conversation_id=p_conversation_id
          and version=p_action_version and state in ('AWAITING_CLARIFICATION','AWAITING_CONFIRMATION','AWAITING_APPROVAL')
    ) then
        raise exception using errcode='P0001', message='APPROVAL_REQUIRED';
    end if;
    if p_target_type='TASK_CANDIDATE' then
        select version,status into v_version,v_status from app_private.task_candidates
        where user_id=p_user_id and candidate_id=p_target_id;
        if not found or v_version<>p_target_version or v_status<>'DRAFT' then raise exception using errcode='P0001', message='STALE_ENTITY_VERSION'; end if;
    elsif p_target_type='PENDING_ACTION' then
        select version,state into v_version,v_status from app_private.pending_actions
        where user_id=p_user_id and action_id=p_target_id;
        if not found or v_version<>p_target_version or v_status not in ('AWAITING_CLARIFICATION','AWAITING_CONFIRMATION','AWAITING_APPROVAL') then raise exception using errcode='P0001', message='STALE_ENTITY_VERSION'; end if;
    else
        select version,status into v_version,v_status from app_private.plan_proposals
        where user_id=p_user_id and proposal_id=p_target_id;
        if not found or v_version<>p_target_version or v_status<>'PROPOSED' then raise exception using errcode='P0001', message='STALE_PROPOSAL'; end if;
    end if;
    insert into app_private.chat_approval_attestations
      (attestation_id,user_id,conversation_id,action_id,action_version,target_type,target_id,target_version,decision,source_message_id,request_fingerprint,expires_at)
    values (v_id,p_user_id,p_conversation_id,p_action_id,p_action_version,p_target_type,p_target_id,p_target_version,p_decision,p_source_message_id,p_request_fingerprint,v_expires);
    return jsonb_build_object('schema_version','1.1','attestation_id',v_id,'expires_at',v_expires);
end;
$$;

grant execute on function app_api.issue_chat_approval_attestation(uuid,uuid,uuid,integer,text,uuid,integer,text,uuid,text) to service_role;
