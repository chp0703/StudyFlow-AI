# F1 integration execution log

## Baseline and ownership

- Integration branch: `feat/f1-mvp-intergration`.
- Initial integrated commit: `ad80c484ba0eb07f8b807bcfff54936f596ef57e`.
- Sources: TV1 `f0d079e`, TV2 `c8b4865`, TV3 `431991d`, TV4 `fecb9f9`.
- Approved logical schema v1.1 and integration package 1.0.0 remain authoritative.
- Sol authors independent acceptance tests, performs Git operations, runs checks and reviews changes.
- Gemini 4 Argon High implements work packages through official Antigravity CLI `agy`; Gemini 3.8 Flash High is the quota-exhaustion fallback. CLI 1.5.1 returned a real successful pinned Argon High response on 2026-11-05 using existing Google sign-in, without an API key. Legacy Gemini CLI OAuth returned `UNSUPPORTED_CLIENT`.
- Runtime Gemini is not part of F1: the demo extractor uses DeepSeek.

## Gates

| Gate | Status | Required evidence |
|---|---|---|
| G1 foundation | IN_PROGRESS | Shared contracts, corrected scheduler, secure atomic RPCs, durable task API, real DB migration/security/rollback checks |
| G2 complete F1 | NOT_STARTED | Ten operations/eight endpoints, deterministic workflow, planning/approval/recovery integration |
| G3 live demo | NOT_STARTED | DeepSeek + new Supabase demo project, live acceptance evidence, UI handoff |

Never mark a gate complete from fixture-only checks. Cloud project credentials and a DeepSeek API key are environment inputs; secrets must not enter tracked files.

## Independent evidence so far (2026-11-05)

- Integrated contract checker passed. Existing TV2 suite: 78 tests passed; planner unit suite: 24 tests passed.
- WP1 ACCEPTED for the pure planner/normalizer scope. Initial independent baseline: 29 methods, 8 failures and 40 errors. Two review rounds added archived/enum/malformed-ID cases and a valid DST-fold clock regression (start before actual now; elapsed workload mismatch). Final Argon correction passed all 33 independent methods, 24 planner unit tests, 78 TV2 tests, contract checker and five evaluation cases repeated 100 times with deterministic results and zero hard-constraint violations. A separate Sol review confirmed DST-fold block identity and locked-block retention. This is not DB/API/live-model acceptance.
- Independent HTTP suite contains 29 methods, including completed-receipt replay across cold apps. Runtime app is absent, so setup fails; no HTTP acceptance success is claimed.
- SQL files parse with pglast. Real Supabase CI baseline at commit 2bac72c replayed all eight existing migrations successfully; pgTAP executed 190 assertions with 128 failures: 03=5/18, 04=18/47, 05=36/44, 06=69/81. Missing secure boundary, infrastructure and approved atomic RPCs remain implementation work. Evidence: https://github.com/chp0703/StudyFlow-AI/actions/runs/42032340280 . This does not validate uncommitted scheduler changes or cloud deployment.
- Vietnamese extractor dataset contains 40 validated cases. No live model evaluation has yet run.
- User supplied shared-or-demo Supabase project ref `phomrutsdhdgejlskwcb`; public JWKS responded 200 with an ES256 key. Schema, permissions, migration history and existing data remain unverified. Do not reset or deploy blindly.
- User approved all A/B/C/D in INTERNAL_RPC_ADDENDUM_PROPOSAL.md for package 1.0.1: six internal helpers, continuation infrastructure and signed first-GET profile initialization. Sol freezes independent tests before Gemini synchronizes schemas/mappings/fixtures. Public eight endpoints, ten operations and logical schema 1.1 remain unchanged. Approval does not establish implementation success.

## Handoff checkpoint

The user requested a handoff due approaching quota, not further implementation.
Argon WP0 conversation `dd1d22b6-130b-48fe-91ac-d062172205bd` finished with native
contract edits only. Sol then ran the actual source: the checker fails its valid
checkpoint ADVANCE fixture; 16 independent addendum methods run with two failures
(valid ADVANCE and a completed continuation prefix containing an empty READ list).
Generic ToolResult READ.data.oneOf overlaps SearchTasksData/TimeWindowListData
for empty items. WP0 is NOT accepted or committed; preserve the dirty snapshot.
Do not use the implementer's completion report as evidence of acceptance.
See root BAN_GIAO.md and docs/handoff/ for the continuation plan, prompts and
portable environment instructions. No 009+ migration or API factory exists yet.

## Work packages

### WP1 — scheduler correctness and TimeWindow normalization (TV4)

Status: ACCEPTED. Implementation: initial Antigravity GUI turn, then official
CLI Argon High conversation `8f23a737-bf8b-4ba2-b8d6-b8c4516835ff` with independent
Sol correction/review. Argon performed native edits; Sol ran all tests and Git.
UTC instant arithmetic preserves actual duration and PEP 495 fold while IANA
local-day rules remain local. Full DB/service integration is subsequent work.
Independent scheduler CI also passed at commit 52ee7c8:
https://github.com/chp0703/StudyFlow-AI/actions/runs/42034378754 . The separate
HTTP/1.0.1 contract jobs remain red until their implementation is delivered.

Implementation owner: Argon High. Sol acceptance tests: `backend/tests/acceptance_sol/` (implementer must not edit).

Allowed implementation scope: `backend/app/f1/scheduler/` and `docs/planner/` only. Preserve existing public classes/functions and tests. Add `normalization.py` exposing:

```python
normalize_time_windows(windows, *, start_at, end_at) -> tuple[Interval, ...]
```

`windows` contains normalized TimeWindow JSON dictionaries. Output concrete aware intervals clipped to the requested finite horizon, sorted and merged. Validate the NONE/WEEKLY union, IANA timezone, valid_from inclusive/valid_until exclusive, weekday 1=Monday, minute alignment, and same-local-day policy. WEEKLY end_time `24:00` means next midnight; start_time cannot be 24:00. Invalid/nonexistent/ambiguous local times raise ValueError; never guess DST fold. Ignore archived windows. Distinct AVAILABILITY and BUSY sets are normalized separately by the caller; reject mixed kinds in one invocation rather than merging busy into availability.

Fix independently reproduced defects:

1. Identical snapshot with 60 covered/60 unallocated must remain PARTIAL, no proposal; do not relabel NO_CHANGE.
2. Match exact existing task/start/end/lock before pairing moved blocks, preserving unchanged IDs.
3. Reject zero/negative, naive, non-minute and reversed generated intervals safely.
4. Public result validation must also check retained context; malformed context must return issues without raising unrelated exceptions.
5. Historical retained blocks must not be evaluated against current future daily/break policy or stop new future work. Preserve them in snapshots.
6. Accept aware clock instants with seconds; round potential generated starts upward, never before actual now. Business timestamps remain minute-aligned.

Do not change contract files, acceptance tests, Git state, runtime/API/storage modules, frontend, or dependencies. Use native file editing tools; do not invoke terminals, shell commands, test commands or Git through the app. Sol will run checks and return exact failures. Return changed paths, decisions, limitations and any tests you were able to inspect. Do not claim tests ran without evidence.
