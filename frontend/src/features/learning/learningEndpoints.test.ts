import assert from "node:assert/strict"
import test from "node:test"
import type { ApiClient, RequestOptions } from "../../api/client.ts"
import { createEndpoints } from "../../api/endpoints.ts"
import type { ActionReference } from "../../api/types.ts"

type Call = {
  method: string
  path: string
  options: RequestOptions
}

function fixture() {
  const calls: Call[] = []
  const client: ApiClient = {
    async request<T,>(
      method: string,
      path: string,
      options: RequestOptions = {},
    ) {
      calls.push({ method, path, options })
      if (path === "/v1/materials")
        return { data: { materials: [], next_cursor: null } } as T
      return { data: { ok: true }, state: "SUCCEEDED" } as T
    },
  }
  return { calls, endpoints: createEndpoints(client) }
}

test("M0 material endpoints preserve contract paths, bodies, and idempotency", async () => {
  const { calls, endpoints } = fixture()
  await endpoints.uploadLearningMaterial(
    "a.pdf",
    "application/pdf",
    "aGk=",
    null,
    "upload-key-123456",
  )
  await endpoints.listLearningMaterials()
  await endpoints.getLearningMaterial("mat/1")
  await endpoints.deleteLearningMaterial("mat/1", "delete-key-123456")
  assert.deepEqual(calls[0].options.body, {
    schema_version: "1.1",
    course_label: null,
    filename: "a.pdf",
    mime_type: "application/pdf",
    content_base64: "aGk=",
  })
  assert.equal(calls[0].options.idempotencyKey, "upload-key-123456")
  assert.deepEqual(calls[1].options.query, { limit: 20, cursor: undefined })
  assert.equal(calls[2].path, "/v1/materials/mat%2F1")
  assert.equal(calls[3].method, "DELETE")
  assert.equal(calls[3].options.idempotencyKey, "delete-key-123456")
})

test("AI turn and summary calls disable automatic retry but keep their keys", async () => {
  const { calls, endpoints } = fixture()
  await endpoints.addLearningTurn(
    "session/1",
    "ASK",
    "Định lý là gì?",
    "turn-key-1234567",
  )
  await endpoints.prepareLearningSummary("session/1", "summary-key-12345")
  assert.equal(calls[0].path, "/v1/learning/sessions/session%2F1/turns")
  assert.equal(calls[0].options.retry, false)
  assert.equal(calls[0].options.idempotencyKey, "turn-key-1234567")
  assert.equal(calls[1].options.retry, false)
})

test("APPROVE and REJECT keep the server-issued action reference unchanged", async () => {
  const reference: ActionReference = {
    action_id: "11111111-1111-4111-8111-111111111111",
    action_version: 2,
    target_type: "PENDING_ACTION",
    target_id: "22222222-2222-4222-8222-222222222222",
    target_version: 3,
  }
  for (const decision of ["APPROVE", "REJECT"] as const) {
    const { calls, endpoints } = fixture()
    await endpoints.decideLearningOutcome(
      "conv-1",
      reference,
      decision,
      `${decision}-key-123456`,
    )
    assert.equal(calls[0].path, "/v1/decisions")
    assert.equal(calls[0].options.retry, false)
    assert.deepEqual(calls[0].options.body, {
      schema_version: "1.1",
      conversation_id: "conv-1",
      action_reference: reference,
      decision,
    })
  }
})

test("planner handoff verifies the real block through the context endpoint", async () => {
  const { calls, endpoints } = fixture()
  await endpoints.getLearningPlannerContext("block/1")
  assert.equal(calls[0].path, "/v1/learning/planner-blocks/block%2F1/context")
})
