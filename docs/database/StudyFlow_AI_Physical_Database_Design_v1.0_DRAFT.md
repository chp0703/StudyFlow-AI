# StudyFlow AI — Physical Database Design v1.0 (DRAFT)

**Scope:** F1 v1.1 physical design only  
**Logical authority:** [`schema_F1.md`](schema_F1.md), version 1.1  
**Architecture authority:** Phase 03.1A ADRs and decision register  
**Status:** Design draft; no SQL, migrations, RPC bodies, or database implementation are included.

## 1. Design boundary

This design maps exactly the ten logical entities in schema v1.1. Supabase Auth owns authentication identity; it is not duplicated as a business table. Business tables are proposed in private schema `app_private`; only controlled functions/read entry points are exposed through `app_api`.

Excluded: Course, SourceDocument/PDF/OCR, StudySession, F2/F3 entities, manual StudyBlock creation, individual block rescheduling, and task update/cancel APIs. These remain `DEFERRED`/`UNSUPPORTED IN F1 v1.1`.

The Scheduling Engine remains a pure Python component. PostgreSQL supplies persistence, constraints, RLS, indexes, and atomic RPC behavior; it does not generate schedules through triggers.

## 2. Physical mapping

| Logical entity | Physical schema.table | Primary key | Owner |
|---|---|---|---|
| User | `app_private.user_profiles` | `user_id` | `user_id` = verified `auth.users.id` |
| TaskCandidate | `app_private.task_candidates` | `candidate_id` | `user_id` |
| AcademicTask | `app_private.academic_tasks` | `task_id` | `user_id` |
| TimeWindow | `app_private.time_windows` | `window_id` | `user_id` |
| StudyPlan | `app_private.study_plans` | `plan_id` | `user_id` |
| StudyBlock | `app_private.study_blocks` | `(plan_id, block_id)` | `user_id` |
| PlanProposal | `app_private.plan_proposals` | `proposal_id` | `user_id` |
| PendingAction | `app_private.pending_actions` | `action_id` | `user_id` |
| ApprovalAction | `app_private.approval_actions` | `approval_action_id` | `user_id` |
| IdempotencyRecord | `app_private.idempotency_records` | `(user_id, operation, idempotency_key)` | `user_id` |

`user_profiles` is an implementation choice for the logical User entity, not an additional business entity. The exact profile table name remains subject to the approved architecture naming review.

## 3. PostgreSQL type conventions

- Logical UUIDs use `uuid`; server/backend creates entity IDs.
- Absolute instants use `timestamptz`; API offsets are normalized to the same instant.
- Local dates use `date`; local recurrence times use `time` plus IANA timezone text.
- Workload and duration values use `integer` minutes.
- Status and kind values use `text` with CHECK constraints rather than undeclared enums, allowing contract validation and controlled migration evolution.
- Nested contract objects use `jsonb`, validated by Pydantic/service schemas and scalar/database checks where safe.
- `24:00` is not stored in a PostgreSQL `time` value or emitted in a timestamp. It is represented by an application-level end-of-day marker and expanded to the next local midnight before persistence as an instant.

## 4. Complete column dictionary

### 4.1 `app_private.user_profiles` — User

| Physical column | Logical field | Type | Null | Default | Constraints/index | Notes |
|---|---|---|---|---|---|---|
| `user_id` | `user_id` | `uuid` | NO | NONE | PK; FK `auth.users.id` | Verified Supabase Auth subject; no duplicate auth table. |
| `timezone` | `timezone` | `text` | NO | NONE | IANA value validated in service | Used for local dates and scheduling. |
| `locale` | `locale` | `text` | NO | NONE | Non-empty validation | Presentation/locale preference. |
| `current_plan_id` | `current_plan_id` | `uuid` | YES | NULL | Same-owner FK to `study_plans(user_id,plan_id)` | Null before first committed plan. |
| `schedule_revision` | `schedule_revision` | `integer` | NO | `0` | CHECK `>=0` | Incremented atomically for scheduling-affecting changes. |
| `scheduling_policy` | `scheduling_policy` | `jsonb` | NO | validated defaults | Pydantic/schema validation | Complete effective profile policy. |
| `created_at` | `created_at` | `timestamptz` | NO | server time | — | Infrastructure timestamp. |
| `updated_at` | `updated_at` | `timestamptz` | NO | server time | — | Updated with profile changes. |

