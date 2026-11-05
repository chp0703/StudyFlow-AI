# WP2b — tasks, settings, receipts (progress notes)

Split into reviewable stages; each stage ends with local pgTAP evidence and a push.

| Stage | Scope | Status |
|---|---|---|
| 2b-1 | Wrapper helpers, `ensure_user_context`, `record_source_message`, `claim/renew/release/complete_api_receipt` | done (migration 013, test 09) |
| 2b-2 | `create_task_candidate`, domain idempotency + `lookup_operation_result`, `update_candidate_draft` | done (migration 014, test 10) |
| 2b-3 | `prepare/review/cancel_pending_action`, `confirm_task`, `search_tasks` | done (migration 015, test 11) |
| 2b-4 | `set_availability`, `set_busy_interval`, `set_scheduling_preferences`, `list_time_windows` | done (migration 016, test 12) |
| 2b-5 | `get_workflow_context`, `get_workflow_continuation`, `initialize/checkpoint_workflow_continuation` | done (migration 017, test 13) |

## 2b-1 decisions

- Every attested writer calls `app_private.lock_owner`, which creates the profile from trusted context
  (timezone, locale, default policy) when absent and takes the owner row lock. `EnsureUserContextArguments`
  accepts only `{}`, so the profile timezone comes from the trusted context, never from arguments.
- Wrappers run `app_private.precheck` first: signature verification, operation binding, `RpcEnvelope` and the
  per-operation arguments schema. Domain errors are returned as ErrorResults; unexpected SQL failures roll back
  the wrapper's subtransaction and become `INTERNAL_ERROR` (`INVALID_PARAMETER` for 22023-class input errors).
- Receipt message/action IDs are allocated at the first claim, before the message or action exists, so the
  receipt has no foreign keys to them (those constraints from migration 009 are dropped in 013).
- Lease: 120 s; a live lease is retryable `SERVICE_UNAVAILABLE`; reclaim bumps `lease_version`; old holders get
  `STALE_ENTITY_VERSION`; 429/503 cannot be completed (release instead). No dedicated fencing code was invented.
- `record_source_message` creates the conversation record and requires the message to match the verified owner,
  the request conversation and the trusted message ID. Re-recording identical content is idempotent.

## Evidence (local pgTAP, 2b-1, historical)

03, 04, 05, 08, 09 pass. 06: 10/81 fail (candidate creation, WP2b-2). 07: 24/58 fail (windows, workflow, 2b-4/2b-5).
Not run: slow wall-clock 120 s expiry, concurrency harness.

## 2b-2 decisions

- Domain idempotency follows the contract order: fast lookup, owner lock, lookup again, validate, write and
  complete the record in one subtransaction. The record stores the full result envelope; a replay swaps in the
  current `request_id`. Fingerprint is `SHA256(canonical{schema_version,user_id,operation,arguments,decision_binding})`.
  Records are retained 7 days (`expires_at`).
- `create_task_candidate` requires a non-null idempotency key, a conversation and a source message that was
  recorded for that owner and conversation (`ENTITY_NOT_FOUND` otherwise). No FK was added on
  `task_candidates.source_message_id` so existing rows stay valid on upgrade.
- `field_sources` records `USER_MESSAGE` provenance for supplied non-null slots; the LLM does not choose it.
- `update_candidate_draft` has no domain-idempotency record: a retry that finds exactly the requested content one
  version ahead is a replay, anything else with an old version is `STALE_ENTITY_VERSION`.
  Invalidating awaiting presentations for an edited candidate is checked in 2b-3 (target version no longer matches).
- `lookup_operation_result` is read-only: stored result, `null`, or `IDEMPOTENCY_CONFLICT` for another fingerprint.

## Evidence (local pgTAP, 2b-2)

03, 04, 05, 06, 08, 09, 10 pass (06 is now fully green). 07: 24/58 fail (windows 2b-4, workflow 2b-5).

## 2b-3 decisions

- **Presentations are server-issued.** `prepare`/`review` check the presented candidate against the stored draft
  (version and slots; otherwise `STALE_ENTITY_VERSION`), rebuild `pending_action` from the row and store one
  presentation per action version with a digest of target triple, content and effective policy. `confirm_task`
  recomputes the digest, so content that was not presented cannot be approved (`APPROVAL_REQUIRED`).
