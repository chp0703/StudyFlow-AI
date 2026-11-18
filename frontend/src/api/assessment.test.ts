import assert from "node:assert/strict"
import test from "node:test"

import { createEndpoints } from "./endpoints.ts"
import type { ApiClient, RequestOptions } from "./client.ts"

function fixture() {
  const calls: Array<{ method: string; path: string; options: RequestOptions }> = []
  const client: ApiClient = {
    async request<T>(method: string, path: string, options: RequestOptions = {}) {
      calls.push({ method, path, options })
      if (path === "/v1/assessment/questions") {
        return { data: { items: [{ question_id: "q-1" }], next_cursor: null } } as T
      }
      return { data: { ok: true } } as T
    },
  }
  return { calls, endpoints: createEndpoints(client) }
}

test("assessment material and draft endpoints send canonical bodies and idempotency keys", async () => {
  const { calls, endpoints } = fixture()
  await endpoints.uploadAssessmentMaterial(
    "conv-1",
    "xac_suat.pdf",
    "application/pdf",
    "aGk=",
    ["Kỳ vọng", "Phương sai"],
    "idem-mat-1",
  )
  await endpoints.getAssessmentMaterial("conv-1", "mat/1")
  await endpoints.generateQuestionDrafts("conv-1", "mat-1", "Kỳ vọng", "MCQ", 5, "idem-draft-1")
  const questions = await endpoints.listAssessmentQuestions({
    material_id: "mat-1",
    status: "VERIFIED",
  })

  assert.equal(calls[0].method, "POST")
  assert.equal(calls[0].path, "/v1/assessment/materials")
  assert.equal(calls[0].options.idempotencyKey, "idem-mat-1")
  assert.deepEqual(calls[0].options.body, {
    schema_version: "1.1",
    conversation_id: "conv-1",
    filename: "xac_suat.pdf",
    mime_type: "application/pdf",
    content_base64: "aGk=",
    topics: ["Kỳ vọng", "Phương sai"],
  })

  assert.equal(calls[1].method, "GET")
  assert.equal(calls[1].path, "/v1/assessment/materials/mat%2F1")
  assert.deepEqual(calls[1].options.query, { conversation_id: "conv-1" })

  assert.equal(calls[2].method, "POST")
  assert.equal(calls[2].path, "/v1/assessment/drafts")
  assert.equal(calls[2].options.idempotencyKey, "idem-draft-1")
  assert.deepEqual(calls[2].options.body, {
    schema_version: "1.1",
    conversation_id: "conv-1",
    material_id: "mat-1",
    topic: "Kỳ vọng",
    question_type: "MCQ",
    count: 5,
  })

  assert.equal(questions.length, 1)
  assert.equal(calls[3].path, "/v1/assessment/questions")
  assert.deepEqual(calls[3].options.query, {
    material_id: "mat-1",
    status: "VERIFIED",
    page_size: 100,
    cursor: undefined,
  })
})

test("assessment attempt, response, stats, and recommendation endpoints match B1 contract", async () => {
  const { calls, endpoints } = fixture()
  await endpoints.createQuizAttempt("mat-1", ["q-1", "q-2"], "MANUAL", null, "idem-att-1")
  await endpoints.saveQuizResponse("att-1", "q-1", "A", "idem-resp-1")
  await endpoints.submitQuizAttempt("att-1", "idem-sub-1")
  await endpoints.getTopicStats("mat-1")
  await endpoints.createRevisionRecommendation("conv-1", "mat-1", "Kỳ vọng", 60, 1, "idem-rec-1")

  assert.equal(calls[0].path, "/v1/assessment/attempts")
  assert.deepEqual(calls[0].options.body, {
    schema_version: "1.1",
    material_id: "mat-1",
    question_ids: ["q-1", "q-2"],
    origin: "MANUAL",
    session_outcome_id: null,
  })

  assert.equal(calls[1].method, "PUT")
  assert.equal(calls[1].path, "/v1/assessment/attempts/att-1/responses/q-1")
  assert.deepEqual(calls[1].options.body, {
    schema_version: "1.1",
    selected_option_id: "A",
  })

  assert.equal(calls[2].path, "/v1/assessment/attempts/att-1/submit")
  assert.deepEqual(calls[2].options.body, { schema_version: "1.1" })

  assert.equal(calls[3].path, "/v1/assessment/topics/stats")
  assert.deepEqual(calls[3].options.query, { material_id: "mat-1" })

  assert.equal(calls[4].path, "/v1/assessment/recommendations")
  assert.deepEqual(calls[4].options.body, {
    schema_version: "1.1",
    conversation_id: "conv-1",
    material_id: "mat-1",
    topic: "Kỳ vọng",
    suggested_minutes: 60,
    priority: 1,
  })
})
