# F1 integration execution log

## Baseline and ownership

- Integration branch: `feat/f1-mvp-intergration`.
- Initial integrated commit: `ad80c484ba0eb07f8b807bcfff54936f596ef57e`.
- Sources: TV1 `f0d079e`, TV2 `c8b4865`, TV3 `431991d`, TV4 `fecb9f9`.
- Approved logical schema v1.1 and integration package 1.0.0 remain authoritative.
- Sol authors independent acceptance tests, performs Git operations, runs checks and reviews changes.
- Gemini 4 Argon High implements work packages through Antigravity; Gemini 3.8 Flash High is the quota-exhaustion fallback.
- Runtime Gemini is not part of F1: the demo extractor uses DeepSeek.

## Gates

| Gate | Status | Required evidence |
|---|---|---|
| G1 foundation | IN_PROGRESS | Shared contracts, corrected scheduler, secure atomic RPCs, durable task API, real DB migration/security/rollback checks |
| G2 complete F1 | NOT_STARTED | Ten operations/eight endpoints, deterministic workflow, planning/approval/recovery integration |
| G3 live demo | NOT_STARTED | DeepSeek + new Supabase demo project, live acceptance evidence, UI handoff |

Never mark a gate complete from fixture-only checks. Cloud project credentials and a DeepSeek API key are environment inputs; secrets must not enter tracked files.

## Work packages

### WP1 — scheduler correctness and TimeWindow normalization (TV4)

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
