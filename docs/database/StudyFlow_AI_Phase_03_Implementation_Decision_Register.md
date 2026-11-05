# StudyFlow AI — Phase 03 Implementation Decision Register

**Phase:** 03.1A — Implementation Decision Review & Architecture Foundation  
**Logical authority:** `docs/database/schema_F1.md`, version 1.1  
**Status:** Draft; decisions marked `PROPOSED`, `RECOMMENDED`, `USER_PREFERRED`, or `TBD` require team review.  
**Implementation state:** No database, migration, backend, or RPC implementation is authorized by this document.

## Decision status summary

| ID | Question | Status | Recommendation | Required approver |
|---|---|---|---|---|
| E-01 | Database/deployment | USER_PREFERRED / PROPOSED | Supabase PostgreSQL with isolated local, development, staging, and production projects | Team + infrastructure owner |
| E-02 | Authentication | USER_PREFERRED / PROPOSED | Supabase Auth; verified JWT becomes FastAPI trusted principal | Team security owner |
| E-03 | Backend/data access | USER_PREFERRED / PROPOSED | FastAPI + request-scoped Supabase Data API client; no direct TCP runtime access initially | Backend owner |
| E-04 | Migrations | USER_PREFERRED / PROPOSED | Supabase CLI as sole migration source | Database owner |
| E-05 | Runtime role/RLS | TBD / PROPOSED | Authenticated JWT context, least privilege, private business schema, controlled API schema | Security + database owner |
| E-06 | User mapping | PROPOSED | One profile/settings row keyed by `auth.users.id`; retain logical `User` fields | Team + database owner |
| E-07 | Same-owner FKs | PROPOSED | Composite owner/entity keys and foreign keys | Database owner |
| E-08 | Approval target | PROPOSED | Typed nullable target FKs plus exactly-one constraint; trigger or equivalent remains TBD | Database owner |
| E-09 | JSON persistence | PROPOSED | Normalize query-critical fields; use validated JSONB for nested contract objects | Backend + database owner |
| E-10 | Concurrency protocol | PROPOSED | Owner transaction lock inside one RPC; `READ COMMITTED`; reload after lock | Backend + database owner |
| E-11 | Overlap enforcement | PROPOSED | Validate inside proposal/approval RPC; constrain only within a concrete plan snapshot | Database owner |
| E-12 | SRS reconciliation | PROPOSED | Record conflicts; revise SRS separately, without changing it in Phase 03.1A | Product/team owner |
| E-13 | Index/deletion policy | PROPOSED | User/foreign-key/scheduling indexes; retain immutable history; no product TTL | Database owner |
| E-14 | Local environment | PROPOSED | Versioned Supabase CLI + Docker-compatible local stack + clean-reset CI | Infrastructure owner |

## Detailed decisions

### E-01 — Database engine and deployment

**Schema requirement:** preserve all F1 entities and relational invariants.  
**Options:** Supabase PostgreSQL; self-managed PostgreSQL; another managed PostgreSQL service.  
**Recommendation:** Supabase PostgreSQL is `USER_PREFERRED` and `PROPOSED` for team approval. Separate local, shared-development, staging, and production projects; never use production for local resets.  
**Rationale:** PostgreSQL supports composite FKs, JSONB, RLS, RPC transactions, and half-open interval/range validation. Supabase supplies an integrated Data API, Auth, local CLI workflow, and hosted environments.  
**Trade-offs:** platform coupling and Data API latency versus reduced operational work.  
**Security/testing:** verify schema exposure, grants, RLS, and clean local reset before acceptance.  
**Dependencies/consequence:** E-02–E-05 and E-14; unresolved choice blocks migrations.

### E-02 — Authentication and trusted principal

**Schema requirement:** owner identity comes from a trusted backend principal, never LLM output.  
**Recommendation:** Supabase Auth is `USER_PREFERRED` and `PROPOSED`. FastAPI verifies the access JWT, extracts `sub`, and forwards the same user JWT to the Data API.  
**Verification:** validate signature, issuer, audience, expiration, subject, key ID, and signing-key rotation. Prefer asymmetric JWKS verification; do not hardcode secrets or algorithms.  
**Security/testing:** test invalid, expired, wrong-audience, rotated-key, and cross-user tokens.  
**Dependencies:** E-05; identity provider must be approved before RLS policies are authored.

