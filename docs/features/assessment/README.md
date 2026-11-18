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

## Topic Statistics (B6)

- `GET /v1/assessment/topics/stats?material_id=<uuid>` uses the existing `TopicStatsResult` contract; omit `material_id` to read all of the caller's materials. Authentication is required; `Idempotency-Key` is not.
- Migration `202611190001_f2_b6_topic_stats.sql` adds the read-only `app_api.get_topic_stats` RPC. It reads durable grades under the caller's JWT and existing FORCE RLS policies, including after a backend restart.
- Each ready material/topic has a separate item. Only graded `VALID` responses in `SUBMITTED` attempts against `VERIFIED` questions contribute to counts, error rate and latest valid submission time. Empty evidence returns `INSUFFICIENT_DATA`, zero counts and null rate/time.
- Missing and foreign material IDs both return `404 ENTITY_NOT_FOUND`. Results describe observed errors without inferring mastery or creating Planner actions.
- Verification: `backend/tests/unit/test_topic_stats.py`, `backend/tests/acceptance_api_sol/test_topic_stats_http.py`, and B6 assertions in `supabase/tests/22_f2_b5_attempts_grading.sql` and `backend/tests/integration/test_attempts_local_supabase.py`.

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

## Revision recommendations (B7)

`POST /v1/assessment/recommendations` creates a durable review action from the latest
50 submitted attempts containing valid graded responses for the selected material/topic.
Counts are calculated before joining source links; citations include at most 50 distinct
chunks from incorrect answers. This window can differ from B6 lifetime statistics.
The immutable snapshot always reports LOW confidence and its sample/coverage limits;
minutes and priority are user choices. No eligible responses or no observed errors
returns 422 without a recommendation. Creation does not change Planner workload.


### Decisions and Planner handoff

`POST /v1/decisions` with the unchanged PENDING_ACTION reference accepts/rejects
recommendations. Acceptance atomically creates one DRAFT TaskCandidate and a F1
CREATE_TASK action in AWAITING_CLARIFICATION. It does not save an AcademicTask or
change the schedule. Rejection creates no candidate. Evidence remains the original
snapshot even if another quiz is submitted. Cancelling the candidate later leaves
the recommendation ACCEPTED and the candidate CANCELLED.

To complete that draft, POST `/v1/actions/{action_id}/review` with the existing
conversation/action version plus both `candidate_patch` (CandidateTaskFields) and
`expected_candidate_version`. Only fields supplied are merged; null clears a field.
An explicit date-only deadline is normalized to the next local midnight. Start time
alone never invents a deadline. Incomplete drafts return NEEDS_CLARIFICATION; complete
drafts return AWAITING_APPROVAL with a fresh TASK_CANDIDATE reference. Confirm that
reference separately through `/v1/decisions` to save the task. Planning/plan approval
remain separate. Ordinary review requests without a patch retain their existing form.

Internal creation arguments contain material/topic, user-selected minutes/priority,
and stable server IDs. The database generates the evidence and recommendation; the
result contains ActionPresentation. `decide_revision_recommendation` is a signed,
non-LLM RPC returning the completed recommendation or F1 draft presentation.
