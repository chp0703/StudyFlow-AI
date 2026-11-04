# ADR-001 — Database and Backend Stack

**Status: PROPOSED — Pending team approval**  
**Created:** 2026-11-04
**Last updated:** 2026-11-05
**Scope:** F1 physical implementation

The decision status and approval owner are maintained in the [Phase 03 decision register](../../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md), especially E-01, E-03, and E-04. This ADR records rationale and constraints only.

## Context

The official schema v1.1 defines logical contracts but does not approve a database engine or backend framework. The user-preferred evaluation stack is Supabase PostgreSQL, FastAPI, Supabase Data API/RPC, and Supabase CLI.

## Recommendation

Recommend Supabase PostgreSQL + FastAPI + Supabase Data API/RPC + Supabase CLI. Do not introduce SQLAlchemy or psycopg initially. The Scheduling Engine remains a pure Python component.

## Rationale and trade-offs

PostgreSQL supports the required composite ownership keys, JSONB, constraints, RLS, and atomic functions. Supabase provides an integrated Data API and reproducible local CLI workflow. FastAPI owns HTTP validation and orchestration; PostgreSQL owns durable integrity and atomic writes. The trade-off is Supabase coupling, HTTP latency, and the need to put every multi-table mutation behind one RPC.

## Consequences and tests

The team must approve environments, roles, API exposure, and local tooling before migrations. Test Data API/RPC errors, pagination, retries, RLS, and clean local resets. This ADR does not authorize implementation. See register E-01, E-03, and E-04 for unresolved status and approvers.