### 4.2 `app_private.task_candidates` — TaskCandidate

| Physical column | Logical field | Type | Null | Default | Constraints/index | Notes |
|---|---|---|---|---|---|---|
| `candidate_id` | `candidate_id` | `uuid` | NO | backend UUID | PK | Draft identity. |
| `user_id` | `user_id` | `uuid` | NO | trusted principal | FK `(user_id)`; owner index | Never sourced from LLM. |
| `conversation_id` | `conversation_id` | `uuid` | NO | NONE | owner/conversation index | Conversation context. |
| `version` | `version` | `integer` | NO | `1` | CHECK `>=1` | Increments on candidate content/state update. |
| `status` | `status` | `text` | NO | `DRAFT` | CHECK `DRAFT,CONFIRMED,CANCELLED` | No product expiry. |
| `slots` | `slots` | `jsonb` | NO | `{}` | CandidateTaskFields validator | May be incomplete before confirmation. |
| `raw_expressions` | `raw_expressions` | `jsonb` | NO | `{}` | Object/map validator | Source wording by field. |
| `field_sources` | `field_sources` | `jsonb` | NO | `{}` | Field-source validator | Provenance does not grant authority. |
| `source_message_id` | `source_message_id` | `uuid` | NO | NONE | owner/context validation | Original message reference. |
| `confirmed_task_id` | `confirmed_task_id` | `uuid` | YES | NULL | Same-owner FK to task | Non-null iff status is CONFIRMED; must match task candidate. |
| `created_at` | `created_at` | `timestamptz` | NO | server time | — | — |
| `updated_at` | `updated_at` | `timestamptz` | NO | server time | — | — |

### 4.3 `app_private.academic_tasks` — AcademicTask

| Physical column | Logical field | Type | Null | Default | Constraints/index | Notes |
|---|---|---|---|---|---|---|
| `task_id` | `task_id` | `uuid` | NO | backend UUID | PK; owner/id index | Confirmed task identity. |
| `user_id` | `user_id` | `uuid` | NO | trusted principal | FK; owner index | — |
| `candidate_id` | `candidate_id` | `uuid` | NO | NONE | UNIQUE; same-owner candidate FK | One task per candidate. |
| `version` | `version` | `integer` | NO | `1` | CHECK `>=1` | Update API is deferred, but version remains contract data. |
| `title` | `title` | `text` | NO | NONE | Trimmed/non-empty | — |
| `description` | `description` | `text` | YES | NULL | — | — |
| `course_label` | `course_label` | `text` | YES | NULL | — | No Course table in F1. |
| `available_from_at` | `available_from_at` | `timestamptz` | YES | NULL | CHECK `<= deadline_at` when present | Absolute start eligibility. |
| `deadline_at` | `deadline_at` | `timestamptz` | NO | NONE | — | Normalized cutoff/instant. |
| `deadline_precision` | `deadline_precision` | `text` | NO | NONE | CHECK `DATE,DATETIME` | Preserves original precision. |
| `deadline_date` | `deadline_date` | `date` | YES | NULL | Required for DATE; null for DATETIME | Local date retained for display/semantics. |
| `deadline_timezone` | `deadline_timezone` | `text` | NO | NONE | IANA validation in service | Required for date-only interpretation. |
| `estimated_minutes` | `estimated_minutes` | `integer` | NO | NONE | CHECK `>0` | — |
| `remaining_minutes` | `remaining_minutes` | `integer` | NO | `estimated_minutes` at creation | CHECK `0<=remaining<=estimated` | Scheduling never decrements it. |
| `priority` | `priority` | `text` | NO | `NORMAL` | CHECK `LOW,NORMAL,HIGH` | — |
| `status` | `status` | `text` | NO | `TODO` | CHECK `TODO,IN_PROGRESS,COMPLETED,CANCELLED` | COMPLETED requires remaining=0; active requires >0. |
| `confirmed_at` | `confirmed_at` | `timestamptz` | NO | server time | — | Candidate confirmation instant. |
| `created_at` | `created_at` | `timestamptz` | NO | server time | — | — |
| `updated_at` | `updated_at` | `timestamptz` | NO | server time | — | — |

### 4.4 `app_private.time_windows` — TimeWindow

