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
