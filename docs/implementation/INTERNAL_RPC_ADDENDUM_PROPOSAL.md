# Internal RPC addendum — review proposal, not approved

Prepared for review on 2026-11-05. Proposed additive package version: **1.0.1**;
logical schema_version remains **1.1**. This file does not change the approved package,
SQL inventory, runtime behavior, eight public endpoints or ten LLM/domain
operations. Implement affected seams only after approval and a synchronized
contract revision. Approved README §1 requires stopping related integration
when specifications do not provide a consistent interface.

## Evidence and scope of the gap

1. GET time-windows and GET preferences are approved in OpenAPI, but
   service-contract.json has no matching list/profile read interface. Private
   tables cannot be exposed or read using a privileged service-role workaround.
2. prepare_pending_action and review_pending_action require a complete input
   ActionPresentation. UserDecision supplies only reference and decision. No
   declared routine loads current pending/candidate/presentation/source state
   after a process restart. get_scheduling_context lacks this workflow data.
3. User timezone/locale/full policy are needed to build trusted context. Profile
   bootstrap is required by the approved security design, but has no standalone
   typed routine in the inventory. Existing TV2 get_profile/get_pending/get_review/
   get_decision/get_ui_event methods are explicitly proposed, not replacements.

## Proposed minimal interfaces

All names below are **proposed internal RPCs**. Each receives exactly
`p_request: RpcEnvelope` extended with an operation-specific RpcRequest branch.
There is no `command_arguments` property for these helpers: that existing field
belongs to PersistProposalArguments only. Each uses `arguments` exactly as below;
all listed keys required; null is explicit; additionalProperties=false. Add them
only to internal_interfaces, not Operation/ValidatedCommand/ActionRequest/LLM.

### A. ensure_user_context — profile/bootstrap and preferences source

Arguments: `{}`. Result `ensure_user_contextInternalResult` has outcome COMMITTED
and data User, or ErrorResult; no alternate user DTO. Existing profile returns
unchanged. Missing profile is created idempotently from authenticated owner using
the approved default timezone/locale/policy and revision=0. No caller user_id,
timezone, policy or current_plan_id input; no existing profile timestamp/revision
change. Existing-profile access is semantically a read, but this wrapper always
requires mutation attestation because bootstrap may write.

WP3 can derive PreferencesData from this authoritative User. The proposed policy
explicitly permits first authenticated GET to initialize infrastructure/profile;
it does not permit GET to change an existing policy, review flag or business data.
This first-GET bootstrap behavior needs approval; it is not established by the
current eight-endpoint document. Context needed to sign this bootstrap uses
trusted configured defaults solely until the returned profile is loaded, never
user input. Existing mutations may continue their own idempotent profile bootstrap.

Alternative: add separate get_user_context (read, User|null) and bootstrap_user
(attested, User). This keeps the read label pure but costs another wrapper and
still requires an explicit first-use bootstrap rule. Reusing claim_api_receipt
works for POST initialization, not first GET; inventing a dummy receipt/key or
generation_scope for a profile read is not acceptable.

### B. list_time_windows — exact approved HTTP pagination semantics

Arguments: `{kind: "AVAILABILITY"|"BUSY"|null,
include_archived: boolean, page_size: integer[1,100], cursor: string[1,2048]|null}`.
HTTP adapter supplies existing defaults null/false/50/null. Result
`list_time_windowsInternalResult` has outcome READ, data TimeWindowListData, or
ErrorResult; HTTP returns the existing TimeWindowListResult, no DTO expansion.

Read only the authenticated owner's rows, optionally kind-filtered; exclude
archived unless requested. Stable keyset order `(created_at,window_id)` ascending.
Opaque integrity-protected cursor binds owner/kind/include_archived/sort/last key.
Invalid/tampered/cross-owner/filter-changed cursor returns INVALID_PARAMETER,
never data or foreign-owner details. No total or cross-page snapshot guarantee.

Alternative: get_scheduling_context already contains time_windows but is intended
for a finite generation scope and consistent scheduling snapshot. It does not
promise archived rows, correct list pagination or cursor binding. It can be reused
only if its semantics are formally expanded; ad hoc filtering/truncation in Python
would not implement the approved cursor contract.

### C. get_workflow_context — cold-load current state and issued evidence

Arguments: `{conversation_id: UUID, action_id: UUID|null, message_id: UUID|null}`.
Result `get_workflow_contextInternalResult` has outcome READ with the following
new internal WorkflowContextData, or ErrorResult:

