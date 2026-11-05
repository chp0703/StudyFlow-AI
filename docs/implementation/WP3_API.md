# WP3 — FastAPI, authentication and RPC adapter handoff

Implementation owner: Gemini. Sol owns independent acceptance tests and execution.
This handoff does not amend the approved contract. Read `contracts/README.md`,
`contracts/openapi.yaml`, `contracts/service-contract.json`, and
`contracts/schemas/f1.schema.json` first; these supersede older TV2 draft READMEs.

## Scope and current baseline

Implement the eight approved HTTP endpoints and the HTTP/RPC infrastructure
used by WP4. At inspection there is no `backend/app/main.py`, config Settings,
JWT verifier, HTTP RPC client, or real repository wiring. Existing TV2 code is
partial service logic, not a running API. Its `TrustedContext` dataclass and
proposed store evidence methods are not the approved wire `ExecutionContext`.
Use explicit adapters where reusing them; never serialize that dataclass as if
it already matched `f1.schema.json`.

The dispatcher currently loads `validated_command.json` / `tool_result.json`
and older result names. Reconcile validation with approved `f1.schema.json`
definitions; retain one ten-operation allowlist rather than a competing set.

## Frozen executable seam

```python
backend.app.main.create_app(
    settings=None, *, rpc_transport=None, llm_transport=None,
    jwks_transport=None, clock=None,
) -> FastAPI
```

`backend.app.core.config.Settings` accepts lower-snake fields:
`supabase_url`, `supabase_publishable_key`, `supabase_jwt_audience="authenticated"`,
`supabase_jwt_algorithm="ES256"`, `deepseek_api_key`, `deepseek_base_url`,
`deepseek_model`, `rpc_signing_key_id`, `rpc_signing_secret_base64`, and
`cors_origins: list[str]`. Injected transports are HTTPX AsyncBaseTransport-
compatible transports (`httpx.MockTransport` supports both clients). `clock`
returns an aware datetime. Keep actual external HTTP behind these transports,
including JWKS refresh. Own clients through application lifespan and close them.
No business/auth monkeypatch or alternate factory is needed by acceptance tests.

## Endpoint map

| HTTP | Exact request/result definition | Adapter behavior |
|---|---|---|
| POST `/v1/messages` | UserMessage → OrchestratorReply | WP4 persisted source/extraction workflow; not raw tool execution |
| POST `/v1/actions` | ActionRequest → OrchestratorReply | WP4 typed preparation; only five preparation operations |
| POST `/v1/actions/{action_id}/review` | ReviewActionRequest → OrchestratorReply | WP4 explicit review, never implicit approval |
| POST `/v1/decisions` | UserDecision → OrchestratorReply | WP4 exact owner/conversation/action/target/version binding |
| GET `/v1/tasks` | search_tasksResult | `search_tasks` RPC, canonical arguments below |
| GET `/v1/time-windows` | TimeWindowListResult | Read adapter; missing approved persistence seam, see addendum proposal |
| GET `/v1/preferences` | PreferencesResult | Full policy + schedule_revision; missing approved persistence seam |
| GET `/v1/plans` | get_study_planResult | `get_study_plan` RPC, view-specific rules below |

Only expose these routes for F1. No public raw execute, task CRUD, independent
StudyBlock CRUD, internal helper, or caller-supplied principal/approval route.

## Authentication and transport

- Verify the bearer access JWT using Supabase issuer `/auth/v1`, configured
  audience, ES256 allowlist, valid subject UUID, expiry and signature. Fetch
  `/auth/v1/.well-known/jwks.json`; support key rotation and reject unknown keys
  after refresh. Do not trust decoded unsigned claims or caller-selected alg.
- Allocate a fresh server request_id; ignore caller `X-Request-ID` as authority.
  Return the same value in header and response body, including errors/replays.
  GET audit message IDs are fresh server IDs, not persisted approval sources.
