# StudyFlow AI

StudyFlow AI is a student-controlled academic planning assistant. It turns confirmed tasks, availability and scheduling preferences into reviewable study plans. A plan is persisted only after explicit user approval.

The repository contains the React frontend, FastAPI backend, deterministic scheduler, shared F1 contract, Supabase migrations and automated acceptance tests.

## Repository map

```text
backend/    FastAPI API, workflow orchestration, RPC client, NLU and scheduler
contracts/  Approved OpenAPI, JSON Schema, registries and validation fixtures
docs/       Current product, architecture, database and planner documentation
eval/       Independent Vietnamese NLU acceptance dataset
frontend/   React 19 and Vite application
supabase/   Local configuration, immutable migrations and database tests
worklogs/   Team implementation logs
```

See [docs/README.md](docs/README.md) for the documentation index and
[docs/architecture/StudyFlow_AI_Repo_Structure.md](docs/architecture/StudyFlow_AI_Repo_Structure.md)
for the current runtime map.

## Prerequisites

- Python 3.11 or newer
- Node.js and npm
- Supabase CLI 3.0.0 for database and integration tests

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Copy `frontend/.env.example` to a local environment file when connecting the UI to the API. Without API variables, supported demo flows use local fallback data.

Build the production bundle with `npm run build`.

## Backend API

Install dependencies and start the local Supabase stack:

```bash
python -m pip install -r backend/requirements.txt
supabase start
supabase db reset --yes
uvicorn backend.app.main:create_app --factory --port 8000
```

Configure the variables documented in [.env.example](.env.example). Register a local RPC signing key using
`supabase/scripts/register_dev_key.sql`. Keep signing secrets and API keys outside Git.

The API exposes the eight F1 endpoints declared in `contracts/openapi.yaml`. Authentication uses Supabase JWTs, database access goes through signed RPC envelopes, and the scheduler remains deterministic.

## Verification

Run commands from the repository root:

```bash
python -B contracts/check_contract.py
python -B -m unittest discover -s backend/tests/unit -t . -v
python -B -m unittest discover -s backend/tests/acceptance_sol -v
python -B -m unittest discover -s backend/tests/acceptance_api_sol -v
python -B backend/scripts/evaluate_planner.py

cd frontend
npm run build
```

Database, integration and concurrency suites require the local Supabase stack:

```bash
supabase test db
python -B -m unittest discover -s backend/tests/integration -t . -v
python -B -m unittest discover -s supabase/tests_concurrency -v
```

## Sources of truth

- Business semantics: [F1 schema v1.1](docs/database/schema_F1.md)
- HTTP and service boundaries: [contracts/README.md](contracts/README.md)
- Database mapping: [database baseline v1.1](docs/database/StudyFlow_AI_Database_Design_Baseline_v1.1.md)
- Product requirements: [SRS Markdown](docs/srs/StudyFlow_AI_Software_Requirements_Specification_v1.0_Draft.md)

Supabase migrations are append-only history. Do not edit an applied migration; add a new migration instead.
