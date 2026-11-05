# WP2b — tasks, settings, receipts (progress notes)

Split into reviewable stages; each stage ends with local pgTAP evidence and a push.

| Stage | Scope | Status |
|---|---|---|
| 2b-1 | Wrapper helpers, `ensure_user_context`, `record_source_message`, `claim/renew/release/complete_api_receipt` | done (migration 013, test 09) |
| 2b-2 | `create_task_candidate`, domain idempotency + `lookup_operation_result`, `update_candidate_draft` | planned |
| 2b-3 | `prepare/review/cancel_pending_action`, `confirm_task`, `search_tasks` | planned |
| 2b-4 | `set_availability`, `set_busy_interval`, `set_scheduling_preferences`, `list_time_windows` | planned |
| 2b-5 | `get_workflow_context`, `get_workflow_continuation`, `initialize/checkpoint_workflow_continuation` | planned |

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

## Evidence (local pgTAP, 2b-1)

03, 04, 05, 08, 09 pass. 06: 10/81 fail (candidate creation, WP2b-2). 07: 24/58 fail (windows, workflow, 2b-4/2b-5).
Not run: slow wall-clock 120 s expiry, concurrency harness.