| Physical column | Logical field | Type | Null | Default | Constraints/index | Notes |
|---|---|---|---|---|---|---|
| `window_id` | `window_id` | `uuid` | NO | backend UUID | PK | — |
| `user_id` | `user_id` | `uuid` | NO | trusted principal | FK; `(user_id,kind)` index | — |
| `version` | `version` | `integer` | NO | `1` | CHECK `>=1` | Expected-version writes. |
| `kind` | `kind` | `text` | NO | NONE | CHECK `AVAILABILITY,BUSY` | Unified entity. |
| `label` | `label` | `text` | YES | NULL | — | — |
| `recurrence` | `recurrence` | `text` | NO | `NONE` | CHECK `NONE,WEEKLY` | — |
| `timezone` | `timezone` | `text` | NO | NONE | IANA validation in service | — |
| `start_at` | `start_at` | `timestamptz` | YES | NULL | Required only for NONE | — |
| `end_at` | `end_at` | `timestamptz` | YES | NULL | Required only for NONE; `end>start` | — |
| `weekday` | `weekday` | `smallint` | YES | NULL | WEEKLY only; CHECK 1..7 | Monday=1. |
| `start_time` | `start_time` | `time` | YES | NULL | WEEKLY only | Local time. |
| `end_time` | `end_time` | `time` | YES | NULL | WEEKLY only | End-day marker handled before persistence. |
| `valid_from` | `valid_from` | `date` | YES | NULL | Required for WEEKLY | Inclusive. |
| `valid_until` | `valid_until` | `date` | YES | NULL | Null or `> valid_from` | Exclusive. |
| `archived_at` | `archived_at` | `timestamptz` | YES | NULL | — | Archive, not hard delete by default. |
| `created_at` | `created_at` | `timestamptz` | NO | server time | — | — |
| `updated_at` | `updated_at` | `timestamptz` | NO | server time | — | — |

NONE rows require absolute start/end and all weekly fields NULL. WEEKLY rows require weekday/start/end/valid_from and absolute fields NULL. Cross-midnight input is split in the application layer. PostgreSQL checks shape/ranges; IANA/DST validity is application validation.

### 4.5 `app_private.study_plans` — StudyPlan

| Physical column | Logical field | Type | Null | Default | Constraints/index | Notes |
|---|---|---|---|---|---|---|
| `plan_id` | `plan_id` | `uuid` | NO | backend UUID | PK; UNIQUE `(user_id,plan_id)` | — |
| `user_id` | `user_id` | `uuid` | NO | trusted principal | FK; history index | — |
| `version` | `version` | `integer` | NO | NONE | UNIQUE `(user_id,version)`; CHECK >=1 | Sequential per owner. |
| `previous_plan_id` | `previous_plan_id` | `uuid` | YES | NULL | Same-owner self-FK | Null only for first plan. |
| `source_proposal_id` | `source_proposal_id` | `uuid` | NO | NONE | UNIQUE; proposal FK | One committed plan per proposal. |
| `approved_at` | `approved_at` | `timestamptz` | NO | server time | — | Commit instant. |
| `created_at` | `created_at` | `timestamptz` | NO | server time | — | Immutable after commit. |

### 4.6 `app_private.study_blocks` — StudyBlock

| Physical column | Logical field | Type | Null | Default | Constraints/index | Notes |
|---|---|---|---|---|---|---|
| `plan_id` | `plan_id` | `uuid` | NO | NONE | PK part; same-owner plan FK | — |
| `block_id` | `block_id` | `uuid` | NO | backend UUID for new block | PK part | Repeats across historical snapshots legitimately. |
| `user_id` | `user_id` | `uuid` | NO | trusted principal | Same-owner FK support | — |
| `task_id` | `task_id` | `uuid` | NO | NONE | Same-owner task FK; `(task_id,plan_id)` index | — |
| `start_at` | `start_at` | `timestamptz` | NO | NONE | Range/index | — |
| `end_at` | `end_at` | `timestamptz` | NO | NONE | CHECK `end>start` | — |
| `is_locked` | `is_locked` | `boolean` | NO | `false` | — | Replanning protection; no completion state. |
| `created_at` | `created_at` | `timestamptz` | NO | server time | — | Immutable snapshot row timestamp. |

There is deliberately no `UNIQUE(user_id,block_id)`, no duration column, no source block ID, no change type, and no StudySession.