### E-03 — FastAPI and runtime data access

**Recommendation:** FastAPI is `USER_PREFERRED` and `PROPOSED`; use Supabase Data API/PostgREST and RPC over HTTPS as the initial runtime path. Do not introduce SQLAlchemy or psycopg initially.  
**Boundary:** FastAPI owns API validation, orchestration, trusted principal extraction, services, and the pure scheduler. PostgreSQL owns persistence, constraints, RLS, indexes, and atomic RPC writes.  
**Risk:** independent REST requests do not share one transaction; all multi-table writes must be one RPC call.  
**Client:** construct a request-scoped or immutable-client request with the caller JWT. Never mutate one shared client's Authorization header across concurrent requests.  
**Dependencies:** E-05 and E-10.

### E-04 — Migration system

**Recommendation:** Supabase CLI is `USER_PREFERRED` and `PROPOSED` as the sole migration source. Commit `config.toml`, ordered migrations, and safe seed data. Do not maintain Alembic or dashboard-only schema changes in parallel.  
**Testing:** clean local reset, migration replay, and CI validation.  
**Trade-off:** migration tooling is platform-specific but gives reproducible local/remote history.  
**Dependency:** E-01.

### E-05 — Runtime role, RLS, and schema exposure

**Recommendation:** `PROPOSED`: keep business tables in a private schema (for example `app_private`) and expose only controlled read/mutation RPCs in an API schema (for example `app_api`). Grant only the required routines and schema usage.  
**Default:** `SECURITY INVOKER`; RLS remains effective. Use `SECURITY DEFINER` only for a documented necessity, with fixed `search_path`, schema-qualified names, restricted EXECUTE, and explicit owner checks.  
**TBD:** exact role grants, whether FastAPI forwards JWTs through a publishable key, and whether any administrative context exists.  
**Security:** never use secret/service-role credentials for ordinary user requests; never expose them to frontend or logs.

### E-06 — Physical User mapping

**Recommendation:** `PROPOSED`: one profile/settings table keyed one-to-one by `auth.users.id`, retaining `timezone`, `locale`, `current_plan_id`, `schedule_revision`, and complete `scheduling_policy`. Do not create a duplicate authentication-user table.  
**Circular FK:** create profile and plans with a deferred/second-step `current_plan_id` FK, or equivalent safe migration ordering. Enforce `(user_id, plan_id)` same-owner identity.  
**Initialization:** create profile through a controlled service/RPC after authenticated signup; default policy is validated before use.  
**Dependency:** E-02 and E-07.

### E-07 — Same-owner composite foreign keys

**Recommendation:** `PROPOSED`: each owner-scoped table exposes a unique `(user_id, entity_id)` key; children reference parent `(user_id, id)` pairs. Apply to candidate/task, plan/previous-plan, user/current-plan, proposal/base-plan, block/plan/task, actions, and idempotency.  
**Alternative:** service checks alone are insufficient; use them only as a supplement where a physical limitation is documented.  
**Testing:** cross-user relationship attempts must fail at the database boundary.

### E-08 — ApprovalAction polymorphic target

**Recommendation:** `PROPOSED`: store the contract's `target_type`, `target_id`, and `target_version`, plus nullable typed candidate/action/proposal references. A check requires exactly one typed reference and type/ID agreement.  
**Enforcement:** use a database constraint/trigger or an equivalent RPC resolver; the exact mechanism is `TBD` until PostgreSQL implementation review. Backend rechecks owner, version, state, `requires_review`, and presented content.  
**Rejected option:** a generic `target_id` without typed integrity.

### E-09 — JSON/JSONB strategy

**Recommendation:** `PROPOSED` for PostgreSQL: normalize owner, ID, version, status, timestamps, deadline, interval, and relational fields; use validated JSONB for nested `slots`, raw expressions, field sources, proposal payload, generation scope, policies, action arguments, issues, and idempotency responses.  
**Validation:** Pydantic validates API objects; service validation enforces domain rules; PostgreSQL checks enforce scalar invariants. JSONB does not replace ownership or relational constraints.  
**Compatibility:** version nested objects and preserve immutable proposal/policy snapshots; avoid duplicate authoritative copies.

