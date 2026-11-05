-- WP2a / migration 009: SECURITY DEFINER owner role and durable infrastructure tables.
-- Additive only: migrations 001-008 are untouched. Row-level policies and grants for
-- these tables are installed in 011 together with the rest of the boundary.

-- The RPC owner owns every app_api wrapper. It cannot log in, bypass RLS or be assumed
-- by client roles; postgres is made a member only so migrations can transfer ownership.
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'sf_rpc_owner') then
        create role sf_rpc_owner nologin nosuperuser nocreatedb nocreaterole noinherit nobypassrls;
    end if;
end $$;
grant sf_rpc_owner to postgres;

grant usage, create on schema app_private to sf_rpc_owner;
grant usage, create on schema app_api to sf_rpc_owner;
grant usage on schema extensions to sf_rpc_owner;

-- Global HMAC key store. Rows are written only by the migration/key-rotation owner.
create table app_private.rpc_attestation_keys (
    key_id text primary key check (length(btrim(key_id)) > 0),
    key_material bytea not null check (length(key_material) >= 32),
    not_before timestamptz not null,
    not_after timestamptz not null,
    constraint rpc_attestation_keys_window_check check (not_after > not_before)
);

create table app_private.conversation_records (
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    conversation_id uuid not null,
    created_at timestamptz not null default clock_timestamp(),
    primary key (user_id, conversation_id)
);

create table app_private.source_messages (
    message_id uuid primary key,
    user_id uuid not null,
    conversation_id uuid not null,
    source text not null check (source in ('UI', 'CHAT')),
    role text not null check (role in ('USER', 'ASSISTANT')),
    text text not null,
    received_at timestamptz not null,
    constraint fk_source_messages_conversation_owner
        foreign key (user_id, conversation_id)
        references app_private.conversation_records (user_id, conversation_id)
        on delete restrict on update restrict,
    constraint source_messages_user_message_key unique (user_id, message_id)
);

create table app_private.api_request_receipts (
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    http_operation text not null
        check (http_operation in ('send_message', 'prepare_action', 'review_action', 'submit_decision')),
    idempotency_key text not null
        check (length(idempotency_key) between 16 and 128 and idempotency_key ~ '^[A-Za-z0-9._:-]+$'),
    request_fingerprint text not null check (request_fingerprint ~ '^[a-f0-9]{64}$'),
    state text not null check (state in ('IN_PROGRESS', 'COMPLETED')),
    lease_version bigint not null default 1 check (lease_version between 1 and 9007199254740991),
    lease_until timestamptz,
    message_id uuid,
    action_id uuid,
    http_status bigint check (http_status between 200 and 599),
    response jsonb,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    primary key (user_id, http_operation, idempotency_key),
    constraint fk_receipts_message_owner foreign key (user_id, message_id)
        references app_private.source_messages (user_id, message_id)
        on delete restrict on update restrict,
    constraint fk_receipts_action_owner foreign key (user_id, action_id)
        references app_private.pending_actions (user_id, action_id)
        on delete restrict on update restrict,
    -- A live receipt holds a lease and no result; a completed one holds the stored result.
    constraint api_receipts_state_shape_check check (
        (state = 'IN_PROGRESS' and lease_until is not null and response is null and http_status is null)
        or (state = 'COMPLETED' and response is not null and http_status is not null)
    )
);

create table app_private.action_presentations (
    user_id uuid not null,
    action_id uuid not null,
    action_version bigint not null check (action_version between 1 and 9007199254740991),
    target_type text not null check (target_type in ('TASK_CANDIDATE', 'PENDING_ACTION', 'PLAN_PROPOSAL')),
    target_id uuid not null,
    target_version bigint not null check (target_version between 1 and 9007199254740991),
    content_digest text not null check (content_digest ~ '^[a-f0-9]{64}$'),
    presentation jsonb not null,
    source_message_id uuid,
    created_at timestamptz not null default clock_timestamp(),
    primary key (user_id, action_id, action_version),
    constraint fk_presentations_action_owner foreign key (user_id, action_id)
        references app_private.pending_actions (user_id, action_id)
        on delete restrict on update restrict,
    constraint fk_presentations_source_owner foreign key (user_id, source_message_id)
        references app_private.source_messages (user_id, message_id)
        on delete restrict on update restrict
);

