# StudyFlow AI

StudyFlow AI is a student-controlled learning workspace with three connected features: Intelligent Academic Planner, Learning Assessment & Adaptive Revision, and Daily AI Learning.

The repository currently contains the implemented Planner foundation: React frontend, FastAPI backend, deterministic scheduler, shared contract, Supabase migrations and automated acceptance tests. Assessment and Daily Learning are part of the current product scope; their requirements are defined and their implementation remains pending.

## Product scope

| Feature | Purpose | Status |
|---|---|---|
| Intelligent Academic Planner | Tasks, personalized working time, deterministic plans and approval | Foundation implemented |
| Learning Assessment & Adaptive Revision | Verified quizzes, deterministic grading and revision recommendations | Requirements defined |
| Daily AI Learning | Source-grounded explanations, hints and confirmed session outcomes | Requirements defined |

## Repository map

```text
backend/    FastAPI API, workflow orchestration, RPC client, NLU and scheduler
contracts/  Approved OpenAPI, JSON Schema, registries and validation fixtures
docs/       Product, feature and architecture documentation
eval/       Independent Vietnamese NLU acceptance dataset
frontend/   React 19 and Vite application
supabase/   Local configuration, immutable migrations and database tests
worklogs/   Team implementation logs
```

See [docs/README.md](docs/README.md) for the documentation index and
[docs/architecture/overview.md](docs/architecture/overview.md)
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

The current API exposes the eight Planner endpoints declared in `contracts/openapi.yaml`. Authentication uses Supabase JWTs, database access goes through signed RPC envelopes, and the scheduler remains deterministic. The technical `F1` identifiers remain for compatibility with the implemented Planner contract.

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

- Product requirements: [StudyFlow AI requirements](docs/product/requirements.md)
- Feature map: [StudyFlow AI features](docs/features/README.md)
- Planner semantics: [Planner domain schema](docs/features/planner/schema.md)
- Planner HTTP and service boundaries: [contracts/README.md](contracts/README.md)
- Database implementation: [Supabase migrations](supabase/migrations/)

Supabase migrations are append-only history. Do not edit an applied migration; add a new migration instead.