```text
{
  conversation_id: UUID,
  active_action: WorkflowActionContext|null,
  selected_action: WorkflowActionContext|null,
  source_message: SourceMessageRecord|null,
  read_at: RFC3339 UTC
}
WorkflowActionContext = {
  pending_action: PendingAction,
  candidate: TaskCandidate|null,
  proposal: PlanProposal|null,
  last_presentation: ActionPresentationRecord|null,
  presentation_source_message: SourceMessageRecord|null
}
```

All keys required; all objects closed. Reuse existing schemas without extending
logical entities. `active_action` is the single current awaiting action in that
conversation; null when none. `selected_action` is null iff action_id is null;
otherwise load that exact action, including terminal state. Both may refer to the
same action. Current candidate/proposal comes from authoritative rows, not the
old presentation payload. `last_presentation` is the immutable latest issued
record for that action; compare its recorded target/content/version with current
state before executing. It is null for a never-issued clarification draft.
Its source message is returned exactly when the record has a source_message_id.
`source_message` loads the exact requested message_id for receipt recovery; null
iff message_id is null. It does not return unrestricted conversation history.

Require existing same-owner conversation; absent/foreign conversation, action or
requested message returns ENTITY_NOT_FOUND with no ownership distinction. Action,
candidate, proposal, presentation and source must all match the conversation and
owner. Read all related rows from one consistent SQL statement/snapshot. This
read never clears requires_review, issues a new presentation, updates state or
creates a conversation. First-use create-if-absent remains in the existing
attested record_source_message/receipt preparation path; WP4 must not perform a
context read expecting it to create ownership. Domain mutation repeats current
checks under owner lock; the read does not authorize a later write.

Alternative: only load an action by ID. That is enough for typed decisions/review,
but not CHAT clarification, unambiguous approval resolution or recovered message
loading. Querying private tables using service_role, or passing normalized command
from FE, is prohibited. Overloading a write helper to return current data would
give GET/read paths hidden review effects and is not recommended.

## Security and result envelope for all proposed routines

- Exact schema_version=1.1; proposed contract_version=1.0.1 requires formal
  addendum approval. Match request_id/operation/routine. Use existing
  internal result envelope `{schema_version,request_id,outcome,data,error,warnings}`
  with error=null on success and existing ErrorResult on failure. Warnings are
  Issue[]; no SQL details. These wrappers create no new domain idempotency names.
- list_time_windows/get_workflow_context: attestation=null, JWT required,
  approval_action=null and idempotency_key=null. ensure_user_context: valid
  backend attestation, approval_action=null; idempotency_key may be null because
  bootstrap uses same-owner insert-on-conflict and no business mutation/replay.
  This is a deliberate new helper branch, not a loosening of domain writer rules.
- TrustedContext principal must equal auth.uid(); never accept a second owner
  argument. Same JWT forwarding and app_api Content-Profile remain mandatory.
  SECURITY DEFINER owner sf_rpc_owner, NOLOGIN/NOBYPASSRLS, search_path empty,
  fully qualified objects, FORCE RLS and least touched-table grants. Revoke
  PUBLIC/anon execute. User reads expose only their own records. Sign and validate
  ensure_user_context exactly like every other potential writer.
- Profile/bootstrap: only user_profiles touched; list: time_windows only;
  workflow: conversation_records, pending_actions, task_candidates,
  plan_proposals, action_presentations and source_messages read-only.
  Read helpers cannot access rpc_attestation_keys except through the verifier's
  existing private privileges. No broad private-schema/table permissions.

## D. Durable ordered continuation — concrete infrastructure proposal

This is needed for ORCH-03 and restart recovery: ConversationRecord has no queue,
ApiReceipt has only one action/message/final reply, and only one action may await
in a conversation. Re-extracting source text is not durable deterministic state.
The following is a proposed infrastructure record, not an eleventh business entity
or LLM/domain operation. It is not hidden inside PendingAction.draft_arguments.

### Record and mapping

New private table `app_private.workflow_continuations`, schema
`WorkflowContinuationRecord`, primary key `(user_id,source_message_id)`:

