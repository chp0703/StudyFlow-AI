# WP2c — planning (progress notes)

| Stage | Scope | Status |
|---|---|---|
| 2c-1 | `get_scheduling_context`, `get_study_plan` (reads) | done (migration 018, test 14) |
| 2c-2 | `persist_plan_proposal` (+ generation idempotency, scope/policy cross-check) | done (migration 019, test 15) |
| 2c-3 | `approve_study_plan`, `reject_study_plan`, STALE durability, window-change warnings | planned |

## 2c-1 decisions

- `get_scheduling_context` returns the whole owner snapshot (all tasks, active windows, unfiltered base plan,
  `schedule_revision`); the engine applies the generation scope. It needs an initialized profile (reads cannot
  create one) and rejects inverted windows and selected tasks that are missing or belong to someone else.
- `get_study_plan`: CURRENT with no plan is `PlanView(plan=null, [])`; a time window filters only the blocks
  (overlap rule), never the plan metadata; PROPOSAL always returns the full payload and rejects a window.
- Known limit: one SQL statement is not used for the snapshot; the routine runs several statements under READ
  COMMITTED. A concurrent writer is excluded only for writers that take the owner lock. If strict snapshot
  consistency is required, switch to REPEATABLE READ at the HTTP layer (WP3) or lock the owner row here.

## 2c-2 decisions

- Idempotency uses the `generate_study_plan` namespace and a fingerprint of the original command only, so a retry
  with new engine IDs or clocks replays the stored proposal. A new key cannot reuse a stored `proposal_id`.
- The database does not trust the proposal's self-description: scope must equal the command scope, the policy
  snapshot must equal default + stored policy + command overrides, and base revision / base plan must equal the
  owner's current ones (else `STALE_PROPOSAL`). Persisting never changes `schedule_revision`.
- Block checks: owner, non-empty, inside the generation window, unique IDs, no overlap (`TIME_CONFLICT`), task
  belongs to the owner and to the selection.
- **Not checked here (engine's job):** that blocks respect availability/busy windows, deadlines and policy block
  sizes. Approval (2c-3) is where a plan becomes real, so it should re-validate against current windows.
- Older PROPOSED proposals are not superseded on persist; approval's revision check makes them stale.
