# ADR-005 — Concurrency and Transaction Strategy

**Status: ACCEPTED — Unified Integration Contract 1.0.0, IC-06/IC-07**
**Created:** 2026-11-04
**Last updated:** 2026-11-05

Accepted effective 05/11/2026 through the [official contract, section 7](../../../contracts/README.md#7-transaction-và-idempotency) and [approval record](../../../contracts/APPROVAL.md), with scope tracked in the [decision register](../../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md). The owner row lock below supersedes the earlier advisory-key proposal; E-12/SRS work remains separate.

## Decision (E-10, E-11)

Use `SELECT ... FOR UPDATE` on the verified owner's `app_private.user_profiles` row inside the single mutation RPC transaction. Acquire it before authoritative reads, use `READ COMMITTED`, reload after waiting and capture authoritative time after lock acquisition. Profile initialization uses controlled insert-on-conflict before the lock when needed. All writers follow the same owner-first lock order; do not derive separate advisory-lock keys.

All task confirmation, TimeWindow/policy writes, proposal persistence, rejection, approval, and current-plan/revision changes must use the same protocol. LLM, PDF, and network calls occur outside the scheduling transaction.

## Consistent SchedulingContext snapshot (R-06)

A multi-statement `READ COMMITTED` read transaction alone is not sufficient: each statement may observe a different committed state. The recommended design is a single read RPC that returns tasks, TimeWindows, current plan, retained blocks, effective policy, and `schedule_revision` from one SQL statement/snapshot. If the implementation requires multiple statements, use an explicitly consistent `REPEATABLE READ` transaction and document its lifecycle and resource cost.

The engine must receive all inputs and the revision from that same snapshot. After computation, the persistence RPC reacquires the owner lock, reloads authoritative conditions as needed, and compares the expected revision. A mismatch rejects persistence and requires regeneration. Test the race where a TimeWindow changes after the read snapshot but before persistence; no proposal based on mixed state may be stored.

Mutation ordering is JWT/attestation verification → fast idempotency lookup → owner row lock → idempotency lookup again → authoritative state/version reads → validation → atomic write/result. A completed matching request returns the original result before terminal/stale checks; a different fingerprint returns `IDEMPOTENCY_CONFLICT`. Approval atomically creates StudyPlan/all StudyBlocks, updates current_plan_id/revision, proposal state/backlink, ApprovalAction, action completion and idempotency. A technical failure rolls back all writes. A terminal stale rejection may instead commit the STALE state and typed error receipt without creating a plan, as specified in the contract.

Generation fingerprints use the original generation_scope/policy_overrides, not newly generated IDs/timestamps. The service checks lookup_operation_result before engine execution; persist_plan_proposal checks again after the lock. Domain idempotency/API receipts retain retry results for at least seven days. API receipt leases last 120 seconds, renew at most every 30 seconds and use lease_version fencing; recovery reuses stable message/action IDs and domain keys. These operational leases do not expire business actions/proposals.

## Overlap policy

Validate half-open intervals `[start_at,end_at)` in proposal and approval RPCs. Historical plans may overlap one another. The accepted database enforcement is a GiST exclusion constraint over a timestamp range keyed by plan_id, with btree_gist for UUID equality as required by the selected PostgreSQL setup. Non-overlap applies within one snapshot only; do not inspect parent plan status or reject overlaps across snapshots. Availability, BUSY, deadline, workload and current-context checks remain separate service/RPC validation.

## Consequences and tests

Row locking requires every writer to participate, so attestation, least-privilege grants, private schemas and centralized RPCs must prevent bypass writers. Test direct RPC authorization, double approval, lost-response retry, rejection replay, stale revisions, mixed-snapshot races, concurrent writes, rollback, lease fencing and block identity continuity across historical snapshots. The design is accepted; these runtime cases remain unrun until implementation evidence is recorded.

