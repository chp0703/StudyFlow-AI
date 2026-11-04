# ADR-005 — Concurrency and Transaction Strategy

**Status: PROPOSED — Pending team approval**  
**Created:** 2026-11-04
**Last updated:** 2026-11-05

Decision status and approvers remain authoritative in the [decision register](../../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md), especially E-10, E-11, E-12, and E-13. **The lock protocol below is PROPOSED — Pending team approval**, not finalized.

## Recommendation (E-10, E-11)

Use a transaction-scoped owner-level lock within the RPC that performs a scheduling-affecting write. Derive the key from the verified owner UUID, acquire it before authoritative reads, use `READ COMMITTED`, and reload after waiting. Capture authoritative time after lock acquisition.

All task confirmation, TimeWindow/policy writes, proposal persistence, rejection, approval, and current-plan/revision changes must use the same protocol. LLM, PDF, and network calls occur outside the scheduling transaction.

## Consistent SchedulingContext snapshot (R-06)

A multi-statement `READ COMMITTED` read transaction alone is not sufficient: each statement may observe a different committed state. The recommended design is a single read RPC that returns tasks, TimeWindows, current plan, retained blocks, effective policy, and `schedule_revision` from one SQL statement/snapshot. If the implementation requires multiple statements, use an explicitly consistent `REPEATABLE READ` transaction and document its lifecycle and resource cost.

The engine must receive all inputs and the revision from that same snapshot. After computation, the persistence RPC reacquires the owner lock, reloads authoritative conditions as needed, and compares the expected revision. A mismatch rejects persistence and requires regeneration. Test the race where a TimeWindow changes after the read snapshot but before persistence; no proposal based on mixed state may be stored.

Approval first resolves the owner and performs idempotency lookup. A completed matching request returns its original committed result immediately; a different fingerprint returns `IDEMPOTENCY_CONFLICT`. Only when no completed record exists does approval check proposal state, acquire the owner lock, revalidate, and commit. It atomically creates the immutable StudyPlan and all StudyBlocks, updates `current_plan_id`, increments `schedule_revision`, changes proposal state, and completes idempotency. Failure rolls back all writes. This ordering supports safe retry after a successful commit whose response was lost.

## Overlap policy

Validate half-open intervals `[start_at,end_at)` in proposal and approval RPCs. Historical plans may overlap one another. The recommended database enforcement is a GiST exclusion constraint over a timestamp range keyed by `plan_id`, so non-overlap applies within one snapshot only. `btree_gist` may be required to index the UUID/equality key; the extension dependency is `PROPOSED`. The constraint must not inspect parent plan status. Availability, BUSY, deadline, workload, and current scheduling-context checks remain service/RPC validation, not a substitute for snapshot-level non-overlap. Final enforcement remains `PROPOSED` under E-11.

## Consequences and tests

Advisory locks do not stop bypass writers, so grants, private schemas, centralized RPCs, and bypass/concurrency tests are required. Test direct RPC authorization, double approval, lost-response retry, rejection replay, stale revisions, mixed-snapshot races, concurrent scheduling-input writes, rollback, same logical block IDs across snapshots, and retained historical snapshots. See register E-10 through E-13.

