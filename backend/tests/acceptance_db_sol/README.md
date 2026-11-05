# Independent next-stage F1 database acceptance

Status: **PLAN / NOT_RUN**, 2026-11-05. This is a test handoff, not evidence of a
running database. Local Docker, PostgreSQL/psql and Supabase CLI are unavailable.
Run against a disposable local Supabase stack in GitHub CI after migration replay;
cloud credentials and production migrations are not prerequisites for these tests.

Sources: [approved contract](../../../contracts/README.md),
[RPC registry](../../../contracts/service-contract.json),
[persistence mapping](../../../contracts/data-contract.json),
[acceptance cases](../../../contracts/acceptance-cases.md), and
[WP2](../../../docs/implementation/WP2_DATABASE.md).

## Existing evidence and boundaries

`supabase/tests/03_*.sql` through `06_*.sql` cover table/key/type constraints,
private grants, the 21 approved wrapper signatures/owners, canonical/HMAC golden
vectors, attestation tampering, signed candidate replay/conflict and candidate
rollback. Their SQL was parsed independently; this does not execute PL/pgSQL,
RLS, JSON Schema validation or transactions. None currently has a real DB pass.

Test 06 does **not** prove task confirmation, complete plan approval, concurrent
serialization, durable STALE, protected snapshots or receipt recovery. Its
cross-owner envelope test also does not prove same-owner envelopes cannot refer
to someone else's target/message/conversation. Add those checks below.

Use only approved `app_api.<routine>(p_request jsonb)` calls for product actions.
Do not invent fetch helpers or call private domain writers. The only agreed
private test seams remain `canonical_json(jsonb)` and
`verify_rpc_request(jsonb,text)`. Administrative SQL may create users, provision
synthetic signing keys, inspect mapped tables, hold a documented owner row lock,
and inject a rollback fault in the disposable test database. Administrative
inspection is an oracle, never the application read path.

## Harness and deterministic fixtures

- Use real PostgreSQL connections: an administrative observer plus two independent
  request connections with authenticated role/JWT claims. Never share a connection,
  mutable JWT context or transaction between worker threads. Add actual PostgREST
  JWT smoke checks separately; setting session claims does not verify a JWT.
- Validate every request/result against the approved schemas. Sign the complete
  normalized envelope independently in Python using the existing golden bytes;
  refresh the 60-second transport token immediately before each call. Keep the
  business key, message/action identity and decision binding stable on retry.
- Build owner A and owner B, separate conversations C1/C2 for A, durable messages,
  a complete DRAFT candidate eligible for confirmation, confirmed task, approved availability and policy via the
  approved routines. Preserve exact response IDs/versions. One awaiting action per
  conversation means racing proposals need **different conversations**, same owner.
- Construct complete valid `PlanProposal` DTOs from the full snapshot, with
  `payload.study_blocks`, task summaries, diff, full policy and base revision.
  Assign future blocks on a UTC minute comfortably beyond the test run. Scheduler
  execution stays outside SQL; using known deterministic valid payloads is enough.
- Use bounded barrier synchronization and `pg_blocking_pids`/`pg_stat_activity`
  to observe actual blocking. Do not use a sleep as evidence of serialization.
  An observer can hold A's existing profile `FOR UPDATE`, start both requests,
  confirm they wait, then release. Sign after fixture work and release within the
  transport validity window. Set finite lock/statement/test timeouts.
- Give each test isolated owners/namespaces and reset the disposable DB or perform
  administrative cleanup. A single outer rollback cannot clean separate sessions
  that committed. Never run these tests against a shared or cloud project.

## Minimum release gate

