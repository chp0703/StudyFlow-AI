# Learning Assessment & Adaptive Revision

This feature owns source-grounded question preparation, verified answer keys, quiz attempts, deterministic assessment results, topic performance and revision recommendations.

## Boundaries

- Generated questions are drafts until reviewed or verified.
- Automatic grading is allowed only against verified answer keys.
- Insufficient evidence is reported explicitly and is not treated as mastery.
- Revision recommendations carry source and assessment evidence.
- Recommendations can propose Planner workload changes but cannot edit a confirmed schedule.

## Specifications and Contracts

- Product requirements: [requirements.md](../../product/requirements.md#feature-2--learning-assessment--adaptive-revision)
- Domain schema, states, invariants, and consumer impact matrix: [schema.md](schema.md)
- Contract extension overview (`1.0.0`): [contracts/ASSESSMENT.md](../../../contracts/ASSESSMENT.md)
- OpenAPI 3.1 specification: [contracts/assessment-openapi.yaml](../../../contracts/assessment-openapi.yaml)

## Question Generation & Verification Bounds (B3 + B4)

- Configuration bounds (`backend/app/core/config.py`):
  - `QUESTION_MODEL_TIMEOUT_SECONDS` (default `30.0`, `(0, 120]`)
  - `QUESTION_MAX_TOKENS` (default `2048`, `[256, 8192]`)
  - `QUESTION_MAX_INPUT_CHARS` (default `24000`, `[1000, 100000]`)
  - `QUESTION_MAX_CONTEXT_CHUNKS` (default `12`, `[1, 20]`)
  - `QUESTION_MAX_RESPONSE_BYTES` (default `131072`, `[4096, 1048576]`)
- Generation behavior (`POST /v1/assessment/drafts`):
  - Verifies owner/conversation material (`MaterialOperations.get`) and topic chunks (`MaterialOperations.search`) before calling DeepSeek; missing/foreign material returns `404` (`ENTITY_NOT_FOUND`), missing topic chunks returns `422` (`INVALID_PARAMETER`), active awaiting action returns `409` (`ACTION_REVIEW_REQUIRED`).
  - Retry after a durable `create_question_drafts` DB write checks `lookup_operation_result` before any second model call.
  - Uses a single bounded DeepSeek call requiring `finish_reason="stop"` and strict JSON `{"questions":[...]}`. Timeout, HTTP failure, truncation, malformed JSON, or `0` valid normalized items returns `503` (`SERVICE_UNAVAILABLE`) with zero drafts/actions saved. The completed error receipt makes repeated requests with the same key replay the failure. A deliberate new generation uses a new key. The generation client disables automatic retries.
  - Per-item validation drops invalid questions (wrong type/topic, invalid option IDs, missing `answer_key`, non-retrieved chunk citations) while keeping partial valid batches (e.g., `4/5`) with an explicit count and `PARTIAL_QUESTION_BATCH` warning.
- Verification & immutability (`POST /v1/decisions`, `GET /v1/assessment/questions`):
  - Only `POST /v1/decisions` with the unchanged `ActionReference` (`target_type="PENDING_ACTION"`) and UI attestation (`source="UI"`, `source_message_id=null`) can transition a batch from `DRAFT` to `VERIFIED` (`APPROVE`) or `REJECTED` (`REJECT`); chat approval is rejected.
  - Finalized (`VERIFIED`/`REJECTED`) rows and question content are immutable via DB triggers; deletes are blocked.
  - PostgreSQL/pgTAP and HTTP integration tests run against local Supabase, including concurrent decisions and recovery after a persisted batch loses its HTTP response. Live DeepSeek verification requires API credentials.
