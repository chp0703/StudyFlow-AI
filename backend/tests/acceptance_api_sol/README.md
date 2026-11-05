# Sol public HTTP acceptance tests

Run from the repository root with Python 3.11+ and the backend HTTP dependencies
(`fastapi`, `httpx`, `PyJWT`, `cryptography`, `jsonschema`) installed:

```powershell
python -m unittest discover -s backend/tests/acceptance_api_sol -v
```

The tests call the real `backend.app.main.create_app` factory and
`backend.app.core.config.Settings`. The agreed factory accepts `settings=None`
and keyword-only `rpc_transport`, `llm_transport`, `jwks_transport`, `clock`.
The three transports are HTTPX transports; the clock returns an aware datetime.
Only outbound HTTP is simulated. No auth validator, dispatcher, or business
handler is monkeypatched. Test-only ES256 keys are generated in memory.

Sources: approved `contracts/README.md` sections 2, 3, and 6.2;
`contracts/openapi.yaml`; `contracts/schemas/f1.schema.json`; official
`contracts/examples/valid/search_tasks-result.json`.

Coverage: bearer verification and server identity, method-specific catalog error
envelopes, body/header/query limits, action operation allowlist, RPC envelope and
per-request JWT propagation, request IDs, concurrent user separation, and CORS.
Raw approval operations are rejected with `422 UNSUPPORTED_OPERATION`, per the
approved outside-scope mapping. Unparseable query/header input uses `400`; valid
JSON with invalid fields uses `422`. The source does not settle `400` versus
`422` for query constraint violations such as `page_size=101`, so these cases
accept either while requiring the catalog envelope, `INVALID_PARAMETER`, and
no RPC call. The explicit PROPOSAL time-filter rule remains `422`.

A passing suite proves the HTTP adapter behavior against simulated dependency
responses. It does **not** prove live Supabase ownership/RLS/grants, RPC database
transactions, real DeepSeek extraction, end-to-end approval or idempotency
persistence, deployment rate limits, or production performance. Missing runtime
imports intentionally fail the class setup with an explicit baseline error.

Initial execution on 2026-11-05 loaded all test dependencies, then failed class
setup because `backend.app.main` did not exist (`Ran 0 tests`, one setup error).
This is a failing implementation baseline, not successful runtime validation.
