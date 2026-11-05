# StudyFlow AI — Physical Design Traceability

**Logical authority:** `docs/database/schema_F1.md` v1.1  
**Physical design:** `StudyFlow_AI_Physical_Database_Design_v1.0_DRAFT.md`  
**Status:** Design traceability draft; no implementation approved by this document.

## 1. Entity traceability

| Schema v1.1 entity | Physical table | Key traceability | Relevant ADR/register |
|---|---|---|---|
| User | `app_private.user_profiles` | `user_id`, timezone, locale, current plan, revision, policy | ADR-002; E-02, E-05, E-06 |
| TaskCandidate | `app_private.task_candidates` | candidate fields, status, version, confirmation link | ADR-003; E-03, E-07, E-09 |
| AcademicTask | `app_private.academic_tasks` | workload, deadline precision, status, candidate uniqueness | ADR-003; E-07, E-09 |
| TimeWindow | `app_private.time_windows` | unified kind/recurrence and conditional fields | ADR-001, ADR-003; E-01, E-03 |
| StudyPlan | `app_private.study_plans` | immutable versioned snapshot and previous plan | ADR-005; E-06, E-07, E-11 |
| StudyBlock | `app_private.study_blocks` | `(plan_id,block_id)`, task/plan owner, locked interval | ADR-005; E-07, E-11 |
| PlanProposal | `app_private.plan_proposals` | full payload, base revision, policy snapshot, commit link | ADR-003, ADR-005; E-03, E-10 |
| PendingAction | `app_private.pending_actions` | awaiting-state uniqueness, version, review flag | ADR-003; E-07, E-09 |
| ApprovalAction | `app_private.approval_actions` | typed target support for polymorphic contract | ADR-002, ADR-003; E-05, E-08 |
| IdempotencyRecord | `app_private.idempotency_records` | composite uniqueness, fingerprint, replay state | ADR-003, ADR-005; E-03, E-10 |

## 2. Field traceability

All logical fields are represented in the physical dictionary. The following physical-only columns or structures do not add business entities:

| Physical addition | Reason | Approval source/status |
|---|---|---|
| `user_profiles` table name | Maps logical User to an authenticated `auth.users` subject | E-06 `PROPOSED` |
| `candidate_target_id`, `pending_action_target_id`, `proposal_target_id` | Enforces one exact ApprovalAction target despite polymorphic `target_type/target_id` | `IMPLEMENTATION_BASELINE`: exactly-one CHECK, same-owner FKs, and BEFORE INSERT validation trigger. |
| Supporting `(user_id,id)` unique keys | Enables database-enforced same-owner composite FKs | E-07 `PROPOSED` |
| B-tree/partial/GiST indexes | Query and snapshot integrity performance | E-11/E-13 `PROPOSED` |

## 3. Constraint traceability

| Constraint | Physical design | Schema rule | Status |
|---|---|---|---|
| Candidate promotion | Unique task `candidate_id`; candidate confirmation link matches task | One candidate creates at most one task | `CONFIRMED_FROM_SCHEMA` + physical design `PROPOSED` |
| Task workload | `estimated_minutes > 0`; `0 <= remaining <= estimated`; status implications | AcademicTask invariants | `CONFIRMED_FROM_SCHEMA` |
| Deadline precision | DATE requires date; DATETIME retains instant | Date-only semantics preserved | `CONFIRMED_FROM_SCHEMA` |
| TimeWindow union | NONE/WEEKLY mutually exclusive field checks; WEEKLY `start_time < 24:00:00`, `end_time > start_time`, `end_time <= 24:00:00` | Unified TimeWindow and F1 end-of-day boundary | `CONFIRMED_FROM_SCHEMA`; PostgreSQL representation `PROPOSED` |
| Plan versions | Unique `(user_id,version)` and `source_proposal_id` | Immutable history | `CONFIRMED_FROM_SCHEMA` |
| Current plan | Same-owner composite FK; staged circular dependency | One current plan | E-06 `PROPOSED` |
| Block identity | PK `(plan_id,block_id)`; no global block-ID uniqueness | Logical identity across snapshots | `CONFIRMED_FROM_SCHEMA` |
| PendingAction | Partial unique awaiting `(user_id,conversation_id)` | One awaiting action | `CONFIRMED_FROM_SCHEMA` |
| Approval target | Typed target columns + exactly-one constraint/equivalent | Exact owner/version/content target | E-08 `PROPOSED` |
| Idempotency | Unique owner/operation/key and fingerprint replay | Retry safety | `CONFIRMED_FROM_SCHEMA` |
| Snapshot overlap | Proposed GiST exclusion keyed by plan ID | Half-open non-overlap per snapshot | E-11 `PROPOSED` |