```text
user_id: UUID                          # uuid NOT NULL
conversation_id: UUID                  # uuid NOT NULL
source_message_id: UUID                # uuid NOT NULL; unique same-owner source
origin_http_operation: send_message|prepare_action
origin_idempotency_key: contract key
origin_request_fingerprint: lowercase SHA256 hex
version: safe integer >=1              # bigint NOT NULL
extraction: ExtractionResult           # jsonb NOT NULL; normalized once, immutable
extraction_digest: lowercase SHA256 hex # text NOT NULL
depends_on: integer[][]                # jsonb NOT NULL; one list per intent
cursor: integer >=0                    # bigint NOT NULL; first unfinished index
awaiting_reference: ActionReference|null # jsonb nullable; at most one action
completed_steps: WorkflowStepOutcome[] # jsonb NOT NULL; contiguous prefix
created_at: UTC instant                # timestamptz NOT NULL
updated_at: UTC instant                # timestamptz NOT NULL

WorkflowStepOutcome = {
  intent_index: integer >=0,
  step_key: lowercase SHA256 hex,
  operation: Operation|null,
  disposition: SUCCEEDED|REJECTED|FAILED|DEPENDENCY_CANCELLED,
  result: ToolResult|null,
  error: Error|null
}
```

All JSON objects closed and keys required; scalar lengths/ranges use existing
definitions. The extraction has ordered intents, absolute normalized instants
where resolvable, original raw_expressions and unresolved ambiguities. It is not
a grant to execute an arbitrary slots map. Reuse the existing ExtractionResult
intent-item shape and run server intent-specific slot/temporal validation before
storage and again before dispatch. Dependencies are server-derived: each index
must reference only earlier indices, no duplicates, and array length equals
intent count. `cursor <= intent_count`, completed_steps has exactly cursor items
with indices 0..cursor-1, and awaiting_reference may only describe cursor's step.
No queued step becomes a PendingAction until it is selected for processing.

Same-owner FKs bind conversation, source message and origin API receipt
`(user_id,http_operation,idempotency_key)`; compare receipt fingerprint and source
message/conversation. Source must be the original USER CHAT/UI message, not a new
retry audit ID. No account/message/history cascade delete. Completed records
remain available for the receipt retry window of at least seven days; do not
delete live awaiting continuations by lease or product TTL. Protect immutable
queue/origin fields against UPDATE. Add `(user_id,conversation_id,updated_at)`
index and allow at most one unfinished continuation per conversation; a new
message that clarifies the active step updates its action via existing helpers
instead of silently replacing the immutable queue.

Stable step_key for index i is lowercase SHA256 of canonical
`{api_key:origin_idempotency_key,source_message_id,intent_index:i}`. Domain key for
operation op is SHA256 of canonical `{step_key,operation:op}`; this distinguishes
prepare/generate from confirm/approve for the same intent. Helper-specific child
keys include helper name instead of operation. Do not incorporate extraction retry output, request_id,
generated IDs or current clock. Data and index are server-owned infrastructure,
never additional FE request fields.

### Exact proposed helper arguments and results

`get_workflow_continuation` (read-only, attestation=null):

```text
arguments = {conversation_id: UUID, source_message_id: UUID|null}
data = {continuation: WorkflowContinuationRecord|null}
```

With source_message_id, load that exact owned source/continuation; source missing
or foreign returns ENTITY_NOT_FOUND, existing owned source with no continuation
returns null. With null, return the single unfinished continuation for the owned
conversation, or null. Never select an arbitrary recent completed queue. One SQL
snapshot; never change cursor/flags. A helper result is READ or ErrorResult.

`initialize_workflow_continuation` (attested mutation):

```text
arguments = {
  conversation_id: UUID, source_message_id: UUID,
  extraction: ExtractionResult, depends_on: integer[][],
  receipt_binding: ActiveApiReceiptBinding
}
ActiveApiReceiptBinding = {
  http_operation: send_message|prepare_action|review_action|submit_decision,
  idempotency_key: contract key, request_fingerprint: lowercase SHA256 hex,
  expected_lease_version: safe integer >=1
}
data = WorkflowContinuationRecord
```

Only send_message/prepare_action may initialize; receipt source and conversation
must match the durable source message. Under owner lock verify the current
unexpired receipt lease/fencing and fingerprint. First insert sets version=1,
cursor=0, awaiting_reference=null, completed_steps=[]. Compute digest server-side.
Same owner/source/origin receipt/fingerprint returns the original record before
any extraction comparison, even if a duplicate in-flight extractor produced a
different output: the first stored extraction wins and is the only executable
queue. Another origin/fingerprint conflicts. Call load before invoking DeepSeek;
load again/use returned canonical extraction after initialize. No LLM in SQL.

