# StudyFlow AI architecture overview

This document describes the code that currently exists and its runtime relationships. It is not a proposed directory tree.

StudyFlow AI's product boundary includes Planner, Assessment & Adaptive Revision, and Daily AI Learning. The runtime below is the implemented Planner foundation; the other two modules are current delivery scope but are not yet wired into this runtime.

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
    |                         +--> deterministic Planner scheduler
    |
    +--> clients/rpc.py --> signed app_api RPC --> Supabase/PostgreSQL
```

The HTTP layer verifies the user JWT and creates server-owned request context. The workflow layer prepares and reviews actions. Database mutations are performed through approved RPCs and retain PostgreSQL transaction boundaries. The scheduler is pure and does not authenticate users or persist plans.

## Product-level module boundaries

```text
Student web application
        |
Shared authentication, orchestration and authorized source access
        |
        +--> Intelligent Academic Planner
        +--> Learning Assessment & Adaptive Revision
        +--> Daily AI Learning
        |
Shared academic records with feature-owned domain entities
```

Planner is implemented in the current runtime. Assessment owns quiz and revision records. Daily Learning owns learning sessions and confirmed outcomes. Cross-feature handoffs are typed proposals; no module may silently modify another feature's confirmed state.

## Top-level directories

| Path | Responsibility |
|---|---|
| `backend/app/api/v1/` | Current Planner HTTP endpoints and workflow adapter |
| `backend/app/orchestrator/` | Durable receipt, action and chat workflow steps |
| `backend/app/clients/rpc.py` | Approved RPC transport and request signing |
| `backend/app/core/` | Configuration, contract validation and JWT verification |
| `backend/app/f1/scheduler/` | Deterministic Planner implementation; path retained for compatibility |
| `backend/app/nlu/` | Untrusted extraction and evaluation |
| `backend/tests/` | Unit, independent acceptance and local integration tests |
| `contracts/` | Approved OpenAPI, schema bundle, registries and fixtures |
| `frontend/` | React/Vite user interface and API adapters |
| `supabase/migrations/` | Append-only database history |
| `supabase/tests/` | pgTAP database behavior and security tests |
| `supabase/tests_concurrency/` | Real-PostgreSQL transaction and concurrency tests |
| `eval/` | Held-out NLU acceptance data |

## Sources of truth

Product scope and feature boundaries are defined in `docs/product/requirements.md`. The implemented Planner model is defined in `docs/features/planner/schema.md`. Machine-readable Planner HTTP, service and data contracts live in `contracts/`. Physical database behavior is defined by the ordered migrations and verified by database tests.

Historical proposals and parallel draft dispatcher/service implementations have been removed so that the repository exposes one current runtime path.
