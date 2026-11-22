-- Local-only F3 M4 + M5 pgTAP tests (summary -> decision -> SessionOutcome, 30-day retention). Rolled back after test.
begin;
select no_plan();
set local search_path = public, extensions;

create function pg_temp.m4_call(
    op text,
    args jsonb,
    uid uuid default 'd3440000-0000-4000-8000-000000000001',
    idem text default null,
    conversation uuid default null,
    approval jsonb default null,
    ref jsonb default null
) returns jsonb language plpgsql as $$
declare
    res jsonb;
    stamp timestamptz := clock_timestamp();
    payload text;
    req jsonb := jsonb_build_object(
        'contract_version', '1.0.1', 'schema_version', '1.1', 'request_id', 'm4-pgtap-request',
        'operation', op, 'arguments', args, 'attestation', null,
        'execution_context', jsonb_build_object(
            'conversation_id', conversation, 'idempotency_key', idem,
            'approval_action', approval, 'action_reference', ref,
            'trusted_context', jsonb_build_object(
                'request_id', 'm4-pgtap-request', 'message_id', 'd3440000-0000-4000-8000-000000000099',
                'principal', jsonb_build_object('user_id', uid), 'timezone', 'Asia/Ho_Chi_Minh',
                'locale', 'vi-VN', 'received_at', app_private.iso(stamp))));
begin
    if not app_private.rpc_is_read(op) then
        payload := rtrim(translate(replace(encode(convert_to(app_private.canonical_json(jsonb_build_object(
            'v', 1, 'key_id', 'm4-test-key', 'user_id', uid::text, 'rpc', op, 'request_id', 'm4-pgtap-request',
            'request_digest', encode(extensions.digest(convert_to(app_private.canonical_json(req - 'attestation'), 'UTF8'), 'sha256'), 'hex'),
            'issued_at', app_private.iso(stamp), 'expires_at', app_private.iso(stamp + interval '60 seconds'))), 'UTF8'), 'base64'),
            E'\n', ''), '+/', '-_'), '=');
        req := jsonb_set(req, '{attestation}', jsonb_build_object('key_id', 'm4-test-key', 'payload', payload,
            'signature', encode(extensions.hmac(convert_to(payload, 'UTF8'), decode(repeat('44', 32), 'hex'), 'sha256'), 'hex')));
    end if;
    perform set_config('request.jwt.claims', jsonb_build_object('sub', uid, 'role', 'authenticated')::text, true);
    perform set_config('request.jwt.claim.sub', uid::text, true);
    set local role authenticated;
    begin
        execute format('select app_api.%I($1)', op) into res using req;
    exception when others then
        res := jsonb_build_object('sqlstate', sqlstate, 'message', sqlerrm);
    end;
    reset role;
    return res;
end
$$;

create function pg_temp.m4_approval(uid uuid, ref jsonb, decision text) returns jsonb language sql as $$
    select jsonb_build_object('approval_action_id', gen_random_uuid(), 'user_id', uid, 'target_type', 'PENDING_ACTION',
        'target_id', ref ->> 'action_id', 'target_version', (ref ->> 'action_version')::bigint, 'decision', decision,
        'source', 'UI', 'source_message_id', null, 'created_at', app_private.iso(clock_timestamp()))
$$;

-- Session with two turns, created directly so the test does not depend on M1 indexing.
create function pg_temp.m4_session(sid uuid, uid uuid, conv uuid, expires timestamptz default null) returns void language sql as $$
    insert into app_private.conversation_records(user_id, conversation_id) values (uid, conv);
    insert into app_private.learning_session(session_id, user_id, conversation_id, goal, material_ids, created_at, expires_at)
    values (sid, uid, conv, 'Ôn tính chẵn lẻ', array['d3440000-0000-4000-8000-0000000000aa'::uuid],
            clock_timestamp() - interval '40 days', coalesce(expires, clock_timestamp() + interval '30 days'));
    insert into app_private.learning_turn(user_id, session_id, ordinal, role, kind, content, supported, created_at) values
        (uid, sid, 1, 'USER', 'ASK', 'Số chẵn là gì?', null, now() - interval '10 minutes'),
        (uid, sid, 2, 'ASSISTANT', 'ASK', 'Tài liệu hiện có không đủ căn cứ để trả lời câu này', false, now() - interval '6 minutes');