| Test / approved cases | Trigger through approved interfaces | Required observable result |
|---|---|---|
| R1 concurrent confirmation and lost response — DB-01/03 | Prepare one valid candidate/presentation/APPROVE binding. Two sessions call `confirm_task` with the same business key behind the owner-lock barrier. Disconnect after one committed result; retry from a fresh connection with a fresh attestation/request_id. | Both successful responses identify the same task; exactly one AcademicTask and ApprovalAction, consistent candidate backlink, completed action and one domain result; revision increases once. Replay occurs before the candidate's terminal-state check. A changed signed body under the same key returns `IDEMPOTENCY_CONFLICT`, with no additional state change. |
| R2 competing plan approval — DB-02/04 | Persist P1/P2 against the same current plan/revision; prepare their approvals in C1/C2. Race `approve_study_plan` behind the owner barrier with distinct keys. Retry the winner after discarding its response. | Exactly one COMMITTED plan/version, one pointer/revision advance and one approval/action completion. Loser returns a typed stale ErrorResult (`STALE_PROPOSAL` or `STALE_PLAN_VERSION`, according to the failed guard), persists STALE where the proposal is invalid, and cannot overwrite the winner. Winner retry returns original plan, not a stale error. |
| R3 revision stale without plan-version change — DB-05/06 | Read `get_scheduling_context`; change an approved TimeWindow or scheduling policy without committing a new plan. Attempt `persist_plan_proposal` using the old revision. Separately persist a fresh proposal, then change policy/window and attempt approval. | Persistence of obsolete inputs is rejected; approval of the obsolete stored proposal returns `STALE_PROPOSAL`, commits no plan/approval/pointer change, and leaves durable proposal STALE. A new connection sees STALE. Same-key retry returns the saved error; no repeatedly advancing revision. Existing plan version remains unchanged by the settings mutation. |
| R4 failure halfway through snapshot — DB-07 | Prepare a valid proposal with at least two new blocks. In the test transaction install a test-only AFTER INSERT trigger that raises `XX000` on the second block. Call `approve_study_plan`. Repeat with a failure just after plan insertion. | Typed `INTERNAL_ERROR` without injected SQL text. A complete before/after snapshot matches for plans, blocks, pointer/revision, proposal, ApprovalAction, pending action and domain idempotency. No APPROVED-without-snapshot state. Remove fault and retry same key successfully, proving a transient internal error did not become a completed business result. |
| R5 protected full snapshot and history — DB-08/09, PLAN-02/04 | Build current plan with a historical block, future locked block, block outside horizon, block crossing horizon and an unselected-task block. Replan only selected eligible work; commit then read CURRENT and HISTORY. Submit signed variants that drop/change a protected ID/interval, reuse an ID for different content, omit a block outside a filtered calendar view, or overlap two blocks in one snapshot. | Complete snapshot retains protected content/IDs and historical metadata byte-for-byte. `(plan_id,block_id)` permits the same retained ID in both snapshots. Old plan/blocks cannot be updated/deleted even under ordinary RPC-owner privileges. Same-plan overlap is rejected; identical intervals across snapshots and adjacent half-open intervals are allowed. Task remaining is unchanged by scheduling; summaries conserve remaining = retained future + new + unallocated. |
| R6 generation and rejection recovery — DB-10/16 | Persist proposal via `persist_plan_proposal` with original `command_arguments`; discard result. Retry using the same key/original command but freshly generated proposal ID/clock/block IDs, and call `lookup_operation_result` with the stable fingerprint. Separately reject a proposal and retry after losing response. | Generation reuses the stored proposal under operation `generate_study_plan`; no duplicate proposal/presentation or revision increase. Altering scope/override under same key conflicts. Reject retry returns original REJECTED proposal and leaves current pointer/revision untouched. |
| R7 receipt fencing and worker restart — DB-11/15 | `claim_api_receipt` for a stable HTTP operation/key/fingerprint; retain returned message/action IDs and lease V1. Reclaim after expiry as worker B (V2). Worker A attempts renew/release/complete at V1; B completes at V2, then a new connection claims/replays. Also release a retryable failure then reclaim. | Initial lease is 120 seconds and reclaim increases version. Old worker gets a schema-valid ErrorResult and cannot change B's receipt. IDs are reused; one completed response is durable. Claim while live returns retryable SERVICE_UNAVAILABLE without completing/caching the busy error. Transient 429/503 is not terminal; completed/domain-stale outcomes are replayed. HTTP mapping/Retry-After is verified in the API suite. |
| R8 approval authority, review and foreign references — SEC-05, DB-12, ORCH-02/05 | Sign an otherwise-valid A envelope referencing B's message/conversation/candidate/proposal. Try stale ActionReference after candidate edit, `requires_review=true`, mismatched target/version, CHAT without durable matching source, and PARTIAL presentation omitting unallocated/warnings. Attempt two awaiting actions in one conversation. | Exact approved owner/not-found/review/stale errors, no unauthorized business/approval writes, no leaked B data. A GET/read does not clear review or write. `review_pending_action` returns a new reference/version when required and same-key retry does not review twice. PARTIAL cannot commit without matching full stored presentation. At most one awaiting action in the three approved AWAITING states. |

