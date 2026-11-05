-- WP2a / migration 011: security boundary for the approved 27-wrapper inventory.
-- 1. removes legacy overloads and bypass helpers, 2. moves row access from client roles to
-- sf_rpc_owner under FORCE RLS, 3. installs fail-closed wrappers that WP2b/2c replace.
-- Business state is preserved: no table is dropped or altered.

-- 1. Legacy surface. The old multi-argument RPCs, the CHAT attestation issuer/consumer and
-- the helpers that only served them are removed; the attestation table keeps its rows.
do $$
declare f record;
begin
    for f in select p.oid::regprocedure as sig from pg_proc p
             where p.pronamespace = 'app_api'::regnamespace loop
        execute format('drop function %s', f.sig);
    end loop;
    for f in select p.oid::regprocedure as sig from pg_proc p
             where p.pronamespace = 'app_private'::regnamespace
               and p.proname in ('consume_chat_attestation', 'idempotency_begin', 'idempotency_complete',
                                 'lock_owner', 'owner_lock_key', 'require_owner', 'upsert_time_window') loop
        execute format('drop function %s', f.sig);
    end loop;
end $$;

-- 2. Client roles lose every private privilege; sf_rpc_owner receives the least set the
-- wrappers touch. Immutable snapshot tables are insert-only.
revoke usage on schema app_private from public, anon, authenticated;
revoke create on schema app_private, app_api from public, anon, authenticated;
revoke all on all tables in schema app_private from public, anon, authenticated;
revoke all on all sequences in schema app_private from public, anon, authenticated;
revoke all on all functions in schema app_private from public, anon, authenticated;
alter default privileges in schema app_private revoke all on tables from public, anon, authenticated;
alter default privileges in schema app_private revoke all on functions from public, anon, authenticated;
alter default privileges in schema app_api revoke all on functions from public, anon;
grant usage on schema app_api to authenticated;

do $$
declare p record;
begin
    for p in select policyname, tablename from pg_policies where schemaname = 'app_private' loop
        execute format('drop policy %I on app_private.%I', p.policyname, p.tablename);
    end loop;
end $$;

-- user_id-scoped tables: [table, privileges the wrappers need].
do $$
declare t record;
begin
    for t in select * from (values
        ('user_profiles', array['select', 'insert', 'update']),
        ('task_candidates', array['select', 'insert', 'update']),
        ('academic_tasks', array['select', 'insert']),
        ('time_windows', array['select', 'insert', 'update']),
        ('study_plans', array['select', 'insert']),
        ('study_blocks', array['select', 'insert']),
        ('plan_proposals', array['select', 'insert', 'update']),
        ('pending_actions', array['select', 'insert', 'update']),
        ('approval_actions', array['select', 'insert']),
        ('idempotency_records', array['select', 'insert', 'update']),
        ('conversation_records', array['select', 'insert']),
        ('source_messages', array['select', 'insert']),
        ('api_request_receipts', array['select', 'insert', 'update']),
        ('action_presentations', array['select', 'insert']),
        ('workflow_continuations', array['select', 'insert', 'update'])
    ) v(name, privs) loop
        execute format('grant %s on app_private.%I to sf_rpc_owner', array_to_string(t.privs, ', '), t.name);
        execute format('create policy %I on app_private.%I for select to sf_rpc_owner using (user_id = app_private.current_uid())',
                       t.name || '_owner_select', t.name);
        if 'insert' = any (t.privs) then
            execute format('create policy %I on app_private.%I for insert to sf_rpc_owner with check (app_private.current_uid() is not null and user_id = app_private.current_uid())',
                           t.name || '_owner_insert', t.name);
        end if;
        if 'update' = any (t.privs) then
            execute format('create policy %I on app_private.%I for update to sf_rpc_owner using (user_id = app_private.current_uid()) with check (user_id = app_private.current_uid())',
                           t.name || '_owner_update', t.name);
        end if;
    end loop;
end $$;

-- The global key store is read-only for the verifier and has no user_id.
grant select on app_private.rpc_attestation_keys to sf_rpc_owner;
create policy rpc_keys_verifier_select on app_private.rpc_attestation_keys
    for select to sf_rpc_owner using (true);
revoke all on app_private.chat_approval_attestations from public, anon, authenticated, sf_rpc_owner;

-- Functions the DEFINER wrappers call: nothing else is granted to sf_rpc_owner.
grant execute on function app_private.current_uid() to sf_rpc_owner;
grant execute on function app_private.touch_updated_at() to sf_rpc_owner;
alter function app_private.touch_updated_at() owner to sf_rpc_owner;
alter function app_private.validate_approval_action_target() owner to sf_rpc_owner;
alter function app_private.workflow_continuation_immutable() owner to sf_rpc_owner;
revoke all on function app_private.touch_updated_at(), app_private.validate_approval_action_target(),
    app_private.workflow_continuation_immutable() from public, anon, authenticated;

-- 3. Fail-closed wrappers: 21 approved + 6 added internal helpers (all p_request jsonb).
-- Each verifies the request exactly as a real wrapper will, then reports the routine as not
-- implemented. Replaced by `create or replace` in WP2b/WP2c; never returns fake success.
do $$
declare name text;
begin
    foreach name in array array[
        'create_task_candidate', 'confirm_task', 'search_tasks', 'set_availability',
        'set_busy_interval', 'set_scheduling_preferences', 'get_study_plan', 'approve_study_plan',
        'reject_study_plan', 'get_scheduling_context', 'persist_plan_proposal',
        'prepare_pending_action', 'review_pending_action', 'update_candidate_draft',
        'cancel_pending_action', 'record_source_message', 'claim_api_receipt',
        'complete_api_receipt', 'lookup_operation_result', 'renew_api_receipt',
        'release_api_receipt', 'ensure_user_context', 'list_time_windows',
        'get_workflow_context', 'get_workflow_continuation',
        'initialize_workflow_continuation', 'checkpoint_workflow_continuation']
    loop
        execute format($f$
            create function app_api.%1$I(p_request jsonb) returns jsonb
            language plpgsql security definer set search_path = '' as $b$
            begin
                return coalesce(app_private.security_error(p_request, %1$L),
                    app_private.error_result(p_request, 'UNSUPPORTED_OPERATION',
                        'This database routine is not implemented yet.'));
            end $b$
            $f$, name);
        execute format('alter function app_api.%I(jsonb) owner to sf_rpc_owner', name);
        execute format('revoke all on function app_api.%I(jsonb) from public, anon', name);
        execute format('grant execute on function app_api.%I(jsonb) to authenticated', name);
    end loop;
end $$;
