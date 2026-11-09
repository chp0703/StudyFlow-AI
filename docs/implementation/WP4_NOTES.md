# WP4 — chat workflow (POST /v1/messages)

## Flow

1. Claim the API receipt, store the CHAT message (`received_at` = receipt creation time, so a retry stores the same row).
2. A queue for this message already stored? Use it (a retry never re-extracts). Another unfinished queue in the
   conversation? Only a clarification answer is accepted (merged into the draft with `update_candidate_draft`);
   anything else gets `ACTION_REVIEW_REQUIRED`.
3. Otherwise extract once, validate against `ExtractionResult`, derive `depends_on` (a plan request waits for every
   earlier write) and persist the queue with `initialize_workflow_continuation`.
4. Run intents in order. Reads (`SEARCH_TASKS`, `GET_STUDY_PLAN`) execute at once. Writes are only *prepared*
   (candidate / pending action / proposal) and the queue parks with `WAIT`.
5. Approval is never inferred from chat text. `/v1/decisions` executes the decision, then `resume` records the outcome
   (`ADVANCE`) and continues with the remaining stored intents, so the reply can carry the next waiting action.

Action IDs are `uuid5(source_message_id, "action-<index>")` and database keys derive from the request key plus the
step index, so a crash at any point is repaired by repeating the request.

## Extractor

`backend/app/nlu/extractor.py`: `DeepSeekExtractor` (temperature 0, JSON mode, output validated; a bad answer is a
retryable 503, never a guess), `ScriptedExtractor` (tests/offline demo), `UnavailableExtractor` (no key configured).
`create_app(..., extractor=...)` injects one; the default is DeepSeek when `DEEPSEEK_API_KEY` is set.

## Evidence and what is NOT run

- Chat flows over HTTP on real local Supabase with a scripted extractor: multi-intent resume, clarification merge,
  interruption refusal, fake-approval text, unavailable language service + retry, restart replay (5 tests).
- `backend/tests/fixtures/nlu_eval_vi.json` (40 Vietnamese messages) and `backend/scripts/evaluate_nlu.py` exist and the
  scorer is unit-tested, but **the real 38/40 measurement is NOT_RUN: it needs a DeepSeek key.**
- The prompt in `extractor.py` is a first version; expect tuning once it can be measured.

## Known limits

- Chat can create/search/plan/set windows and preferences only with `change_type = ADD`; updating or archiving a window
  by chat is declined (use the form).
- A queue left unfinished whose awaited action was finished elsewhere is healed by the next message (recorded as FAILED
  `STALE_ENTITY_VERSION`), then that message is not processed; the user resends.
- Cancelling a queued action by chat is not possible (no cancel intent in the contract); use the decision button.
