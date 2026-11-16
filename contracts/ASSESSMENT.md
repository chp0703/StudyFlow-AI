# Assessment & Adaptive Revision extension 1.0.0

The existing Planner integration package (`1.0.1`), logical schema `1.1`, ten
Planner domain tools, eighteen Planner internal interfaces and BE-04 ingestion
extension (`1.0.0`) remain unchanged.

Feature 2 (Learning Assessment & Adaptive Revision) is registered as an additive,
separately versioned contract extension `1.0.0` under `extensions.assessment` in
[service-contract.json](service-contract.json) and
[data-contract.json](data-contract.json), and linked via `x-assessment-contract`
in [openapi.yaml](openapi.yaml). Its nine HTTP endpoints under `/v1/assessment`
live in [assessment-openapi.yaml](assessment-openapi.yaml), while its JSON Schema
definitions share [schemas/f1.schema.json](schemas/f1.schema.json) and the
generated SQL contract bundle.

## Core contract invariants

- Every HTTP endpoint requires `Authorization: Bearer <Supabase JWT>`; all write
  requests (`POST`, `PUT`) require `Idempotency-Key`.
- Generated questions start in `DRAFT` and require explicit approval through
  `POST /v1/decisions` with the unchanged `action_reference` before becoming
  `VERIFIED`. `VERIFIED` questions are immutable.
- Quiz attempts reference only `VERIFIED` questions (`MCQ` or `TRUE_FALSE`) and
  record `origin` (`MANUAL` | `SESSION_HANDOFF`) plus optional plain UUID
  `session_outcome_id`.
- Blank (`OMITTED`) or out-of-range (`INVALID`) responses have `is_correct: null`
  and are excluded from error rates rather than counted as wrong answers.
- Topics with zero valid responses report `status: "INSUFFICIENT_DATA"` and
  `error_rate: null`.
- Revision recommendations include attempt/chunk provenance and confidence
  limitations, and propose Planner workload only as a pending action requiring
  user confirmation through `/v1/decisions`.

See [docs/features/assessment/schema.md](../docs/features/assessment/schema.md)
for full entity definitions, state transitions and consumer impact analysis.
