# WP0 — implement the approved internal contract 1.0.1 addendum

Implementation owner: Gemini. Sol owns independent acceptance tests and execution.
The user has explicitly approved **all A/B/C/D** in
`INTERNAL_RPC_ADDENDUM_PROPOSAL.md`, including its six helper RPCs, continuation
infrastructure and attested first-GET profile bootstrap. The proposal file's
historical “not approved” wording predates that approval. This package records the
implementation handoff; it does not itself pretend machine-readable artifacts
have already changed.

## Fixed scope

Update contract package **1.0.0 → 1.0.1** while logical schema_version stays
**1.1**, eight public method/path pairs stay unchanged, ten domain/LLM operations
and ten logical business entities stay unchanged. Infrastructure is not an
eleventh entity or an additional ActionRequest/ValidatedCommand/LLM operation.
Preserve all twelve existing internal routines and add exactly these six:

| Internal routine | read_only | attestation_required | Success outcome/data |
|---|---|---|---|
| ensure_user_context | false | true | COMMITTED / User |
| list_time_windows | true | false | READ / TimeWindowListData |
| get_workflow_context | true | false | READ / WorkflowContextData |
| get_workflow_continuation | true | false | READ / {continuation: WorkflowContinuationRecord|null} |
| initialize_workflow_continuation | false | true | COMMITTED / WorkflowContinuationRecord |
| checkpoint_workflow_continuation | false | true | COMMITTED / WorkflowContinuationRecord |

Each receives exactly `p_request` with an operation-specific RpcRequest branch.
Each is llm_callable=false and uses result_schema `<routine>InternalResult`,
with the existing internal envelope or ErrorResult. There is no new public route
and no command_arguments field on these helpers. Existing generation persistence
continues to use original PersistProposalArguments.command_arguments.

## Source changes in this package

- Synchronize contracts README/approval/version records, service-contract.json,
  data-contract.json, OpenAPI package metadata and f1.schema.json $id/envelopes
  to 1.0.1. Public OpenAPI requests/responses remain the approved ones.
- Add the six internal entries, closed argument definitions, result definitions
  and RpcRequest branches. Preserve all existing operation mappings and wrappers.
  Follow the approved argument/data shapes exactly. Definitions explicitly named
  by the addendum are WorkflowContextData, WorkflowActionContext,
  WorkflowContinuationRecord, WorkflowStepOutcome and ActiveApiReceiptBinding.
  Argument-definition names can follow the existing convention; expose their
  names through internal_interfaces.arguments_schema rather than a second registry.
- Map app_private.workflow_continuations as infrastructure, PK
  (user_id,source_message_id), with exactly the approved fifteen columns and types.
  Declare same-owner conversation/source/origin receipt FKs, immutable queue/
  origin fields, owner-lock/CAS/lease semantics, retention and least grants.
- Extend the existing pure `contracts.check_contract.semantic_errors(value, path)`
  / `validate_instance(definitions,name,value,semantic=True)` boundary for
  single-payload invariants below; do not create a separate test-only validator.
  Register new valid/invalid official fixtures in the normal checker manifest.
  Independent acceptance fixtures remain owned by Sol and must not be edited.

## Closed shape and pure invariant requirements

All listed keys are required; nullable is not optional; unknown object fields are
rejected. Reuse UUID, safe integer, key, hash, timestamp, ActionReference,
ExtractionResult, ToolResult, Error and existing entity definitions.

- ensure_user_context arguments `{}`; signed even with null context idempotency
  key and null approval, because first access can bootstrap the profile. It returns
  authoritative User, leaves existing profile/revision/audit fields unchanged,
  and creates only approved defaults for a missing profile. GET preferences
  derives its existing PreferencesData from that User; no dummy domain key/receipt.
- list_time_windows has required kind/null, include_archived boolean, page_size
  1–100 and cursor/null (1–2048 characters when present). Exact cursor ownership/
  filter binding remains DB acceptance, not something JSON Schema can prove.
- get_workflow_context requires conversation_id, action_id/null and message_id/null.
  Its data and nested WorkflowActionContext have all exact fields from addendum C.
  No unbounded conversation_history field, writes or review side effects.
- Continuation reads require conversation_id and source_message_id/null; their data
  is a closed one-key nullable continuation wrapper. Initialize takes conversation,
  source, normalized ExtractionResult, depends_on and ActiveApiReceiptBinding.
  Only send_message/prepare_action may initialize; review_action/submit_decision
  remain valid bindings for a later checkpoint but cannot start a queue.
- ActiveApiReceiptBinding has exactly http_operation, idempotency_key,
  request_fingerprint and expected_lease_version>=1, with strict integer typing.
- Checkpoint arguments are a disjoint WAIT/ADVANCE union. WAIT requires non-null
  ActionReference and outcome=null. ADVANCE requires non-null WorkflowStepOutcome;
  action_reference is nullable for immediate reads. Versions >=1, cursors >=0,
  safe integers; no generic unknown transition. Outcome intent_index must equal
  expected_cursor. FAILED requires Error. Other result/operation relationships
  must use the approved operation/outcome schemas and D's terminal-step semantics.
- Continuation cursor is <= extraction intent count; completed_steps length equals
  cursor and indices are contiguous 0..cursor-1. depends_on has exactly one list
  per intent, with unique nonnegative indices strictly earlier than that intent;
  reject self, forward, duplicate and invalid references. Completed queues have no
  awaited current step. Preserve unresolved ambiguities, original expressions and
  absolute resolved dates; no schema-level fabrication of relative-date context.

Use JSON Schema for closed fields/types/unions and the existing pure checker for
cross-field lengths/index comparisons. A checker cannot prove owner, current
action terminal state, lease ownership, immutable storage or authentic decisions;
those belong to later SQL/runtime acceptance. Do not claim otherwise.

## Follow-on implementation constraints

WP2 must implement the six wrappers with user JWT, SECURITY DEFINER least privilege,
FORCE RLS and the approved owner lock; all potential writers, including
bootstrap/continuation, use backend HMAC. The three new read helpers require null
attestation/approval/idempotency key. No service_role workaround or private-table
access from FE. The continuation write helpers use active receipt lease fencing;
initialize is first-write-wins for the immutable extraction, checkpoint WAIT and
ADVANCE use CAS and exact-once prefix progress. Domain mutation and checkpoint
are separate atomic RPC transactions, recovered through stable operation keys
before re-execution. Preserve this distinction in implementation claims.

The exact D record, stable step/operation key formulas, dependency cancellation,
matching current terminal action/domain replay evidence, cold-load selection and
new follow-up receipt binding are in the approved addendum. WP3/WP4 handoffs apply
with the formerly blocked addendum now approved; preserve their frozen factory,
Settings, transports and clock seam. No runtime work is required in WP0 itself.

## Independent acceptance gate

```powershell
python -m unittest discover -s backend/tests/acceptance_api_sol -p test_contract_addendum.py -v
python contracts/check_contract.py
```

`test_contract_addendum.py` reads the actual source package, not a test substitute.
Its acceptance-owned fixtures include a valid continuation, invalid cursor record,
valid WAIT/ADVANCE and invalid WAIT carrying an outcome. It also mutates boundary
conditions to verify required fields, null unions, dependencies and closed maps.
The existing HTTP suite is a separate runtime gate; it adds a first-preferences-
GET test requiring real adapter signing before simulated ensure_user_context.
Passing these checks proves contract structure/pure invariants and simulated
adapter behavior only. Real SQL/profile defaults/immutability/concurrency/restart
checks remain mandatory. Do not edit independent tests or weaken assertions.