create table app_private.workflow_continuations (
    user_id uuid not null,
    conversation_id uuid not null,
    source_message_id uuid not null,
    origin_http_operation text not null check (origin_http_operation in ('send_message', 'prepare_action')),
    origin_idempotency_key text not null
        check (length(origin_idempotency_key) between 16 and 128
               and origin_idempotency_key ~ '^[A-Za-z0-9._:-]+$'),
    origin_request_fingerprint text not null check (origin_request_fingerprint ~ '^[a-f0-9]{64}$'),
    version bigint not null default 1 check (version between 1 and 9007199254740991),
    extraction jsonb not null check (jsonb_typeof(extraction -> 'intents') = 'array'),
    extraction_digest text not null check (extraction_digest ~ '^[a-f0-9]{64}$'),
    depends_on jsonb not null check (jsonb_typeof(depends_on) = 'array' and jsonb_array_length(depends_on) >= 1),
    cursor bigint not null default 0 check (cursor between 0 and 9007199254740991),
    awaiting_reference jsonb,
    completed_steps jsonb not null default '[]'::jsonb check (jsonb_typeof(completed_steps) = 'array'),
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    primary key (user_id, source_message_id),
    constraint fk_continuations_conversation_owner foreign key (user_id, conversation_id)
        references app_private.conversation_records (user_id, conversation_id)
        on delete restrict on update restrict,
    constraint fk_continuations_source_owner foreign key (user_id, source_message_id)
        references app_private.source_messages (user_id, message_id)
        on delete restrict on update restrict,
    constraint fk_continuations_origin_receipt
        foreign key (user_id, origin_http_operation, origin_idempotency_key)
        references app_private.api_request_receipts (user_id, http_operation, idempotency_key)
        on delete restrict on update restrict,
    -- Progress never runs ahead of the persisted extraction or its recorded outcomes.
    constraint workflow_continuations_progress_check check (
        cursor <= jsonb_array_length(extraction -> 'intents')
        and jsonb_array_length(completed_steps) = cursor
    )
);

create index ix_continuations_conversation
    on app_private.workflow_continuations (user_id, conversation_id, updated_at);
-- At most one unfinished continuation per conversation; finished ones are retained.
create unique index ux_continuations_unfinished_conversation
    on app_private.workflow_continuations (user_id, conversation_id)
    where cursor < jsonb_array_length(extraction -> 'intents');
create index ix_receipts_lease on app_private.api_request_receipts (user_id, state, lease_until);

-- Columns fixed by the first write stay fixed (first-write-wins extraction).
create function app_private.workflow_continuation_immutable() returns trigger
language plpgsql set search_path = '' as $$
begin
    if (new.user_id, new.conversation_id, new.source_message_id, new.origin_http_operation,
        new.origin_idempotency_key, new.origin_request_fingerprint, new.extraction,
        new.extraction_digest, new.depends_on, new.created_at)
       is distinct from
       (old.user_id, old.conversation_id, old.source_message_id, old.origin_http_operation,
        old.origin_idempotency_key, old.origin_request_fingerprint, old.extraction,
        old.extraction_digest, old.depends_on, old.created_at) then
        raise exception using errcode = '23514', message = 'workflow continuation origin is immutable';
    end if;
    return new;
end $$;
create trigger trg_workflow_continuation_immutable
    before update on app_private.workflow_continuations
    for each row execute function app_private.workflow_continuation_immutable();
create trigger trg_workflow_continuation_updated
    before update on app_private.workflow_continuations
    for each row execute function app_private.touch_updated_at();
create trigger trg_api_receipt_updated
    before update on app_private.api_request_receipts
    for each row execute function app_private.touch_updated_at();

alter table app_private.rpc_attestation_keys enable row level security;
alter table app_private.conversation_records enable row level security;
alter table app_private.source_messages enable row level security;
alter table app_private.api_request_receipts enable row level security;
alter table app_private.action_presentations enable row level security;
alter table app_private.workflow_continuations enable row level security;
alter table app_private.rpc_attestation_keys force row level security;
alter table app_private.conversation_records force row level security;
alter table app_private.source_messages force row level security;
alter table app_private.api_request_receipts force row level security;
alter table app_private.action_presentations force row level security;
alter table app_private.workflow_continuations force row level security;

revoke all on app_private.rpc_attestation_keys, app_private.conversation_records,
    app_private.source_messages, app_private.api_request_receipts,
    app_private.action_presentations, app_private.workflow_continuations
    from public, anon, authenticated;