### E-10 — Owner lock and transaction protocol

**Recommendation:** `PROPOSED`: transaction-scoped owner lock acquired inside the single RPC transaction, using a key derived from the verified owner UUID. Use `READ COMMITTED`; after waiting, reload authoritative inputs.  
**Writers:** task confirmation, TimeWindow/policy writes, proposal persistence, rejection, approval, and current-plan/revision changes.  
**External work:** LLM, PDF, and network calls occur outside scheduling transactions. Proposal generation uses read snapshot → pure engine → persistence RPC with revision compare.  
**Guarantee:** advisory locks do not stop bypass writers; permissions, private schemas, centralized RPCs, and concurrency tests are required.  
**Dependency:** E-05; final lock mechanism requires team approval.

### E-11 — Overlap enforcement

**Recommendation:** `PROPOSED`: validate `[start_at,end_at)` conflicts in proposal-generation and approval RPCs under owner serialization. Historical snapshots may overlap each other because they are different plans.  
**Physical constraint:** an exclusion/GiST constraint may be considered for blocks within one concrete committed plan snapshot only; it must not inspect parent plan status or reject overlaps across historical plans.  
**Testing:** adjacent intervals pass; intersecting intervals fail; concurrent approvals cannot both commit conflicting current snapshots.

### E-12 — SRS reconciliation

The SRS remains unchanged. Required formal revisions include `course_id` versus `course_label`, PDF/OCR scope, unified TimeWindow, current-plan pointer, immutable snapshots, removal of product TTL/EXPIRED states, manual block operations, task update/cancel APIs, and StudySession/progress tracking.

### E-13 — Index and deletion policy

**Recommendation:** `PROPOSED`: index owner/FK columns, task `(user_id,status,deadline_at)`, TimeWindow `(user_id,kind)`, proposals `(user_id,status,generated_at)`, blocks `(plan_id,start_at)` and `(task_id,plan_id)`, awaiting PendingActions, and idempotency unique keys.  
**Retention:** preserve candidate/task/proposal/action/audit history; never add product TTLs. Retain immutable StudyPlans/StudyBlocks. Only IdempotencyRecord uses operational `expires_at`; cleanup must not affect business records.  
**Deletion:** archive/cancel where contract allows; do not cascade-delete confirmed tasks or historical plans.

### E-14 — Local database and test environment

**Recommendation:** `PROPOSED`: version the Supabase CLI, Docker-compatible local stack, `supabase/config.toml`, ordered migrations, and non-production `seed.sql`. CI runs clean reset, migrations, RLS, RPC, ownership, idempotency, and concurrency tests.  
**Safety:** no production linking or data in seeds; secrets remain in ignored environment configuration.  
**Dependency:** E-01 and E-04.

## Entry criteria for Stage 03.2

Stage 03.2 may begin only after team approval of E-01 through E-05, E-07 through E-11, and E-14, plus formal SRS reconciliation for E-12. E-06 and E-08 require a concrete physical design review. Until then, no migrations, SQL, RPC functions, or backend scaffold should be created.

## Phase 03.1A revision amendments

These amendments address reviewer feedback. The register remains the single source of truth for status, owners, approval state, and unresolved questions; ADRs reference these IDs and provide rationale only.

### E-03 amendment — direct RPC boundary and latency evaluation

`PROPOSED`: FastAPI is the normal gateway, but it is not automatically a security boundary when authenticated users have EXECUTE on mutation RPCs. The team must choose between user-authorized RPCs (each RPC independently enforces all security and business rules) and backend-only mutation RPCs (separate trusted backend identity, not an undocumented service-role shortcut). Initial performance targets are `PROPOSED`, not SLOs: same-region p95 ≤300 ms for ordinary reads and ≤1000 ms for atomic mutation RPCs, excluding LLM and Scheduling Engine time. Benchmark with a representative F1 dataset, expected concurrency, warm-up, and at least 30 measured runs per operation.

### E-05 amendment — privileges and exposed schemas

