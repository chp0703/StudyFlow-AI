# StudyFlow AI — Backend Contract Integration

**Stage:** 03.3 Commit 01 — Contract integration  
**Source branch:** `origin/feat/BE_contract_schema`  
**Exact source commit:** `b629a5e251be59570a0f719b5596d7d457e2708d`  
**Contract package:** 1.0.0, `REVIEW_READY`, logical `schema_version: "1.1"`  
**Status:** Integrated as a read-only contract package; runtime implementation is not yet claimed.

## 1. Authority and integration boundary

The source-of-truth order is:

1. `docs/database/schema_F1.md` v1.1 — logical business semantics.
2. Stage 03.2 physical design — PostgreSQL mapping and integrity design.
3. ADR-001 through ADR-005 and the decision register — approved architecture and transaction/security boundaries.
4. The Backend Contract package — API, DTO, serialization, validation, and operation mapping.
5. Existing code — evidence of implementation only.

The branch was inspected before integration. Only the `contracts/` package was integrated. The branch’s root `schema_F1.md`, `.vscode/settings.json`, README changes, `.gitignore` changes, and architecture-document edits were not imported because they are duplicates or unrelated to the database milestone. No secrets or environment files were present in the integrated package.

## 2. Discovered contract artifacts

| Artifact | Purpose | Integrated |
|---|---|---|
| `contracts/README.md` | Trust boundary, transport, service, persistence, RPC, and review rules | YES |
| `contracts/schemas/f1.schema.json` | JSON Schema 2020-12 DTO/entity definitions and enums | YES |
| `contracts/openapi.yaml` | OpenAPI 3.1.1 HTTP paths, headers, responses, references | YES |
| `contracts/service-contract.json` | Ten operation registry, arguments/results, RPC mapping, approval/idempotency flags | YES |
| `contracts/data-contract.json` | Entity/table/column/type/nullability/PK mapping | YES |
| `contracts/examples/valid/*` | Positive contract fixtures | YES |
| `contracts/examples/invalid/*` | Negative validation/security fixtures | YES |
| `contracts/examples/manifest.json` | Fixture catalog and expected validation | YES |
| `contracts/check_contract.py` | Static contract checker | YES |
| `contracts/requirements-check.txt` | Checker-only dependencies | YES |
| `contracts/VALIDATION.md` | Backend team static validation evidence and limits | YES |
| `contracts/acceptance-cases.md` | Runtime acceptance cases, currently NOT_RUN | YES |
| `contracts/CHANGELOG.md` | Contract package history | YES |
| `contracts/.gitignore` | Contract-package ignore rules | YES |

No Python Pydantic implementation, API handler, ORM model, migration, or database runtime implementation was supplied by the branch.

## 3. Contract package summary

- API uses `Authorization: Bearer <Supabase access JWT>`; FastAPI verifies the token and derives owner identity from verified claims.
- POST requests require an idempotency key; GET requests are read-only.
- Public HTTP paths are `/v1/messages`, `/v1/actions`, `/v1/actions/{action_id}/review`, `/v1/decisions`, `/v1/tasks`, `/v1/time-windows`, `/v1/preferences`, and `/v1/plans`.
- The contract exposes ten F1 operations: `create_task_candidate`, `confirm_task`, `search_tasks`, `set_availability`, `set_busy_interval`, `set_scheduling_preferences`, `generate_study_plan`, `get_study_plan`, `approve_study_plan`, and `reject_study_plan`.
- `ActionPresentation` is a presentation DTO, not an eleventh logical entity.
- F1 excludes task update/cancel APIs, manual StudyBlock creation, and individual StudyBlock rescheduling.
- CHAT approval must use a trusted, one-time backend attestation; client-provided approval booleans and provenance do not authorize mutation.

## 4. Entity and field mapping

The contract package maps the ten entities to the Stage 03.2 physical tables in `app_private`. Relational identity, owner, status, version, timestamp, and workload fields remain typed columns. Nested contract objects remain validated JSONB.

