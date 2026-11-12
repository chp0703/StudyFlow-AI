# StudyFlow AI backend

The backend is a FastAPI application implementing the eight public F1 endpoints. It verifies Supabase JWTs, coordinates durable workflows, calls signed database RPCs and uses the deterministic scheduler under `app/f1/scheduler/`.

## Run locally

Start and reset local Supabase, install dependencies, then run the API:

```bash
supabase start
supabase db reset --yes
python -m pip install -r backend/requirements.txt
uvicorn backend.app.main:create_app --factory --port 8000
```

Configure the values in the root `.env.example`. Register a local signing key with `supabase/scripts/register_dev_key.sql`. `POST /v1/messages` requires a DeepSeek key; structured endpoints remain available without one.

## Test

From the repository root:

```bash
python -B contracts/check_contract.py
python -B -m unittest discover -s backend/tests/unit -t . -v
python -B -m unittest discover -s backend/tests/acceptance_sol -v
python -B -m unittest discover -s backend/tests/acceptance_api_sol -v
python -B backend/scripts/evaluate_planner.py
```

The tests in `backend/tests/integration/` require a running local Supabase stack and the environment variables used by `.github/workflows/database-tests.yml`.
