# Daily AI Learning API contract

Daily Learning is an additive `1.0.0` extension registered in the shared
OpenAPI, service, and data contracts. Requests and responses use
`schema_version: "1.1"`. The [OpenAPI document](learning-openapi.yaml) and
[JSON Schema bundle](schemas/f1.schema.json) define wire shapes. The M0
fixtures are registered in the [example manifest](examples/manifest.json).

Every request requires a Supabase bearer token. Every write additionally
requires an `Idempotency-Key`. Reusing a key for the same principal, operation,
resource and request body replays the original result. Reusing it for a different
request returns `409`. Resolve ownership from the authenticated principal and
return `404` for inaccessible resource IDs. Check access and state before
writing. Materials and session endpoints use `ErrorResult`. The shared
`POST /v1/decisions` uses `OrchestratorReply` on success and error.

## Materials and citations

- Upload text PDF, plain text or Markdown as base64 JSON. Enforce 5 MiB
  decoded, 50 pages, 200,000 extracted characters including page separators,
  and 20 F3 materials per owner. FAILED materials count toward quota until deleted. Use
  `decode_upload(..., max_bytes=5 * 1024 * 1024)` for strict decoding and
  `read_document_pages(..., max_pages=50, max_text=200_000)` for extraction.
  The schema checks encoded length and alphabet. Keep extracted text and metadata
  including the SHA-256 of the original bytes.
- Before reserving a material, return `400` for invalid base64 or a PDF
  missing its signature, `415` for an unsupported format, and `413` for
  exceeding the upload size. If the index worker is busy and the upload needs
  a new claim, return retryable `503 SERVICE_UNAVAILABLE` with `Retry-After`.
  These responses carry no material ID. A busy response creates no claim or
  receipt, so retry with the same key. Existing replays and deduplication still work.
- Once reserved, return `200` with the material ID. Poll GET for
  `UPLOADED`, `INDEXING`, `READY` or `FAILED`. A ready material has a page
  count. Corrupt or unextractable content returns `FAILED / INVALID_DOCUMENT`.
  A worker deadline returns `FAILED / INDEX_TIMEOUT`. A temporary indexing
  dependency failure returns `FAILED / INDEX_UNAVAILABLE`. M1 must distinguish
  worker timeouts from invalid documents when adapting the extractor.
- If the HTTP call times out, send the same key to replay a completed receipt.
  While the first request is still processing, the same key returns `409`.
  With a fresh key and the same SHA-256, reuse the material ID. Only
  `INDEX_TIMEOUT` and `INDEX_UNAVAILABLE` may retry indexing, by atomically
  claiming the existing row and clearing its error as it returns to `INDEXING`.
  Other states return the existing record. Serialize lookup, insert and retry
  claims per owner and hash. Treat list cursors as opaque.
- M1 extends the existing `app_private.materials` and
  `app_private.material_chunks` as one shared library. F3 uses the same IDs
  and preserves F2's conversation ownership, topic metadata and wire shapes.
  F3 uploads populate metadata required by F2 and are reusable under the
  existing F2 authorization rules. F3 can expose older F2 materials that
  fit the F3 limits once indexed for F3. For legacy duplicate hashes, prefer
  an eligible F3-ready record, then creation time and ID for a stable tie-break.
  Preserve all existing IDs and references.
- Delete material and chunks atomically if Assessment has no dependent
  records. If F2 references either, return `409` with
  `error.code: TIME_CONFLICT` and `error.details.reason: MATERIAL_IN_USE`.
  Keep both the material and its chunks available on conflict. Serialize
  deletion against concurrent F2 writes, or handle the foreign key conflict
  with a rollback. On successful deletion, old F3 citations retain their IDs
  and original page and return `material_deleted: true`. The delete confirmation
  in F2 and F3 should explain that successful deletion removes the material
  from both libraries, including any failed material occupying an F3 slot.
- A session uses one to five unique, owned, ready materials. An optional
  `planner_block_id` provides read-only context and must belong to the same
  owner. Only retrieve chunks from selected materials.
- `GET /v1/learning/planner-blocks/{id}/context` reads the owned block's task
  title and time range and returns a `suggested_goal` the client
  may prefill. It never writes to the Planner.

### CPU cold-start follow-up

On a fresh CPU process, measure E5 download and initialization separately from
first-document indexing, once with an empty disk cache and once with a populated
disk cache. Record CPU, dependency versions, document size and elapsed times, and
compare total first-upload latency against the 90-second deadline before deciding
whether to preload E5 at startup.

## Sessions, answers, and approval

- Session reads return turns in ordinal order. Each submitted question or
  hint returns the saved user and assistant turns in the same session.
- A supported assistant turn requires at least one server-validated citation.
  An unsupported turn has no citations and explicitly states that the selected
  material provides insufficient evidence. Treat uploaded text and model
  output as data and validate citation IDs against the retrieved chunks.
- Hints accept optional text. Without it, use the last question in the session.
  If there is no question to infer, return `400`. The server assigns levels
  1–3 for the same question, beginning with a conceptual cue and progressing
  to a cited passage and then guided steps.
- Creating a summary moves the session to `SUMMARY_PENDING` and returns
  `DRAFTED`, a draft, and the versioned `action_reference`. To decide, send
  the session's server-issued `conversation_id` and the unchanged reference
  to `POST /v1/decisions`. Resolve the pending operation server-side and check
  that both the action and session versions still match. A stale decision
  returns `409` so the client can request a fresh summary.
- Approval returns `state: SUCCEEDED` with `result.outcome: COMMITTED`,
  closes the session and creates one immutable `SessionOutcome`. Rejection
  returns `state: SUCCEEDED` with `result.outcome: REJECTED`, reopens the session and
  returns a null outcome. Other decision operations keep their existing
  response shapes. Chat cannot approve an action. A confirmed outcome records
  a learning activity and does not certify mastery.
- Set session expiry to 30 days after the last activity. Expiry removes
  turns and preserves any confirmed outcome.

## Embedding contract

Use `intfloat/multilingual-e5-small` locally on CPU and cache the model files
outside Git. Prefix chunks with `passage: ` and questions with `query: `,
including Vietnamese inputs. Enforce 512 tokens including the prefix and
tokenizer overhead. Approximately 800 characters per chunk is a starting point
for the chunker. L2-normalize the 384-dimensional vector and use cosine
similarity. Persist the model identifier with each chunk. Model changes require
re-indexing all affected chunks. [Model card](https://huggingface.co/intfloat/multilingual-e5-small)

Install `backend/requirements-embedding.txt` only in the embedding environment.
On Linux install CPU PyTorch first with
`python -m pip install torch --index-url https://download.pytorch.org/whl/cpu`.
Then install the optional requirements file. Planner and Assessment CI use the
shared backend requirements.

M0 publishes the contract and fixtures for frontend review. Endpoint handlers,
storage, model initialization, and the frontend client ship in later milestones.