- **One awaiting action per conversation** is now a partial unique index. A second one is refused with
  `ACTION_REVIEW_REQUIRED` (the contract names no dedicated code; revisit if the team prefers another).
- **Review** clears `requires_review` and bumps the action version once; retries find the issued version and return
  the stored presentation. A read never changes review state.
- **cancel_pending_action** moves the action (and optionally its DRAFT candidate) to CANCELLED and writes no
  ApprovalAction or official data.
- **confirm_task** requires a backend approval context naming this candidate and version, a matching action reference,
  a recorded USER message for CHAT approvals, a non-review awaiting action and a candidate that is complete.
  A DATE deadline is normalized to local midnight of the next day. One transaction writes ApprovalAction, AcademicTask,
  candidate backlink, action completion, `schedule_revision + 1` and the idempotency record; replay is answered before
  stale checks, and a later key gets `STALE_ENTITY_VERSION`.
- **search_tasks** is keyset-paginated on `(deadline_at, task_id)`. Cursors are opaque, bound to owner and filter and
  authenticated with a key derived from the active attestation key (rotation invalidates open cursors).
- The approval-target trigger from migration 006 now reads the owner from `app_private.current_uid()` instead of `auth.uid()`.

## Evidence (local pgTAP, 2b-3)

03, 04, 05, 06, 08, 09, 10, 11 pass. 07: 24/58 fail (windows 2b-4, workflow 2b-5).

## 2b-4 decisions

- The three writers share `consume_pending_approval`: the approval must name a PENDING_ACTION and match the
  action reference; the action must be un-reviewed and awaiting; its stored presentation must carry a
  `normalized_command` equal to the command being executed. Only then is the ApprovalAction written and the
  action completed, in the same subtransaction as the data write, `schedule_revision + 1` and the idempotency record.
- Business validation (real time zone, whole minutes, one local day for one-off windows, `end > start`,
  `valid_until > valid_from`, 24:00 ends) and version checks run before the approval is consumed, so a rejected
  command leaves the action awaiting.
- `set_availability` and `set_busy_interval` share one body keyed on kind; a window can only be edited or archived
  through the routine of its own kind. ARCHIVE sets `archived_at` and bumps the version; nothing is deleted.
- `set_scheduling_preferences` merges the patch into default policy plus stored policy, checks min/max/daily/break
  and guards on `expected_schedule_revision`. Defaults are not hard caps (120-150 min, 600 min/day, no break is valid).
- `list_time_windows` is keyset on `(created_at, window_id)` with the same signed, owner/filter-bound cursor as search.
- **Not yet done (WP2c):** the contract says a window change must warn about affected approved blocks. The routines
  return no warnings until plans and blocks exist in the snapshot reads.

## Evidence (local pgTAP, 2b-4)

03, 04, 05, 06, 08, 09, 10, 11, 12 pass. 07: 22/58 fail, all in workflow reads and continuations (2b-5).

## 2b-5 decisions

- Reads never create state: an absent conversation, action or message is `ENTITY_NOT_FOUND`. `proposal` is always
  null until plans exist (WP2c). The active action is the single awaiting action (unique index from 2b-3).
- `initialize` is first-write-wins: the stored queue is returned before the extractor output is compared. It needs
  a live origin receipt (same fingerprint, fencing version, unexpired lease) and a USER message equal to the
  receipt's allocated `message_id`. `depends_on` must match the intent count and only point backwards.
  A second unfinished queue in a conversation returns `STALE_ENTITY_VERSION` (no dedicated contract code).
- `checkpoint` re-checks the receipt lease first (so even a duplicate cannot act on an expired lease), then detects
  an identical already-applied step/WAIT as a replay, then compare-and-sets on (version, cursor). ADVANCE must
  carry the step at the cursor with the key derived from origin key + source message + index; a step whose
  dependency did not succeed can only be DEPENDENCY_CANCELLED (and the reverse); an awaited action must be finished.
  Approval-gated operations (`confirm_task`, `set_*`, plan approve/reject) require a COMPLETED awaited action.
- **Limit:** for approval-gated writes the result payload is not re-derived from the stored entities; only the
  completed action is checked. Reads are trusted as attested.

## Evidence (local pgTAP, 2b-5)

All 11 suites pass (404 checks), including the whole 07 addendum.
