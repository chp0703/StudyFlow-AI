-- WP2b-3 / migration 015: pending actions with server-side presentations, task confirmation
-- and task search. confirm_task is the first routine that writes official data: it commits the
-- ApprovalAction, AcademicTask, candidate backlink, action completion, schedule revision and
-- domain idempotency record together or not at all.

-- The approval-target trigger predates sf_rpc_owner and called auth.uid(), which that role cannot reach.
create or replace function app_private.validate_approval_action_target()
returns trigger language plpgsql security invoker set search_path = '' as $$
declare
    v_version bigint;
    v_status text;
begin
    if tg_op in ('DELETE', 'UPDATE') then
        raise exception using errcode = '42501', message = 'APPROVAL_ACTION_IMMUTABLE';
    end if;
    if app_private.current_uid() is distinct from new.user_id then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;
    if new.target_type = 'TASK_CANDIDATE' then
        select version, status into v_version, v_status from app_private.task_candidates
        where user_id = new.user_id and candidate_id = new.candidate_target_id;
        if not found then raise exception using errcode = 'P0001', message = 'ENTITY_NOT_FOUND'; end if;
        if v_version <> new.target_version or v_status <> 'DRAFT' then
            raise exception using errcode = 'P0001', message = 'STALE_ENTITY_VERSION';
        end if;
    elsif new.target_type = 'PENDING_ACTION' then
        select version, state into v_version, v_status from app_private.pending_actions
        where user_id = new.user_id and action_id = new.pending_action_target_id;
        if not found then raise exception using errcode = 'P0001', message = 'ENTITY_NOT_FOUND'; end if;
        if v_version <> new.target_version or v_status not in
            ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL') then
            raise exception using errcode = 'P0001', message = 'STALE_ENTITY_VERSION';
        end if;
    elsif new.target_type = 'PLAN_PROPOSAL' then
        select version, status into v_version, v_status from app_private.plan_proposals
        where user_id = new.user_id and proposal_id = new.proposal_target_id;
        if not found then raise exception using errcode = 'P0001', message = 'ENTITY_NOT_FOUND'; end if;
        if v_version <> new.target_version or v_status <> 'PROPOSED' then
            raise exception using errcode = 'P0001', message = 'STALE_PROPOSAL';
        end if;
    else
        raise exception using errcode = 'P0001', message = 'INVALID_PARAMETER';
    end if;
    return new;
end $$;

-- One awaiting action per conversation, enforced by the database.
create unique index ux_pending_one_awaiting_conversation
    on app_private.pending_actions (user_id, conversation_id)
    where state in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL');

-- ---------------------------------------------------------------- shared helpers
create function app_private.field_error(p_request jsonb, p_code text, p_message text, p_field text) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_set(app_private.error_result(p_request, p_code, p_message), '{error,field}', to_jsonb(p_field))
$$;

create function app_private.pending_json(p_action app_private.pending_actions) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('action_id', p_action.action_id, 'user_id', p_action.user_id,
        'conversation_id', p_action.conversation_id, 'version', p_action.version, 'intent', p_action.intent,
        'state', p_action.state, 'requires_review', p_action.requires_review, 'candidate_id', p_action.candidate_id,
        'proposal_id', p_action.proposal_id, 'draft_arguments', p_action.draft_arguments,
        'missing_fields', p_action.missing_fields, 'ambiguities', p_action.ambiguities,
        'depends_on_action_id', p_action.depends_on_action_id,
        'created_at', app_private.iso(p_action.created_at), 'updated_at', app_private.iso(p_action.updated_at))
$$;

