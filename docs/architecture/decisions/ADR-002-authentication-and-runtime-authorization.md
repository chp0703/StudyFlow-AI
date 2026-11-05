# ADR-002 — Authentication and Runtime Authorization

**Status: PROPOSED — Pending team approval**  
**Created:** 2026-11-04
**Last updated:** 2026-11-05

Decision status, owner, and approval state are authoritative in the [decision register](../../database/StudyFlow_AI_Phase_03_Implementation_Decision_Register.md), especially E-02, E-05, E-06, and E-12. This ADR records rationale and security constraints only.

## Context

Schema v1.1 requires ownership from a trusted backend principal. No authentication or backend exists in the repository.

## Recommendation (E-02, E-05, E-06)

Recommend Supabase Auth as the authentication candidate. The frontend obtains a user access JWT; FastAPI verifies signature, issuer, audience, expiration, subject, and signing-key selection; FastAPI forwards the request-scoped JWT to the Supabase Data API. LLM output and browser owner fields never authorize access.

Use asymmetric JWKS verification where available. Do not hardcode signing secrets or trust an unverified decoded token. Use separate migration/admin credentials, never for ordinary user-scoped requests.

## Direct RPC trust boundary (R-04)

Two alternatives were evaluated:

**Option A — user-authorized database RPC (`PROPOSED`).** Authenticated users receive EXECUTE only on explicitly approved `app_api` mutation functions. Each function independently validates owner, target, version, state, approval evidence, idempotency, and business constraints. A user's JWT supplies the PostgREST `authenticated` role and RLS context. FastAPI remains the normal gateway, but it is not a security boundary by itself because a user may invoke an allowed RPC directly.

**Option B — backend-only mutation RPC (`PROPOSED alternative`).** Revoke mutation EXECUTE from frontend roles and use a separate trusted backend identity or signed backend-origin mechanism. Forwarding the same frontend JWT does not prove that FastAPI originated the call. A privileged identity may bypass RLS, so every RPC must still enforce owner, target, and version checks. A service-role secret must not be used as an undocumented shortcut.

**Recommendation:** Option A is `PROPOSED` for F1 because it preserves the caller's RLS context and avoids introducing an unapproved privileged backend identity. This means every exposed mutation RPC is itself an authenticated API boundary. Direct-RPC tests must attempt forged targets, cross-user IDs, invalid versions, forged approval claims, invalid payloads, and idempotency conflicts.

## Approval provenance (R-04)

Direct user RPC approval may record a `UI` decision only where the RPC call is itself the user's explicit decision action and verifies authenticated owner, exact target, expected target version, state/context, and a server-derived presentation/content binding. The client must not establish approval by supplying `source='CHAT'`, `source_message_id`, an arbitrary context ID, or an LLM-produced boolean.

Under Option A, direct authenticated RPC approval is restricted to UI origin. CHAT-origin approval requires a separately authenticated backend-attestation mechanism that binds verified user, conversation/message, target/version, decision, expiry, and anti-replay identifier; the attestation must be verified by the RPC. This mechanism is not yet approved, so ordinary authenticated callers cannot submit CHAT approval and CHAT approval is rejected until E-05 is resolved.

## Physical schema exposure and grants (R-05, R-11)

`app_private` is the proposed unexposed schema for business tables and internal objects. `app_api` is the proposed exposed schema for approved read endpoints and RPC functions. These are physical names only and do not change schema v1.1.

For `SECURITY INVOKER` functions, schema USAGE, function EXECUTE, and table privileges are separate requirements. Minimum privileges must explicitly cover: `authenticated` schema USAGE on `app_api`, EXECUTE on approved functions, and only the underlying `app_private` table SELECT/INSERT/UPDATE/DELETE privileges required by each function, with RLS enabled. Exposing a schema or granting EXECUTE alone does not grant table access. `anon` receives no mutation EXECUTE or private-table privilege; `PUBLIC` receives no broad EXECUTE. The migration/function-owner role owns objects but is not a user runtime identity, and no separate privileged backend role is approved under Option A.

If table grants are too broad, a `SECURITY DEFINER` exception is `PROPOSED` only per function: least-privilege owner, fixed `search_path = ''`, schema-qualified references, restricted EXECUTE (never PUBLIC/anon by default), explicit owner checks, and documented RLS implications. The exact grants remain E-05 `TBD`.

## RLS and schema exposure

Recommend private `app_private` tables plus controlled exposed `app_api` functions. Prefer `SECURITY INVOKER`; use `SECURITY DEFINER` only under the exception requirements above.

## Consequences and tests

Requires approval of runtime roles, JWT forwarding, schema exposure, RLS policies, and any CHAT backend-attestation mechanism. Required tests include: authorized authenticated RPC success; anonymous mutation-RPC denial; cross-user task/candidate/proposal rejection; forged target-version rejection; fabricated approval-evidence rejection; ordinary-user CHAT-provenance fabrication rejection; denied direct `app_private` Data API access; successful allowed `app_api` access; and RLS cross-user denial within `SECURITY INVOKER` execution. Also test invalid/expired/rotated tokens, leaked headers, request-client isolation, invalid payloads, and idempotency conflicts. See register E-02, E-05, E-06, E-08, and E-12.

## Stage 03.2 implementation baseline

**IMPLEMENTATION_BASELINE — selected for F1 implementation; not a claim of separate team approval.** `app_api` is the only application schema exposed through PostgREST; `app_private` is unexposed. Normal user requests use a caller-JWT Data API client and allowlisted `SECURITY INVOKER` RPCs. `authenticated` has only the documented schema/table/function privileges and owner RLS; `anon` has no mutation execution; `PUBLIC` has no broad function execution; DELETE is denied by default. The migration/admin owner is deployment-only.

CHAT approval is resolved through `app_private.chat_approval_attestations`: FastAPI verifies the caller and exact message/action/target/version/decision binding, then uses a separate immutable privileged client with the secret API key (never the caller JWT) to invoke `app_api.issue_chat_approval_attestation`. Only `service_role` can invoke issuance. A user mutation receives only the attestation ID, validates and consumes it atomically, and derives CHAT provenance internally. The five-minute, one-time artifact is neither a product TTL nor evidence from an LLM. The physical design is authoritative for exact RLS, grants, and test cases.