## 4. Index traceability

| Index family | Physical purpose | Contract/access path |
|---|---|---|
| User/foreign-key B-trees | Owner and same-owner joins | Ownership rules |
| Tasks `(user_id,status,deadline_at)` | Eligible task retrieval | Scheduling/search operations |
| TimeWindows `(user_id,kind)` | Availability/BUSY loading | TimeWindow contract |
| Plans `(user_id,version)` and `(user_id,plan_id)` | History/current-pointer resolution | StudyPlan snapshots |
| Blocks `(plan_id,start_at)` and `(task_id,plan_id)` | Calendar/task views | StudyBlock contract |
| Proposals `(user_id,status,generated_at)` | Proposal listing | PlanProposal lifecycle |
| Pending partial awaiting index | Active action lookup | One awaiting action rule |
| Approval target index | Exact target/version lookup | ApprovalAction |
| Idempotency unique index | Replay/conflict lookup | IdempotencyRecord |
| GiST plan/range exclusion | Snapshot-level overlap | E-11 proposed design |

No JSONB index is proposed without a concrete query requirement. No global `(user_id,block_id)` unique index exists.

## 5. RPC traceability

| RPC | Schema operations | Transaction/security requirement | Status |
|---|---|---|---|
| `app_api.create_task_candidate` | Insert candidate/idempotency | Authenticated owner; controlled write | `PROPOSED` |
| `app_api.confirm_task` | Candidate → task + approval + idempotency | Atomic; owner lock; revision | `PROPOSED` |
| `app_api.search_tasks` | Read tasks | User-scoped RLS; no mutation | `PROPOSED` |
| `app_api.set_availability` | Add/update/archive TimeWindow | Version, owner lock, revision | `PROPOSED` |
| `app_api.set_busy_interval` | Add/update/archive BUSY TimeWindow | Version, owner lock, revision | `PROPOSED` |
| `app_api.set_scheduling_preferences` | Merge policy/profile | Expected revision, owner lock | `PROPOSED` |
| `app_api.generate_study_plan` | Persist full proposal | Consistent input snapshot and revision compare | `PROPOSED` |
| `app_api.get_study_plan` | Read current/history/proposal | User-scoped read | `PROPOSED` |
| `app_api.approve_study_plan` | Plan/blocks/profile/proposal/idempotency | Idempotency first; atomic owner lock | `PROPOSED` |
| `app_api.reject_study_plan` | Proposal/approval/idempotency | Idempotency first; atomic result | `PROPOSED` |

Task update/cancel, manual StudyBlock creation, and individual StudyBlock rescheduling are intentionally not mapped to RPCs: `DEFERRED / UNSUPPORTED IN F1 v1.1`.

## 6. Security traceability

`app_private` is unexposed through PostgREST; `app_api` exposes only allowlisted RPC/read entry points. Exposure, schema `USAGE`, table privileges, function `EXECUTE`, RLS, and `SECURITY INVOKER` execution context are separate controls. Under Option A, FastAPI is the normal gateway but not the exclusive gateway: authenticated users may directly invoke only allowlisted `app_api` RPCs.

| Category | `authenticated` minimum | `anon` | Owner/migration role | RLS/direct API result |
|---|---|---|---|---|
| Approved reads | `USAGE app_api`, named read `EXECUTE`, required private-table `SELECT` | No private access | Owns/migrates objects; not a runtime caller | Owner `SELECT` RLS; direct allowlisted RPC permitted. |
| UI approval and other mutations | `USAGE app_api`, named mutation `EXECUTE`, only required private-table `SELECT`/`INSERT`/`UPDATE` | No mutation `EXECUTE` | Owns/migrates objects; not a runtime caller | Owner RLS for each operation; direct UI RPC permitted. |
| CHAT-origin approval | No direct user grant that accepts CHAT evidence | Denied | No separate backend role approved | Requires future approved backend attestation; otherwise reject. |

