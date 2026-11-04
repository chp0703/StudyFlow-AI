# ADR-002 — Authentication and Runtime Authorization

**Status: PROPOSED — Pending team approval**  
**Date:** 2026-11-04

## Context

Schema v1.1 requires ownership from a trusted backend principal. No authentication or backend exists in the repository.

## Decision

Recommend Supabase Auth as the authentication candidate. The frontend obtains a user access JWT; FastAPI verifies signature, issuer, audience, expiration, subject, and signing-key selection; FastAPI forwards the request-scoped JWT to the Supabase Data API. LLM output and browser owner fields never authorize access.

Use asymmetric JWKS verification where available. Do not hardcode signing secrets or trust an unverified decoded token. Use separate migration/admin credentials, never for ordinary user-scoped requests.

## RLS and schema exposure

Recommend private business tables plus a controlled exposed API schema. Prefer `SECURITY INVOKER`; use `SECURITY DEFINER` only with a documented need, fixed search path, schema-qualified references, restricted execute grants, and explicit ownership checks.

## Consequences and tests

Requires approval of runtime roles, JWT forwarding, schema exposure, and RLS policies. Test invalid/expired/rotated tokens, cross-user reads/writes, leaked headers, and connection/client isolation.

