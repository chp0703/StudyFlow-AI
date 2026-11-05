-- Stage 03.3 / commit 04: immutable planning, review, and replay persistence.

create table app_private.study_plans (
    plan_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    version bigint not null check (version >= 1),
    previous_plan_id uuid,
    source_proposal_id uuid not null,
    approved_at timestamptz not null default clock_timestamp(),
    created_at timestamptz not null default clock_timestamp(),
    unique (user_id, version),
    unique (user_id, plan_id)
);

create table app_private.study_blocks (
    plan_id uuid not null,
    block_id uuid not null,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    task_id uuid not null,
    start_at timestamptz not null,
    end_at timestamptz not null,
    is_locked boolean not null default false,
    created_at timestamptz not null default clock_timestamp(),
    primary key (plan_id, block_id),
    unique (user_id, plan_id, block_id),
    constraint study_blocks_time_check check (end_at > start_at)
);

create table app_private.plan_proposals (
    proposal_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    -- F1 schema v1.1 requires integer >= 1. See the contract integration note
    -- for the unresolved data-contract.json text representation.
    version bigint not null default 1 check (version >= 1),
    status text not null default 'PROPOSED'
        check (status in ('PROPOSED', 'APPROVED', 'REJECTED', 'STALE')),
    base_plan_id uuid,
    base_plan_version bigint,
    base_schedule_revision bigint not null check (base_schedule_revision >= 0),
    generation_scope jsonb not null,
    payload jsonb not null,
    algorithm_version text not null check (length(btrim(algorithm_version)) > 0),
    policy_snapshot jsonb not null,
    generated_at timestamptz not null default clock_timestamp(),
    committed_plan_id uuid,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    unique (user_id, proposal_id),
    constraint plan_proposals_base_check check (
        (base_plan_id is null and base_plan_version is null)
        or (base_plan_id is not null and base_plan_version is not null and base_plan_version >= 1)
    ),
    constraint plan_proposals_commit_state_check check (
        (status = 'APPROVED' and committed_plan_id is not null)
        or (status <> 'APPROVED' and committed_plan_id is null)
    )
);

create table app_private.pending_actions (
    action_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    conversation_id uuid not null,
    version bigint not null default 1 check (version >= 1),
    intent text not null check (length(btrim(intent)) > 0),
    state text not null default 'AWAITING_CLARIFICATION'
        check (state in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL', 'COMPLETED', 'CANCELLED')),
    requires_review boolean not null default false,
    candidate_id uuid,
    proposal_id uuid,
    draft_arguments jsonb not null default '{}'::jsonb,
    missing_fields jsonb not null default '[]'::jsonb,
    ambiguities jsonb not null default '[]'::jsonb,
    depends_on_action_id uuid,
    created_at timestamptz not null default clock_timestamp(),
    updated_at timestamptz not null default clock_timestamp(),
    unique (user_id, action_id)
);

create table app_private.approval_actions (
    approval_action_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    target_type text not null check (target_type in ('TASK_CANDIDATE', 'PENDING_ACTION', 'PLAN_PROPOSAL')),
    target_id uuid not null,
    target_version bigint not null check (target_version >= 1),
    decision text not null check (decision in ('APPROVE', 'REJECT')),
    source text not null check (source in ('UI', 'CHAT')),
    source_message_id uuid,
    candidate_target_id uuid,
    pending_action_target_id uuid,
    proposal_target_id uuid,
    created_at timestamptz not null default clock_timestamp(),
    constraint approval_actions_one_typed_target check (
        num_nonnulls(candidate_target_id, pending_action_target_id, proposal_target_id) = 1
    ),
    constraint approval_actions_typed_target_check check (
        (target_type = 'TASK_CANDIDATE' and candidate_target_id = target_id and pending_action_target_id is null and proposal_target_id is null)
        or (target_type = 'PENDING_ACTION' and pending_action_target_id = target_id and candidate_target_id is null and proposal_target_id is null)
        or (target_type = 'PLAN_PROPOSAL' and proposal_target_id = target_id and candidate_target_id is null and pending_action_target_id is null)
    ),
    constraint approval_actions_chat_source_check check (
        (source = 'CHAT' and source_message_id is not null)
        or (source = 'UI' and source_message_id is null)
    )
);

create table app_private.idempotency_records (
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    operation text not null check (length(btrim(operation)) > 0),
    idempotency_key text not null check (length(btrim(idempotency_key)) > 0),
    request_fingerprint text not null,
    state text not null default 'IN_PROGRESS' check (state in ('IN_PROGRESS', 'COMPLETED')),
    result_reference_or_response jsonb,
    created_at timestamptz not null default clock_timestamp(),
    expires_at timestamptz not null,
    primary key (user_id, operation, idempotency_key)
);

create table app_private.chat_approval_attestations (
    attestation_id uuid primary key,
    user_id uuid not null references app_private.user_profiles(user_id) on delete restrict,
    conversation_id uuid not null,
    action_id uuid not null,
    action_version bigint not null check (action_version >= 1),
    target_type text not null check (target_type in ('TASK_CANDIDATE', 'PENDING_ACTION', 'PLAN_PROPOSAL')),
    target_id uuid not null,
    target_version bigint not null check (target_version >= 1),
    decision text not null check (decision in ('APPROVE', 'REJECT')),
    source_message_id uuid not null,
    request_fingerprint text not null,
    issued_at timestamptz not null default clock_timestamp(),
    expires_at timestamptz not null,
    consumed_at timestamptz,
    constraint chat_attestation_expiry_check check (expires_at > issued_at)
);

create index ix_proposals_user_status_generated
    on app_private.plan_proposals (user_id, status, generated_at);
create index ix_blocks_plan_start
    on app_private.study_blocks (plan_id, start_at);
create index ix_blocks_task_plan
    on app_private.study_blocks (task_id, plan_id);
create index ix_pending_awaiting_conversation
    on app_private.pending_actions (user_id, conversation_id)
    where state in ('AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL');
create index ix_approval_target
    on app_private.approval_actions (user_id, target_type, target_id, target_version);
create index ix_chat_attestation_binding
    on app_private.chat_approval_attestations (user_id, action_id, target_id, expires_at);
