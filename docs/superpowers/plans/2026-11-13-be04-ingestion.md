# BE-04 Source Ingestion Implementation Plan

> Execute inline with the test-driven-development and verification workflows.

**Goal:** Import source-backed task and calendar drafts without implicit approval.
**Architecture:** Authenticated uploads, signed source RPCs, leased extraction,
then the existing durable confirmation queue. DeepSeek Flash handles untrusted
document/image interpretation; deterministic parsers handle calendar events.
**Tech Stack:** Existing FastAPI/httpx/jsonschema/PostgreSQL; optional pypdf.
**Spec:** `docs/features/planner/ingestion.md`.

## Global constraints

- Work only on `feat/be-04-source-ingestion`; publish incremental commits.
- Keep existing API, RPC wire version and confirmation behavior compatible.
- Add migrations; never modify applied migrations or the cloud database.
- Use the user's Git identity and update `worklogs/dmh612.md` before each push.
- No source body, key, private URL or provider error body in logs.

## Review focus

1. Foreign-owner/conversation references never reach extraction or the scheduler.
2. Replays and concurrent workers never apply duplicate changes or stale results.
3. Source prompt injection cannot add approval or plan-generation instructions.
4. Malformed calendar dates/recurrence and spoofed uploads fail explicitly.
5. Missing providers, oversized inputs and truncated responses fail closed.

## Tasks

- [x] 1. Publish this scoped design and worklog; verify the clean baseline.
- [x] 2. Write failing parser/provider tests; implement `ingestion/{models,
  document,image,calendar,service}.py`; run source unit tests. Commit and push.
- [x] 3. Write source schema fixtures and RPC tests; extend contracts and add
  source/provenance/lease migration plus a new generated-schema migration. Run
  static contract/schema checks. Commit and push.
- [x] 4. Write failing API/chat tests; wire source endpoints and source IDs into
  existing receipt/confirmation behavior; add FE endpoint DTOs without enabling
  unverified attachment UI. Run unit and API acceptance tests. Commit and push.
- [x] 5. Run the full affected checks, review the branch independently, fix
  material findings with regression tests, and publish the final tested state.

## Progress

- Baseline: 44 backend unit tests passed on 2026-11-13.
- Ruling: use the dedicated clean checkout explicitly prepared by the user;
  creating another worktree would duplicate it without adding isolation.
- Environment: shell DNS blocks GitHub/PyPI. GitHub connector can publish the
  branch; dependency installation and database/live-provider checks may be limited.
- Prerequisites: Ponytail and local Graphify available. Hosted Graphify has no
  indexed repository. RTK is missing and cannot be downloaded with current shell
  networking; use bounded native command output and report this limitation.

## Verified handoff

- Integrated the current BE-01/02/03 baseline `c7b93f8` from PR #37 without rewriting
  the published BE-04 commits. Production code verified at `21c7c23`.
- Local: 75 unit tests including real PDF extraction, 35 scheduler acceptance,
  16 contract-addendum checks and all 36 frontend Node tests passed. Contract and
  generated-migration checks passed; planner evaluation remained deterministic
  with zero hard-constraint violations.
- [Backend CI](https://github.com/chp0703/StudyFlow-AI/actions/runs/43435790211):
  all groups passed, including 31 existing HTTP tests and 7 source HTTP/handler tests.
- [Database CI](https://github.com/chp0703/StudyFlow-AI/actions/runs/43435790209):
  clean migration replay, 500 pgTAP checks, upgrade-route verification, 12 HTTP
  integration tests and 6 real-PostgreSQL concurrency tests passed.
- Independent review's numeric/canonicalization and calendar-width findings were
  reproduced with failing tests, fixed, and verified green. Cancellation enum
  case handling was treated as a functional scheduling issue and fixed as well.
- Ruling: when source IDs are supplied, text is annotation only. This prevents
  source import from smuggling planning or approval instructions; users request
  a plan separately after confirming imports. The tradeoff is a separate message.
- No paid-provider live test, frontend build/typecheck or attachment-UI activation
  was performed. Provider tests replace HTTP transport; the source endpoint DTOs
  are ready for FE integration. Recurring ICS events and scanned PDFs remain
  explicitly unsupported; scanned pages can be supplied as supported images.