$$;

insert into auth.users(id) values ('d3440000-0000-4000-8000-000000000001'), ('d3440000-0000-4000-8000-000000000002');
insert into app_private.user_profiles(user_id, timezone, locale, scheduling_policy)
select u, 'Asia/Ho_Chi_Minh', 'vi', app_private.default_policy()
from unnest(array['d3440000-0000-4000-8000-000000000001', 'd3440000-0000-4000-8000-000000000002']::uuid[]) u
on conflict do nothing;
insert into app_private.rpc_attestation_keys(key_id, key_material, not_before, not_after)
values ('m4-test-key', decode(repeat('44', 32), 'hex'), clock_timestamp() - interval '1 hour', clock_timestamp() + interval '1 hour');

select pg_temp.m4_session('d3440000-0000-4000-8000-000000000101', 'd3440000-0000-4000-8000-000000000001', 'd3440000-0000-4000-8000-000000000201');
select pg_temp.m4_session('d3440000-0000-4000-8000-000000000102', 'd3440000-0000-4000-8000-000000000001', 'd3440000-0000-4000-8000-000000000202');
create temporary table m4 (label text primary key, val jsonb);
grant all on m4 to authenticated;

-- 1. Boundary
select ok(not has_table_privilege('authenticated', 'app_private.session_outcome', 'INSERT'),
    'authenticated cannot insert session_outcome directly');
select ok(not has_function_privilege('anon', 'app_api.decide_learning_session_outcome(jsonb)', 'EXECUTE'),
    'anon cannot decide a session outcome');
select ok(not has_function_privilege('anon', 'app_api.purge_expired_learning(jsonb)', 'EXECUTE'), 'anon cannot purge');

-- 2. Summary drafting
select is(pg_temp.m4_call('prepare_learning_summary', jsonb_build_object(
    'session_id', 'd3440000-0000-4000-8000-000000000101', 'fingerprint', repeat('1', 64),
    'expected_session_version', 9, 'summary', 'x', 'topics', '[]'::jsonb), idem => 'm4-summary-stale-01') #>> '{error,code}',
    'STALE_ENTITY_VERSION', 'summary with an old session version is stale');

insert into m4 select 'draft', pg_temp.m4_call('prepare_learning_summary', jsonb_build_object(
    'session_id', 'd3440000-0000-4000-8000-000000000101', 'fingerprint', repeat('2', 64),
    'expected_session_version', 1, 'summary', 'Đã hỏi về số chẵn.', 'topics', '["Tính chẵn lẻ"]'::jsonb),
    idem => 'm4-summary-ok-0001');
