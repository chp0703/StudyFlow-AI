# ADR-004 — Database Migration Strategy

**Status: PROPOSED — Pending team approval**  
**Created:** 2026-11-04
**Last updated:** 2026-11-05

Decision status and approval state remain authoritative in the [decision register](../../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md), especially E-01, E-04, and E-14. This ADR records migration rationale and safeguards only.

## Recommendation (E-01, E-04, E-14)

Use Supabase CLI as the sole migration source. Commit `supabase/config.toml`, ordered migration files, and non-production seed data. Do not maintain Alembic or dashboard-only changes in parallel.

Recommended dependency order:

1. schemas/extensions and shared functions;
2. user profile and policy;
3. candidate/task entities;
4. unified TimeWindow;
5. proposal/plan entities;
6. StudyBlocks and same-owner constraints;
7. PendingAction, ApprovalAction, IdempotencyRecord;
8. indexes and deletion rules;
9. grants/RLS/schema exposure;
10. RPC functions;
11. seed/test fixtures.

## Consequences and safeguards

Local development is reproducible from a clean reset, while production deployment remains separately authorized. CI must apply migrations to a clean local database and run integrity/RLS/RPC tests. No remote project is linked in this phase.

