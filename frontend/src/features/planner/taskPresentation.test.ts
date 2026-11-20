import assert from "node:assert/strict"
import test from "node:test"
import { presentTaskDescription } from "./taskPresentation.ts"

const recommendation = "11111111-1111-4111-8111-111111111111"
const attempt = "22222222-2222-4222-8222-222222222222"
const chunk = "33333333-3333-4333-8333-333333333333"

test("ordinary and incomplete descriptions remain unchanged", () => {
  const ordinary = "Tự ôn lại chương 2\nrecommendation_id: ghi chú của tôi"
  assert.equal(presentTaskDescription(ordinary)?.summary, ordinary)
  assert.equal(presentTaskDescription(ordinary)?.isRevision, false)
  assert.equal(presentTaskDescription(null), null)
})

test("known F2 provenance is hidden while the original remains available", () => {
  const original = [
    "Bạn trả lời sai 5/5 câu trong bài kiểm tra gần nhất. Nên ôn tập lại chủ đề này.",
    `recommendation_id: ${recommendation}`,
    `attempt_ids: ${attempt}, 44444444-4444-4444-8444-444444444444`,
    `chunk_ids: ${chunk}`,
  ].join("\n")
  const result = presentTaskDescription(original)!
  assert.equal(result.isRevision, true)
  assert.equal(
    result.summary,
    "Bạn trả lời sai 5/5 câu trong bài kiểm tra gần nhất. Nên ôn tập lại chủ đề này.",
  )
  assert.equal(result.original, original)
  assert.doesNotMatch(result.summary, /[0-9a-f]{8}-/i)
})

test("unknown trailing content and malformed IDs are never stripped", () => {
  for (const description of [
    `Nội dung\nrecommendation_id: ${recommendation}\nattempt_ids: not-a-uuid`,
    `Nội dung\nrecommendation_id: ${recommendation}\nchunk_ids: ${chunk}\nGhi chú khác`,
  ]) {
    assert.equal(presentTaskDescription(description)?.summary, description)
  }
})

test("long student-facing text is preserved for the disclosure", () => {
  const summary = "Nội dung dài ".repeat(80).trim()
  const original = `${summary}\nrecommendation_id: ${recommendation}\nchunk_ids: ${chunk}`
  assert.equal(presentTaskDescription(original)?.summary, summary)
})
