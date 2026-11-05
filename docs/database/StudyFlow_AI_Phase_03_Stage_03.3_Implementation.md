# StudyFlow AI — Stage 03.3 Implementation Record

Status: implementation branch only (`feat/supabase-database-foundation`)

This stage integrates the reviewed backend contract package and creates a local Supabase migration foundation for F1 schema v1.1. The migration source is the repository `supabase/` directory; no remote project was linked and no production database was contacted.

## Migration order

1. `202611050001_create_core_entities.sql` — `app_private`/`app_api`, `btree_gist`, User profile, TaskCandidate, AcademicTask, and unified TimeWindow.
2. `202611050002_create_planning_and_approval_entities.sql` — immutable StudyPlan/StudyBlock/PlanProposal, PendingAction, ApprovalAction, IdempotencyRecord, and the authorization-only chat attestation table.
3. `202611050003_add_integrity_constraints_and_indexes.sql` — same-owner composite foreign keys, current/source/commit relationships, half-open per-plan overlap exclusion, workload/status checks, and timestamp triggers.
4. `202611050004_enable_rls_and_grants.sql` — forced owner-scoped RLS, private-schema grants, and no public table/function access.
5. `202611050005_create_f1_rpcs.sql` — allow-listed invoker RPC boundary, trusted-owner advisory lock helper, read context/plan functions, mutation wrappers, and service-role-only chat attestation issuance.

## Contract boundary

The exact contract source is `origin/feat/BE_contract_schema` at `b629a5e251be59570a0f719b5596d7d457e2708d`. Only its `contracts/` package was imported. The package metadata declares `PlanProposal.version` as `text`, while logical schema v1.1, physical design, and `f1.schema.json` require an integer-compatible entity version (currently fixed to `1` in JSON). The mapping is resolved as metadata correction: envelope `schema_version` remains `"1.1"`, entity `version` remains numeric, and base-plan/version/revision remain separate fields. No text column is introduced; the backend contract package should correct its metadata in its next revision.

## Security and transaction boundary

- `auth.uid()` is the only runtime owner source; no client/LLM `user_id` is trusted.
- Writers call `pg_advisory_xact_lock` using a deterministic hash of the trusted owner UUID on the same transaction connection before authoritative reads.
- `READ COMMITTED` is the intended protocol isolation; callers must reload inputs after lock acquisition.
- `app_private` is not in the exposed Supabase schema list. Public API access is through allow-listed `app_api` functions.
- CHAT approval issuance is restricted to `service_role`; attestation data is one-time and short-lived. It is not a product TTL.
- The current RPC foundation is intentionally small and requires backend adapter hardening for full idempotency/replay, proposal payload validation, typed approval target validation, and attestation consumption before production use. Until that consumption path is implemented, user-facing mutation RPCs reject a supplied attestation rather than treating it as proof.

## Verification record

The repository has no Supabase CLI, Docker engine, or `psql` executable in the current environment, so `supabase db reset`, `supabase test db`, and migration replay were not run. The Python contract checker was invoked but cannot start because the optional `jsonschema` dependency is not installed. These are explicit blockers, not passing test results.

The pgTAP smoke test in `supabase/tests/03_foundation.sql` is designed for local execution only. No secrets, `.env` files, remote links, or production commands are part of this stage.
