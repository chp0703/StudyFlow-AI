# StudyFlow AI — Database Design Baseline v1.0 (DRAFT)

## 1. Document control

| Field | Value |
|---|---|
| Scope | F1 Initial MVP only |
| Status | Draft for team review; not formally approved |
| Source | Consolidated Phase 02A–02G.2.1 outputs |
| Implementation | Design only; no SQL, migrations, ORM or repositories |

Earlier phase reports were supplied in the conversation rather than as repository files. Their complete outputs are conversation sources, not independently versioned repository documents.

Version history: 0.1 initial architecture; 0.2 candidate/lifecycle/security refinement; 0.3 concurrency/time/allocation refinement; 0.4 scheduling/lineage refinement; 1.0-DRAFT consolidation.

## 2. Purpose and F1 boundaries

F1 includes manual task capture and explicit confirmation, authorized text-PDF metadata, availability, manual busy intervals, deterministic plan generation, supplemental proposals, complete plan-level replacement, approval/commit, pending actions, ownership, audit evidence and private PDF metadata.

F2/F3 entities, calendar synchronization, advanced recurrence, overnight availability, automatic task completion/progress, UPDATE_TASK, DELETE_TASK, independent CREATE_STUDY_BLOCK and dedicated FixedCommitment are excluded or deferred.

## 3. Architecture decisions

| Decision | Label |
|---|---|
| Supabase PostgreSQL | BASELINE |
| SQLAlchemy 2.x + psycopg 3 | PROPOSED |
| Supabase CLI as sole migration source | PROPOSED |
| Supabase Auth | TBD |
| Verified JWT to trusted owner context | BASELINE |
| Backend deterministic scheduler | BASELINE |
| Private Supabase Storage | PROPOSED |
| Applicable RLS plus backend authorization | BASELINE |
| Owner advisory lock and READ COMMITTED | PROPOSED |

Direct PostgreSQL does not automatically receive Supabase auth.uid context. Never use separate Supabase CLI and Alembic migration sources.

## 4. Tables and responsibilities

| Table | Responsibility |
|---|---|
| user_settings | Timezone, locale, approved preferences |
| courses | Owner-scoped courses |
| source_documents | PDF metadata, processing, provenance |
| task_candidates | Untrusted manual/PDF candidates |
| academic_tasks | Explicitly confirmed tasks |
| availability | Date-specific/weekly availability |
| busy_intervals | Manual busy intervals |
| study_plans | Concrete proposals and confirmed plans |
| plan_task_allocations | Proposal workload accounting |
| planned_study_blocks | Blocks and source lineage |
| pending_actions | Conversation-scoped clarification |
| approval_events | Verified append-only decisions |

No F2/F3 entities are included.

## 5. ERD

