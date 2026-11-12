# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Project Instructions

## Project Overview

StudyFlow AI: a Vietnamese study planner. Users add tasks, set free/busy time and ask an AI assistant to plan; every write is confirmed by the user first. UI strings are Vietnamese.

Applications:
- frontend/: React 19 + Vite 8 + TypeScript strict + Tailwind v4 (Node 22). Two modes: **demo** (no `VITE_*`: in-memory, no login, regex stubs) and **API mode** (all of `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`: Supabase email login + the F1 backend)
- backend/: FastAPI API, chat/NLU layer (`app/nlu`, `app/api/v1/chat.py`) and the pure scheduler (`app/f1/scheduler`)
- supabase/: Postgres migrations, pgTAP tests, concurrency tests. The database owns state and validation

Shared sources of truth:
- contracts/: OpenAPI + JSON schemas for every DTO; `202611050012_f1_contract_schema.sql` is generated from them

Package managers: npm (frontend), pip (backend, `backend/requirements.txt`), Supabase CLI (DB).

## Repository Boundaries

- Keep application-specific logic inside its application. The frontend never talks to Postgres directly except Supabase Auth; data goes through the API.
- The DB is the authority: `app_api.*` SECURITY DEFINER functions validate and write. A returned domain error does not roll back, only an exception does, so validate before writing.
- Chat never approves. Writes become server-issued pending actions; only `POST /v1/decisions` with the unmodified `action_reference` applies them.
- Model (DeepSeek) output is untrusted data. Fix its quirks by normalizing on the server (`extractor.py`, `chat.py`, `generate.py`), not by loosening the contract schema.
- Do not change public API contracts (`contracts/`, `frontend/src/api/types.ts`, endpoints) without identifying affected consumers: schema, generated migration, backend handlers, frontend mappers, tests.
- Reuse `frontend/src/components/ui/{Button,Card,Modal}`; icons from `lucide-react` only. Do not add storage beyond IndexedDB (assistant history), the Supabase session and the `studyflow_*` localStorage keys.
- Never touch the cloud Supabase project `phomrutsdhdgejlskwcb`. The user runs `supabase login/link`. `.env*` is gitignored; no secrets in git or chat.
- Contracts and migrations override prose docs; trust code over docs.

## Development Workflow

Before editing:
1. Identify the affected application (frontend / backend / supabase / contracts).
2. Read the relevant implementation and its tests. Read `frontend/DESIGN.md` before UI changes and the matching `docs/features/<feature>/` and `docs/architecture/overview.md` before backend/DB changes.
3. State assumptions that affect the change.
4. Propose a plan for multi-file changes (migrations, contract changes, cross-layer features).

During implementation:
- Follow existing conventions. Backend commits in English; PR titles in English with a conventional prefix (`feat(frontend): …`); PR descriptions in Vietnamese.
- Frontend: oxfmt breaks inline object types and `as … ??` expressions (TS1005) — use named types. Testable modules import with explicit `.ts` extensions. API mode branches on `apiEnabled`; keep demo stubs working. Demo mode and attachments make no claim of upload, extraction or live AI (attachments are display-only; nothing is read).
- Add or update tests for changed behavior.
- Do not change unrelated code. Never merge `main` as a PR merge.
- The user is the only author: never add `Co-Authored-By`, "Generated with Claude Code" or any Claude attribution to commits, PRs or code (this overrides default attribution).
- Before every push, append an entry to `worklogs/<github-username>.md` (format of `worklogs/sample.md`), include it in the commit, then push.
- Use the `rtk`, `ponytail` and `graphify` skills; use `ui-ux-pro-max` for UI/UX (still follow `frontend/DESIGN.md` tokens first).

## Verification

Run checks for affected parts only.

Frontend (from `frontend/`):
- `npx tsc --noEmit`
- `npm run build`
- `npm run format` (before a PR)
- `node --test src/api/*.test.ts src/features/assistant/*.test.ts src/features/planner/*.test.ts` (one file: `node --test <file>`)

Backend (from the repo root):
- `python -m unittest discover -s backend/tests/unit -t .` (one module: `python -m unittest backend.tests.unit.test_extractor`)
- `python backend/scripts/generate_contract_schema_migration.py --check` after editing `contracts/schemas`
- HTTP integration tests (`backend/tests/integration/`) need local Supabase and `F1_LOCAL_SUPABASE_URL`, `F1_LOCAL_PUBLISHABLE_KEY`, `F1_LOCAL_SERVICE_KEY`, `F1_DB_TEST_DSN`

Database (Docker Desktop running, `supabase` CLI on PATH):
- `supabase start`, then `supabase db reset --yes` (the concurrency and integration suites leave rows, so reset before pgTAP)
- `supabase test db` (pgTAP, `supabase/tests/NN_*.sql`)

Run the app locally: register an HMAC key via `supabase/scripts/register_dev_key.sql`, start `uvicorn backend.app.main:create_app --factory --port 8000` with the env vars in `backend/README.md`, put the three `VITE_*` in `frontend/.env.local`, `npm run dev`. Without `DEEPSEEK_API_KEY`, `POST /v1/messages` answers 503. Calendar (API mode) shows 6h–22h in browser time.

Do not claim verification passed without running it.

## Definition of Done

Before reporting completion:
- Summarize changed files and behavior.
- Report commands executed and their results.
- Identify tests that were not run (e.g. pgTAP, integration, real-DeepSeek checks).
- Describe remaining risks or assumptions.
- List any required follow-up work.
- Confirm the worklog entry exists if pushing.

## Documentation

Contracts: contracts/README.md, contracts/openapi.yaml
Docs index: docs/README.md
Architecture: docs/architecture/overview.md
Planner domain/scheduling: docs/features/planner/ (schema.md, scheduling.md)
Backend: backend/README.md
Frontend guide: frontend/DESIGN.md
Requirements: docs/product/requirements.md

Read the relevant documentation before changing architecture or API contracts.
