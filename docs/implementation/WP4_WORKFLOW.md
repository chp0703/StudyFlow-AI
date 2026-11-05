# WP4 — deterministic F1 workflow handoff

Implementation owner: Gemini. Approved `contracts/README.md` §§3–8,
`service-contract.json`, `f1.schema.json` and `acceptance-cases.md` govern this
package. Preserve the WP3 factory/Settings/HTTPX transport seam. Implement public
behavior through the real API; no second public execute interface or new LLM tool.

## Current implementation and reuse

`TaskService`, `SettingsService` and `PlanReadService` contain partial logic with
proposed transaction/evidence APIs. Their READMEs predate contract approval and
cannot authorize a parallel store protocol. Their flat TrustedContext,
approval_action_id, UI event/decision evidence methods and older result schemas
need explicit reconciliation with approved ExecutionContext and atomic RPCs.
Do not make unapproved get_ui_event/get_decision tables mandatory infrastructure.

Reuse the pure `PlanningService.generate_proposal_payload` and shared policy
merge/TimeWindow normalizer. WP1 correctness is a prerequisite, not a reason to
create another scheduler. No live workflow or restart success is presently proven.

## Deterministic processing boundary

1. WP3 authenticates; construct principal, IDs and audit clock server-side.
   Load trusted profile and conversation/action context through approved storage
   seams. Several required loads are absent; see the addendum proposal.
2. Validate HTTP input and claim the durable API receipt before external work.
   Use receipt-owned stable message/action IDs on first execution and recovery.
3. Persist UI synthetic source or CHAT user message via record_source_message
   before extraction/candidate preparation. All IDs/owner come from the server.
4. Treat DeepSeek output only as schema-checked ExtractionResult. Enforce intent
   and slot allowlists, resolve relative dates using the stored original message
   instant/timezone, validate owner/reference/temporal/policy semantics, then form
   ValidatedCommand. LLM output cannot grant consent, principal, ApprovalAction,
   requires_review, engine output or attestation. Ambiguity requires clarification.
5. Persist current draft/action/presentation through declared attested helpers;
   return exact typed ActionPresentation and ActionReference. Never claim a task
   or official plan is saved while only a draft/proposal exists.
6. For decisions, resolve current server state before dispatch; verify the exact
   reference and the persisted content that was issued. The DB repeats binding
   and version checks atomically with the mutation. Complete the API receipt only
   after the terminal reply and each preceding domain result are durable.

No LLM/network call runs while a DB write transaction is held. Dependency order
is deterministic; only one awaiting action per conversation. Do not schedule
from a proposed availability change until its approval commits. Durable storage
for remaining multi-intent work is proposed concretely in addendum D, pending approval.

## Ten operations and routing

| Operation | Preparation/decision behavior | Persistence/result |
|---|---|---|
| create_task_candidate | UI or CHAT supplies slots; incomplete draft asks questions; complete draft presents normalized candidate | create_task_candidate → DRAFTED/TaskCandidate; prepare_pending_action persists ActionPresentation |
| confirm_task | Only verified APPROVE for TASK_CANDIDATE, exact action/candidate versions and displayed slots | confirm_task → COMMITTED/AcademicTask; atomic approval, one task, pending completion, receipt/revision |
| search_tasks | Read-only CHAT intent or GET adapter, owner-scoped defaults | search_tasks → READ/SearchTasksData |
| set_availability | Preparation displays full ADD/UPDATE/ARCHIVE; writes pending only; commit follows verified APPROVE | set_availability → COMMITTED/TimeWindow |
| set_busy_interval | Same preparation/approval pattern with kind BUSY | set_busy_interval → COMMITTED/TimeWindow |
| set_scheduling_preferences | Nonempty patch; merge/validate and display full effective policy before approval | set_scheduling_preferences → COMMITTED/PreferencesData |
| generate_study_plan | Get consistent scheduling input/revision, run pure engine, materialize/validate full snapshot | lookup_operation_result before engine; persist_plan_proposal uses original command_arguments; PROPOSED/PlanProposal or READ/SchedulingReadData |
| get_study_plan | CURRENT/HISTORY/PROPOSAL semantics from WP3; no write/review side effects | get_study_plan → READ/PlanView or ProposalView |
| approve_study_plan | Only verified APPROVE for PLAN_PROPOSAL, full presentation including PARTIAL unallocated/warnings | approve_study_plan → COMMITTED/StudyPlan after approval-time revalidation |
| reject_study_plan | Only verified REJECT for exact proposal/reference; no current-plan mutation | reject_study_plan → REJECTED/PlanProposal |

