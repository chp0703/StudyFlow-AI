-- BE-01 & BE-02 / migration 023: versioned Planner task schema (start_at, numeric priority weight,
-- hex color, retired course_label) and fixed Vietnam product timezone (Asia/Ho_Chi_Minh).

-- 1. Migrate app_private.academic_tasks with a deterministic compatibility path for stored rows.
alter table app_private.academic_tasks
    add column if not exists start_at timestamptz,
    add column if not exists color text default '#596CF0';

update app_private.academic_tasks
set start_at = coalesce(start_at, available_from_at, deadline_at - (estimated_minutes * interval '1 minute')),
    available_from_at = coalesce(available_from_at, start_at, deadline_at - (estimated_minutes * interval '1 minute')),
    color = coalesce(nullif(btrim(color), ''), '#596CF0'),
    deadline_timezone = 'Asia/Ho_Chi_Minh';

alter table app_private.academic_tasks
    alter column start_at set not null,
    alter column color set not null,
    alter column deadline_timezone set default 'Asia/Ho_Chi_Minh';

alter table app_private.academic_tasks
    drop constraint if exists academic_tasks_priority_check;

alter table app_private.academic_tasks
    alter column priority drop default,
    alter column priority type numeric using (
        case
            when priority::text in ('LOW', '0.1') then 0.1
            when priority::text in ('HIGH', '1', '1.0') then 1
            else 0.5
        end
    ),
    alter column priority set default 0.5,
    alter column priority set not null;

alter table app_private.academic_tasks
    drop column if exists course_label;

alter table app_private.academic_tasks
    add constraint academic_tasks_priority_check check (priority in (0.1, 0.5, 1)),
    add constraint academic_tasks_color_check check (color ~ '^#[0-9A-Fa-f]{6}$'),
    add constraint academic_tasks_start_before_deadline_check check (start_at <= deadline_at),
    add constraint academic_tasks_deadline_timezone_vn_check check (deadline_timezone = 'Asia/Ho_Chi_Minh');

-- 2. Migrate stored TaskCandidate drafts to the versioned slot schema.
update app_private.task_candidates
set slots = (slots - 'course_label')
    || case
        when slots ->> 'priority' = 'LOW' then '{"priority": 0.1}'::jsonb
        when slots ->> 'priority' = 'NORMAL' then '{"priority": 0.5}'::jsonb
        when slots ->> 'priority' = 'HIGH' then '{"priority": 1}'::jsonb
        else '{}'::jsonb
    end
    || case
        when slots ? 'deadline_timezone' and slots -> 'deadline_timezone' <> 'null'::jsonb
            then '{"deadline_timezone": "Asia/Ho_Chi_Minh"}'::jsonb
        else '{}'::jsonb
    end;

-- 3. Enforce Asia/Ho_Chi_Minh across user_profiles and time_windows (BE-02).
update app_private.user_profiles set timezone = 'Asia/Ho_Chi_Minh' where timezone is distinct from 'Asia/Ho_Chi_Minh';
alter table app_private.user_profiles
    alter column timezone set default 'Asia/Ho_Chi_Minh',
    add constraint user_profiles_timezone_vn_check check (timezone = 'Asia/Ho_Chi_Minh');

update app_private.time_windows set timezone = 'Asia/Ho_Chi_Minh' where timezone is distinct from 'Asia/Ho_Chi_Minh';
alter table app_private.time_windows
    alter column timezone set default 'Asia/Ho_Chi_Minh',
    add constraint time_windows_timezone_vn_check check (timezone = 'Asia/Ho_Chi_Minh');

-- 4. Update private helpers and public RPCs.
create or replace function app_private.canonical_json(p_value jsonb) returns text
language plpgsql immutable set search_path = '' as $$
declare
    v_type text := jsonb_typeof(p_value);
    v_text text;
