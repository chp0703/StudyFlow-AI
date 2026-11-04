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
| `target_candidate_id`, `target_pending_action_id`, `target_proposal_id` | Enforces one exact ApprovalAction target despite polymorphic `target_type/target_id` | E-08 `PROPOSED`; trigger/equivalent `TBD` |
| Supporting `(user_id,id)` unique keys | Enables database-enforced same-owner composite FKs | E-07 `PROPOSED` |
| B-tree/partial/GiST indexes | Query and snapshot integrity performance | E-11/E-13 `PROPOSED` |

## 3. Constraint traceability

| Constraint | Physical design | Schema rule | Status |
|---|---|---|---|
| Candidate promotion | Unique task `candidate_id`; candidate confirmation link matches task | One candidate creates at most one task | `CONFIRMED_FROM_SCHEMA` + physical design `PROPOSED` |
| Task workload | `estimated_minutes > 0`; `0 <= remaining <= estimated`; status implications | AcademicTask invariants | `CONFIRMED_FROM_SCHEMA` |
| Deadline precision | DATE requires date; DATETIME retains instant | Date-only semantics preserved | `CONFIRMED_FROM_SCHEMA` |
| TimeWindow union | NONE/WEEKLY mutually exclusive field checks | Unified TimeWindow | `CONFIRMED_FROM_SCHEMA` |
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

The proposed `app_private`/`app_api` split is physical only. Option A from ADR-002 permits authenticated direct calls to explicitly granted mutation RPCs; therefore FastAPI is not the sole security boundary. Every RPC must independently enforce verified identity, owner, target, version, approval evidence, idempotency, and domain invariants. `SECURITY INVOKER` is preferred. Exact grants, RLS policy text, and any SECURITY DEFINER exception remain Stage 03.3 implementation decisions.

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
- [x] Task, proposal, snapshot, overlap, and deletion rules documented.
- [x] Index and migration dependency plans documented.
- [x] RPC signatures and F1 exclusions documented.
- [x] RLS/grant/schema exposure design documented.
- [x] Physical-only choices identified and labeled.
- [ ] Team approval of remaining physical choices.
- [ ] Stage 03.3 implementation authorization.

