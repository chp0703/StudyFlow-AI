# ADR-002 — Authentication and Runtime Authorization

**Status: ACCEPTED — Unified Integration Contract 1.0.0, IC-05**
**Created:** 2026-11-04
**Last updated:** 2026-11-05

Accepted effective 05/11/2026 through the [official contract, section 6](../../../contracts/README.md#6-rpc-quyền-và-nguồn-request) and [approval record](../../../contracts/APPROVAL.md). The [decision register](../../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md) tracks scope under E-02/E-05/E-06. The accepted decision below supersedes the earlier INVOKER preference and open Option A/Option B recommendation; formal SRS reconciliation under E-12 remains separate.

## Context

Schema v1.1 requires ownership from a trusted backend principal. No authentication or backend exists in the repository.

## Decision (E-02, E-05, E-06)

Use Supabase Auth. The frontend obtains a user access JWT; FastAPI verifies signature, issuer, audience, expiration, subject, and signing-key selection; FastAPI forwards the request-scoped JWT to the Supabase Data API. LLM output and browser owner fields never authorize access. The logical User maps to `app_private.user_profiles`, keyed by `auth.users.id`.

Use asymmetric JWKS verification where available. Do not hardcode signing secrets or trust an unverified decoded token. Use separate migration/admin credentials, never for ordinary user-scoped requests.

## Direct RPC trust boundary (R-04)

The accepted boundary is **user JWT plus backend HMAC attestation for every mutation RPC**. Forwarding the JWT alone is insufficient proof of backend origin. Every wrapper independently checks owner, targets/versions, state, approval evidence, idempotency and business constraints.

`authenticated` may EXECUTE only allowlisted wrappers in `app_api`. A direct caller with the frontend JWT cannot mutate without a valid backend attestation. No separate privileged backend user role or service-role shortcut is selected.

Attestation binds the verified user, RPC, request ID and digest of the complete normalized request, including arguments, trusted context, approval and generated proposal payload where applicable. Use the exact HMAC format, key lifecycle, 60-second validity and 5-second clock-skew allowance in the official contract. Tokens are server-only; token expiry never expires a business draft/action/proposal.

UI/CHAT approvals originate from authenticated decisions and stored user messages bound to a server-issued presentation and target/version. Client-supplied CHAT provenance or LLM approval booleans are insufficient. CHAT attestation is part of the accepted boundary; the verifier and message/presentation persistence still require implementation and runtime tests.

## Physical schema exposure and grants (R-05, R-11)

`app_private` is the unexposed schema for business tables and internal objects. `app_api` exposes only approved wrappers. These physical names do not change logical schema v1.1.

Use controlled **SECURITY DEFINER** wrappers owned by `sf_rpc_owner`: NOLOGIN, NOSUPERUSER, NOBYPASSRLS, minimal touched-table grants, `search_path=''` and fully qualified names. Do not grant this role or private-table privileges to `authenticated`. PUBLIC/anon cannot EXECUTE wrappers or private helpers. Explicit checks compare ownership with `auth.uid()`.

Enable and FORCE RLS on tables. Business-table policies for `sf_rpc_owner` use `auth.uid()`; the global private attestation key store has its separately role-restricted policy as specified in data-contract.json.security_support. Exact SQL grants and policies are implementation deliverables that must conform to this accepted model and have a touched-table matrix per wrapper.

## RLS and schema exposure

Ordinary users receive schema USAGE/EXECUTE on allowlisted API entry points, with no private-table DML/SELECT/USAGE. Approved wrapper privileges and RLS are separate controls; neither schema exposure nor EXECUTE substitutes for correct owner checks. Every write helper, including source messages, receipts, presentations and proposals, follows the attestation boundary; no bypass writer is allowed.

## Consequences and tests

Runtime roles, JWT forwarding, schema exposure and the policy model are accepted within IC-05. Test invalid/expired/rotated tokens, forged/expired/wrong-user/wrong-routine attestations, cross-user reads/writes, leaked headers, request-client isolation and unauthorized direct RPC invocation. Design approval is not proof these tests passed; track runtime evidence in contracts/acceptance-cases.md.

