# ADR-003 — Data Access and RPC Boundaries

**Status: PROPOSED — Pending team approval**  
**Date:** 2026-11-04

## Decision

FastAPI uses a request-scoped Supabase Data API client or equivalent immutable HTTPX wrapper. No shared mutable client may overwrite Authorization headers between concurrent requests. Ordinary reads may use controlled PostgREST access. Any multi-table business write uses one PostgreSQL RPC call.

Initial RPC inventory:

| Function | Lock | Revision/idempotency |
|---|---:|---|
| `create_task_candidate` | owner lock if write protocol requires | idempotency; revision as applicable |
| `confirm_task` | yes | approval + idempotency + revision |
| `search_tasks` | no | read-only |
| `set_availability` / `set_busy_interval` | yes | approval + idempotency + revision |
| `set_scheduling_preferences` | yes | approval + idempotency + revision |
| `generate_study_plan` persistence step | yes | idempotency; revision compare |
| `get_study_plan` | no | read-only |
| `approve_study_plan` | yes | approval + idempotency + revision |
| `reject_study_plan` | yes | approval/version validation |

RPC functions must not manually commit or roll back inside normal PostgREST execution. The request transaction provides atomicity. The pure scheduler runs outside PostgreSQL and returns data to a persistence RPC.

## Consequences

HTTP latency and pagination must be measured. Independent API calls cannot be treated as one transaction. RPC contracts, grants, and error mapping require integration tests before implementation approval.

