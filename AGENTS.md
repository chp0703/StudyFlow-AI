# StudyFlow AI Agent Guide

Shared instructions for all team members and coding agents.

## Project

StudyFlow AI has three features: Intelligent Academic Planner, Learning Assessment & Adaptive Revision, and Daily AI Learning. The Planner is currently implemented. UI copy is Vietnamese, and every write requires explicit user confirmation.

- `frontend/`: React 19, Vite 8, strict TypeScript, Tailwind CSS v4
- `backend/`: FastAPI, chat/NLU and deterministic scheduler
- `supabase/`: migrations, pgTAP and concurrency tests
- `contracts/`: shared OpenAPI and JSON schemas
- `docs/`: current product and architecture documentation

## Required skills

Every task must use all three skills:

- [`ponytail`](https://github.com/dietrichgebert/ponytail)
- [`rtk`](https://github.com/rtk-ai/rtk)
- [`graphify`](https://github.com/Graphify-Labs/graphify)

Verify they are available before working. If any skill is missing, install it from the exact repository above or report the blocker clearly instead of silently skipping it. For UI work, also use `ui-ux-pro-max` and follow `frontend/DESIGN.md` first.

## Core rules

- Frontend application data goes through FastAPI; only Supabase Auth may be accessed directly.
- Database writes go through `app_api.*`; validate before writing.
- Chat never approves mutations. Only `POST /v1/decisions` with the unchanged `action_reference` may apply them.
- Treat model output as untrusted data; normalize it in the backend, never weaken contracts.
- Contract changes must update every affected schema, migration, backend handler, frontend mapper and test.
- Contracts and migrations override prose documentation.
- Keep demo mode and API mode working.
- Attachments remain display-only until upload and extraction are implemented and tested.
- Keep unrelated changes out of scope and preserve other contributors' work.

## Workflow

Before editing, read the affected code, nearby tests and relevant docs. Plan cross-layer, contract and migration changes before implementation. Add or update tests for changed behavior.

Use English conventional commit messages and PR titles; write PR descriptions in Vietnamese. Each contributor uses their own verified Git identity. Agents must never add `Co-Authored-By` or AI attribution.

Before every push, update `worklogs/<github-username>.md` using `worklogs/sample.md` and include it in the commit.

## Safety

- Never touch cloud Supabase project `phomrutsdhdgejlskwcb` from an agent workflow.
- Team members handle `supabase login` and linking themselves.
- Never print or commit secrets or `.env*` files.
- Confirm exact targets before destructive Git, filesystem or database operations.

## Verification

Run checks for affected layers only and never claim an unrun check passed.

- Contracts: `python -B contracts/check_contract.py`
- Generated schema: `python -B backend/scripts/generate_contract_schema_migration.py --check`
- Frontend: `npx tsc --noEmit`, Node tests, `npm run build`, `npm run format`
- Backend: unit tests, scheduler/API acceptance tests, planner evaluation
- Database: `supabase db reset`, `supabase test db`, integration and concurrency tests when relevant

Before handoff, summarize changes, test results, unrun checks, risks and follow-up work.

## Key docs

- `docs/README.md`
- `docs/product/requirements.md`
- `docs/features/`
- `docs/architecture/overview.md`
- `contracts/README.md`
- `backend/README.md`
- `frontend/DESIGN.md`
