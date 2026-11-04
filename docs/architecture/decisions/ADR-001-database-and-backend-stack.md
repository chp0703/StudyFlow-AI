# ADR-001 — Database and Backend Stack

**Status: PROPOSED — Pending team approval**  
**Date:** 2026-11-04  
**Scope:** F1 physical implementation

## Context

The official schema v1.1 defines logical contracts but does not approve a database engine or backend framework. The user-preferred evaluation stack is Supabase PostgreSQL, FastAPI, Supabase Data API/RPC, and Supabase CLI.

## Decision

Recommend Supabase PostgreSQL + FastAPI + Supabase Data API/RPC + Supabase CLI. Do not introduce SQLAlchemy or psycopg initially. The Scheduling Engine remains a pure Python component.

## Rationale and trade-offs

PostgreSQL supports the required composite ownership keys, JSONB, constraints, RLS, and atomic functions. Supabase provides an integrated Data API and reproducible local CLI workflow. FastAPI owns HTTP validation and orchestration; PostgreSQL owns durable integrity and atomic writes. The trade-off is Supabase coupling, HTTP latency, and the need to put every multi-table mutation behind one RPC.

## Consequences and tests

The team must approve environments, roles, API exposure, and local tooling before migrations. Test Data API/RPC errors, pagination, retries, RLS, and clean local resets. This ADR does not authorize implementation.

