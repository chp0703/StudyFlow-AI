# StudyFlow AI backend

The backend is a FastAPI application implementing the eight public Planner endpoints. It verifies Supabase JWTs, coordinates durable workflows, calls signed database RPCs and uses the deterministic scheduler under `app/f1/scheduler/`. The `f1` package name is a compatibility path for the existing Planner implementation; Assessment and Daily Learning are additional product features that are not implemented here yet.

## Source ingestion (BE-04)

The additive source API and its limits are documented in
[`contracts/INGESTION.md`](../contracts/INGESTION.md). It adds upload, private
source reads and explicit extraction to the eight existing Planner endpoints.
Source IDs may then be attached to a chat message to enter the existing approval
queue. Upload/extraction alone never creates tasks, imports busy intervals or
generates a plan. With source IDs, message text is an annotation; request planning
separately after approving imports.

Use the existing `DEEPSEEK_API_KEY` and `DEEPSEEK_BASE_URL` environment variables.
`INGESTION_MODEL` defaults to `deepseek-flash`; the existing NLU model setting is
independent. Thinking is disabled for extraction, output is capped at 2,048 tokens,
and paid extraction is never automatically retried. Set secrets locally, not in Git.
Install updated backend requirements for text-PDF support. Calendar parsing needs
no paid API; scanned PDF pages must be uploaded as images in this version.

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