### 4.7 `app_private.plan_proposals` — PlanProposal

| Physical column | Logical field | Type | Null | Default | Constraints/index | Notes |
|---|---|---|---|---|---|---|
| `proposal_id` | `proposal_id` | `uuid` | NO | backend UUID | PK | — |
| `user_id` | `user_id` | `uuid` | NO | trusted principal | FK; `(user_id,status,generated_at)` index | — |
| `version` | `version` | `integer` | NO | `1` | CHECK >=1 | Content version; payload immutable. |
| `status` | `status` | `text` | NO | `PROPOSED` | CHECK `PROPOSED,APPROVED,REJECTED,STALE` | — |
| `base_plan_id` | `base_plan_id` | `uuid` | YES | NULL | Same-owner plan FK | Null for first plan proposal. |
| `base_plan_version` | `base_plan_version` | `integer` | YES | NULL | Null iff base_plan_id null; CHECK >=1 | — |
| `base_schedule_revision` | `base_schedule_revision` | `integer` | NO | NONE | CHECK >=0 | — |
| `generation_scope` | `generation_scope` | `jsonb` | NO | NONE | Pydantic + shape validation | Full scope object. |
| `payload` | `payload` | `jsonb` | NO | NONE | Immutable ProposalPayload validator | Full resulting snapshot. |
| `algorithm_version` | `algorithm_version` | `text` | NO | NONE | Non-empty | — |
| `policy_snapshot` | `policy_snapshot` | `jsonb` | NO | NONE | Complete SchedulingPolicy validator | Effective policy after override. |
| `generated_at` | `generated_at` | `timestamptz` | NO | server time | — | — |
| `committed_plan_id` | `committed_plan_id` | `uuid` | YES | NULL | Unique; same-owner plan FK | Non-null iff APPROVED. |
| `created_at` | `created_at` | `timestamptz` | NO | server time | — | — |
| `updated_at` | `updated_at` | `timestamptz` | NO | server time | Status only. |

### 4.8 `app_private.pending_actions` — PendingAction

| Physical column | Logical field | Type | Null | Default | Constraints/index | Notes |
|---|---|---|---|---|---|---|
| `action_id` | `action_id` | `uuid` | NO | backend UUID | PK; dependency FK | — |
| `user_id` | `user_id` | `uuid` | NO | trusted principal | FK; partial awaiting unique index | — |
| `conversation_id` | `conversation_id` | `uuid` | NO | NONE | owner/conversation index | — |
| `version` | `version` | `integer` | NO | `1` | CHECK >=1 | — |
| `intent` | `intent` | `text` | NO | NONE | Catalog validation | — |
| `state` | `state` | `text` | NO | `AWAITING_CLARIFICATION` | CHECK five states | No EXPIRED. |
| `requires_review` | `requires_review` | `boolean` | NO | `false` | — | Re-display before decision. |
| `candidate_id` | `candidate_id` | `uuid` | YES | NULL | Same-owner candidate FK | — |
| `proposal_id` | `proposal_id` | `uuid` | YES | NULL | Same-owner proposal FK | — |
| `draft_arguments` | `draft_arguments` | `jsonb` | NO | `{}` | Intent-specific Pydantic model | — |
| `missing_fields` | `missing_fields` | `jsonb` | NO | `[]` | Array-of-string validator | — |
| `ambiguities` | `ambiguities` | `jsonb` | NO | `[]` | Issue[] validator | — |
| `depends_on_action_id` | `depends_on_action_id` | `uuid` | YES | NULL | Same-owner self-FK | — |
| `created_at` | `created_at` | `timestamptz` | NO | server time | — | — |
| `updated_at` | `updated_at` | `timestamptz` | NO | server time | — | — |

The partial unique index covers `(user_id, conversation_id)` only when state is one of the three AWAITING states. COMPLETED/CANCELLED rows do not block future actions.

### 4.9 `app_private.approval_actions` — ApprovalAction