create function app_private.task_json(p_task app_private.academic_tasks) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object('task_id', p_task.task_id, 'user_id', p_task.user_id, 'candidate_id', p_task.candidate_id,
        'version', p_task.version, 'title', p_task.title, 'description', p_task.description,
        'course_label', p_task.course_label,
        'available_from_at', case when p_task.available_from_at is null then null else app_private.iso(p_task.available_from_at) end,
        'deadline_at', app_private.iso(p_task.deadline_at), 'deadline_precision', p_task.deadline_precision,
        'deadline_date', p_task.deadline_date, 'deadline_timezone', p_task.deadline_timezone,
        'estimated_minutes', p_task.estimated_minutes, 'remaining_minutes', p_task.remaining_minutes,
        'priority', p_task.priority, 'status', p_task.status, 'confirmed_at', app_private.iso(p_task.confirmed_at),
        'created_at', app_private.iso(p_task.created_at), 'updated_at', app_private.iso(p_task.updated_at))
$$;

-- Opaque keyset cursor bound to owner and filter, authenticated with a key derived from the
-- active attestation key. Any edit, other owner or other filter is rejected (22023).
-- shortcut: rotating the signing key invalidates open cursors; callers restart the listing.
create function app_private.cursor_mac(p_payload text) returns text
language plpgsql security definer set search_path = '' as $$
declare v_key bytea;
begin
    select k.key_material into v_key from app_private.rpc_attestation_keys k
    where k.not_before <= clock_timestamp() and k.not_after > clock_timestamp()
    order by k.not_before desc, k.key_id limit 1;
    if v_key is null then
        raise exception using errcode = '42501', message = 'FORBIDDEN';
    end if;
    return encode(extensions.hmac(convert_to(p_payload, 'UTF8'),
                  extensions.hmac(convert_to('cursor-v1', 'UTF8'), v_key, 'sha256'), 'sha256'), 'hex');
end $$;

create function app_private.cursor_encode(p_user uuid, p_filter jsonb, p_position jsonb) returns text
language plpgsql security definer set search_path = '' as $$
declare v_body text := rtrim(translate(replace(encode(convert_to(app_private.canonical_json(
        jsonb_build_object('u', p_user, 'f', p_filter, 'p', p_position)), 'UTF8'), 'base64'), E'\n', ''), '+/', '-_'), '=');
begin
    return 'v1.' || v_body || '.' || app_private.cursor_mac(v_body);
end $$;

create function app_private.cursor_decode(p_user uuid, p_filter jsonb, p_cursor text) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_parts text[] := string_to_array(p_cursor, '.');
    v_nonce bytea := extensions.gen_random_bytes(32);
    v_payload jsonb;
begin
    if array_length(v_parts, 1) is distinct from 3 or v_parts[1] <> 'v1' or v_parts[2] !~ '^[A-Za-z0-9_-]+$'
       or extensions.hmac(convert_to(app_private.cursor_mac(v_parts[2]), 'UTF8'), v_nonce, 'sha256')
          is distinct from extensions.hmac(convert_to(v_parts[3], 'UTF8'), v_nonce, 'sha256') then
        raise exception using errcode = '22023', message = 'invalid cursor';
    end if;
    v_payload := convert_from(decode(translate(v_parts[2], '-_', '+/') || repeat('=', (4 - length(v_parts[2]) % 4) % 4),
                                     'base64'), 'UTF8')::jsonb;
    if v_payload ->> 'u' is distinct from p_user::text or v_payload -> 'f' is distinct from p_filter then
        raise exception using errcode = '22023', message = 'cursor does not match the request';
    end if;
    return v_payload -> 'p';
end $$;

-- Digest of what the user is shown: target triple, content and policy. Re-derived at decision time.
create function app_private.presentation_digest(p_action app_private.pending_actions, p_target_type text,
                                                p_target_id uuid, p_target_version bigint,
                                                p_presentation jsonb) returns text
language sql immutable set search_path = '' as $$
    select encode(extensions.digest(convert_to(app_private.canonical_json(jsonb_build_object(
        'intent', p_action.intent, 'state', p_action.state, 'draft_arguments', p_action.draft_arguments,
        'missing_fields', p_action.missing_fields, 'ambiguities', p_action.ambiguities,
        'target_type', p_target_type, 'target_id', p_target_id, 'target_version', p_target_version,
        'candidate_slots', p_presentation #> '{candidate,slots}', 'proposal', p_presentation -> 'proposal',
        'normalized_command', p_presentation -> 'normalized_command',
        'effective_policy', p_presentation -> 'effective_policy')), 'UTF8'), 'sha256'), 'hex')
