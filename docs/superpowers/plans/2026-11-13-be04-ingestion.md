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

- [ ] 1. Publish this scoped design and worklog; verify the clean baseline.
- [ ] 2. Write failing parser/provider tests; implement `ingestion/{models,
  document,image,calendar,service}.py`; run source unit tests. Commit and push.
- [ ] 3. Write source schema fixtures and RPC tests; extend contracts and add
  source/provenance/lease migration plus a new generated-schema migration. Run
  static contract/schema checks. Commit and push.
- [ ] 4. Write failing API/chat tests; wire source endpoints and source IDs into
  existing receipt/confirmation behavior; add FE endpoint DTOs without enabling
  unverified attachment UI. Run unit and API acceptance tests. Commit and push.
- [ ] 5. Run the full affected checks, review the branch independently, fix
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
