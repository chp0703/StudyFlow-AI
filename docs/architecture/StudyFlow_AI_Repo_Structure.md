# StudyFlow AI repository structure

This document describes the code that currently exists and its runtime relationships. It is not a proposed directory tree.

## Runtime flow

```text
React frontend
    |
    | HTTP /v1, Supabase access token
    v
backend/app/main.py
    |
    v
backend/app/api/v1/routes.py
    |
    +--> workflow.py --> orchestrator/{receipts,actions,chat}.py
    |                         |
    |                         +--> NLU extractor
    |                         +--> deterministic F1 scheduler
    |
    +--> clients/rpc.py --> signed app_api RPC --> Supabase/PostgreSQL
```

The HTTP layer verifies the user JWT and creates server-owned request context. The workflow layer prepares and reviews actions. Database mutations are performed through approved RPCs and retain PostgreSQL transaction boundaries. The scheduler is pure and does not authenticate users or persist plans.

## Top-level directories

| Path | Responsibility |
|---|---|
| `backend/app/api/v1/` | Eight public F1 HTTP endpoints and workflow adapter |
| `backend/app/orchestrator/` | Durable receipt, action and chat workflow steps |
| `backend/app/clients/rpc.py` | Approved RPC transport and request signing |
| `backend/app/core/` | Configuration, contract validation and JWT verification |
| `backend/app/f1/scheduler/` | Deterministic planning, constraints and replanning |
| `backend/app/nlu/` | Untrusted extraction and evaluation |
| `backend/tests/` | Unit, independent acceptance and local integration tests |
| `contracts/` | Approved OpenAPI, schema bundle, registries and fixtures |
| `frontend/` | React/Vite user interface and API adapters |
| `supabase/migrations/` | Append-only database history |
| `supabase/tests/` | pgTAP database behavior and security tests |
| `supabase/tests_concurrency/` | Real-PostgreSQL transaction and concurrency tests |
| `eval/` | Held-out NLU acceptance data |

## Sources of truth

The logical business model is defined by `docs/database/schema_F1.md`. Machine-readable HTTP, service and data contracts live in `contracts/`. Physical database behavior is defined by the ordered migrations and verified by database tests.

Historical proposals and parallel draft dispatcher/service implementations have been removed so that the repository exposes one current runtime path.