- POST JSON is at most 65,536 UTF-8 bytes; text limit is separately 8,000
  characters. Require Content-Type JSON and Idempotency-Key matching the exact
  length/alphabet in the contract. Preserve strict JSON types and reject unknown
  request fields. Do not leak framework validation bodies, SQL or exceptions.
- Error status/code mapping follows README §3.1: malformed JSON/header/query
  parsing or unsupported schema_version 400; missing/invalid JWT 401;
  foreign/nonexistent entity 404; review/stale/approval conflicts 409; oversized
  body 413; invalid JSON fields 422; unallowlisted operation 422
  UNSUPPORTED_OPERATION; temporary dependency faults 503 with Retry-After.
  Query constraint classification beyond parsing is not fully pinned down:
  independent tests allow 400 or 422, always INVALID_PARAMETER. PROPOSAL time
  filters are explicitly 422. GET errors use ErrorResult; every POST error uses
  OrchestratorReply(state=ERROR). 429/503 are retryable; domain review errors are not.
- CORS uses the configured origin allowlist, permits Authorization,
  Idempotency-Key and Content-Type, and exposes X-Request-ID,
  Idempotency-Replayed and Retry-After. New/replayed POSTs return replay false/true.
  Never log JWT, API keys, attestation, message text or full context.

## Read argument normalization

`GET /v1/tasks` sends `{query:null,status_filter:[],page_size:50,cursor:null}`
when omitted. Repeated status_filter keys form the enum array. Max page_size is
100; cursor is opaque, 1–2048 characters. Preserve a supplied cursor exactly;
DB validates owner/filter/sort binding. Tasks sort by `(deadline_at,task_id)`.

`GET /v1/plans` sends all `{view,version,proposal_id,start_at,end_at}` keys,
default CURRENT and nullable other values. CURRENT accepts neither version nor
proposal_id; HISTORY requires version; PROPOSAL requires proposal_id and rejects
time filtering. Range endpoints are both present or both null, end > start.
CURRENT without plan is successful null/[]; absent HISTORY/PROPOSAL is 404.
Time filters use half-open overlap without clipping or mutating stored blocks.

Time-window defaults are kind=null, include_archived=false, page_size=50,
cursor=null; sort `(created_at,window_id)`. Do not pretend the scheduling input
snapshot implements this archived/cursor contract. See the explicit blocker.

## Exact RPC transport and signing

Send POST `{supabase_url}/rest/v1/rpc/<approved routine>` with user request's
`Authorization: Bearer <same JWT>`, publishable `apikey`, JSON Content-Type and
`Content-Profile: app_api`. Build headers per request; never mutate a shared
client Authorization default. The sole JSON argument is `{p_request: RpcRequest}`.
Validate the operation-specific envelope and result. Read envelopes use null
approval, idempotency key and attestation; GET conversation_id is null.

All mutations, including source/action/receipt helpers, require backend signing.
Apply README §6.2 literally: normalize timestamps to UTC, reject unsupported
numeric types, canonical compact UTF-8 JSON with sorted keys, digest entire
envelope excluding attestation, sign unpadded base64url payload using HMAC-SHA256.
Payload contains exactly v=1, key_id, user_id, rpc, request_id, request_digest,
issued_at, expires_at; lifetime 60 seconds. Secret is decoded base64 with at least
32 bytes. Do not forward FE attestation or use service_role. A transport retry
may re-sign with a new time while retaining the stable business request/key.
Keep attestation and request_id out of business fingerprints.

## Gates and unresolved seams

Implement JWT/errors, canonical signing, declared RPC reads and factory wiring
independently now. GET preferences/time-windows and cold-start workflow loading
need approval of the concrete proposal in `INTERNAL_RPC_ADDENDUM_PROPOSAL.md`; do not add its
proposed routines to runtime or approved contracts before authorization.

Run `backend/tests/acceptance_api_sol/` without editing its assertions. Its initial
baseline is a missing-factory setup failure. A mock RPC pass proves adapter
behavior only; WP2 real database security/rollback/concurrency checks and WP4
durable workflows remain separate acceptance gates.
