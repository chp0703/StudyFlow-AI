# BE-04 — Source ingestion

## Scope and decisions

This additive boundary builds on BE-01/02/03 at `07bcebb`. Uploads create private,
server-owned source records. They never create academic tasks, busy intervals or
plans. Images use the official `deepseek-flash` API with thinking disabled;
documents with text and calendars are parsed locally before any model call.
The existing confirmation queue and `/v1/decisions` remain the only way to apply
task/calendar mutations. The scheduler continues reading confirmed data only.

Supported initial inputs: UTF-8 TXT/Markdown, text PDFs, JPEG/PNG/WebP/GIF images,
iCalendar `.ics` and CSV calendars (`title,start_at,end_at`). Recurring calendar
rules are rejected with an explicit error rather than partially imported.
All-day events use exclusive end dates; floating calendar times mean Vietnam
time. Unsupported timezone identifiers, malformed dates and reversed intervals
are rejected. PDF text extraction requires `pypdf`; scanned PDFs must be supplied
as page images in this version. No Google/Microsoft calendar OAuth or scraping.

## HTTP boundary

- `POST /v1/sources`: authenticated JSON upload containing `schema_version`,
  `conversation_id`, `filename`, `mime_type`, `content_base64`; requires an
  `Idempotency-Key`. File limit: 5 MiB after decoding, 7 MiB JSON body.
- `GET /v1/sources/{source_id}?conversation_id=...`: private metadata and results.
- `POST /v1/sources/{source_id}/extract`: explicit extraction request with
  `schema_version`, `conversation_id`. A database lease fences concurrent workers;
  completed results are reused. Failed extraction can be explicitly retried.
- `POST /v1/messages`: optional unique `source_ids` (maximum 5). References must
  belong to the authenticated owner AND conversation and be fully extracted.
  With source IDs, text is an annotation: only the source candidates enter the
  durable confirmation queue. Request a plan separately after confirming imports.
  Source content cannot authorize a plan or an unrelated write operation.

Sources and provenance are immutable after successful extraction. Original bytes
are held privately in PostgreSQL while awaiting extraction and removed after
success; no public file URLs or source bodies appear in logs. A source records
its SHA-256, declared/verified MIME, byte count, parser/model/prompt version,
extraction time, usage and draft intents. Message/source links preserve lineage.
Every persistence operation uses signed `app_api.*` RPCs, FORCE RLS, owner checks
and conversation checks. Foreign sources return the same 404 as unknown IDs.

## Limits and failure behavior

Maximum 20 candidates/source and 20 intents/message, 20 PDF pages, 24,000 extracted
text characters, 2,048 model output tokens and 45 seconds/model call. No automatic
model retries or paid-provider fallback. Missing key/dependency returns a safe
503. Invalid/empty/truncated provider output never becomes a candidate. API keys,
provider bodies, file contents and encoded images are never logged. The existing
DeepSeek API key is reused; the ingestion model is independently configurable and
defaults to `deepseek-flash`. No paid live test without an available configured key.

The existing schema `1.1` and RPC wire version `1.0.1` remain compatible. The
additive ingestion extension is separately versioned as `1.0.0` in the contract
registries; older message clients may continue omitting `source_ids`.

## Verification and delivery

Commit and publish each coherent step: design, parser/provider tests and code,
contract/database boundary, API/chat integration, then final validation fixes.
Run contract and generated-migration checks, backend unit and acceptance suites,
planner evaluation, and source-specific authorization/retry/privacy tests.
Database tests require local Supabase and must never target the forbidden cloud
project. No existing migration is rewritten. FE receives optional source DTOs and
endpoint methods; attachment controls remain disabled until end-to-end UI work.

## References

- [BE-01/02 PR](https://github.com/chp0703/StudyFlow-AI/pull/32)
- [BE-03 issue](https://github.com/chp0703/StudyFlow-AI/issues/36)
- User-supplied `backend-demo-follow-up (1).md`, section BE-04.
- [DeepSeek Vision](https://api-docs.deepseek.com/guides/vision/)
- [DeepSeek thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/)
