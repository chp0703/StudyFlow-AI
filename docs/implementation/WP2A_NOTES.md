# WP2a — boundary, infrastructure, helpers (implementation notes)

Migrations 009–012 are additive; 001–008 are untouched. Verified on a local Supabase
(CLI 3.0.0) by replaying from empty and by upgrading from baseline 202611050008.

| Migration | Content |
|---|---|
| 009 | `sf_rpc_owner` (NOLOGIN, NOSUPERUSER, NOBYPASSRLS); tables `rpc_attestation_keys`, `conversation_records`, `source_messages`, `api_request_receipts`, `action_presentations`, `workflow_continuations` with keys, same-owner FKs, checks, immutability trigger, ENABLE/FORCE RLS |
| 010 | `canonical_json`, `verify_rpc_request`, `current_uid`, `error_result`, `security_error`, `rpc_is_read` |
| 011 | Removes legacy overloads, `issue_chat_approval_attestation`, `read_scheduling_context` and the old helpers; moves RLS policies and grants from client roles to `sf_rpc_owner`; 27 fail-closed `app_api` wrappers |
| 012 | Generated `contract_defs`, `matches_contract`, `contract_schema_digest` (pg_jsonschema); regenerate with `backend/scripts/generate_contract_schema_migration.py` |

## Decisions

- `auth.uid()` is not reachable by `sf_rpc_owner` (the auth schema grants are not available to the
  migration role), so policies and the verifier read the same JWT claims through `app_private.current_uid()`.
- Stub wrappers verify the request exactly like the final ones, then return `UNSUPPORTED_OPERATION`.
  They never return success. WP2b/WP2c replace them with `create or replace`.
- `chat_approval_attestations` keeps its rows but has no grants and no policy.

## Privilege draft for `sf_rpc_owner` (refine in WP2b/WP2c)

select+insert+update: user_profiles, task_candidates, time_windows, plan_proposals, pending_actions,
idempotency_records, api_request_receipts, workflow_continuations. select+insert (immutable):
academic_tasks, study_plans, study_blocks, approval_actions, conversation_records, source_messages,
action_presentations. select only: rpc_attestation_keys. No delete anywhere.

## Evidence (local pgTAP)

03, 04, 05, 08 pass fully. 06: canonical/HMAC vectors, verifier negatives, grants and catalog pass; the
12 remaining failures need `record_source_message` and `create_task_candidate` (WP2b). 07: 33 of 58
fail on the six helpers' domain behavior (WP2b). Not run: concurrency harness, real JWT over HTTP.