begin
    if v_type = 'null' then
        return 'null';
    elsif v_type = 'boolean' then
        return p_value::text;
    elsif v_type = 'number' then
        v_text := p_value::text;
        if v_text !~ '^-?(0|[1-9][0-9]{0,15})$' or abs(v_text::numeric) > 9007199254740991 then
            raise exception using errcode = '22023',
                message = 'canonical JSON accepts only safe integers';
        end if;
        return v_text;
    elsif v_type = 'string' then
        return to_jsonb(p_value #>> '{}')::text;
    elsif v_type = 'array' then
        return '[' || coalesce((select string_agg(app_private.canonical_json(e.value), ',' order by e.ord)
                                from jsonb_array_elements(p_value) with ordinality e(value, ord)), '') || ']';
    end if;
    return '{' || coalesce((select string_agg(
        to_jsonb(e.key)::text || ':' ||
        case
            when e.key = 'priority' and jsonb_typeof(e.value) = 'number' and e.value::text in ('0.1', '0.5')
                then e.value::text
            else app_private.canonical_json(e.value)
        end,
        ',' order by convert_to(e.key, 'UTF8'))
        from jsonb_each(p_value) e), '') || '}';
end $$;

create or replace function app_private.lock_owner(p_uid uuid, p_request jsonb, p_timezone text default null) returns void
language plpgsql security definer set search_path = '' as $$
declare
    v_locale text := coalesce(nullif(btrim(p_request #>> '{execution_context,trusted_context,locale}'), ''), 'vi');
begin
    insert into app_private.user_profiles (user_id, timezone, locale, scheduling_policy)
    values (p_uid, 'Asia/Ho_Chi_Minh', v_locale,
            '{"min_block_minutes":25,"max_block_minutes":90,"allow_short_final_block":true,"max_daily_minutes":240,"break_minutes":10}'::jsonb)
    on conflict (user_id) do nothing;
    perform 1 from app_private.user_profiles where user_id = p_uid for update;
end $$;

create or replace function app_private.task_json(p_task app_private.academic_tasks) returns jsonb
language sql immutable set search_path = '' as $$
    select jsonb_build_object(
        'task_id', p_task.task_id,
        'user_id', p_task.user_id,
        'candidate_id', p_task.candidate_id,
        'version', p_task.version,
        'title', p_task.title,
        'description', p_task.description,
        'start_at', app_private.iso(p_task.start_at),
        'available_from_at', case when p_task.available_from_at is null then null else app_private.iso(p_task.available_from_at) end,
        'deadline_at', app_private.iso(p_task.deadline_at),
        'deadline_precision', p_task.deadline_precision,
        'deadline_date', p_task.deadline_date,
        'deadline_timezone', p_task.deadline_timezone,
        'estimated_minutes', p_task.estimated_minutes,
        'remaining_minutes', p_task.remaining_minutes,
        'priority', case when p_task.priority = 1 then to_jsonb(1::int) else to_jsonb(p_task.priority) end,
        'color', p_task.color,
        'status', p_task.status,
        'confirmed_at', app_private.iso(p_task.confirmed_at),
        'created_at', app_private.iso(p_task.created_at),
        'updated_at', app_private.iso(p_task.updated_at)
    )
$$;

create or replace function app_private.validate_window(p_request jsonb, p_window jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_tz text := p_window ->> 'timezone';
    v_start timestamptz;
    v_end timestamptz;
    v_local_start timestamp;
    v_local_end timestamp;
begin
    if v_tz is distinct from 'Asia/Ho_Chi_Minh' then
        return app_private.field_error(p_request, 'INVALID_PARAMETER', 'Only Asia/Ho_Chi_Minh is supported.', 'window.timezone');
    end if;
    if p_window ->> 'recurrence' = 'NONE' then
        v_start := (p_window ->> 'start_at')::timestamptz;
        v_end := (p_window ->> 'end_at')::timestamptz;
        if v_end <= v_start then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'The window must end after it starts.', 'window.end_at');
        end if;
        if extract(second from v_start) <> 0 or extract(second from v_end) <> 0 then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'Windows use whole minutes.', 'window.start_at');
        end if;
        v_local_start := v_start at time zone v_tz;
        v_local_end := v_end at time zone v_tz;
        if v_local_end::date <> v_local_start::date and v_local_end <> (v_local_start::date + 1)::timestamp then
            return app_private.field_error(p_request, 'INVALID_PARAMETER',
                'Split an interval that crosses midnight into two windows.', 'window.end_at');
        end if;
    else
        if (p_window ->> 'end_time')::time <= (p_window ->> 'start_time')::time then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'The window must end after it starts.', 'window.end_time');
        end if;
        if p_window ->> 'valid_until' is not null and (p_window ->> 'valid_until')::date <= (p_window ->> 'valid_from')::date then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'valid_until must be after valid_from.', 'window.valid_until');
        end if;
    end if;
    return null;
end $$;

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
    v_start_at timestamptz;
    v_available_from timestamptz;
    v_deadline timestamptz;
    v_title text;
    v_minutes bigint;
    v_priority numeric;
    v_color text;
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

        v_slots := c.slots;
        v_title := nullif(btrim(v_slots ->> 'title'), '');
        v_minutes := (v_slots ->> 'estimated_minutes')::bigint;
        v_start_at := (v_slots ->> 'start_at')::timestamptz;
        v_precision := coalesce(v_slots ->> 'deadline_precision', case when v_start_at is not null then 'DATETIME' end);
        v_tz := coalesce(v_slots ->> 'deadline_timezone', case when v_start_at is not null then 'Asia/Ho_Chi_Minh' end);

        v_missing := case
            when v_title is null then 'title'
            when v_minutes is null then 'estimated_minutes'
            when v_start_at is null and v_precision is null then 'start_at'
            when v_tz is null then 'deadline_timezone'
            when v_precision = 'DATE' and v_slots ->> 'deadline_date' is null then 'deadline_date'
            when v_precision = 'DATETIME' and v_slots ->> 'deadline_at' is null and v_start_at is null then 'deadline_at'
        end;
        if v_missing is not null then
            return app_private.field_error(p_request, 'MISSING_REQUIRED_FIELD', 'The candidate is missing a required field.', v_missing);
        end if;
        if v_tz <> 'Asia/Ho_Chi_Minh' then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'Only Asia/Ho_Chi_Minh is supported.', 'deadline_timezone');
        end if;
        if v_precision = 'DATE' then
            v_date := (v_slots ->> 'deadline_date')::date;
            v_deadline := (v_date + 1)::timestamp at time zone v_tz;
            if v_slots ->> 'deadline_at' is not null and (v_slots ->> 'deadline_at')::timestamptz <> v_deadline then
                return app_private.field_error(p_request, 'INVALID_PARAMETER',
                    'A date-only deadline ends at the start of the next local day.', 'deadline_at');
            end if;
        else
            v_deadline := coalesce((v_slots ->> 'deadline_at')::timestamptz, v_start_at + (v_minutes * interval '1 minute'));
            if v_slots ->> 'deadline_date' is not null then
                return app_private.field_error(p_request, 'INVALID_PARAMETER', 'A date-time deadline has no deadline_date.', 'deadline_date');
            end if;
        end if;
        v_start_at := coalesce(v_start_at, (v_slots ->> 'available_from_at')::timestamptz, v_deadline - (v_minutes * interval '1 minute'));
        v_available_from := coalesce((v_slots ->> 'available_from_at')::timestamptz, v_start_at);
        if v_start_at > v_deadline then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'start_at is after the deadline.', 'start_at');
        end if;
        if v_available_from > v_deadline then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'available_from_at is after the deadline.', 'available_from_at');
        end if;

        if v_slots ? 'priority' and v_slots -> 'priority' <> 'null'::jsonb then
            if jsonb_typeof(v_slots -> 'priority') <> 'number' then
                return app_private.field_error(p_request, 'INVALID_PARAMETER', 'priority must be numeric.', 'priority');
            end if;
            v_priority := (v_slots ->> 'priority')::numeric;
            if v_priority not in (0.1, 0.5, 1) then
                return app_private.field_error(p_request, 'INVALID_PARAMETER', 'priority must be 0.1, 0.5 or 1.', 'priority');
            end if;
        else
            v_priority := 0.5;
        end if;

        v_color := coalesce(nullif(btrim(v_slots ->> 'color'), ''), '#596CF0');
        if v_color !~ '^#[0-9A-Fa-f]{6}$' then
            return app_private.field_error(p_request, 'INVALID_PARAMETER', 'color must be a 6-digit hex color.', 'color');
        end if;

        insert into app_private.approval_actions
            (approval_action_id, user_id, target_type, target_id, target_version, decision, source, source_message_id,
             candidate_target_id)
        values ((v_approval ->> 'approval_action_id')::uuid, v_uid, 'TASK_CANDIDATE', c.candidate_id, c.version, 'APPROVE',
                v_approval ->> 'source', (v_approval ->> 'source_message_id')::uuid, c.candidate_id);
        insert into app_private.academic_tasks
            (task_id, user_id, candidate_id, title, description, start_at, available_from_at, deadline_at,
             deadline_precision, deadline_date, deadline_timezone, estimated_minutes, remaining_minutes, priority, color, status)
        values (extensions.gen_random_uuid(), v_uid, c.candidate_id, v_title, v_slots ->> 'description',
                v_start_at, v_available_from, v_deadline,
                v_precision, v_date, v_tz, v_minutes, v_minutes, v_priority, v_color, 'TODO')
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
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_ENTITY_VERSION') then sqlerrm else 'INVALID_PARAMETER' end,
                'The approval target is no longer valid.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;

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
              and (v_query is null or x.title ilike v_like escape '\' or x.description ilike v_like escape '\')
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

create or replace function app_api.approve_study_plan(p_request jsonb) returns jsonb
language plpgsql security definer set search_path = '' as $$
declare
    v_error jsonb := app_private.precheck(p_request, 'approve_study_plan', 'approve_study_planArguments');
    v_uid uuid;
    v_args jsonb := p_request -> 'arguments';
    v_ctx jsonb := p_request -> 'execution_context';
    v_approval jsonb := p_request #> '{execution_context,approval_action}';
    v_ref jsonb := p_request #> '{execution_context,action_reference}';
    v_key text := p_request #>> '{execution_context,idempotency_key}';
    v_binding jsonb;
    v_fp text;
    v_reply jsonb;
    v_user app_private.user_profiles;
    v_cur app_private.study_plans;
    pr app_private.plan_proposals;
    d record;
    v_plan app_private.study_plans;
    v_result jsonb;
    v_max bigint;
begin
    if v_error is not null then
        return v_error;
    end if;
    v_uid := app_private.current_uid();
    v_error := app_private.plan_decision_guard(p_request, v_uid, 'APPROVE');
    if v_error is not null then
        return v_error;
    end if;
    v_binding := jsonb_build_object('decision', 'APPROVE', 'action_id', v_ref -> 'action_id',
        'action_version', v_ref -> 'action_version', 'target_type', 'PLAN_PROPOSAL',
        'target_id', v_args -> 'proposal_id', 'target_version', v_args -> 'expected_proposal_version');
    v_fp := app_private.domain_fingerprint(v_uid, 'approve_study_plan', v_args, v_binding);
    begin
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'approve_study_plan', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        perform app_private.lock_owner(v_uid, p_request);
        v_reply := app_private.idempotent_reply(p_request, v_uid, 'approve_study_plan', v_key, v_fp);
        if v_reply is not null then
            return v_reply;
        end if;
        select * into pr from app_private.plan_proposals
        where user_id = v_uid and proposal_id = (v_args ->> 'proposal_id')::uuid for update;
        if not found then
            return app_private.error_result(p_request, 'ENTITY_NOT_FOUND', 'The proposal was not found.');
        end if;
        if pr.status <> 'PROPOSED' or pr.version <> (v_args ->> 'expected_proposal_version')::bigint then
            return app_private.error_result(p_request, 'STALE_PROPOSAL', 'The proposal is no longer pending.');
        end if;
        select * into v_user from app_private.user_profiles where user_id = v_uid;
        select * into v_cur from app_private.study_plans where user_id = v_uid and plan_id = v_user.current_plan_id;
        if pr.base_schedule_revision <> v_user.schedule_revision or pr.base_plan_id is distinct from v_user.current_plan_id then
            update app_private.plan_proposals set status = 'STALE' where proposal_id = pr.proposal_id;
            v_result := app_private.error_result(p_request, 'STALE_PROPOSAL', 'The schedule changed after the proposal was generated.');
            insert into app_private.idempotency_records
                (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
            values (v_uid, 'approve_study_plan', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
            return v_result;
        end if;
        if (v_args ->> 'expected_plan_version')::bigint is distinct from v_cur.version then
            return app_private.error_result(p_request, 'STALE_PLAN_VERSION', 'The current plan version is not the expected one.');
        end if;
        select * into d from app_private.plan_decision_action(p_request, v_uid, pr);
        if d.o_error is not null then
            return d.o_error;
        end if;

        v_max := (pr.policy_snapshot ->> 'max_block_minutes')::bigint;
        if exists (
            select 1 from jsonb_array_elements(pr.payload -> 'study_blocks') b
            left join app_private.academic_tasks t on t.user_id = v_uid and t.task_id = (b ->> 'task_id')::uuid
            where not app_private.is_base_plan_block(v_uid, b)
              and (t.task_id is null or t.status not in ('TODO', 'IN_PROGRESS')
                   or (b ->> 'start_at')::timestamptz < t.start_at
                   or (b ->> 'end_at')::timestamptz > t.deadline_at
                   or (t.available_from_at is not null and (b ->> 'start_at')::timestamptz < t.available_from_at)
                   or extract(epoch from ((b ->> 'end_at')::timestamptz - (b ->> 'start_at')::timestamptz)) / 60 > v_max)) then
            return app_private.error_result(p_request, 'INVALID_PARAMETER', 'A proposed block no longer fits its task or the policy.');
        end if;

        insert into app_private.approval_actions
            (approval_action_id, user_id, target_type, target_id, target_version, decision, source, source_message_id,
             proposal_target_id)
        values ((v_approval ->> 'approval_action_id')::uuid, v_uid, 'PLAN_PROPOSAL', pr.proposal_id, pr.version, 'APPROVE',
                v_approval ->> 'source', (v_approval ->> 'source_message_id')::uuid, pr.proposal_id);
        insert into app_private.study_plans (plan_id, user_id, version, previous_plan_id, source_proposal_id)
        values (extensions.gen_random_uuid(), v_uid, coalesce(v_cur.version, 0) + 1, v_cur.plan_id, pr.proposal_id)
        returning * into v_plan;
        insert into app_private.study_blocks (plan_id, block_id, user_id, task_id, start_at, end_at, is_locked)
        select v_plan.plan_id, (b ->> 'block_id')::uuid, v_uid, (b ->> 'task_id')::uuid,
               (b ->> 'start_at')::timestamptz, (b ->> 'end_at')::timestamptz, (b ->> 'is_locked')::boolean
        from jsonb_array_elements(pr.payload -> 'study_blocks') b;
        update app_private.user_profiles
        set current_plan_id = v_plan.plan_id, schedule_revision = schedule_revision + 1 where user_id = v_uid;
        update app_private.plan_proposals set status = 'APPROVED', committed_plan_id = v_plan.plan_id
        where proposal_id = pr.proposal_id;
        update app_private.pending_actions set state = 'COMPLETED', version = version + 1 where action_id = (d.o_action).action_id;
        v_result := app_private.ok_result(p_request, 'COMMITTED', app_private.plan_json(v_plan));
        insert into app_private.idempotency_records
            (user_id, operation, idempotency_key, request_fingerprint, state, result_reference_or_response, expires_at)
        values (v_uid, 'approve_study_plan', v_key, v_fp, 'COMPLETED', v_result, clock_timestamp() + interval '7 days');
        return v_result;
    exception
        when sqlstate 'P0001' then
            return app_private.error_result(p_request,
                case when sqlerrm in ('ENTITY_NOT_FOUND', 'STALE_PROPOSAL') then sqlerrm else 'INVALID_PARAMETER' end,
                'The approval target is no longer valid.');
        when sqlstate '23P01' then
            return app_private.error_result(p_request, 'TIME_CONFLICT', 'The proposed blocks overlap.');
        when others then
            return app_private.failure(p_request, sqlstate);
    end;
end $$;

alter function app_private.canonical_json(jsonb) owner to sf_rpc_owner;
alter function app_private.lock_owner(uuid, jsonb, text) owner to sf_rpc_owner;
alter function app_private.task_json(app_private.academic_tasks) owner to sf_rpc_owner;
alter function app_private.validate_window(jsonb, jsonb) owner to sf_rpc_owner;
revoke all on function app_private.canonical_json(jsonb),
    app_private.lock_owner(uuid, jsonb, text),
    app_private.task_json(app_private.academic_tasks),
    app_private.validate_window(jsonb, jsonb) from public, anon, authenticated;