Raw action requests allow only create_task_candidate, set_availability,
set_busy_interval, set_scheduling_preferences and generate_study_plan. Window and
policy preparation does not invoke the committing operation yet. A typed form
cannot call confirm/approve/reject directly. Non-proposal REJECT goes through
cancel_pending_action: cancel pending and draft candidate if present, without
writing official task/window/policy. Review uses review_pending_action and is
never approval. Internal helpers remain non-LLM-callable.

## Decision binding and recovery rules

- UserDecision contains only schema_version, conversation_id, decision and exact
  ActionReference. Never choose the newest target, infer consent from time or
  accept client normalized_command/policy as execution authority.
- Owner/conversation/action/action_version/target_type/id/version and displayed
  normalized content must all match current authoritative state. Hide a foreign
  entity as 404. Stale/reference mismatch or requires_review blocks the write.
- UI decisions are authenticated requests. Server creates the typed ApprovalAction
  in ExecutionContext; CHAT approvals require a persisted USER message bound to
  the same owner/conversation and unambiguous action. Bare “đồng ý” with missing
  context asks again. LLM claims of approval are never evidence.
- Reopening/returning to old context or changing topic must preserve the draft and
  require review. Review reconstructs full presentation, clears requires_review
  and increments action version if review was required; return its new reference.
  Same-key review retry returns the issued reference without a second increment.
  Old relative dates stay absolute; no candidate/action/proposal product TTL.
- API receipt uses its own HTTP operation namespace: send_message, prepare_action,
  review_action, submit_decision. Keys/fingerprints are owner-scoped. Same key and
  changed payload conflict. Completed replay precedes stale/terminal checks,
  refreshes envelope request_id and sets Idempotency-Replayed true.
- IN_PROGRESS lease is 120 seconds; renew within 30 seconds during long work.
  Compare expected_lease_version for renew/release/complete. Busy same-key work
  returns 503 SERVICE_UNAVAILABLE/Retry-After without completing the receipt.
  Release temporary 429/503; complete 200 and terminal domain errors. Keep receipts
  and domain replay at least seven days; do not delete business history.
- Domain fingerprint is canonical {schema_version,user_id,operation,arguments,
  decision_binding}. Derive stable child keys from API key + step/action identity
  + operation. Generated IDs/clock/audit request_id/signature are excluded.
  Generation uses original arguments and lookup_operation_result before rerun;
  worker death after proposal persist must reuse the old proposal.

## Planning and approval

Load full base plan and scheduling revision from one consistent snapshot, never a
calendar-filtered response. Apply custom policy and one-time override separately;
an override does not update profile. Normalize availability and busy separately.
Preserve protected/history/locked/out-of-horizon/cross-boundary blocks and IDs.
An active block requires progress clarification before reallocating its task.
Maintain remaining = retained_future + new + unallocated, without reducing task
remaining because time passes or a plan commits.

Only FULL/PARTIAL with actual diff and no hard conflict creates a proposal.
NONE/NO_CHANGE/empty diff returns approved SchedulingReadData; empty-diff PARTIAL
remains PARTIAL. At approval reload revision/base/clock/policy/tasks/windows and
validate the full snapshot. Newly scheduled/moved blocks cannot be in the past;
retained history is protected. Atomic RPC commits plan+blocks+pointer+revision+
proposal+approval+pending+domain replay, or keeps terminal STALE with its replay.

## Acceptance and honest blockers

Exercise API-01–08, ORCH-01–06, DB-01–03/10–11/15–16 and PLAN-01–07 through the
factory and real database when available. Independent mock receipt tests may
prove cold-app replay routing; they cannot prove durable database transactions,
requires_review transitions, owner binding or restart recovery of uncompleted
work. Do not add fake success stubs to satisfy these gates.

Formerly missing seams are now explicitly approved: profile/bootstrap and window
list reads, cold workflow state and durable remaining-intent queue. Implement
A/B/C/D in `INTERNAL_RPC_ADDENDUM_PROPOSAL.md` after WP0 synchronizes package 1.0.1
and WP2 delivers the actual persistence. No further design approval is needed
for these additions. Public eight endpoints/ten operations stay unchanged; never
fill live state with fixture values or claim incomplete persistence is complete.