select is((select val ->> 'outcome' from m4 where label = 'draft'), 'DRAFTED', 'summary returns DRAFTED');
select is((select val #>> '{data,session,status}' from m4 where label = 'draft'), 'SUMMARY_PENDING', 'session moves to SUMMARY_PENDING');
select is((select (val #>> '{data,draft,duration_minutes}')::int from m4 where label = 'draft'), 4,
    'duration comes from turn timestamps, not the model');
select is((select val #>> '{data,action_reference,target_type}' from m4 where label = 'draft'), 'PENDING_ACTION',
    'summary returns a pending-action reference');
select ok(app_private.matches_contract('PrepareLearningSummaryResult', (select val from m4 where label = 'draft')),
    'summary result matches contract');
select is(pg_temp.m4_call('prepare_learning_summary', jsonb_build_object(
    'session_id', 'd3440000-0000-4000-8000-000000000101', 'fingerprint', repeat('2', 64),
    'expected_session_version', 1, 'summary', 'khác', 'topics', '[]'::jsonb), idem => 'm4-summary-ok-0001') #>> '{data,replayed}',
    'true', 'same key replays the stored summary');
select is(pg_temp.m4_call('prepare_learning_summary', jsonb_build_object(
    'session_id', 'd3440000-0000-4000-8000-000000000101', 'fingerprint', repeat('3', 64),
    'expected_session_version', 2, 'summary', 'x', 'topics', '[]'::jsonb), idem => 'm4-summary-dup-0001') #>> '{error,code}',
    'TIME_CONFLICT', 'a pending session cannot be summarized again');
insert into m4 select 'ref', val #> '{data,action_reference}' from m4 where label = 'draft';

-- 3. Decision
select is(pg_temp.m4_call('decide_learning_session_outcome', '{"decision":"APPROVE"}', idem => 'm4-decide-noref-01',
    conversation => 'd3440000-0000-4000-8000-000000000201') #>> '{error,code}',
    'APPROVAL_REQUIRED', 'decision without approval/action reference is refused');
select is(pg_temp.m4_call('decide_learning_session_outcome', '{"decision":"APPROVE"}', idem => 'm4-decide-stale-01',
    conversation => 'd3440000-0000-4000-8000-000000000201',
    approval => pg_temp.m4_approval('d3440000-0000-4000-8000-000000000001',
        (select val || '{"action_version":2,"target_version":2}' from m4 where label = 'ref'), 'APPROVE'),
    ref => (select val || '{"action_version":2,"target_version":2}' from m4 where label = 'ref')) #>> '{error,code}',
    'STALE_ENTITY_VERSION', 'modified action version is stale');
select is(pg_temp.m4_call('decide_learning_session_outcome', '{"decision":"APPROVE"}',
    'd3440000-0000-4000-8000-000000000002', 'm4-decide-other-01', 'd3440000-0000-4000-8000-000000000201',
    pg_temp.m4_approval('d3440000-0000-4000-8000-000000000002', (select val from m4 where label = 'ref'), 'APPROVE'),
    (select val from m4 where label = 'ref')) #>> '{error,code}',
    'ENTITY_NOT_FOUND', 'another user cannot decide this outcome');

insert into m4 select 'approved', pg_temp.m4_call('decide_learning_session_outcome', '{"decision":"APPROVE"}',
    idem => 'm4-decide-ok-00001', conversation => 'd3440000-0000-4000-8000-000000000201',
    approval => pg_temp.m4_approval('d3440000-0000-4000-8000-000000000001', (select val from m4 where label = 'ref'), 'APPROVE'),
    ref => (select val from m4 where label = 'ref'));
select is((select val ->> 'outcome' from m4 where label = 'approved'), 'COMMITTED', 'approve commits');
select is((select val #>> '{data,session,status}' from m4 where label = 'approved'), 'CLOSED', 'approve closes the session');
select is((select val #>> '{data,session_outcome,summary}' from m4 where label = 'approved'), 'Đã hỏi về số chẵn.',
    'outcome stores the reviewed draft');
select ok(app_private.matches_contract('DecideLearningSessionOutcomeResult', (select val from m4 where label = 'approved')),
    'decision result matches contract');
select is((select count(*)::int from app_private.session_outcome where session_id = 'd3440000-0000-4000-8000-000000000101'), 1,
    'exactly one outcome exists');
select is(pg_temp.m4_call('decide_learning_session_outcome', '{"decision":"APPROVE"}',
    idem => 'm4-decide-again-01', conversation => 'd3440000-0000-4000-8000-000000000201',
    approval => pg_temp.m4_approval('d3440000-0000-4000-8000-000000000001', (select val from m4 where label = 'ref'), 'APPROVE'),
    ref => (select val from m4 where label = 'ref')) #>> '{error,code}',
    'STALE_ENTITY_VERSION', 'an already decided reference cannot be reused with a new key');
select throws_ok($$update app_private.session_outcome set summary = 'sửa' where session_id = 'd3440000-0000-4000-8000-000000000101'$$,
    '23514', null, 'session outcome is immutable');

-- 4. Reject reopens and allows a fresh summary
insert into m4 select 'draft2', pg_temp.m4_call('prepare_learning_summary', jsonb_build_object(
    'session_id', 'd3440000-0000-4000-8000-000000000102', 'fingerprint', repeat('4', 64),
    'expected_session_version', 1, 'summary', 'Bản nháp 1.', 'topics', '[]'::jsonb), idem => 'm4-summary-b-00001');
insert into m4 select 'rejected', pg_temp.m4_call('decide_learning_session_outcome', '{"decision":"REJECT"}',
    idem => 'm4-reject-b-000001', conversation => 'd3440000-0000-4000-8000-000000000202',
    approval => pg_temp.m4_approval('d3440000-0000-4000-8000-000000000001', (select val #> '{data,action_reference}' from m4 where label = 'draft2'), 'REJECT'),
    ref => (select val #> '{data,action_reference}' from m4 where label = 'draft2'));
select is((select val ->> 'outcome' from m4 where label = 'rejected'), 'REJECTED', 'reject returns REJECTED');
select is((select val #>> '{data,session,status}' from m4 where label = 'rejected'), 'ACTIVE', 'reject reopens the session');
select is((select val #> '{data,session_outcome}' from m4 where label = 'rejected'), 'null'::jsonb, 'reject creates no outcome');
select is(pg_temp.m4_call('prepare_learning_summary', jsonb_build_object(
    'session_id', 'd3440000-0000-4000-8000-000000000102', 'fingerprint', repeat('5', 64),
    'expected_session_version', 3, 'summary', 'Bản nháp 2.', 'topics', '[]'::jsonb), idem => 'm4-summary-b-00002') ->> 'outcome',
    'DRAFTED', 'a rejected session can be summarized again');

-- 4b. An expired session that was not purged yet rejects writes and keeps its expiry.
select pg_temp.m4_session('d3440000-0000-4000-8000-000000000104', 'd3440000-0000-4000-8000-000000000001',
    'd3440000-0000-4000-8000-000000000204', clock_timestamp() - interval '1 minute');
select is(pg_temp.m4_call('append_learning_turn', jsonb_build_object(
    'session_id', 'd3440000-0000-4000-8000-000000000104', 'fingerprint', repeat('6', 64), 'expected_last_ordinal', 2,
    'kind', 'ASK', 'user_content', 'Hỏi tiếp', 'assistant_content', 'Tài liệu hiện có không đủ căn cứ để trả lời câu này',
    'hint_level', null, 'citations', '[]'::jsonb, 'supported', false, 'model', null, 'prompt_version', null),
    idem => 'm4-expired-turn-0001') #>> '{error,details,reason}', 'SESSION_EXPIRED', 'expired session rejects a new turn');
select is(pg_temp.m4_call('prepare_learning_summary', jsonb_build_object(
    'session_id', 'd3440000-0000-4000-8000-000000000104', 'fingerprint', repeat('7', 64),
    'expected_session_version', 1, 'summary', 'x', 'topics', '[]'::jsonb), idem => 'm4-expired-sum-00001') #>> '{error,details,reason}',
    'SESSION_EXPIRED', 'expired session cannot be summarized');
select ok((select expires_at < clock_timestamp() from app_private.learning_session where session_id = 'd3440000-0000-4000-8000-000000000104'),
    'rejected writes do not extend the expiry');
select is((select count(*)::int from app_private.learning_turn where session_id = 'd3440000-0000-4000-8000-000000000104'), 2,
    'rejected writes add no turns');

-- 5. Retention: expired outcome session keeps the outcome; expired unsummarized session is removed.
select pg_temp.m4_session('d3440000-0000-4000-8000-000000000103', 'd3440000-0000-4000-8000-000000000001',
    'd3440000-0000-4000-8000-000000000203', clock_timestamp() - interval '1 day');
update app_private.learning_session set expires_at = clock_timestamp() - interval '1 day'
 where session_id in ('d3440000-0000-4000-8000-000000000101', 'd3440000-0000-4000-8000-000000000102');
select is(pg_temp.m4_call('purge_expired_learning', '{}', 'd3440000-0000-4000-8000-000000000002') #>> '{data,deleted_sessions}',
    '0', 'purge only touches the caller''s sessions');
insert into m4 select 'purge', pg_temp.m4_call('purge_expired_learning', '{}');
select is((select val #> '{data}' from m4 where label = 'purge'), '{"deleted_sessions":3,"closed_sessions":1}'::jsonb,
    'purge removes three unconfirmed sessions and closes one with an outcome');
select is((select count(*)::int from app_private.learning_turn where user_id = 'd3440000-0000-4000-8000-000000000001'), 0,
    'expired sessions keep no turns');
select is((select count(*)::int from app_private.session_outcome where session_id = 'd3440000-0000-4000-8000-000000000101'), 1,
    'confirmed outcome survives retention');
select is((select count(*)::int from app_private.learning_session where user_id = 'd3440000-0000-4000-8000-000000000001'), 1,
    'only the session with an outcome remains');
select is((select count(*)::int from app_private.learning_session_receipts where user_id = 'd3440000-0000-4000-8000-000000000001'), 0,
    'receipts holding turn or draft text are purged');
select is((select state from app_private.pending_actions where (draft_arguments ->> 'session_id') = 'd3440000-0000-4000-8000-000000000102'
           order by created_at desc limit 1), 'CANCELLED', 'pending summary of a purged session is cancelled');

-- 6. Planner context is read-only and owner-scoped. FK/trigger checks are skipped only while seeding the plan.
set local session_replication_role = replica;
insert into app_private.academic_tasks(task_id, user_id, candidate_id, title, start_at, deadline_at, deadline_precision,
    deadline_timezone, estimated_minutes, remaining_minutes)
values ('d3440000-0000-4000-8000-0000000000c1', 'd3440000-0000-4000-8000-000000000001', gen_random_uuid(),
    'Ôn chương 2: Tính chẵn lẻ', now(), now() + interval '3 days', 'DATETIME', 'Asia/Ho_Chi_Minh', 60, 60);
insert into app_private.study_blocks(plan_id, block_id, user_id, task_id, start_at, end_at)
values (gen_random_uuid(), 'd3440000-0000-4000-8000-0000000000e1', 'd3440000-0000-4000-8000-000000000001',
    'd3440000-0000-4000-8000-0000000000c1', now() + interval '1 day', now() + interval '1 day 1 hour');
set local session_replication_role = origin;
insert into m4 select 'planner', pg_temp.m4_call('get_learning_planner_context',
    '{"block_id":"d3440000-0000-4000-8000-0000000000e1"}');
select is((select val #>> '{data,suggested_goal}' from m4 where label = 'planner'), 'Ôn chương 2: Tính chẵn lẻ',
    'planner context suggests a goal from the task title');
select ok(app_private.matches_contract('DailyLearningPlannerContextResult', (select val from m4 where label = 'planner')),
    'planner context result matches contract');
select is(pg_temp.m4_call('get_learning_planner_context', '{"block_id":"d3440000-0000-4000-8000-0000000000e1"}',
    'd3440000-0000-4000-8000-000000000002') #>> '{error,code}', 'ENTITY_NOT_FOUND', 'another user cannot read the block');
select is((select remaining_minutes::int from app_private.academic_tasks where task_id = 'd3440000-0000-4000-8000-0000000000c1'), 60,
    'reading planner context leaves the task unchanged');

select * from finish();
rollback;