For R7, the fast fencing test may administratively set only the mapped
`api_request_receipts.lease_until` into the past after asserting the initial lease
duration. Label that fixture manipulation explicitly. Include one slow CI case
that waits for the real 120-second expiry to prove clock-driven reclamation;
poll in short bounded intervals. Do not add a production clock-override routine.
The approved contract does not fix a dedicated lease-fencing error code; require
the declared ErrorResult and unchanged state, and record the chosen existing
domain code rather than inventing a new enum.

R5 malformed variants must be signed **after** tampering so they exercise database
semantic checks, not merely attestation digest rejection. For protected historical
fixtures, administrative seeding may establish an already-committed historical
base plan; all attempted new product mutations still go through approved RPCs.

## Additional targeted checks after the minimum gate

1. Snapshot consistency: while one worker commits approved policy changes with
   monotonically increasing revisions, repeatedly call `get_scheduling_context`.
   Assert each returned user policy/version/revision and full base plan describe
   one recorded committed state. This can expose tearing; a finite stress run
   does not prove all interleavings. Review the one-statement/REPEATABLE READ design
   alongside runtime evidence (IC-06), rather than claiming stress alone proves it.
2. Revalidation clock: old `generated_at` alone does not expire an otherwise-valid
   proposal; newly generated blocks already started at approval are stale. Historical
   protected blocks remain legal. Use controlled fixtures/short minute-boundary
   cases, not a new clock seam or product TTL.
3. Maintenance and grants: expiration cleanup after seven days preserves business
   history/backlinks/uniqueness, defaults remain protected after creating another
   helper/table, and the touched-table matrix documents exactly what each wrapper
   needs. Repeat empty and upgraded migration replay; preserve legacy data.

## WP2 review and package handoff

The implementation work order is large enough to conceal partial success. Split
delivery into WP2a boundary/infrastructure/helpers, WP2b tasks/settings/receipts,
and WP2c proposal reads/persistence/commit validation. Each adds new migrations,
replays from an empty real stack and from the eight-migration baseline in CI,
and reports remaining red tests. All tests stay intact; the complete 03–06 suite
may remain red until the relevant domain package is delivered.

Important corrections incorporated into the work order:

- ApprovalAction/action completion is atomic **when the operation requires it**.
  Candidate drafts, messages, review and receipt lease operations do not manufacture
  approvals; receipt storage must not occupy domain idempotency namespaces.
- Proposal invalidation must remain durable and replayable for DB-06; distinguish
  that terminal business state from technical-failure rollback.
- Include actual 120-second lease fencing, unchanged-history checks, and an explicit
  per-wrapper privilege matrix as acceptance outputs. Catalog existence alone is
  insufficient.
- Unknown missing persistence reads must be resolved through an approved addendum.
  The current 21-wrapper inventory must not silently grow to unblock API handlers.
  Full restart/review flows remain blocked where the approved interfaces lack a
  necessary read. Do not fill the gap with authenticated table grants.

CI evidence must record commit, PostgreSQL/Supabase versions, migration replay
logs, pgTAP output, independent connection counts/barrier observations, exact
schema-valid results, fixture/fault conditions, and failed/skipped cases. Red,
NOT_RUN and contract-blocked are distinct statuses; no stage is accepted from
SQL parsing or mocked responses alone.
