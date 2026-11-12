# ADR-001 — Database and Backend Stack

**Status: ACCEPTED — Unified Integration Contract 1.0.0**
**Created:** 2026-11-04
**Last updated:** 2026-11-05
**Scope:** Planner physical implementation within the three-feature product

Accepted effective 05/11/2026 through the [official contract](../../../contracts/README.md) and [approval record](../../../contracts/APPROVAL.md). The implementation is represented by the current backend and append-only Supabase migrations.

## Context

The official schema v1.1 defines logical contracts. The team-approved integration contract 1.0.0 supplies the concrete stack: Supabase PostgreSQL, FastAPI, Supabase Data API/RPC, and Supabase CLI. Logical schema v1.1 remains unchanged.

## Decision

Use Supabase PostgreSQL + FastAPI + Supabase Data API/RPC + Supabase CLI. Do not introduce SQLAlchemy or psycopg initially. The Scheduling Engine remains a pure Python component. Follow the approved shared schemas and API/Service/Data boundaries.

## Rationale and trade-offs

PostgreSQL supports the required composite ownership keys, JSONB, constraints, RLS, and atomic functions. Supabase provides an integrated Data API and reproducible local CLI workflow. FastAPI owns HTTP validation and orchestration; PostgreSQL owns durable integrity and atomic writes. The trade-off is Supabase coupling, HTTP latency, and the need to put every multi-table mutation behind one RPC.

## Consequences and tests

Runtime role/API exposure decisions are accepted within contract IC-05. Concrete environments, tool versions, local/CI setup and formal SRS reconciliation remain separate work tracked by E-12/E-14. Test Data API/RPC errors, pagination, retries, RLS, and clean local resets during implementation. This approval does not authorize remote deployment or claim that these checks have run.