~~~mermaid
erDiagram
    AUTH_USER ||--|| USER_SETTINGS : owns
    AUTH_USER ||--o{ COURSE : owns
    AUTH_USER ||--o{ SOURCE_DOCUMENT : owns
    AUTH_USER ||--o{ TASK_CANDIDATE : owns
    AUTH_USER ||--o{ ACADEMIC_TASK : owns
    AUTH_USER ||--o{ AVAILABILITY : owns
    AUTH_USER ||--o{ BUSY_INTERVAL : owns
    AUTH_USER ||--o{ STUDY_PLAN : owns
    AUTH_USER ||--o{ PENDING_ACTION : owns
    AUTH_USER ||--o{ APPROVAL_EVENT : creates
    COURSE ||--o{ ACADEMIC_TASK : contains
    COURSE ||--o{ TASK_CANDIDATE : resolves_to
    SOURCE_DOCUMENT ||--o{ TASK_CANDIDATE : produces
    TASK_CANDIDATE ||--o| ACADEMIC_TASK : promotes_to
    STUDY_PLAN ||--o{ PLAN_TASK_ALLOCATION : contains
    ACADEMIC_TASK ||--o{ PLAN_TASK_ALLOCATION : allocated_for
    STUDY_PLAN ||--o{ PLANNED_STUDY_BLOCK : contains
    ACADEMIC_TASK ||--o{ PLANNED_STUDY_BLOCK : scheduled_for
    PLANNED_STUDY_BLOCK ||--o| PLANNED_STUDY_BLOCK : source_lineage
    STUDY_PLAN ||--o{ APPROVAL_EVENT : receives
    STUDY_PLAN ||--o{ PENDING_ACTION : referenced_by
    STUDY_PLAN ||--o{ STUDY_PLAN : supersedes
~~~

## 6. Data dictionary

All user-owned records have owner_id. UUID identity columns are primary keys. Defaults are design proposals.

### user_settings

| Column | Type | Null | Meaning |
|---|---|---:|---|
| user_id | uuid | No | PK/FK authenticated user |
| timezone | text | No | IANA timezone |
| locale | text | No | Locale, exact set TBD |
| planning_preferences | jsonb | No | Approved preferences |
| created_at, updated_at | timestamptz | No | Audit timestamps |

### courses

| Column | Type | Null | Meaning |
|---|---|---:|---|
| course_id | uuid | No | PK |
| owner_id | uuid | No | Owner FK |
| name | text | No | Non-empty name |
| external_reference | text | Yes | Optional code |
| created_at, updated_at | timestamptz | No | Audit timestamps |

### source_documents

| Column | Type | Null | Meaning |
|---|---|---:|---|
| document_id | uuid | No | PK |
| owner_id | uuid | No | Owner FK |
| storage_path | text | No | Private Storage path |
| original_filename | text | No | Filename |
| mime_type | text | No | F1 text PDF |
| file_size_bytes | bigint | No | Positive size |
| checksum_sha256 | text | No | Integrity |
| processing_status | text | No | UPLOADED, PROCESSING, EXTRACTED, RETRYABLE_FAILURE, UNSUPPORTED, REJECTED |
| extraction_provenance | jsonb | Yes | Page/text metadata |
| uploaded_at | timestamptz | No | Upload timestamp |

### task_candidates

| Column | Type | Null | Meaning |
|---|---|---:|---|
| candidate_id, owner_id | uuid | No | PK and owner |
| source_type | text | No | MANUAL or PDF |
| source_document_id | uuid | Conditional | Required for PDF |
| title | text | Yes | Required before READY |
| candidate_course_name, candidate_course_reference | text | Yes | Unresolved course |
| resolved_course_id | uuid | Yes | Backend-resolved course |
| start_date, deadline_date | date | Yes | Candidate dates |
| estimated_minutes, remaining_minutes | integer | Yes | Workload |
| priority | text | Yes | Taxonomy TBD |
| candidate_status | text | No | ACTIVE, PROMOTED, REJECTED, EXPIRED |
| validation_status | text | No | READY, NEEDS_CLARIFICATION, INVALID, UNSUPPORTED |
| missing_fields, provenance | jsonb | No/Yes | Validation and provenance |
| confirmed_at, promoted_at | timestamptz | Yes | Confirmation/promotion |
| confirmed_by, promoted_task_id | uuid | Yes | Trusted confirmer/result task |
| expires_at, created_at, updated_at | timestamptz | Yes/No | Lifecycle/audit |

### academic_tasks

| Column | Type | Null | Meaning |
|---|---|---:|---|
| task_id, owner_id | uuid | No | PK and owner |
| course_id | uuid | Yes | Same-owner course |
| title | text | No | Non-empty |
| start_date, deadline_date | date | Yes/No | Eligibility and deadline |
| estimated_minutes, remaining_minutes | integer | No | 0..estimated |
| priority | text | No | Taxonomy/rank TBD |
| status | text | No | Explicit F1 CONFIRMED; no unsafe default |
| version | integer | No | Scheduling update version |
| created_at, updated_at | timestamptz | No | Audit timestamps |

Completion/cancellation/archive are TBD/DEFERRED.

### availability

| Column | Type | Null | Meaning |
|---|---|---:|---|
| availability_id, owner_id | uuid | No | PK and owner |
| recurrence_type | text | No | DATE_SPECIFIC or WEEKLY |
| available_date | date | Conditional | Date-specific |
| weekday | smallint | Conditional | ISO 1–7 weekly |
| start_time, end_time | time(0) | No | Local half-open interval |
| timezone | text | No | IANA timezone |
| effective_from, effective_until | date | Yes | Inclusive/exclusive dates |
| version | integer | No | Concurrency |
| status | text | No | ACTIVE or INACTIVE |
| created_at, updated_at | timestamptz | No | Audit timestamps |

Overnight and advanced recurrence are DEFERRED.

### busy_intervals

| Column | Type | Null | Meaning |
|---|---|---:|---|
| busy_interval_id, owner_id | uuid | No | PK and owner |
| start_at, end_at | timestamptz(0) | No | Absolute half-open interval |
| source_type | text | No | MANUAL in F1 |
| status | text | No | ACTIVE or INACTIVE |
| version | integer | No | Concurrency |
| created_at, updated_at | timestamptz | No | Audit timestamps |

### study_plans

| Column | Type | Null | Meaning |
|---|---|---:|---|
| plan_id, owner_id | uuid | No | Concrete plan and owner |
| supersedes_plan_id | uuid | Yes | Same-owner source plan |
| period_start, period_end | date | No | Inclusive/exclusive period |
| status | text | No | PROPOSED, CONFIRMED, REJECTED, CANCELLED, STALE, EXPIRED, SUPERSEDED |
| row_version | integer | No | Lifecycle concurrency |
| policy_version | text | No | Complete scheduler policy |
| input_snapshot | jsonb | No | Immutable effective inputs |
| input_fingerprint | text | No | Canonical hash |
| expires_at, approved_at | timestamptz | Yes | Proposal lifecycle |
| cancelled_at, cancelled_by | timestamptz/uuid | Proposed | Cancellation audit |
| created_at | timestamptz | No | Creation |

Replacement preserves source period exactly.

### plan_task_allocations

| Column | Type | Null | Meaning |
|---|---|---:|---|
| allocation_id, owner_id | uuid | No | PK and owner |
| plan_id, task_id | uuid | No | Exact plan and task |
| remaining_minutes_snapshot | integer | No | Workload at generation |
| reserved_minutes_snapshot | integer | No | External reservation |
| requested_minutes | integer | No | Workload available to proposal |
| allocated_minutes | integer | No | Exact proposal block sum |
| unscheduled_minutes | integer | No | Requested minus allocated |
| over_reserved_minutes | integer | No | Explicit overage |
| unscheduled_reason | text | Yes | Diagnostic |
| created_at | timestamptz | No | Creation |

### planned_study_blocks

| Column | Type | Null | Meaning |
|---|---|---:|---|
| block_id, owner_id, plan_id, task_id | uuid | No | Identity, owner, plan, task |
| start_at, end_at | timestamptz(0) | No | Half-open block |
| duration_minutes | integer | No | Exact whole-minute duration |
| change_type | text | No | NEW, CARRIED_FORWARD, RESCHEDULED |
| source_plan_id, source_block_id | uuid | Conditional | Source lineage |
| expected_source_plan_row_version | integer | Conditional | Stale detection |
| source_start_at_snapshot, source_end_at_snapshot | timestamptz(0) | Conditional | Source timing |
| source_duration_minutes_snapshot | integer | Conditional | Source duration |
| created_at | timestamptz | No | Creation |

No independent block status exists.

### pending_actions

| Column | Type | Null | Meaning |
|---|---|---:|---|
| action_id, owner_id | uuid | No | PK and owner |
| conversation_id | uuid | No | Server-issued scope |
| action_sequence | integer | No | Monotonic |
| proposal_id | uuid | Yes | Same-owner plan |
| intent | text | No | Allowlisted |
| slots, missing_fields, ambiguities | jsonb | No | Normalized workflow data |
| workflow_state | text | No | OPEN, RESOLVED, CANCELLED, EXPIRED |
| version | integer | No | Concurrency |
| expires_at, created_at, updated_at | timestamptz | No | Lifecycle/audit |

### approval_events

| Column | Type | Null | Meaning |
|---|---|---:|---|
| approval_id, owner_id | uuid | No | PK and approver |
| proposal_id | uuid | No | Same-owner plan |
| approved_row_version | integer | No | Exact version |
| decision | text | No | APPROVED or REJECTED |
| idempotency_key | text | No | Unique per owner |
| created_at, expires_at | timestamptz | No/Yes | Audit/validity |
| metadata | jsonb | Yes | Non-authoritative metadata |

## 7. Keys and ownership

Owner-scoped parent keys:

~~~text
UNIQUE(owner_id, course_id)
UNIQUE(owner_id, document_id)
UNIQUE(owner_id, task_id)
UNIQUE(owner_id, plan_id)
UNIQUE(owner_id, block_id)
~~~

Required composite relationships:

~~~text
task_candidates(owner_id, source_document_id)
  → source_documents(owner_id, document_id)
task_candidates(owner_id, resolved_course_id)
  → courses(owner_id, course_id)
task_candidates(owner_id, promoted_task_id)
  → academic_tasks(owner_id, task_id)
academic_tasks(owner_id, course_id)
  → courses(owner_id, course_id)
study_plans(owner_id, supersedes_plan_id)
  → study_plans(owner_id, plan_id)
plan_task_allocations(owner_id, plan_id)
  → study_plans(owner_id, plan_id)
plan_task_allocations(owner_id, task_id)
  → academic_tasks(owner_id, task_id)
planned_study_blocks(owner_id, plan_id)
  → study_plans(owner_id, plan_id)
planned_study_blocks(owner_id, task_id)
  → academic_tasks(owner_id, task_id)
planned_study_blocks(owner_id, source_plan_id, source_block_id, task_id)
  → planned_study_blocks(owner_id, plan_id, block_id, task_id)
pending_actions(owner_id, proposal_id)
  → study_plans(owner_id, plan_id)
approval_events(owner_id, proposal_id)
  → study_plans(owner_id, plan_id)
~~~

## 8. Uniqueness and checks

Unique/partial rules:

~~~text
UNIQUE(owner_id, plan_id, task_id) on plan_task_allocations
UNIQUE(owner_id, plan_id, source_block_id)
  WHERE source_block_id IS NOT NULL
UNIQUE(owner_id, conversation_id, action_sequence)
UNIQUE(owner_id, idempotency_key)
UNIQUE(owner_id, proposal_id, approved_row_version)
  WHERE decision = APPROVED
UNIQUE(owner_id, supersedes_plan_id)
  WHERE status = CONFIRMED
~~~

Checks include valid candidate/validation/source statuses, positive estimated workload, remaining between zero and estimated, valid recurrence combinations, start before end, valid effective period, valid plan period, positive row versions, non-negative allocation values, requested equals allocated plus unscheduled, and valid lineage change types. NEW has null source fields; carried/rescheduled rows require all source fields and the same task.

## 9. Lifecycles

Candidate: ACTIVE to PROMOTED, REJECTED or EXPIRED. Validation is independent.

Source document: UPLOADED to PROCESSING; PROCESSING to EXTRACTED, RETRYABLE_FAILURE, UNSUPPORTED or REJECTED; retryable failure may return to PROCESSING.

Study plan: PROPOSED to CONFIRMED, REJECTED, CANCELLED, STALE, EXPIRED or SUPERSEDED; CONFIRMED to SUPERSEDED only after a successful replacement.

Pending action: OPEN to RESOLVED, CANCELLED or EXPIRED.

Approval events are append-only APPROVED or REJECTED decisions.

## 10. Scheduling and replacement policy

Date-specific availability uses available_date; weekly availability uses ISO weekday 1–7. Local time uses the IANA timezone. All intervals are half-open. Overnight and advanced recurrence are deferred.

After acquiring the owner lock:

~~~text
decision_at = exact database time
scheduler_as_of = decision_at truncated to approved minute
~~~

Task horizon:

~~~text
eligibility_start = local midnight at task.start_date
H_task = [max(scheduler_as_of, eligibility_start), task_deadline_boundary)
~~~

The exact deadline boundary is TBD.

Confirmed plans and blocks are active commitments. A supplemental proposal has no supersedes_plan_id and cannot overlap confirmed blocks. A complete replacement preserves the source period exactly, maps every future source block once, keeps past source blocks historical, requires explicit in-progress resolution, excludes only its source plan from external reservation subtraction, and supersedes the source plan only after atomic commit. F1 replaces at most one source confirmed plan.

## 11. Workload accounting

remaining_minutes is uncompleted workload and is not automatically decremented on plan confirmation.

For a task:

~~~text
external_reserved =
  future confirmed reservations intersecting H_task,
  excluding only source-plan blocks during replacement

requested_minutes =
  remaining_minutes_snapshot - external_reserved

requested_minutes =
  allocated_minutes + unscheduled_minutes

allocated_minutes =
  SUM(block durations for exact owner, plan and task)
~~~

If external reservations plus required replacement allocations exceed remaining workload, reject with an explicit diagnostic; never silently clamp. Past blocks are historical. In-progress blocks require explicit resolution and contribute only remaining interval. Confirmed reservations do not prove completion.

## 12. Snapshot and fingerprint

input_snapshot is immutable JSONB containing decision_at, scheduler_as_of, period, timezone, policy version, task IDs/versions/status/deadlines/workload/priority, availability definitions and resolved intervals, busy intervals and versions, confirmed blocks/source plans/versions/timestamps, lineage, reservation totals and diagnostics.

input_fingerprint is a canonical hash for stale detection. Approval reloads authoritative records and revalidates; the hash is not a substitute.

## 13. Owner lock and transaction protocol

All scheduling-input mutations, proposal generation and approval use one centralized backend helper.

Protocol:

1. derive lock key from trusted owner UUID;
2. begin READ COMMITTED;
3. acquire transaction-scoped advisory lock as first database operation;
4. ensure and lock user_settings;
5. capture decision_at and scheduler_as_of;
6. reload authoritative inputs;
7. validate and write;
8. commit before lock release.

LLM, PDF and network calls occur outside scheduling transactions. Read-only calendar retrieval does not require the lock. Advisory locks are an application protocol and do not block non-cooperating direct writers; browser writes are denied by grants/RLS and runtime repositories require the scheduling context.

Proposal generation locks before reading snapshot inputs. Approval locks before loading current commitments. Both use the same connection and transaction.

Approval pseudo-sequence:

~~~text
BEGIN READ COMMITTED
acquire owner lock
lock user_settings and proposal/source rows deterministically
capture decision_at and scheduler_as_of
reload confirmed commitments and inputs
if expired: set EXPIRED, increment version, COMMIT, return
if stale: set STALE, increment version, COMMIT, return
revalidate ownership, periods, lineage, reservations,
  allocations, availability and overlaps
insert verified approval
confirm proposal and supersede source plan if applicable
COMMIT
~~~

Technical failure rolls back and leaves the proposal proposed and the old plan unchanged.

## 14. Security and Storage

Identity comes from verified authentication, never LLM or client owner fields. Browser Data API access requires correct RLS. FastAPI direct PostgreSQL requires explicit owner scoping. Privileged/bypass-RLS roles are not runtime user roles.

Browser direct writes to confirmed tasks, plans, allocations, blocks, approvals and promotions are denied or API-mediated.

PDF binaries use an owner-scoped private Storage bucket; source_documents stores metadata/provenance only.

## 15. Index strategy

Recommended indexes:

~~~text
(owner_id, status, deadline_date) on academic_tasks
(owner_id, candidate_status, validation_status, expires_at)
(owner_id, source_document_id) on task_candidates
(owner_id, recurrence_type, status) on availability
(owner_id, weekday, status) on availability
(owner_id, start_at, end_at) on busy_intervals
(owner_id, status, period_start, period_end) on study_plans
(owner_id, plan_id, task_id) on plan_task_allocations
(owner_id, plan_id, source_block_id) on planned_study_blocks
(owner_id, task_id, plan_id) on planned_study_blocks
(owner_id, conversation_id, workflow_state, expires_at)
(owner_id, proposal_id, approved_row_version) on approval_events
~~~

## 16. Migration order

1. UUID/timestamp conventions.
2. Auth ownership references.
3. user_settings.
4. courses.
5. source_documents.
6. task_candidates.
7. academic_tasks.
8. availability.
9. busy_intervals.
10. study_plans.
11. plan_task_allocations.
12. planned_study_blocks.
13. pending_actions.
14. approval_events.
15. Composite keys/FKs.
16. CHECK constraints.
17. Indexes/partial uniqueness.
18. RLS/grants.
19. Private Storage policies.
20. Test fixtures.

Supabase CLI is the proposed sole migration source.

## 17. Test matrix

Integrity tests cover required fields, dates, intervals, durations, status combinations, same-owner/same-task lineage, source uniqueness and allocation arithmetic.

Scheduling tests cover deadline-first ordering, policy-version priority/tie-break, confirmed blocks and busy intervals as exclusions, supplemental reservation subtraction, complete replacement carry-forward, past/in-progress source handling, invalid commitments, over-reservation and zero workload.

Concurrency tests cover owner lock before reads, shared locking for proposal/approval and all scheduler-input writes, two overlapping supplemental proposals, competing replacements, same connection for lock/writes, missing scheduling context and browser direct-write denial.

Lifecycle/audit tests cover atomic/idempotent promotion, committed stale/expired outcomes, technical rollback, immutable snapshots and historical lineage.

## 18. SRS traceability

| Design | SRS coverage |
|---|---|
| Candidate/task separation | F1-TASK-001…010 |
| Explicit confirmation/trusted identity | F1-TASK-008…010 |
| PDF metadata/provenance | F1-PDF-001…007 |
| Availability/conflict detection | F1-AVL-001…008 |
| Deterministic scheduler | F1-PLAN-001…004 |
| Confirmed blocks as commitments | F1-PLAN-002…003 |
| Unscheduled workload | F1-PLAN-005…007 |
| Plan lifecycle/approval | F1-PLAN-005…008 |
| Plan retrieval/status | F1-GET-001…004 |
| Rescheduling lineage/stale checks | F1-RSCH-001…006 |
| Pending actions | F1-ORC-004…006 |
| Exact approval binding | F1-ORC-008…009 |
| No silent schedule mutation | F1-RSCH-005 and approval requirements |

## 19. Decision register

| ID | Decision | Label |
|---|---|---|
| D-01 | Supabase PostgreSQL | BASELINE |
| D-02 | Separate task_candidates | BASELINE |
| D-03 | No implicit confirmed-task default | BASELINE |
| D-04 | Atomic explicit candidate promotion | BASELINE |
| D-05 | Complete plan-level replacement | PROPOSED |
| D-06 | Replacement preserves source period | PROPOSED |
| D-07 | source_block_id plus change_type | PROPOSED |
| D-08 | Normalized plan allocations | PROPOSED |
| D-09 | Confirmed blocks are reservations, not completion | BASELINE |
| D-10 | No automatic remaining-work decrement | BASELINE/DEFERRED |
| D-11 | Owner advisory lock for scheduling operations | PROPOSED |
| D-12 | READ COMMITTED lock protocol | PROPOSED |
| D-13 | SQLAlchemy plus psycopg | PROPOSED |
| D-14 | Supabase CLI sole migration source | PROPOSED |
| D-15 | Supabase Auth provider | TBD |
| D-16 | Deadline boundary | TBD |
| D-17 | Reservation horizon/invalid commitment scope | TBD |
| D-18 | Priority taxonomy/rank | TBD |
| D-19 | Task progress workflow | TBD/DEFERRED |
| D-20 | Runtime PostgreSQL role/RLS context | TBD |
| D-21 | Cancellation audit fields | PROPOSED |
| D-22 | Overnight/advanced recurrence | DEFERRED |
| D-23 | Calendar synchronization | DEFERRED |

## 20. Remaining blockers and Phase 03 prerequisites

Phase 03 requires explicit approval of authentication/JWT verification, runtime PostgreSQL role/RLS context, owner-lock key derivation and enforcement, deadline boundary/reservation horizon, invalid commitment scope, over-reservation behavior, priority/scheduler constants, task progress semantics, cancellation audit fields, and complete replacement/lineage policy.

After approval: freeze schema-affecting decisions, implement one migration source, create ORM models matching this dictionary, require trusted owner context in repositories, implement deterministic scheduling independently of DB/LLM, implement owner-locked proposal/approval transactions, configure RLS/Storage, and add schema/ownership/lineage/workload/concurrency tests.

## 21. Review status

F1 boundary preserved. No F2/F3 entities included. No SQL, migration, ORM or repository implementation included. No secrets or remote database accessed. Superseded alternatives are not presented as approved. Ready for team review; not formally approved.