| Physical column | Logical field | Type | Null | Default | Constraints/index | Notes |
|---|---|---|---|---|---|---|
| `approval_action_id` | `approval_action_id` | `uuid` | NO | backend UUID | PK | — |
| `user_id` | `user_id` | `uuid` | NO | trusted principal | FK; owner/target index | — |
| `target_type` | `target_type` | `text` | NO | NONE | CHECK three target types | — |
| `target_id` | `target_id` | `uuid` | NO | NONE | Must equal typed target ID | Contract mirror. |
| `target_version` | `target_version` | `integer` | NO | NONE | CHECK >=1 | Exact displayed version. |
| `decision` | `decision` | `text` | NO | NONE | CHECK APPROVE/REJECT | — |
| `source` | `source` | `text` | NO | NONE | CHECK UI/CHAT | — |
| `source_message_id` | `source_message_id` | `uuid` | YES | NULL | Required when CHAT | — |
| `target_candidate_id` | physical typed target | `uuid` | YES | NULL | Same-owner candidate FK | Exactly-one target strategy. |
| `target_pending_action_id` | physical typed target | `uuid` | YES | NULL | Same-owner action FK | Exactly-one target strategy. |
| `target_proposal_id` | physical typed target | `uuid` | YES | NULL | Same-owner proposal FK | Exactly-one target strategy. |
| `created_at` | `created_at` | `timestamptz` | NO | server time | — | — |

The typed columns are physical integrity support, not additional logical entities. A CHECK/trigger or equivalent RPC constraint requires exactly one typed target, matching `target_type` and `target_id`, same owner, current target state, and exact `target_version`. The exact trigger implementation remains a physical implementation detail for Stage 03.3.

### 4.10 `app_private.idempotency_records` — IdempotencyRecord

| Physical column | Logical field | Type | Null | Default | Constraints/index | Notes |
|---|---|---|---|---|---|---|
| `user_id` | `user_id` | `uuid` | NO | trusted principal | PK/UNIQUE composite | — |
| `operation` | `operation` | `text` | NO | NONE | Composite unique; catalog validation | — |
| `idempotency_key` | `idempotency_key` | `text` | NO | NONE | Composite unique | — |
| `request_fingerprint` | `request_fingerprint` | `text` | NO | NONE | — | Canonical normalized request. |
| `state` | `state` | `text` | NO | `IN_PROGRESS` | CHECK IN_PROGRESS/COMPLETED | — |
| `result_reference_or_response` | `result_reference_or_response` | `jsonb` | YES | NULL | Response/result validator | — |
| `created_at` | `created_at` | `timestamptz` | NO | server time | — | — |
| `expires_at` | `expires_at` | `timestamptz` | NO | operational policy | Retention only | The only v1.1 expires_at. |

Same key/same fingerprint returns the stored result. Same key/different fingerprint returns `IDEMPOTENCY_CONFLICT`. Completion is in the same RPC transaction as the business write.

## 5. JSONB contract dictionary

| JSONB column | Pydantic model | Required top-level content | Validation boundary | Index |
|---|---|---|---|---|
| candidate `slots` | `CandidateTaskFields` | candidate task fields; incomplete allowed | Pydantic + confirmation service | None initially |
| `raw_expressions` | `dict[str,str]` | field-to-original-expression map | Pydantic shape | None |
| `field_sources` | `dict[str,FieldSource]` | source enum and reference | Pydantic; not authorization | None |
| proposal `generation_scope` | `GenerationScope` | start/end/mode/task_ids | Pydantic + RPC shape checks | None |
| proposal `payload` | `ProposalPayload` | blocks, summaries, coverage, warnings, diff | Pydantic + immutable persistence | None initially |
| proposal `policy_snapshot` | `SchedulingPolicy` | all five policy fields | Pydantic + scalar checks | None |
| profile `scheduling_policy` | `SchedulingPolicy` | all five policy fields | Pydantic + service validation | None |
| action `draft_arguments` | intent-specific arguments | operation fields | Pydantic allowlist | None |
| action `missing_fields` | `list[str]` | string array | Pydantic shape | None |
| action `ambiguities` | `list[Issue]` | issue objects | Pydantic shape | None |
| idempotency result | operation result | stored result/reference | operation-specific validator | Lookup uses relational key |

GIN indexes are not proposed until a concrete query path requires searching inside JSONB. Contract validation does not replace relational constraints.

## 6. Keys, foreign keys, and deletion behavior

