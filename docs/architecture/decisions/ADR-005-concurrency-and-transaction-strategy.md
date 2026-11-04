# ADR-005 — Concurrency and Transaction Strategy

**Status: PROPOSED — Pending team approval**  
**Date:** 2026-11-04

## Decision

Use a transaction-scoped owner-level lock within the RPC that performs a scheduling-affecting write. Derive the key from the verified owner UUID, acquire it before authoritative reads, use `READ COMMITTED`, and reload after waiting. Capture authoritative time after lock acquisition.

All task confirmation, TimeWindow/policy writes, proposal persistence, rejection, approval, and current-plan/revision changes must use the same protocol. LLM, PDF, and network calls occur outside the scheduling transaction. Proposal generation uses a read snapshot and revision, runs the pure engine, then persists through a single RPC that compares the revision again.

Approval atomically revalidates the proposal, creates the immutable StudyPlan and all StudyBlocks, updates `current_plan_id`, increments `schedule_revision`, changes proposal state, and completes idempotency. Failure rolls back all writes.

## Overlap policy

Validate half-open intervals `[start_at,end_at)` in proposal and approval RPCs. Historical plans may overlap one another. Any exclusion/GiST constraint must be scoped to one concrete plan snapshot and must not inspect parent plan status. The exact physical constraint is `TBD`.

## Consequences and tests

Advisory locks do not stop bypass writers, so grants, private schemas, centralized RPCs, and bypass/concurrency tests are required. Test double approval, stale revisions, concurrent scheduling-input writes, rollback, and retained historical snapshots.

