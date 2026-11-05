# Independent real PostgreSQL concurrency acceptance

These are executable `unittest` + psycopg tests, deliberately outside backend
test discovery. **Authored, AST/import checked; database execution NOT_RUN.**
Contract package **1.0.1** and its runtime migrations must be installed first.
The suite refuses an older registry, missing DSN or unavailable prerequisites;
it does not silently skip, mock responses or accept fake success.

Run only after resetting a disposable local Supabase database:

```bash
python -m pip install -r supabase/tests_concurrency/requirements.txt
F1_DB_TEST_DSN='postgresql://postgres:postgres@127.0.0.1:54322/postgres' \
  python -B -m unittest discover -s supabase/tests_concurrency -v
```

Use the actual local connection details printed by the pinned Supabase CLI if
they differ. There is no cloud target or project reference. DSN validation accepts
exactly one explicit `localhost`, `127.0.0.1` or `::1` host, rejects service files,
Unix sockets, remote/multi-host values and non-loopback `hostaddr`, and pins the
connection's numeric loopback address. The account needs migration-level local
fixture privileges. Do not put a cloud DSN in this variable.

The suite creates unique synthetic auth users, cryptographically random test-only
HMAC keys and committed business fixtures. It deliberately leaves rows for the
next ephemeral CI reset: separate committed sessions cannot be cleaned with one
outer rollback. It never deletes application data. Fault triggers/functions are
removed in `finally` blocks. No synthetic secret is printed or checked in.

Every profile/source/candidate/action/task/window/policy/proposal setup mutation
uses a signed approved RPC; domain rows are not administratively fabricated.
Requests and results use the actual shared `contracts.check_contract` validator,
with an independent Python UTF-8 canonical/HMAC signer. Runtime adapters and their
signing implementation are not imported. Datetime fixtures are UTC, minute-aligned,
two days in the future; audit/attestation clocks use actual UTC now.

Two request connections execute `SET LOCAL ROLE authenticated` and transaction-local
JWT claims. This simulates a trusted gateway for PostgreSQL/RLS/transaction tests;
it **does not prove JWT signature verification or live PostgREST authentication**.
The administrative observer only provisions auth/key fixtures, inspects rows,
holds the documented owner row lock, injects the second-block fault, and backdates
the one explicitly described operational lease column.

## Executable scenarios

| Test | Evidence required |
|---|---|
| Same-key confirmation race + lost response | Two queued request sessions return one identical task; one approval/backlink/action completion/revision/domain result; fresh-connection retry returns original data with current request_id. |
| Distinct-key confirmation race | Exactly one promotion; loser `STALE_ENTITY_VERSION`; one task and approval, revision advances once. |
| Competing proposals | Same owner/base, different conversations; exactly one plan and complete blocks, loser durably STALE, pointer/revision advances once; winner replay does not re-commit. |
| Revision-only stale + replay | Approved policy change leaves base pointer unchanged; old proposal approval fails, STALE is visible through a fresh authenticated read, saved error replays without plan writes. Minimal fixture starts with no current plan; an existing-plan-version variant remains additional coverage. |
| Second-block failure | A test-only trigger raises `XX000` after the second actual block INSERT; complete owner-state snapshot is unchanged, error is typed/sanitized, removing fault permits same-key retry. |
| 120-second receipt fencing | Initial lease duration is checked; only mapped `api_request_receipts.lease_until` is backdated; real reclaim increases version/preserves IDs; old worker cannot renew/release/complete; new worker completes and a fresh call replays durable response. |

The race harness holds the actual `user_profiles` row `FOR UPDATE`, coordinates
independent connections with a start barrier, and requires observed
`pg_blocking_pids` paths from **both** request PIDs to that lock holder. A
`OWNER_LOCK_BARRIER` record is emitted as CI evidence. Poll intervals are not
treated as proof. Requests are freshly signed after the Python start barrier,
immediately before SQL. The observer releases within six seconds; an executing
RPC's already-bound signature cannot be refreshed while it waits inside SQL.
Finite barrier/lock/statement/future deadlines prevent indefinite hangs.

Not yet executed/covered here: real wall-clock 120-second expiry, live JWT/HTTP,
full retained/protected snapshot variants, halfway-plan-insert fault, existing-plan
revision-only stale variant, snapshot tearing stress, continuation WAIT/domain
recovery or migrations of an existing populated deployment. See
[the full handoff](../../backend/tests/acceptance_db_sol/README.md). No claim of
passing concurrency or production readiness follows from syntax/fixture checks.

Local dependency metadata used for author checks: psycopg and psycopg-binary
**3.3.8**, jsonschema **4.26.0**. Requirements pin psycopg 3.3.8; shared checker
dependencies remain governed by `contracts/requirements-check.txt`.