| Contract entity | Physical table | Key mapping | Nested JSONB |
|---|---|---|---|
| User | `app_private.user_profiles` | `user_id`, `current_plan_id`, `schedule_revision` | `scheduling_policy` |
| TaskCandidate | `app_private.task_candidates` | candidate/version/status/owner | `slots`, `raw_expressions`, `field_sources` |
| AcademicTask | `app_private.academic_tasks` | task/candidate/owner/version/status/workload/deadline | none |
| TimeWindow | `app_private.time_windows` | window/owner/version/kind/recurrence | none |
| StudyPlan | `app_private.study_plans` | plan/owner/version/previous/source proposal | none |
| StudyBlock | `app_private.study_blocks` | `(plan_id,block_id)`, owner/task | none |
| PlanProposal | `app_private.plan_proposals` | proposal/owner/status/base/commit | `generation_scope`, `payload`, `policy_snapshot` |
| PendingAction | `app_private.pending_actions` | action/owner/conversation/version/state | `draft_arguments`, `missing_fields`, `ambiguities` |
| ApprovalAction | `app_private.approval_actions` | approval/owner/typed target/version | none |
| IdempotencyRecord | `app_private.idempotency_records` | owner/operation/key/fingerprint/state | `result_reference_or_response` |

Derived fields such as `ActionPresentation`, page cursors, HTTP headers, `request_id`, `Retry-After`, `Idempotency-Replayed`, and filtered calendar views are not database columns. They are transport/service values.

## 5. Type, enum, and validation mapping

