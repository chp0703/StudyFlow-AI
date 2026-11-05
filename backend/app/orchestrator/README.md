# Tool dispatcher (TV2-03)

`Dispatcher(handlers)` receives a mapping from each v1.1 operation name to a handler callable. Each handler receives `(arguments, context)`, calls the application service and returns the operation's `ToolResult`, including the current server `request_id` even when replaying an earlier result. The service owns the use case; the handler does not duplicate it. A missing handler or invalid result produces `INTERNAL_ERROR`; service-returned schema-valid errors pass through. Unexpected exceptions are not returned to the caller. Handler timeout policy belongs to the integrating service/transport.

The registry marks `generate_study_plan` as a write because it can persist a proposal, even when a particular execution returns `READ`. The five confirmation operations require an approval action ID. A rejected proposal still requires the service to validate the authenticated user decision and target/version; absence of an approval requirement in the registry does not establish authorization to reject.

`TrustedContext` is an internal integration shape, not a public API or an authentication mechanism. Only the server may construct it. A7 transport obtains authenticated `Principal.user_id` from a trusted auth mechanism; the auth owner and mechanism remain to be decided. TV3 gathers `UserDecision`, source, target and version and manages conversation state. TV2 services check that evidence, owner, target, content, version and state, and handle `ApprovalAction`; TV1 stores the records. Nonempty idempotency keys only pass the dispatch gate: TV2 owns fingerprint, replay and result behavior; TV1 provides atomic storage, uniqueness and concurrency protection. The context shape, including conversation binding, must be reconciled with TV3 before service integration.

The dispatcher loads the TV2-02 schemas and uses the selected operation's result definition. For `get_study_plan`, the returned view kind must also match the requested view. `generate_study_plan` READ remains a provisional internal shape; do not publish it until the group approves it. Runtime needs a JSON Schema Draft 2020-12 validator with format checks (`jsonschema` is used here); no dependency is installed or declared by this patch. A missing or blank server request ID raises `ValueError` because a valid `ToolResult` cannot be constructed without it.

The dispatcher registers a local date-time checker because a bare `FormatChecker` may lack one. It requires an RFC 3339 date-time with `Z` or a numeric offset and validates calendar dates and offset ranges for command and result. Python's datetime rejects leap-second `:60` and year `0000`; those values are not accepted here pending a shared decision. This does not compare timestamps or validate timezone/DST semantics. Other direct consumers of the JSON Schema must enable their own date-time format checker; this dispatcher-local checker does not change them.

An INFO `tool_execution` record exposes only `request_id`, recognized `operation` (otherwise `UNKNOWN`), `outcome`, `error_code`, and `duration_ms` as structured fields. The dispatcher does not include arguments, context, idempotency keys, results or raw exceptions. Runtime logging configuration and formatter are provided by the host; the host must preserve these privacy constraints. If the logging handler fails, the dispatch result or original exception is preserved, so the log may be lost.

## Service integration dependencies

Inject real service callables only after the following interfaces and guarantees are supplied and reviewed; mocks in the tests are not services.

| Operation | Blocking inputs and acceptance needed |
| --- | --- |
| `search_tasks` | TV1: owner-scoped query and pagination interface; tests showing cross-user isolation. A7: authenticated principal from trusted transport/auth. |
| `create_task_candidate` | TV1: same-owner candidate persistence and atomic idempotency storage. TV3: conversation and message context; TV2 verifies their binding to the authenticated principal. Its exact trusted-context shape remains open. |
| `confirm_task` | TV1: atomic candidate-to-task promotion, version/uniqueness and idempotency storage/rollback. TV3: UserDecision with source, displayed candidate and version; TV2 verifies it and handles ApprovalAction. |
| `set_availability`, `set_busy_interval`, `set_scheduling_preferences` | TV1: owner/version/revision-aware transactional persistence; TV3: UserDecision and source/target/version; TV2 verifies the precise change or merged policy and handles ApprovalAction. |
| `generate_study_plan` | TV1: authoritative same-owner inputs, immutable proposal persistence, concurrency and idempotency; TV4: scheduler and validator interfaces; TV3/TV4: agree the still-provisional no-proposal READ shape. |
| `get_study_plan` | TV1: same-owner current/history/proposal read interfaces and associated data. |
| `approve_study_plan`, `reject_study_plan` | TV1: owner-locked atomic transaction, idempotency storage and rollback; TV3: UserDecision with source and target/version; TV2 checks decision and handles ApprovalAction; TV4: approval revalidation against current time and snapshot. Reject must not change the current plan. |

Before a stale decision on a retry, the service must check for the prior idempotent result as required by official v1.1; the TV1 draft's illustrative pseudocode should be reconciled before integration. Complete tests must cover forged approval, cross-user access, stale data, replay after timeout, concurrent requests and rollback. No integration or end-to-end success is implied by the dispatcher tests.

TV2 owns proposal use-case assembly (A4). TV4's existing `PlanningService` in PR #12 already materializes payloads; agree its handoff and reuse the helper where appropriate instead of creating a second competing planning service. The PARTIAL empty-diff regression and approval-time validator interface remain open.

## Fixture-only executor for TV3

`tests.fakes.tool_executor.FakeToolExecutor` provides `execute(command, trusted_context) -> ToolResult` by calling the real dispatcher with fixture-only handlers. Construct it with an optional per-operation scenario map, for example `FakeToolExecutor({'confirm_task': 'STALE_ENTITY_VERSION'})`. Default `success` uses the existing fixture for each operation. Fixed error scenarios: `APPROVAL_REQUIRED`, `ACTION_REVIEW_REQUIRED`, `ENTITY_NOT_FOUND`, `FORBIDDEN`, `STALE_ENTITY_VERSION`, `STALE_PROPOSAL`, `STALE_PLAN_VERSION`, `IDEMPOTENCY_CONFLICT`. For `get_study_plan`, `proposal` and `history` select compatible view fixtures. Match the command view to the scenario. Scenario selection is test configuration, not command input.

Pass a `TrustedContext` with the gates needed by the operation; the fake checks only what the dispatcher checks and does not authenticate or validate real approval/owner/version. Every execution returns a fresh copy with the current request ID. Fixtures are fixed: they do not follow input IDs or represent persistent state; a write result cannot be read back as a real write. The `generate_study_plan` no-proposal READ payload remains unresolved and is intentionally unavailable as a fake scenario. No database, runtime wiring or production implementation is provided.

Internal A3/A4 helper `backend.app.services.scheduling_policy.merge_scheduling_policy(policy, patch)` validates full policy and patch against the shared schemas, checks the cross-field bound after merge, and returns a new policy. It does not write a profile, ask for approval, or apply a default. An empty override is accepted; `set_scheduling_preferences` rejects an empty patch at its command boundary.

Run `python -B -m unittest discover -s tests -v` with that runtime available. Mocks test routing and boundary checks only; they do not implement the service or demonstrate authorization, persistence or transaction safety.