All owner-scoped parent tables expose a supporting unique `(user_id, entity_id)` key where required by composite references. Foreign keys use `ON UPDATE RESTRICT` (IDs are immutable) and `ON DELETE RESTRICT` for confirmed tasks, plans, proposals, and referenced records. User/profile deletion is a separate lifecycle decision and must not cascade-delete history. Pending/action drafts may be archived/cancelled by controlled operations; no automatic product TTL is allowed.

| Relationship | Referencing columns | Referenced columns | Delete | Same-owner guarantee |
|---|---|---|---|---|
| Candidate → User | candidate `(user_id)` | profile `(user_id)` | RESTRICT | owner FK |
| Task → User | task `(user_id)` | profile `(user_id)` | RESTRICT | owner FK |
| Task → Candidate | `(user_id,candidate_id)` | candidate `(user_id,candidate_id)` | RESTRICT | composite FK |
| Profile → current plan | `(user_id,current_plan_id)` | plan `(user_id,plan_id)` | SET NULL only for pre-current profile lifecycle; otherwise RESTRICT | composite FK |
| TimeWindow → User | `(user_id)` | profile `(user_id)` | RESTRICT | owner FK |
| Plan → User | `(user_id)` | profile `(user_id)` | RESTRICT | owner FK |
| Plan → previous plan | `(user_id,previous_plan_id)` | plan `(user_id,plan_id)` | RESTRICT | composite self-FK |
| Block → Plan | `(user_id,plan_id)` | plan `(user_id,plan_id)` | RESTRICT | composite FK |
| Block → Task | `(user_id,task_id)` | task `(user_id,task_id)` | RESTRICT | composite FK |
| Proposal → base plan | `(user_id,base_plan_id)` | plan `(user_id,plan_id)` | RESTRICT | composite FK |
| Proposal → committed plan | `(user_id,committed_plan_id)` | plan `(user_id,plan_id)` | RESTRICT | composite FK |
| PendingAction → candidate/proposal/dependency | owner plus ID | same-owner parent | RESTRICT | composite FK |
| ApprovalAction → typed target | owner plus typed ID | exact target | RESTRICT | typed FK + trigger/equivalent |
| Idempotency → User | `(user_id)` | profile `(user_id)` | RESTRICT | owner FK |

## 7. Circular current-plan design

`user_profiles.current_plan_id` and `study_plans.user_id` form a circular dependency. Recommended migration sequence:

1. Create profile table with `current_plan_id` nullable and without the final FK.
2. Create `study_plans` with owner FK and `(user_id,plan_id)` unique support key.
3. Add the composite current-plan FK as a deferred constraint or staged `ALTER` after both tables exist.
4. Initialize a profile with `current_plan_id=NULL`.
5. Insert first plan with `previous_plan_id=NULL`.
6. Update profile pointer and increment revision in the same approval RPC.

The first plan uses version 1. Later plans use `previous_plan_id` equal to the current plan and the next per-user version. No ACTIVE status is added.

## 8. Transaction and RPC design

The approved architecture uses Option A: authenticated users may call specifically authorized RPCs directly. FastAPI remains the normal gateway but is not the only security boundary. Every mutation RPC independently resolves `auth.uid()`, checks ownership, versions, states, approval evidence, idempotency, and business invariants.