`PROPOSED`: use physical names `app_private` for business tables/internal objects and `app_api` for explicitly exposed functions/read endpoints. Schema USAGE, table privileges, function EXECUTE, and RLS are separate controls. `SECURITY INVOKER` is preferred; any `SECURITY DEFINER` exception requires a least-privilege owner, fixed safe search path, schema-qualified references, restricted EXECUTE, explicit owner checks, and documented RLS behavior. Exact grants remain `TBD`.

**Unresolved approval-provenance decision:** Option A direct RPC may record only an explicit authenticated UI decision after target, version, state/context, and server-derived presentation binding checks. Client-provided CHAT source/message fields and LLM booleans are not trusted. CHAT-origin approval remains disabled unless the security and database owners approve a separately authenticated backend-attestation format and verifier that binds verified user, conversation/message, exact target/version, decision, expiry, and anti-replay value. No separate privileged backend role is approved at present.

### E-10 amendment — consistent proposal input snapshot

`PROPOSED`: a multi-statement `READ COMMITTED` transaction alone is not a consistent SchedulingContext snapshot. Use one read RPC/SQL snapshot, or explicitly use `REPEATABLE READ`. The engine must receive inputs and `schedule_revision` from the same snapshot. The persistence RPC reacquires the owner lock, reloads authoritative conditions, compares the revision, and rejects mismatches for regeneration. The race test is mandatory.

### E-11 amendment — snapshot-scoped overlap

`PROPOSED`: evaluate a GiST exclusion constraint over a half-open timestamp range keyed by `plan_id`; `btree_gist` may be required for UUID equality. Historical plans may overlap each other. Availability, BUSY, deadline, workload, and current-context validation remain RPC/service checks. Responsible owner: Database Architect; technical reviewer: Backend Architect; decision deadline: before Stage 03.2 physical design approval.

### E-07 amendment — StudyBlock uniqueness exception

The approved StudyBlock primary key is `(plan_id, block_id)`. A logical `block_id` may legitimately recur in multiple historical snapshots. Therefore a global `UNIQUE(user_id, block_id)` is prohibited. Same-owner composite foreign keys to StudyPlan and AcademicTask remain required, and logical identity continuity is preserved through the repeated `block_id`.

### E-12 dedicated SRS reconciliation issue

**Issue:** reconcile the SRS with schema v1.1 for course representation, PDF/OCR, unified TimeWindow, current-plan snapshots, TTL/EXPIRED states, manual/individual block operations, task update/cancel APIs, and StudySession/progress.
**Status:** `PROPOSED — open`.
**Accountable role:** Product/Requirements Owner.
**Technical reviewer:** Backend/Database Architect.
**Deliverables:** conflict matrix, proposed wording changes, traceability update, and team acceptance record; do not edit the SRS silently.
**Milestone:** complete before Stage 03.2 physical design approval.
**Dependencies:** E-01 through E-11 and product scope confirmation.

### E-15 — Phase 03.1A review checklist

| Review item | Status |
|---|---|
| Official schema remains unchanged | VERIFIED |
| Baseline remains unchanged | VERIFIED |
| Five ADRs reference this register for status | VERIFIED |
| ADR created/updated dates reflect Git history | VERIFIED |
| Owner-lock protocol explicitly remains PROPOSED | VERIFIED |
| Direct RPC Option A/Option B analyzed | VERIFIED |
| SECURITY INVOKER privileges separated from RLS/schema exposure | VERIFIED |
| Consistent SchedulingContext snapshot requirement added | VERIFIED |
| Rejection idempotency added | VERIFIED |
| Approval lost-response retry ordering added | VERIFIED |
| Global StudyBlock `(user_id, block_id)` uniqueness rejected | VERIFIED |
| Snapshot-scoped overlap strategy and owner/deadline recorded | VERIFIED |
| F1 deferred RPC operations explicitly excluded | VERIFIED |
| Data API latency measurement plan added | VERIFIED |
| SRS reconciliation owner and milestone recorded | VERIFIED |
| Team approval gates complete | NOT COMPLETE — ADRs remain PROPOSED |
| Stage 03.2 authorized | NOT AUTHORIZED |
