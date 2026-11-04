# Tool dispatcher (TV2-03)

`Dispatcher(handlers)` receives a mapping from each v1.1 operation name to an application-service callable. Each callable receives `(arguments, context)` and returns the operation's `ToolResult`, including the current server `request_id` even when replaying an earlier result. A missing handler or invalid result produces `INTERNAL_ERROR`; service-returned schema-valid errors pass through. Unexpected exceptions are not returned to the caller. Handler timeout policy belongs to the integrating service/transport.

The registry marks `generate_study_plan` as a write because it can persist a proposal, even when a particular execution returns `READ`. The five confirmation operations require an approval action ID. A rejected proposal still requires the service to validate the authenticated user decision and target/version; absence of an approval requirement in the registry does not establish authorization to reject.

`TrustedContext` is an internal integration shape, not a public API or an authentication mechanism. Only the server may construct it. The caller must authenticate `Principal.user_id` and verify conversation/message ownership before providing their IDs. The candidate service must verify those relationships too. Approval IDs only identify evidence; the service must verify owner, target, content, version, decision and state. Nonempty idempotency keys only pass the dispatch gate: services and persistence implement fingerprint comparison, retry handling, concurrency and atomicity. The context shape, including conversation binding, must be reconciled with TV3 before service integration.

The dispatcher loads the TV2-02 schemas and uses the selected operation's result definition. For `get_study_plan`, the returned view kind must also match the requested view. `generate_study_plan` READ remains a provisional internal shape; do not publish it until the group approves it. Runtime needs a JSON Schema Draft 2020-12 validator with format checks (`jsonschema` is used here); no dependency is installed or declared by this patch. A missing or blank server request ID raises `ValueError` because a valid `ToolResult` cannot be constructed without it.

The dispatcher registers a local date-time checker because a bare `FormatChecker` may lack one. It requires an RFC 3339 date-time with `Z` or a numeric offset and validates calendar dates and offset ranges for command and result. Python's datetime rejects leap-second `:60` and year `0000`; those values are not accepted here pending a shared decision. This does not compare timestamps or validate timezone/DST semantics. Other direct consumers of the JSON Schema must enable their own date-time format checker; this dispatcher-local checker does not change them.

An INFO `tool_execution` record exposes only `request_id`, recognized `operation` (otherwise `UNKNOWN`), `outcome`, `error_code`, and `duration_ms` as structured fields. The dispatcher does not include arguments, context, idempotency keys, results or raw exceptions. Runtime logging configuration and formatter are provided by the host; the host must preserve these privacy constraints. If the logging handler fails, the dispatch result or original exception is preserved, so the log may be lost.

## Service integration dependencies

Inject real service callables only after the following interfaces and guarantees are supplied and reviewed; mocks in the tests are not services.

| Operation | Blocking inputs and acceptance needed |
| --- | --- |
| `search_tasks` | TV1: owner-scoped query and pagination interface; tests showing cross-user isolation. TV3: authenticated principal context. |
| `create_task_candidate` | TV1: same-owner candidate persistence and idempotency transaction. TV3: server-verified principal, conversation and message binding; its exact context shape remains open. |
| `confirm_task` | TV1: atomic candidate-to-task promotion, version/uniqueness and idempotency replay/rollback. TV3: verified approval bound to the displayed candidate and version. Service must independently verify both. |
| `set_availability`, `set_busy_interval`, `set_scheduling_preferences` | TV1: owner/version/revision-aware transactional persistence and replay; TV3: verified approval tied to the precise change or merged policy. |
| `generate_study_plan` | TV1: authoritative same-owner inputs, immutable proposal persistence, concurrency and idempotency; TV4: scheduler and validator interfaces; TV3/TV4: agree the still-provisional no-proposal READ shape. |
| `get_study_plan` | TV1: same-owner current/history/proposal read interfaces and associated data. |
| `approve_study_plan`, `reject_study_plan` | TV1: owner-locked atomic transaction, idempotency and rollback; TV3: verified decision and target/version; TV4: approval revalidation against current time and snapshot. Reject must not change the current plan. |

Before a stale decision on a retry, the service must check for the prior idempotent result as required by official v1.1; the TV1 draft's illustrative pseudocode should be reconciled before integration. Complete tests must cover forged approval, cross-user access, stale data, replay after timeout, concurrent requests and rollback. No integration or end-to-end success is implied by the dispatcher tests.

After applying TV2-02 and this patch, run `python -B -m unittest discover -s tests -v` with that runtime available. Mocks test routing and boundary checks only; they do not implement the service or demonstrate authorization, persistence or transaction safety.
