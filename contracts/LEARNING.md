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
writing. Return the shared `ErrorResult` shape for F3 errors.

## Materials and citations

- Upload PDF with an extractable text layer, plain text or Markdown as
  base64 JSON. Enforce 5 MiB of decoded bytes, 50 extracted pages and 20 active
  materials per owner. Keep extracted text and metadata, including the SHA-256
  of the original bytes. Deduplicate by owner and SHA-256.
- Material status progresses from `UPLOADED` or `INDEXING` to `READY` or
  `FAILED`. A ready material has a page count. A failed material has an error
  code. Poll the material GET endpoint and treat list cursors as opaque.
- A session uses one to five unique, owned, ready materials. An optional
  `planner_block_id` gives read-only context and must belong to the same owner.
  Only retrieve chunks from the selected materials.
- Deleting a material deletes its chunks. Old citations retain their IDs and
  original one-based page number, and return `material_deleted: true`.
  The client can display “Tài liệu đã xoá” without fetching the deleted material.
- The material and chunk contracts represent the proposed shared library.
  The Assessment material endpoint and payloads already exist. Storage
  convergence belongs to the material implementation and must preserve those
  endpoints and ownership rules.

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
- Approval returns `COMMITTED`, closes the session and creates one immutable
  `SessionOutcome`. Rejection returns `REJECTED`, reopens the session, and
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

M0 publishes the contract and fixtures for frontend review. Endpoint handlers,
storage, model initialization, and the frontend client ship in later milestones.
