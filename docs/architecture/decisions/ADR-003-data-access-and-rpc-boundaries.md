# ADR-003 — Data Access and RPC Boundaries

**Status: PROPOSED — Pending team approval**  
**Created:** 2026-11-04
**Last updated:** 2026-11-05

Decision status and approvers remain authoritative in the [decision register](../../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md), especially E-03, E-04, E-05, E-10, E-12, and E-14. This ADR records data-access rationale and constraints.

## Recommendation (E-03, E-05, E-10)

FastAPI uses a request-scoped Supabase Data API client or equivalent immutable HTTPX wrapper. No shared mutable client may overwrite Authorization headers between concurrent requests. Ordinary reads may use controlled PostgREST access. Any multi-table business write uses one PostgreSQL RPC call.

Initial RPC inventory:

| Function | Lock | Revision/idempotency |
|---|---:|---|
| `create_task_candidate` | owner lock if write protocol requires | idempotency; revision as applicable |
| `confirm_task` | yes | approval + idempotency + revision |
| `search_tasks` | no | read-only |
| `set_availability` / `set_busy_interval` | yes | approval + idempotency + revision |
| `set_scheduling_preferences` | yes | approval + idempotency + revision |
| `generate_study_plan` persistence step | yes | idempotency; revision compare |
| `get_study_plan` | no | read-only |
| `approve_study_plan` | yes | approval + idempotency + revision |
| `reject_study_plan` | yes | approval/version validation + idempotency |

RPC functions must not manually commit or roll back inside normal PostgREST execution. The request transaction provides atomicity. The pure scheduler runs outside PostgreSQL and returns data to a persistence RPC.

## Direct invocation and F1 scope

If Option A in ADR-002 is approved, a user JWT may call an exposed mutation RPC directly. FastAPI validation is not sufficient: every RPC independently enforces ownership, versions, states, approval evidence, payload validation, and idempotency. If Option B is later approved, ordinary frontend roles must lose mutation EXECUTE and a separately approved backend identity must be designed. Neither option is currently approved.

The following are explicitly `DEFERRED / UNSUPPORTED IN F1 v1.1` and must not be added to the RPC inventory: task update API, task cancellation API, manual StudyBlock creation, and individual StudyBlock rescheduling.

## Rejection idempotency (R-07)

`reject_study_plan` must look up idempotency first, reject a different fingerprint with `IDEMPOTENCY_CONFLICT`, and atomically persist the REJECTED result plus a completed IdempotencyRecord. A same-key/same-fingerprint retry returns the original result without rewriting the proposal.

## Approval retry ordering (R-08)

`approve_study_plan` resolves the owner and checks idempotency before interpreting proposal state. A completed matching key returns the original committed plan immediately; only a new key proceeds to proposal/version/stale checks and locking. This prevents a lost response followed by a retry from being misreported as an already-approved conflict or creating duplicate snapshots.

## Data API latency evaluation (R-13)

The following are `PROPOSED` evaluation targets, not SLOs: same-region p95 ≤300 ms for ordinary reads and p95 ≤1000 ms for atomic mutation RPCs, excluding LLM and Scheduling Engine computation. Benchmark with a representative F1 dataset, expected concurrency, a warm-up phase, and at least 30 measured runs per operation. Report p50/p95/p99, errors, retries, and payload sizes. Optimize query shape, indexes, RPC batching, pagination, and client reuse (without sharing mutable auth headers) before considering a different access mode. Direct PostgreSQL access is not justified without benchmark evidence.

## Consequences

HTTP latency and pagination must be measured. Independent API calls cannot be treated as one transaction. RPC contracts, grants, direct-RPC authorization, rejection replay, approval replay, and error mapping require integration tests before implementation approval. See register E-03, E-05, E-10, E-12, E-13, and E-14.

## Stage 03.2 implementation baseline

**IMPLEMENTATION_BASELINE — selected for F1 implementation; not a claim of separate team approval.** The public database boundary is `app_api`, while `app_private` tables and helpers are unexposed. All user mutations use SECURITY INVOKER and derive owner from `auth.uid()`; no RPC accepts client `user_id` as authority. The final inventory is: `create_task_candidate`, `confirm_task`, `search_tasks`, `set_availability`, `set_busy_interval`, `set_scheduling_preferences`, `read_scheduling_context`, `persist_plan_proposal`, `get_study_plan`, `approve_study_plan`, and `reject_study_plan`. `generate_study_plan` is an application operation: read one consistent context, run the pure Python engine, then call revision-checked proposal persistence.

All response envelopes carry `schema_version = "1.1"`; errors use the stable codes documented in the physical design. Helper functions for locks, idempotency, typed target validation, and attestation consumption are private and receive no frontend execute grant. `issue_chat_approval_attestation` is the sole server-only entry point and is executable only by `service_role` from an isolated backend client. Unsupported task update/cancel, manual block creation, individual block rescheduling, and StudySession operations return `UNSUPPORTED_OPERATION` at the application boundary.