`PUBLIC` receives no broad `EXECUTE`; no separate privileged backend role is approved. `SECURITY INVOKER` is preferred and requires the caller's underlying table privileges while RLS remains effective. A `SECURITY DEFINER` exception remains per-function `PROPOSED` work with a least-privilege owner, safe empty search path, schema-qualified references, restricted EXECUTE, owner checks, and documented RLS implications.

Approval provenance is traceable to the RPC action itself: UI approval is valid only when the authenticated RPC call verifies its exact owner, target, version, state/context, and server-derived presentation binding. Client-provided CHAT source/message identifiers and LLM booleans are untrusted. Required authorization tests cover authorized authenticated RPC, anonymous mutation denial, cross-user references, forged versions/evidence/CHAT provenance, private-schema denial, allowed API RPC success, and RLS behavior within invoker execution.

## 7. Stage 03.2 checklist

- [x] Ten logical entities mapped.
- [x] All logical fields assigned physical types and nullability.
- [x] Same-owner FK strategy documented.
- [x] Current-plan circular dependency documented.
- [x] StudyBlock composite identity preserved; global block uniqueness excluded.
- [x] ApprovalAction typed-target strategy documented.
- [x] PendingAction partial uniqueness documented.
- [x] Idempotency uniqueness and replay behavior documented.
- [x] TimeWindow union checks documented.
- [x] PostgreSQL-preserved `24:00:00` end-time expansion and DST handling documented.
- [x] Task, proposal, snapshot, overlap, and deletion rules documented.
- [x] Index and migration dependency plans documented.
- [x] RPC signatures and F1 exclusions documented.
- [x] RLS/grant/schema exposure design documented.
- [x] SECURITY INVOKER privilege matrix, approval provenance, and required authorization tests documented.
- [x] Physical-only choices identified and labeled.
- [x] Routine physical choices finalized as `IMPLEMENTATION_BASELINE`.
- [ ] Stage 03.3 migration execution, environment configuration, and test evidence.

## 8. Stage 03.2 implementation-baseline traceability

**IMPLEMENTATION_BASELINE — selected for F1 implementation.** These physical choices are authorized design baselines, not claims of separate team approval.

| Logical requirement/invariant | Final physical realization | Verification evidence required |
|---|---|---|
| Ten F1 entities only | Ten `app_private` business tables; `chat_approval_attestations` is authorization infrastructure, not a logical entity. | Migration inventory contains exactly the ten mapped domain tables plus the documented support table. |
| User identity/profile | `user_profiles.user_id = auth.users.id`; migration-owned signup trigger creates one profile; deferred `(user_id,current_plan_id)` FK. | Signup, duplicate-profile, missing-profile, and first-plan sequence tests. |
| WEEKLY end boundary | `time without time zone`; preserved `end_time = 24:00:00`; start `< 24:00:00`, end `> start`, end `<= 24:00:00`. | Five documented valid/invalid cases plus DST ambiguity/nonexistence tests. |
| Same-owner integrity | Unique owner/entity keys and composite FKs for all owner-scoped references. | Cross-user candidate/task/plan/block/action reference tests. |
| StudyBlock identity | PK `(plan_id,block_id)`; no global `(user_id,block_id)` uniqueness; per-plan GiST range exclusion. | Stable IDs across snapshots; within-plan overlap fails; historical-plan overlap passes. |
| ApprovalAction target | Exactly-one typed target CHECK, same-owner FK, BEFORE INSERT target/version/state trigger, no update/delete. | Mismatched type/id/version/state and mutation attempts fail. |
| Approval provenance | UI is derived by an explicit authenticated RPC; CHAT derives only from one-time attestation. | Forged CHAT/source message/LLM decision and reused/expired attestation tests fail. |
| User-scoped access | Unexposed `app_private`, exposed `app_api`, invoker functions, explicit grants, and owner RLS. | Direct private Data API denial, allowlisted RPC success, invoker RLS cross-user denial. |
| Scheduling consistency | One-statement `read_scheduling_context`; owner xact advisory lock; reload and revision compare before proposal persistence/approval. | Mixed-snapshot and concurrent writer tests. |
| Durable mutation/retry | Atomic idempotency with approval/rejection and attestation consumption. | Lost approval response and rejection retries replay exactly one committed result. |

The final physical design section 15 is the detailed implementation specification for grants, policies, RPC argument shapes, migration order, and test scope.