| RPC | Signature outline | Reads/writes | Lock | Idempotency/revision | Domain errors |
|---|---|---|---|---|---|
| `app_api.create_task_candidate` | `p_conversation_id uuid, p_source_message_id uuid, p_slots jsonb, p_raw_expressions jsonb, p_field_sources jsonb, p_idempotency_key text, p_request_fingerprint text` | profile; inserts candidate/idempotency | owner protocol | idempotency; revision if scheduling-affecting | FORBIDDEN, INVALID_PARAMETER, IDEMPOTENCY_CONFLICT |
| `app_api.confirm_task` | `p_candidate_id uuid, p_expected_candidate_version integer, p_approval_action jsonb, p_idempotency_key text, p_request_fingerprint text` | candidate; inserts task/approval; updates profile/idempotency | yes | approval + revision + idempotency | STALE_ENTITY_VERSION, APPROVAL_REQUIRED |
| `app_api.search_tasks` | `p_status_filter text[], p_query text, p_limit integer, p_cursor jsonb` | tasks | no | read-only | FORBIDDEN, INVALID_PARAMETER |
| `app_api.set_availability` | `p_operation text, p_window jsonb, p_window_id uuid, p_expected_window_version integer, p_approval_action jsonb, p_idempotency_key text, p_request_fingerprint text` | windows/profile | yes | approval + revision + idempotency | STALE_ENTITY_VERSION, INVALID_PARAMETER |
| `app_api.set_busy_interval` | same shape; kind forced BUSY | windows/profile | yes | approval + revision + idempotency | STALE_ENTITY_VERSION, INVALID_PARAMETER |
| `app_api.set_scheduling_preferences` | `p_policy_patch jsonb, p_expected_schedule_revision integer, p_approval_action jsonb, p_idempotency_key text, p_request_fingerprint text` | profile | yes | approval + revision + idempotency | STALE_ENTITY_VERSION, APPROVAL_REQUIRED |
| `app_api.generate_study_plan` | `p_scope jsonb, p_engine_result jsonb, p_expected_schedule_revision integer, p_idempotency_key text, p_request_fingerprint text` | one consistent read snapshot; inserts proposal | persistence lock | revision compare + idempotency | STALE_PROPOSAL, TIME_CONFLICT |
| `app_api.get_study_plan` | `p_view text, p_version integer, p_proposal_id uuid, p_start_at timestamptz, p_end_at timestamptz` | current/history/proposal | no | read-only | ENTITY_NOT_FOUND, INVALID_PARAMETER |
| `app_api.approve_study_plan` | `p_proposal_id uuid, p_expected_proposal_version integer, p_expected_plan_version integer, p_approval_action jsonb, p_idempotency_key text, p_request_fingerprint text` | proposal/profile/tasks/windows/plans/blocks; writes plan/blocks/profile/proposal/idempotency | yes | idempotency lookup first; revision increment | STALE_PROPOSAL, STALE_PLAN_VERSION, TIME_CONFLICT |
| `app_api.reject_study_plan` | `p_proposal_id uuid, p_expected_proposal_version integer, p_approval_action jsonb, p_idempotency_key text, p_request_fingerprint text` | proposal/approval/idempotency | yes | idempotency lookup first; no schedule revision | STALE_ENTITY_VERSION, IDEMPOTENCY_CONFLICT |

The `engine_result` input is accepted only from the trusted FastAPI service after a consistent read snapshot and pure-engine execution; the RPC validates it before persistence. RPCs are not a substitute for Pydantic/domain validation.

Deferred/unsupported RPCs: task update, task cancellation, manual StudyBlock creation, and individual StudyBlock rescheduling.

## 9. RLS, grants, and exposure

`app_private` remains unexposed through PostgREST. `app_api` is the only proposed exposed schema. Option A requires authenticated users to receive EXECUTE only on approved functions. Schema USAGE, table privileges, function EXECUTE, and RLS policies are distinct:

- `authenticated` receives `USAGE` on `app_api` and EXECUTE on approved RPCs.
- Direct table access is not granted through the exposed API schema.
- SECURITY INVOKER functions require only the underlying `app_private` table privileges needed by their operation, plus RLS policies based on verified `auth.uid()`.
- Any SECURITY DEFINER exception requires least-privilege ownership, `search_path=''`, schema-qualified objects, restricted EXECUTE, and explicit owner checks.
- `anon`, PUBLIC, and service-role execution are not granted for user mutations.

Exact grants and policies are implementation work for Stage 03.3 and must be tested with direct RPC calls, including malicious payloads and cross-user IDs.

## 10. Index strategy

| Index | Table | Definition/type | Unique/partial | Query |
|---|---|---|---|---|
| `uq_study_plans_user_version` | study_plans | `(user_id,version)` B-tree | unique | history/version |
| `uq_study_plans_user_plan` | study_plans | `(user_id,plan_id)` B-tree | unique | composite FKs |
| `uq_study_plans_source_proposal` | study_plans | `source_proposal_id` B-tree | unique | one commit/proposal |
| `ix_tasks_user_status_deadline` | academic_tasks | `(user_id,status,deadline_at)` | nonunique | eligible task search |
| `uq_tasks_candidate` | academic_tasks | `(candidate_id)` | unique | promotion/retry |
| `ix_windows_user_kind` | time_windows | `(user_id,kind)` | nonunique | scheduling context |
| `ix_proposals_user_status_generated` | plan_proposals | `(user_id,status,generated_at)` | nonunique | proposal views |
| `ix_blocks_plan_start` | study_blocks | `(plan_id,start_at)` | nonunique | calendar snapshot |
| `ix_blocks_task_plan` | study_blocks | `(task_id,plan_id)` | nonunique | task allocations |
| `ix_pending_awaiting_conversation` | pending_actions | `(user_id,conversation_id)` | partial where awaiting | active action lookup |
| `ix_approval_target` | approval_actions | `(user_id,target_type,target_id,target_version)` | nonunique | target verification |
| `uq_idempotency_owner_operation_key` | idempotency_records | `(user_id,operation,idempotency_key)` | unique | replay/conflict |
| `ex_study_blocks_plan_time` | study_blocks | GiST `(plan_id WITH =, tstzrange(start_at,end_at,'[)') WITH &&)` | exclusion, proposed | within-snapshot overlap |

