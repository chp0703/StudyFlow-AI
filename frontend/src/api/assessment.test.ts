import assert from "node:assert/strict"
import test from "node:test"

import { createEndpoints } from "./endpoints.ts"
import {
  createApiClient,
  type ApiClient,
  type RequestOptions,
} from "./client.ts"

import type { ActionPresentation } from "./types.ts"

function fixture() {
  const calls: Array<{
    method: string
    path: string
    options: RequestOptions
  }> = []
  const client: ApiClient = {
    async request<T,>(
      method: string,
      path: string,
      options: RequestOptions = {},
    ) {
      calls.push({ method, path, options })
      if (path === "/v1/assessment/questions") {
        return {
          data: { items: [{ question_id: "q-1" }], next_cursor: null },
        } as T
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
  await endpoints.generateQuestionDrafts(
    "conv-1",
    "mat-1",
    "Kỳ vọng",
    "MCQ",
    5,
    "idem-draft-1",
  )
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
  await endpoints.createQuizAttempt(
    "mat-1",
    ["q-1", "q-2"],
    "MANUAL",
    null,
    "idem-att-1",
  )
  await endpoints.saveQuizResponse("att-1", "q-1", "A", "idem-resp-1")
  await endpoints.submitQuizAttempt("att-1", "idem-sub-1")
  await endpoints.getTopicStats("mat-1")
  await endpoints.createRevisionRecommendation(
    "conv-1",
    "mat-1",
    "Kỳ vọng",
    20,
    1,
    "idem-rec-1",
  )

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
    suggested_minutes: 20,
    priority: 1,
  })
})

test("selected revision scheduling uses the approved F1 action contract", async () => {
  const { calls, endpoints } = fixture()
  const arguments_ = {
    generation_scope: {
      start_at: "2026-11-20T03:00:00.000Z",
      end_at: "2026-11-22T16:59:00.000Z",
      selection_mode: "SELECTED_TASKS" as const,
      task_ids: ["task-server-1"],
    },
    policy_overrides: {},
  }
  await endpoints.prepareStudyPlan("planner-conv", arguments_, "idem-plan-1")

  assert.equal(calls[0].path, "/v1/actions")
  assert.equal(calls[0].options.idempotencyKey, "idem-plan-1")
  assert.deepEqual(calls[0].options.body, {
    schema_version: "1.1",
    conversation_id: "planner-conv",
    operation: "generate_study_plan",
    arguments: arguments_,
  })
})

test("createApiClient supports idempotent PUT requests and question_drafts presentations", async () => {
  const seen: Array<{
    url: string
    method?: string
    headers?: unknown
  }> = []

  const client = createApiClient({
    baseUrl: "http://localhost:8000",

    getToken: async () => "tok-1",

    fetchImpl: async (url, init) => {
      seen.push({
        url: String(url),
        method: init?.method,
        headers: init?.headers,
      })

      return new Response(JSON.stringify({ data: { ok: true } }), {
        status: 200,
      })
    },
  })

  const endpoints = createEndpoints(client)

  await endpoints.saveQuizResponse("att-1", "q-1", "A", "idem-put-00000001")

  assert.equal(seen[0].method, "PUT")

  assert.equal(
    (seen[0].headers as Record<string, string>)["Idempotency-Key"],
    "idem-put-00000001",
  )

  const presentation: ActionPresentation = {
    kind: "ACTION_PRESENTATION",

    pending_action: {
      intent: "VERIFY_QUESTION_DRAFTS",
      state: "AWAITING_APPROVAL",
      action_id: "act-1",
      version: 1,
    },

    candidate: null,

    proposal: null,

    normalized_command: null,

    effective_policy: null,

    question_drafts: { items: [], source_chunks: [] },
  }

  assert.equal(presentation.question_drafts?.items.length, 0)
})

test("generateQuestionDrafts never auto-retries on 503 or network error", async () => {
  for (const mode of ["503", "network"] as const) {
    let fetchCount = 0

    const client = createApiClient({
      baseUrl: "http://localhost:8000",

      retryDelayMs: 0,

      getToken: async () => "tok-1",

      fetchImpl: async () => {
        fetchCount += 1

        if (mode === "network") {
          throw new Error("timeout")
        }

        return new Response(
          JSON.stringify({
            error: {
              code: "SERVICE_UNAVAILABLE",
              message: "down",
              field: null,
              retryable: true,
            },
          }),

          { status: 503 },
        )
      },
    })

    const endpoints = createEndpoints(client)

    await assert.rejects(() =>
      endpoints.generateQuestionDrafts(
        "conv-1",
        "mat-1",
        "Kỳ vọng",
        "MCQ",
        3,
        "idem-draft-noretry-1",
      ),
    )

    assert.equal(
      fetchCount,
      1,
      `generateQuestionDrafts must make exactly 1 fetch on ${mode}`,
    )
  }
})

test("B7 candidate review preserves existing call shape and sends patch/version together", async () => {
  const { calls, endpoints } = fixture()

  await endpoints.reviewAction("conv-1", "act-1", 1, "review-key-1")

  await endpoints.reviewAction("conv-1", "act-1", 2, "patch-key-1", {
    candidate_patch: { deadline_at: "2027-03-02T01:00:00Z" },
    expected_candidate_version: 1,
  })

  assert.deepEqual(calls[0].options.body, {
    schema_version: "1.1",
    conversation_id: "conv-1",
    expected_action_version: 1,
  })

  assert.deepEqual(calls[1].options.body, {
    schema_version: "1.1",
    conversation_id: "conv-1",
    expected_action_version: 2,

    candidate_patch: { deadline_at: "2027-03-02T01:00:00Z" },
    expected_candidate_version: 1,
  })

  assert.equal(calls[1].options.idempotencyKey, "patch-key-1")
})
