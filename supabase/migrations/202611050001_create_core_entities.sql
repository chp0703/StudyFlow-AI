-- Stage 03.3 / commit 03: F1 core entity foundation.
-- This migration intentionally contains no API-facing tables or RPCs.

create schema if not exists app_private;
create schema if not exists app_api;
create extension if not exists btree_gist with schema extensions;

create table app_private.user_profiles (
    user_id uuid primary key references auth.users(id) on delete restrict,
    timezone text not null,
    locale text not null,
    current_plan_id uuid,
    schedule_revision bigint not null default 0 check (schedule_revision >= 0),
    scheduling_policy jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp()
);

create table app_private.task_candidates (
    candidate_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    conversation_id uuid not null,
    version bigint not null default 1 check (version >= 1),
    status text not null default 'DRAFT' check (status in ('DRAFT', 'CONFIRMED', 'CANCELLED')),
    slots jsonb not null default '{}'::jsonb,
    raw_expressions jsonb not null default '{}'::jsonb,
    field_sources jsonb not null default '{}'::jsonb,
    source_message_id uuid not null,
    confirmed_task_id uuid,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp()
);

create table app_private.academic_tasks (
    task_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    candidate_id uuid not null unique,
    version bigint not null default 1 check (version >= 1),
    title text not null check (length(btrim(title)) > 0),
    description text,
    course_label text,
    available_from_at timestamptz,
    deadline_at timestamptz not null,
    deadline_precision text not null,
    deadline_date date,
    deadline_timezone text not null,
    estimated_minutes bigint not null check (estimated_minutes > 0),
    remaining_minutes bigint not null check (remaining_minutes >= 0),
    priority text not null default 'NORMAL' check (priority in ('LOW', 'NORMAL', 'HIGH')),
    status text not null default 'TODO' check (status in ('TODO', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    confirmed_at timestamptz not null default clock_timestamp(),
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    constraint academic_tasks_dates_check check (available_from_at is null or available_from_at <= deadline_at),
    constraint academic_tasks_deadline_precision_check check (
        (deadline_precision = 'DATE' and deadline_date is not null)
        or (deadline_precision = 'DATETIME' and deadline_date is null)
    ),
    constraint academic_tasks_workload_check check (remaining_minutes <= estimated_minutes),
    constraint academic_tasks_status_workload_check check (
        (status = 'COMPLETED' and remaining_minutes = 0)
        or (status in ('TODO', 'IN_PROGRESS') and remaining_minutes > 0)
        or status = 'CANCELLED'
    )
);

create table app_private.time_windows (
    window_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    version bigint not null default 1 check (version >= 1),
    kind text not null check (kind in ('AVAILABILITY', 'BUSY')),
    label text,
    recurrence text not null default 'NONE' check (recurrence in ('NONE', 'WEEKLY')),
    timezone text not null,
    start_at timestamptz,
    end_at timestamptz,
    weekday smallint,
    start_time time without time zone,
    end_time time without time zone,
    valid_from date,
    valid_until date,
    archived_at timestamptz,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    constraint time_windows_shape_check check (
        (recurrence = 'NONE'
            and start_at is not null and end_at is not null and end_at > start_at
            and weekday is null and start_time is null and end_time is null
            and valid_from is null and valid_until is null)
        or
        (recurrence = 'WEEKLY'
            and start_at is null and end_at is null
            and weekday between 1 and 7
            and start_time < time '24:00:00'
            and end_time > start_time and end_time <= time '24:00:00'
            and valid_from is not null
            and (valid_until is null or valid_until > valid_from))
    )
);

create index ix_task_candidates_user_conversation
    on app_private.task_candidates (user_id, conversation_id, created_at);
create index ix_tasks_user_status_deadline
    on app_private.academic_tasks (user_id, status, deadline_at);
create index ix_windows_user_kind
    on app_private.time_windows (user_id, kind);