The GiST exclusion requires `btree_gist` for UUID/equality support if the selected PostgreSQL setup does not provide it. No global block-ID uniqueness or cross-plan overlap constraint is permitted. No JSONB GIN indexes are proposed without a concrete query requirement.

## 11. Overlap and snapshot integrity

The proposed `ex_study_blocks_plan_time` constraint rejects overlapping blocks only when they share a `plan_id`. Adjacent half-open blocks are valid. Different historical plans may contain overlapping times because they are immutable alternatives in history.

RPC/service validation separately checks:

1. task eligibility and deadline;
2. availability union and BUSY subtraction;
3. workload and remaining minutes;
4. retained/locked blocks;
5. current authoritative scheduling inputs;
6. owner and revision consistency.

The database exclusion constraint cannot inspect parent plan status and must not be used for these separate validations.

## 12. Lifecycle and deletion

Confirmed tasks, plans, blocks, proposals referenced by plans, approval actions, and audit/idempotency records are retained. Candidate/pending-action/proposal waiting states have no product TTL. Idempotency cleanup may use `expires_at` only after operational retry guarantees and must not delete business history required by references. IDs are immutable; `ON UPDATE RESTRICT` is used. Hard deletion of referenced history is not supported in F1.

## 13. Migration dependency plan (plan only)

| Stage | Purpose/dependencies | Objects | Validation/rollback |
|---|---|---|---|
| 1 | Base schemas/extensions; none | `app_private`, `app_api`, approved extensions | Verify extension availability; remove cleanly before dependents |
| 2 | Auth/profile; Stage 1 | `user_profiles` and owner keys | Verify `auth.users` mapping; pointer FK deferred |
| 3 | Candidate/task; Stage 2 | candidates/tasks, promotion constraints | Test status/workload/deadline checks |
| 4 | TimeWindow; Stage 2 | union table and conditional checks | Test recurrence/DST boundary validation |
| 5 | Plans/proposals; Stages 2–4 | plans/proposals and base/commit keys | Test first-plan/circular FK staging |
| 6 | Blocks; Stages 3 and 5 | blocks, composite PK, same-owner keys | Test identity continuity and snapshot overlap |
| 7 | Actions/idempotency; Stages 2,3,5 | pending/approval/idempotency | Test awaiting uniqueness and target integrity |
| 8 | Supporting constraints/indexes; Stages 3–7 | B-tree/partial/GiST indexes | Verify query plans and rollback safety |
| 9 | RLS/grants/exposure; all tables | policies, grants, API schema exposure | Direct RPC/cross-user tests; no broad grants |
| 10 | RPC functions; all prior stages | controlled `app_api` functions | RPC contract/atomicity tests |
| 11 | Seed/test fixtures; all prior stages | non-production seed data | Clean reset and CI replay |

This is a design dependency plan, not executable migration content. The pointer FK may be added after both profile and plan tables exist; all migration files must remain Supabase CLI-only.

## 14. Traceability and unresolved choices

Every table/column above maps directly to schema v1.1; physical-only support columns are `user_profiles`, typed ApprovalAction target columns, and indexes/constraints. Remaining physical choices are `PROPOSED`/`TBD`: exact profile table name, trigger versus equivalent ApprovalAction enforcement, exact grants/RLS policy text, whether `btree_gist` is enabled, and final RPC argument/result JSON schemas.

Stage 03.3 remains blocked until team approval of the register and ADR gates. No SQL or migration should be generated from this draft before that approval.

