# StudyFlow AI backend

The first implemented backend component is the pure F1 scheduling engine at
`app/f1/scheduler/`. It has no database, framework, authentication, or LLM
dependency. Application and persistence layers can therefore integrate it
without coupling business rules to infrastructure.

## Run the API locally

Needs the local Supabase stack (`supabase start`, `supabase db reset --yes`) and `pip install -r backend/requirements.txt`.

1. Register a signing key for the backend (generate 32+ random bytes, keep the secret out of Git):
   `supabase/scripts/register_dev_key.sql` shows the insert into `app_private.rpc_attestation_keys`.
2. Export the variables from `.env.example` (`SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `RPC_SIGNING_KEY_ID`,
   `RPC_SIGNING_SECRET_BASE64`, `CORS_ORIGINS`; add `DEEPSEEK_API_KEY` for chat). Without a DeepSeek key `POST /v1/messages` answers
   503 and the structured endpoints keep working.
3. `uvicorn backend.app.main:create_app --factory --port 8000`

The frontend then needs `VITE_API_BASE_URL=http://localhost:8000`, `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`
(see `frontend/.env.example`).

## Run scheduler tests

From the repository root:

```bash
python3 -m unittest discover -s backend/tests -v
```

Run the deterministic fixture evaluation:

```bash
python3 backend/scripts/evaluate_planner.py
```

See [`../docs/planner/scheduling_rules.md`](../docs/planner/scheduling_rules.md)
for the supported rules and integration boundary.