`checkpoint_workflow_continuation` (attested mutation):

```text
arguments = {
  conversation_id: UUID, source_message_id: UUID,
  expected_version: safe integer >=1, expected_cursor: integer >=0,
  transition: WAIT|ADVANCE,
  action_reference: ActionReference|null,
  outcome: WorkflowStepOutcome|null,
  receipt_binding: ActiveApiReceiptBinding
}
data = WorkflowContinuationRecord
```

Owner lock + active lease/fingerprint check + compare-and-swap version/cursor
form one transaction. WAIT requires action_reference for the exact owned current
step, outcome=null and an already persisted awaiting action/presentation with the
same original source/conversation; it sets awaiting_reference and increments
version, without moving cursor. If already identically checkpointed, return the
same row without incrementing again. No second awaiting action may be introduced.

ADVANCE requires one outcome at expected_cursor with its deterministic step_key;
action_reference is the prior awaited reference or null for an immediate read.
If awaited, reload the action under the same owner lock and require COMPLETED or
CANCELLED, matching target and decision evidence. requires_review or an unresolved
awaiting action cannot advance. For successful domain writes verify the completed
domain idempotency result matches the derived operation key/result; operation must
be the current intent's allowed terminal operation (e.g. confirm_task for CREATE_TASK,
approve_study_plan for approved GENERATE_STUDY_PLAN). Reject a fabricated success
object even when its JSON shape passes. For immediate read steps, attested backend
supplies the schema-valid read result and stores it atomically as the step outcome.
Append exactly once, clear awaiting_reference, increment cursor/version. Identical
already-applied outcome replays without another increment; incompatible old
version/cursor/outcome returns STALE_ENTITY_VERSION or IDEMPOTENCY_CONFLICT.
FAILED requires Error; REJECTED/DEPENDENCY_CANCELLED may have null result/error and
operation=null when cancellation uses an internal helper rather than a domain op.

If a prerequisite was rejected/failed, its dependent step cannot execute. Store
DEPENDENCY_CANCELLED (no domain call), advance, and explain/ask the user as needed.
Independent steps may proceed in original order. A new policy/availability needed
after rejection requires a new user request, never inferred permission.

### Cold load and atomic progress semantics

Load receipt first. A COMPLETED receipt replays immediately. For an owned/reclaimed
lease, reuse its message/action IDs, load continuation before extraction, and
resume at cursor. Queue writes and progress are atomic CAS operations; the domain
commit and checkpoint are separate existing RPC transactions. A crash between
them is safe because recovery looks up the stable domain key first, verifies the
durable result/current terminal action, then checkpoints without rerunning the
business write. A crash after WAIT loads its stored reference instead of creating
another action. Never advance solely because the worker held an in-memory result.
Retain original queued absolute dates across restarts and review.

The originating HTTP request can complete with AWAITING_APPROVAL while its
continuation stays unfinished. A subsequent review/decision request has a new
active receipt lease; checkpoint verifies that receipt's conversation and exact
awaited reference while preserving the immutable origin receipt binding. The
origin completed receipt cannot authorize a worker to resume on its own. Process
resume requires the authenticated follow-up or valid recovery lease for the
current request. Cross-request dependencies never bypass the decision pipeline.

All write helpers require normal backend attestation; all rows FORCE RLS with
same-owner checks, no PUBLIC/anon execute or user table privileges. Add precise
touched-table grants: continuation read/write plus read-only source/conversation/
receipt/action/presentation/domain replay checks. Cursor transitions execute
under the existing user_profiles owner-lock order, never a new competing lock
protocol. No continuation helper mutates AcademicTask/TimeWindow/StudyPlan.

Alternative: a single-intent restriction avoids this infrastructure but knowingly
fails ORCH-03 and full F1 acceptance. Re-running DeepSeek after every approval or
embedding the queue in a loose draft map does not meet deterministic recovery.

## Approval and implementation checklist

Approve or revise A/B/C/D, including first-GET bootstrap, wrapper names and new
internal data definitions. Then update README, service-contract, schema branches,
data infrastructure mapping if needed, fixtures, checker and approval/version
record together; add SQL migration and independent cross-owner/cursor/snapshot
checks. Public OpenAPI paths/requests and ten-operation enum stay unchanged.
Implement and verify the approved continuation design before marking WP4 complete. Until then,
WP3 JWT/error/signing and existing read adapters can progress independently.