| Contract value | Database mapping | Validation responsibility |
|---|---|---|
| UUID entity IDs | PostgreSQL `uuid` | Backend generates; DB keys/ownership enforce relationships |
| API timestamps | `timestamptz` | Backend RFC3339/offset validation; DB stores instant |
| Local recurrence time | `time(0) without time zone` | Backend validates IANA/DST; DB checks shape; `24:00` is end-only |
| Version/revision/minutes | PostgreSQL integer-compatible type (`bigint` where contract mapping uses it) | Backend range validation plus DB non-negative checks |
| TaskCandidate status | CHECK `DRAFT`, `CONFIRMED`, `CANCELLED` | Both schema validator and DB CHECK |
| AcademicTask status | CHECK `TODO`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED` | Both; workload/status consistency in DB/RPC |
| PlanProposal status | CHECK `PROPOSED`, `APPROVED`, `REJECTED`, `STALE` | Both; committed-plan consistency in RPC |
| TimeWindow kind/recurrence | CHECK enums | Both; union-field checks in DB |
| Approval decision/source/target type | CHECK enums | Both; target integrity in DB/RPC |
| Idempotency state | CHECK `IN_PROGRESS`, `COMPLETED` | DB uniqueness and RPC replay logic |
| `coverage` | JSONB payload enum `FULL`, `PARTIAL`, `NONE`, `NO_CHANGE` | Schema/service; NONE/hard conflict not committable |

## 6. Identified conflict requiring contract correction

The Backend Contract `contracts/data-contract.json` declares `PlanProposal.version` as PostgreSQL `text`, while:

- `docs/database/schema_F1.md` defines proposal `version: integer >= 1` and uses version matching for approval.
- Stage 03.2 physical design defines the proposal version as integer-compatible.
- `contracts/schemas/f1.schema.json` currently constrains the proposal version to JSON constant `1`, not a general string.

This is an actual contract/physical mapping inconsistency. The database implementation follows schema v1.1: proposal version is an integer-compatible typed column, not text. The contract package must be corrected or explicitly amended before planning/approval persistence is accepted. No migration will silently create a text version column.

The package also uses `bigint` for several integer fields where the logical schema says integer. This is compatible as a physical widening when non-negative/range semantics remain unchanged; the API must continue serializing safe JSON integers.

## 7. Operation-to-RPC mapping

| API/service operation | RPC mapping | Authorization | Transaction/idempotency |
|---|---|---|---|
| `create_task_candidate` | `app_api.create_task_candidate` | `auth.uid()` owner | Atomic draft + idempotency; no approval target |
| `confirm_task` | `app_api.confirm_task` | TASK_CANDIDATE exact version | Owner lock; task promotion, approval, revision and idempotency atomically |
| `search_tasks` | `app_api.search_tasks` | User-scoped read | Read-only |
| `set_availability` | `app_api.set_availability` | PENDING_ACTION exact version | Owner lock; TimeWindow/version/revision/idempotency |
| `set_busy_interval` | `app_api.set_busy_interval` | PENDING_ACTION exact version | Same as availability; kind forced BUSY |
| `set_scheduling_preferences` | `app_api.set_scheduling_preferences` | PENDING_ACTION exact version | Owner lock; expected revision and idempotency |
| `generate_study_plan` | application engine + `app_api.persist_plan_proposal` | Trusted service input; user owner | One consistent context snapshot; revision compare; idempotent persistence |
| `get_study_plan` | `app_api.get_study_plan` | User-scoped read | Read-only |
| `approve_study_plan` | `app_api.approve_study_plan` | PLAN_PROPOSAL exact version | Idempotency first; owner lock; atomic plan/blocks/pointer/revision |
| `reject_study_plan` | `app_api.reject_study_plan` | PLAN_PROPOSAL exact version | Idempotency first; atomic REJECTED result; no schedule revision |

The HTTP adapter does not expose raw arbitrary RPC execution. Internal helpers such as `get_scheduling_context`, receipt handling, attestation issuance, and proposal persistence are not additional public F1 operations.

## 8. Error and validation mapping

HTTP validation remains at FastAPI/contract schema boundaries. Domain validation is shared between the backend service and PostgreSQL constraints/RPCs. Database errors are mapped to stable contract errors rather than returned as SQL text.

| Layer | Examples |
|---|---|
| Transport | `UNAUTHENTICATED`, `PAYLOAD_TOO_LARGE`, `RATE_LIMITED`, `SERVICE_UNAVAILABLE` |
| Contract shape | `INVALID_PARAMETER`, `MISSING_REQUIRED_FIELD`, `UNSUPPORTED_OPERATION` |
| Ownership/reference | `FORBIDDEN`, `ENTITY_NOT_FOUND`, `AMBIGUOUS_REFERENCE` |
| Version/concurrency | `STALE_ENTITY_VERSION`, `STALE_PLAN_VERSION`, `STALE_PROPOSAL`, `TIME_CONFLICT` |
| Approval/review | `APPROVAL_REQUIRED`, `ACTION_REVIEW_REQUIRED`, `ACTIVE_BLOCK_REQUIRES_REVIEW` |
| Retry | `IDEMPOTENCY_CONFLICT`; matching completed requests replay the stored result |

PostgreSQL must reject invalid scalar/status/relationship values even if a caller bypasses FastAPI and invokes an allowed RPC directly. RPCs must independently verify owner, target, version, approval evidence, attestation, and idempotency.

## 9. Integrated artifacts

The following exact artifacts from commit `b629a5e251be59570a0f719b5596d7d457e2708d` are integrated under `contracts/`: README, JSON Schema, OpenAPI, service/data contracts, checker, validation metadata, acceptance cases, changelog, requirements, manifest, and valid/invalid fixtures. No backend implementation files, secrets, environment files, or unrelated branch changes were imported.

## 10. Compatibility status before migrations

- Contract package static validation is supplied as `PASS` for schema/OpenAPI/fixtures, with runtime DB/auth/RLS explicitly `NOT_RUN`.
- Contract-to-logical mapping is compatible for the ten entities except the PlanProposal version representation described in Section 6.
- Core entities may proceed only using schema v1.1 types and the compatibility rules above.
- Planning/approval persistence is blocked until the PlanProposal version conflict is corrected or explicitly approved as an adapter-only representation without changing the physical integer column.