$$;

-- Persists the presentation of an action version after checking it against the stored target.
-- Returns the authoritative presentation (pending_action rebuilt from the row) or an ErrorResult.
create function app_private.store_presentation(p_request jsonb, p_uid uuid, p_action app_private.pending_actions,
                                               p_presentation jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    c app_private.task_candidates;
    v_type text;
    v_target uuid;
    v_target_version bigint;
    v_message uuid := (p_request #>> '{execution_context,trusted_context,message_id}')::uuid;
    v_stored jsonb;
begin
    if p_action.candidate_id is not null then
        select * into c from app_private.task_candidates where user_id = p_uid and candidate_id = p_action.candidate_id;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The candidate was not found.');
        end if;
        if p_presentation -> 'candidate' is null or p_presentation -> 'candidate' = 'null'::jsonb
           or c.status <> 'DRAFT'
           or (c.version, c.slots) is distinct from ((p_presentation #>> '{candidate,version}')::bigint, p_presentation #> '{candidate,slots}') then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The presented candidate no longer matches the draft.');
        end if;
        v_type := 'TASK_CANDIDATE'; v_target := c.candidate_id; v_target_version := c.version;
    elsif p_action.proposal_id is not null then
        select p.version into v_target_version from app_private.plan_proposals p
        where p.user_id = p_uid and p.proposal_id = p_action.proposal_id and p.status = 'PROPOSED';
        if v_target_version is null then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The proposal was not found or is no longer pending.');
        end if;
        v_type := 'PLAN_PROPOSAL'; v_target := p_action.proposal_id;
    else
        v_type := 'PENDING_ACTION'; v_target := p_action.action_id; v_target_version := p_action.version;
    end if;
    v_stored := jsonb_set(p_presentation, '{pending_action}', app_private.pending_json(p_action));
    insert into app_private.action_presentations
        (user_id, action_id, action_version, target_type, target_id, target_version, content_digest, presentation,
         source_message_id)
    values (p_uid, p_action.action_id, p_action.version, v_type, v_target, v_target_version,
            app_private.presentation_digest(p_action, v_type, v_target, v_target_version, v_stored), v_stored,
            case when exists (select 1 from app_private.source_messages m where m.user_id = p_uid and m.message_id = v_message)
                 then v_message end);
    return null;
end $$;

-- ---------------------------------------------------------------- prepare / review / cancel
create function app_private.pending_precheck(p_request jsonb, p_uid uuid, p_pending jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
begin
    if p_pending ->> 'user_id' is distinct from p_uid::text
       or p_pending ->> 'conversation_id' is distinct from p_request #>> '{execution_context,conversation_id}' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER',
            'The action must belong to the authenticated owner and the request conversation.');
    end if;
    if p_pending ->> 'state' not in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL') then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'Only awaiting actions can be prepared.');
    end if;
    return null;
end $$;

create or replace function app_api.prepare_pending_action(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'prepare_pending_action', 'PreparePendingActionArguments');
    v_uid uuid;
    v_pres jsonb := p_request #> '{arguments,presentation}';
    v_pending jsonb := v_pres -> 'pending_action';
    v_expected bigint := (p_request #>> '{arguments,expected_action_version}')::bigint;
    a app_private.pending_actions;
    v_stored jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    v_error := app_private.pending_precheck(p_request, v_uid, v_pending);
    if v_error is not null then
        return v_error;
    end if;
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into a from app_private.pending_actions where user_id = v_uid and action_id = (v_pending ->> 'action_id')::uuid for update;
        if v_expected is null then
            if found then
                -- Lost-response retry: the same first version is already stored.
                select p.presentation into v_stored from app_private.action_presentations p
                where p.user_id = v_uid and p.action_id = a.action_id and p.action_version = a.version;
                if a.version = 1 and v_stored is not null and a.intent = v_pending ->> 'intent'
                   and a.draft_arguments = v_pending -> 'draft_arguments' then
                    return app_private.ok_result(p_request, 'COMMITTED', v_stored);
                end if;
                return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action already exists.');
            end if;
            if exists (select 1 from app_private.pending_actions x where x.user_id = v_uid
                       and x.conversation_id = (v_pending ->> 'conversation_id')::uuid
                       and x.state in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL')) then
                return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED',
                    'The conversation already has an awaiting action; review or cancel it first.');
            end if;
            insert into app_private.pending_actions
                (action_id, user_id, conversation_id, version, intent, state, requires_review, candidate_id, proposal_id,
                 draft_arguments, missing_fields, ambiguities, depends_on_action_id)
            values ((v_pending ->> 'action_id')::uuid, v_uid, (v_pending ->> 'conversation_id')::uuid, 1,
                    v_pending ->> 'intent', v_pending ->> 'state', false, (v_pending ->> 'candidate_id')::uuid,
                    (v_pending ->> 'proposal_id')::uuid, v_pending -> 'draft_arguments', v_pending -> 'missing_fields',
                    v_pending -> 'ambiguities', (v_pending ->> 'depends_on_action_id')::uuid)
            returning * into a;
        else
            if not found then
                return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The action was not found.');
            end if;
            if a.version = v_expected + 1 and a.state = v_pending ->> 'state'
               and a.draft_arguments = v_pending -> 'draft_arguments' and a.intent = v_pending ->> 'intent' then
                select p.presentation into v_stored from app_private.action_presentations p
                where p.user_id = v_uid and p.action_id = a.action_id and p.action_version = a.version;
                if v_stored is not null then
                    return app_private.ok_result(p_request, 'COMMITTED', v_stored);
                end if;
            end if;
            if a.version <> v_expected or a.state not in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL')
               or a.intent <> v_pending ->> 'intent' then
                return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action changed since it was read.');
            end if;
            update app_private.pending_actions
            set version = version + 1, state = v_pending ->> 'state', requires_review = false,
                candidate_id = (v_pending ->> 'candidate_id')::uuid, proposal_id = (v_pending ->> 'proposal_id')::uuid,
                draft_arguments = v_pending -> 'draft_arguments', missing_fields = v_pending -> 'missing_fields',
                ambiguities = v_pending -> 'ambiguities', depends_on_action_id = (v_pending ->> 'depends_on_action_id')::uuid
            where action_id = a.action_id returning * into a;
        end if;
        v_error := app_private.store_presentation(p_request, v_uid, a, v_pres);
        if v_error is not null then
            -- Roll the action write back with the failed presentation.
            raise exception using errcode = 'P0001', message = v_error #>> '{error,code}';
        end if;
        select p.presentation into v_stored from app_private.action_presentations p
        where p.user_id = v_uid and p.action_id = a.action_id and p.action_version = a.version;
        return app_private.ok_result(p_request, 'COMMITTED', v_stored);
    exception
        when sqlstate 'P0001' then
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_ENTITY_VERSION') then sqlerrm else 'INVALID_PARAMETER' end,
                'The presentation does not match the stored target.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;

create or replace function app_api.review_pending_action(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'review_pending_action', 'ReviewPendingActionArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_pres jsonb := p_request #> '{arguments,presentation}';
    a app_private.pending_actions;
    v_stored jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    v_error := app_private.pending_precheck(p_request, v_uid, v_pres -> 'pending_action');
    if v_error is not null then
        return v_error;
    end if;
    if v_pres #>> '{pending_action,action_id}' is distinct from v_args ->> 'action_id' then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The presentation is for a different action.');
    end if;
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into a from app_private.pending_actions
        where user_id = v_uid and action_id = (v_args ->> 'action_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The action was not found.');
        end if;
        -- A retry after a lost response finds the review already applied one version ahead.
        if a.version = (v_args ->> 'expected_action_version')::bigint + 1 and not a.requires_review then
            select p.presentation into v_stored from app_private.action_presentations p
            where p.user_id = v_uid and p.action_id = a.action_id and p.action_version = a.version;
            if v_stored is not null then
                return app_private.ok_result(p_request, 'COMMITTED', v_stored);
            end if;
        end if;
        if a.version <> (v_args ->> 'expected_action_version')::bigint
           or a.state not in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL') then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action changed since it was read.');
        end if;
        if not a.requires_review then
            select p.presentation into v_stored from app_private.action_presentations p
            where p.user_id = v_uid and p.action_id = a.action_id and p.action_version = a.version;
            if v_stored is not null then
                return app_private.ok_result(p_request, 'COMMITTED', v_stored);
            end if;
        end if;
        update app_private.pending_actions set version = version + 1, requires_review = false
        where action_id = a.action_id returning * into a;
        v_error := app_private.store_presentation(p_request, v_uid, a, v_pres);
        if v_error is not null then
            raise exception using errcode = 'P0001', message = v_error #>> '{error,code}';
        end if;
        select p.presentation into v_stored from app_private.action_presentations p
        where p.user_id = v_uid and p.action_id = a.action_id and p.action_version = a.version;
        return app_private.ok_result(p_request, 'COMMITTED', v_stored);
    exception
        when sqlstate 'P0001' then
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_ENTITY_VERSION') then sqlerrm else 'INVALID_PARAMETER' end,
                'The presentation does not match the stored target.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- cancel: the user rejected the draft. No official data is written and no ApprovalAction is created.
create or replace function app_api.cancel_pending_action(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'cancel_pending_action', 'CancelPendingActionArguments');
    v_uid uuid;
    v_ref jsonb := p_request #> '{arguments,action_reference}';
    v_candidate uuid := (p_request #>> '{arguments,candidate_id}')::uuid;
    a app_private.pending_actions;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        perform app_private.lock_owner(v_uid, p_request);
        select * into a from app_private.pending_actions
        where user_id = v_uid and action_id = (v_ref ->> 'action_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The action was not found.');
        end if;
        if a.state = 'CANCELLED' and a.version = (v_ref ->> 'action_version')::bigint + 1 then
            return app_private.ok_result(p_request, 'COMMITTED', app_private.pending_json(a));
        end if;
        if a.version <> (v_ref ->> 'action_version')::bigint
           or a.state not in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL') then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action changed since it was read.');
        end if;
        if v_candidate is not null then
            if a.candidate_id is distinct from v_candidate then
                return app_private.error_result(p_request, 'INVALID_PARAMETER', 'The candidate does not belong to this action.');
            end if;
            update app_private.task_candidates set status = 'CANCELLED', version = version + 1
            where user_id = v_uid and candidate_id = v_candidate and status = 'DRAFT';
        end if;
        update app_private.pending_actions set state = 'CANCELLED', version = version + 1
        where action_id = a.action_id returning * into a;
        return app_private.ok_result(p_request, 'COMMITTED', app_private.pending_json(a));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- ---------------------------------------------------------------- confirm_task
create or replace function app_api.confirm_task(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'confirm_task', 'confirm_taskArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_ctx jsonb := p_request -> 'execution_context';
    v_approval jsonb := v_ctx -> 'approval_action';
    v_ref jsonb := v_ctx -> 'action_reference';
    v_key text := v_ctx ->> 'idempotency_key';
    v_conv uuid := (v_ctx ->> 'conversation_id')::uuid;
    v_binding jsonb;
    v_fp text;
    v_reply jsonb;
    c app_private.task_candidates;
    a app_private.pending_actions;
    p app_private.action_presentations;
    t app_private.academic_tasks;
    v_slots jsonb;
    v_precision text;
    v_tz text;
    v_date date;
    v_deadline timestamptz;
    v_title text;
    v_minutes bigint;
    v_missing text;
    v_result jsonb;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    if v_key is null or v_conv is null then
        return app_private.error_result(p_request, 'INVALID_PARAMETER', 'An idempotency key and a conversation are required.');
    end if;
    -- The approval comes from the backend context and must name exactly this candidate and version.
    if jsonb_typeof(v_approval) is distinct from 'object' or jsonb_typeof(v_ref) is distinct from 'object'
       or v_approval ->> 'decision' <> 'APPROVE' or v_approval ->> 'target_type' <> 'TASK_CANDIDATE'
       or v_approval ->> 'user_id' <> v_uid::text
       or v_approval ->> 'target_id' <> v_args ->> 'candidate_id'
       or (v_approval ->> 'target_version')::bigint <> (v_args ->> 'expected_candidate_version')::bigint
       or v_ref ->> 'target_type' <> 'TASK_CANDIDATE' or v_ref ->> 'target_id' <> v_args ->> 'candidate_id'
       or (v_ref ->> 'target_version')::bigint <> (v_args ->> 'expected_candidate_version')::bigint then
        return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'A matching approval for this candidate version is required.');
    end if;
    v_binding := jsonb_build_object('decision', 'APPROVE', 'action_id', v_ref -> 'action_id',
        'action_version', v_ref -> 'action_version', 'target_type', 'TASK_CANDIDATE',
        'target_id', v_args -> 'candidate_id', 'target_version', v_args -> 'expected_candidate_version');
    v_fp := app_private.domain_fingerprint(v_uid, 'confirm_task', v_args, v_binding);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'confirm_task', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'confirm_task', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;

        -- CHAT approval needs a recorded USER message from the same owner and conversation.
        if v_approval ->> 'source' = 'CHAT' and not exists (
               select 1 from app_private.source_messages m
               where m.user_id = v_uid and m.conversation_id = v_conv and m.role = 'USER'
                 and m.message_id = (v_approval ->> 'source_message_id')::uuid) then
            return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'A chat approval needs a recorded user message.');
        end if;

        select * into c from app_private.task_candidates
        where user_id = v_uid and candidate_id = (v_args ->> 'candidate_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The candidate was not found.');
        end if;
        if c.status <> 'DRAFT' or c.version <> (v_args ->> 'expected_candidate_version')::bigint then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The candidate changed since it was presented.');
        end if;
        select * into a from app_private.pending_actions
        where user_id = v_uid and action_id = (v_ref ->> 'action_id')::uuid for update;
        if not found or a.candidate_id is distinct from c.candidate_id or a.conversation_id <> v_conv then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The action for this candidate was not found.');
        end if;
        if a.requires_review then
            return app_private.error_result(p_request, 'ACTION_REVIEW_REQUIRED', 'The action must be reviewed before it can be approved.');
        end if;
        if a.version <> (v_ref ->> 'action_version')::bigint or a.state <> 'AWAITING_CONFIRMATION' then
            return app_private.error_result(p_request, 'STALE_ENTITY_VERSION', 'The action changed since it was presented.');
        end if;
        select * into p from app_private.action_presentations
        where user_id = v_uid and action_id = a.action_id and action_version = a.version;
        if not found or p.target_type <> 'TASK_CANDIDATE' or p.target_id <> c.candidate_id or p.target_version <> c.version
           or p.content_digest <> app_private.presentation_digest(a, 'TASK_CANDIDATE', c.candidate_id, c.version, p.presentation) then
            return app_private.error_result(p_request, 'APPROVAL_REQUIRED', 'The approved content was not presented by the server.');
        end if;

        -- Validate the candidate is complete and normalize the deadline (DATE means end of that local day).
        v_slots := c.slots;
        v_title := nullif(btrim(v_slots ->> 'title'), '');
        v_precision := v_slots ->> 'deadline_precision';
        v_tz := v_slots ->> 'deadline_timezone';
        v_minutes := (v_slots ->> 'estimated_minutes')::bigint;
        v_missing := case when v_title is null then 'title' when v_precision is null then 'deadline_precision'
            when v_tz is null then 'deadline_timezone' when v_minutes is null then 'estimated_minutes'
            when v_precision = 'DATE' and v_slots ->> 'deadline_date' is null then 'deadline_date'
            when v_precision = 'DATETIME' and v_slots ->> 'deadline_at' is null then 'deadline_at' end;
        if v_missing is not null then
            return app_private.field_error(p_request, 'MISSING_REQUIRED_FIELD', 'The candidate is missing a required field.', v_missing);
        end if;
        if not exists (select 1 from pg_catalog.pg_timezone_names n where n.name = v_tz) then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'Unknown time zone.', 'deadline_timezone');
        end if;
        if v_precision = 'DATE' then
            v_date := (v_slots ->> 'deadline_date')::date;
            v_deadline := (v_date + 1)::timestamp at time zone v_tz;
            if v_slots ->> 'deadline_at' is not null and (v_slots ->> 'deadline_at')::timestamptz <> v_deadline then
                return app_private.field_error(p_request, 'INVALID_PARAMETER',
                    'A date-only deadline ends at the start of the next local day.', 'deadline_at');
            end if;
        else
            v_deadline := (v_slots ->> 'deadline_at')::timestamptz;
            if v_slots ->> 'deadline_date' is not null then
                return app_private.field_error(p_request, 'INVALID_PARAMETER', 'A date-time deadline has no deadline_date.', 'deadline_date');
            end if;
        end if;
        if v_slots ->> 'available_from_at' is not null and (v_slots ->> 'available_from_at')::timestamptz > v_deadline then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'available_from_at is after the deadline.', 'available_from_at');
        end if;

        -- One atomic commit; the typed-target trigger sees the candidate still in DRAFT.
        insert into app_private.approval_actions
            (approval_action_id, user_id, target_type, target_id, target_version, decision, source, source_message_id,
             candidate_target_id)
        values ((v_approval ->> 'approval_action_id')::uuid, v_uid, 'TASK_CANDIDATE', c.candidate_id, c.version, 'APPROVE',
                v_approval ->> 'source', (v_approval ->> 'source_message_id')::uuid, c.candidate_id);
        insert into app_private.academic_tasks
            (task_id, user_id, candidate_id, title, description, course_label, available_from_at, deadline_at,
             deadline_precision, deadline_date, deadline_timezone, estimated_minutes, remaining_minutes, priority, status)
        values (extensions.gen_random_uuid(), v_uid, c.candidate_id, v_title, v_slots ->> 'description',
                nullif(btrim(v_slots ->> 'course_label'), ''), (v_slots ->> 'available_from_at')::timestamptz, v_deadline,
                v_precision, v_date, v_tz, v_minutes, v_minutes, coalesce(v_slots ->> 'priority', 'NORMAL'), 'TODO')
        returning * into t;
        update app_private.task_candidates set status = 'CONFIRMED', confirmed_task_id = t.task_id, version = version + 1
        where candidate_id = c.candidate_id;
        update app_private.pending_actions set state = 'COMPLETED', version = version + 1 where action_id = a.action_id;
        update app_private.user_profiles set schedule_revision = schedule_revision + 1 where user_id = v_uid;
        v_result := app_private.ok_result(p_request, 'COMMITTED', app_private.task_json(t));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'confirm_task', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception
        when sqlstate 'P0001' then
            -- Raised by the approval-target trigger when a concurrent change made the target stale.
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_ENTITY_VERSION') then sqlerrm else 'INVALID_PARAMETER' end,
                'The approval target is no longer valid.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- ---------------------------------------------------------------- search_tasks
create or replace function app_api.search_tasks(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'search_tasks', 'search_tasksArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_statuses text[];
    v_query text := nullif(btrim(v_args ->> 'query'), '');
    v_size int := (v_args ->> 'page_size')::int;
    v_filter jsonb;
    v_pos jsonb;
    v_like text;
    v_items jsonb;
    v_more boolean;
    v_last_at text;
    v_last_id text;
    v_next text;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    begin
        select coalesce(array_agg(distinct s.value order by s.value), '{}') into v_statuses
        from jsonb_array_elements_text(v_args -> 'status_filter') s;
        v_filter := jsonb_build_object('q', v_query, 's', to_jsonb(v_statuses));
        v_like := '%' || replace(replace(replace(coalesce(v_query, ''), '\', '\\'), '%', '\%'), '_', '\_') || '%';
        if v_args ->> 'cursor' is not null then
            v_pos := app_private.cursor_decode(v_uid, v_filter, v_args ->> 'cursor');
        end if;
        with page as (
            select x as t, row_number() over (order by x.deadline_at, x.task_id) rn
            from app_private.academic_tasks x
            where x.user_id = v_uid
              and (cardinality(v_statuses) = 0 or x.status = any (v_statuses))
              and (v_query is null or x.title ilike v_like escape '\' or x.course_label ilike v_like escape '\'
                   or x.description ilike v_like escape '\')
              and (v_pos is null or (x.deadline_at, x.task_id) > ((v_pos ->> 0)::timestamptz, (v_pos ->> 1)::uuid))
            order by x.deadline_at, x.task_id limit v_size + 1
        )
        select coalesce(jsonb_agg(app_private.task_json(p.t) order by p.rn) filter (where p.rn <= v_size), '[]'::jsonb),
               max(p.rn) > v_size,
               max(app_private.iso((p.t).deadline_at)) filter (where p.rn = v_size),
               max(((p.t).task_id)::text) filter (where p.rn = v_size)
        into v_items, v_more, v_last_at, v_last_id from page p;
        if v_more then
            v_next := app_private.cursor_encode(v_uid, v_filter, jsonb_build_array(v_last_at, v_last_id));
        end if;
        return app_private.ok_result(p_request, 'READ', jsonb_build_object('items', v_items, 'next_cursor', v_next));
    exception when others then
        return app_private.failure(p_request, sqlstate);
    end;
end $$;

-- Ownership and grants for the new helpers.
alter function app_private.field_error(jsonb, text, text, text) owner to sf_rpc_owner;
alter function app_private.pending_json(app_private.pending_actions) owner to sf_rpc_owner;
alter function app_private.task_json(app_private.academic_tasks) owner to sf_rpc_owner;
alter function app_private.cursor_mac(text) owner to sf_rpc_owner;
alter function app_private.cursor_encode(uuid, jsonb, jsonb) owner to sf_rpc_owner;
alter function app_private.cursor_decode(uuid, jsonb, text) owner to sf_rpc_owner;
alter function app_private.presentation_digest(app_private.pending_actions, text, uuid, bigint, jsonb) owner to sf_rpc_owner;
alter function app_private.store_presentation(jsonb, uuid, app_private.pending_actions, jsonb) owner to sf_rpc_owner;
alter function app_private.pending_precheck(jsonb, uuid, jsonb) owner to sf_rpc_owner;
alter function app_private.validate_approval_action_target() owner to sf_rpc_owner;
revoke all on function app_private.field_error(jsonb, text, text, text), app_private.pending_json(app_private.pending_actions),
    app_private.task_json(app_private.academic_tasks), app_private.cursor_mac(text),
    app_private.cursor_encode(uuid, jsonb, jsonb), app_private.cursor_decode(uuid, jsonb, text),
    app_private.presentation_digest(app_private.pending_actions, text, uuid, bigint, jsonb),
    app_private.store_presentation(jsonb, uuid, app_private.pending_actions, jsonb),
    app_private.pending_precheck(jsonb, uuid, jsonb), app_private.validate_approval_action_target()
    from public, anon, authenticated;
