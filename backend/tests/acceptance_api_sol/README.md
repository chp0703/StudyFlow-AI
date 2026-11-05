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
Two approved-receipt scenarios start distinct cold application instances against
an externally retained COMPLETED receipt: replay of preparation and replay of a
terminal review-required decision error. They check replay precedes any new
extraction/domain call, stable fingerprints, fresh response IDs, and exact HMAC
attestation/digest/60-second signing on claim_api_receipt. They do not assert that
the mock database established ownership or review state.
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

The original HTTP suite reached 29 discoverable tests with the same explicit
missing-factory baseline. After user approval of A/B/C/D, one signed first-GET
preferences/bootstrap case raises the HTTP count to 30. It requires the approved
ensure_user_context helper; no mocked profile defaults stand in for its result.

The approved 1.0.1 context/bootstrap addition also permits each task read to make
either just search_tasks, or one signed ensure_user_context followed by
search_tasks. This changes the former single-RPC expectation because the user
approved authoritative profile loading before reads. Each outbound call still
checks the exact user JWT/principal/profile header; bootstrap checks HMAC/digest,
and task reads keep canonical argument validation. A second bootstrap, reversed
order or unknown RPC fails. Concurrent owner isolation remains asserted. Cold
COMPLETED POST receipt replay is still strictly claim_api_receipt-only.

`test_contract_addendum.py` separately contains 16 static acceptance methods for
approved package 1.0.1/logical schema 1.1. It reads the actual contracts and their
existing `validate_instance`/pure semantic checker. Full representative positive
and negative JSON payloads are in `fixtures/`. Continuation digests and stable
step keys in those fixtures are derived from the approved canonical formulas;
the RPC-envelope signature used in static shape tests is explicitly fake and is
never sent to a service. These tests introduce no substitute schema/validator.

```powershell
python -m unittest discover -s backend/tests/acceptance_api_sol -p test_contract_addendum.py -v
python -m unittest discover -s backend/tests/acceptance_api_sol -p test_http_contract.py -v
```

Frozen contract baseline before Gemini WP0: 16 methods ran, two passed (unchanged
public scope and existing bundle validity); 35 failing subcases reported absent
approved helper/record definitions and the old 1.0.0 version/inventory. Failing
subcases are not 35 separate test methods. No implementation success is claimed.
