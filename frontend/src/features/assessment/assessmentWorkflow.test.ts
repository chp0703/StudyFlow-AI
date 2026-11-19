import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"
import { ApiError } from "../../api/client.ts"
import type {
  ActionReference,
  MaterialChunk,
  OrchestratorReply,
  QuestionDraft,
} from "../../api/types.ts"
import {
  attemptQuestionIds,
  createQuizFromVerified,
  decisionFingerprint,
  operationFor,
  recommendationFromReply,
  referencedSources,
  revisionCandidatePatch,
  submitQuestionDecision,
  uncertainDecisionMessage,
} from "./assessmentWorkflow.ts"

const reference: ActionReference = {
  action_id: "action-1",
  action_version: 2,
  target_type: "PENDING_ACTION",
  target_id: "action-1",
  target_version: 2,
}

const question = (id: string, overrides: Partial<QuestionDraft> = {}) =>
  ({
    question_id: id,
    material_id: "material-1",
    status: "VERIFIED",
    question_type: "MCQ",
    source_chunk_ids: [],
    ...overrides,
  }) as QuestionDraft

const reply = (state: OrchestratorReply["state"] = "SUCCEEDED") =>
  ({ state, error: null }) as OrchestratorReply

test("attempt IDs are stable, VERIFIED-only, capped at 50 and do not mutate input", () => {
  for (const count of [0, 1, 49, 50, 51, 68]) {
    const input = Array.from({ length: count }, (_, i) => question(`q-${i}`))
    const before = structuredClone(input)
    assert.deepEqual(
      attemptQuestionIds(input, "material-1"),
      input.slice(0, 50).map((item) => item.question_id),
    )
    assert.deepEqual(input, before)
  }

  assert.deepEqual(
    attemptQuestionIds(
      [
        question("verified-1"),
        question("draft", { status: "DRAFT" }),
        question("rejected", { status: "REJECTED" }),
        question("other", { material_id: "material-2" }),
        question("verified-2", { question_type: "TRUE_FALSE" }),
      ],
      "material-1",
    ),
    ["verified-1", "verified-2"],
  )
})

test("the actual quiz request body never contains more than 50 IDs", async () => {
  let sent: string[] = []
  await createQuizFromVerified(
    {
      createQuizAttempt: async (_materialId: string, questionIds: string[]) => {
        sent = questionIds
        return { data: {} as never }
      },
    } as never,
    "material-1",
    Array.from({ length: 68 }, (_, i) => question(`q-${i}`)),
    "attempt-key",
  )
  assert.equal(sent.length, 50)
  assert.deepEqual(
    sent,
    Array.from({ length: 50 }, (_, i) => `q-${i}`),
  )
})

test("referenced source lookup preserves IDs and reports missing chunks", () => {
  const chunks = [
    { chunk_id: "chunk-2", text: "Nội dung 2" },
    { chunk_id: "chunk-1", text: "Nội dung 1" },
  ] as MaterialChunk[]
  const draft = question("q", {
    source_chunk_ids: ["chunk-1", "missing", "chunk-2"],
  })
  assert.deepEqual(
    referencedSources(draft, chunks).map(({ chunkId, chunk }) => [
      chunkId,
      chunk?.text ?? null,
    ]),
    [
      ["chunk-1", "Nội dung 1"],
      ["missing", null],
      ["chunk-2", "Nội dung 2"],
    ],
  )
})

test("approval and rejection resolve with the exact reference and key", async () => {
  for (const decision of ["APPROVE", "REJECT"] as const) {
    const calls: unknown[][] = []
    const original = structuredClone(reference)
    const outcome = await submitQuestionDecision(
      {
        decide: async (...args: unknown[]) => {
          calls.push(args)
          return reply()
        },
        listAssessmentQuestions: async () => [question("saved")],
      } as never,
      "conversation-1",
      "material-1",
      reference,
      decision,
      "stable-key",
    )
    assert.equal(outcome.kind, "resolved")
    assert.deepEqual(calls[0], [
      "conversation-1",
      reference,
      decision,
      "stable-key",
    ])
    assert.deepEqual(reference, original)
  }
})

test("retryable, network and unknown decision outcomes preserve safe retry state", async () => {
  const retryable = new ApiError(503, {
    code: "SERVICE_UNAVAILABLE",
    message: "Tạm thời lỗi",
    field: null,
    retryable: true,
  })
  for (const error of [retryable, new TypeError("network"), "unknown"]) {
    const outcome = await submitQuestionDecision(
      {
        decide: async () => {
          throw error
        },
        listAssessmentQuestions: async () => [],
      } as never,
      "conversation-1",
      "material-1",
      reference,
      "APPROVE",
      "stable-key",
    )
    assert.deepEqual(outcome, {
      kind: "uncertain",
      message: uncertainDecisionMessage,
    })
  }
})

test("non-retryable decisions block without discarding state", async () => {
  const outcome = await submitQuestionDecision(
    {
      decide: async () => {
        throw new ApiError(409, {
          code: "STALE_ENTITY_VERSION",
          message: "Tham chiếu đã cũ.",
          field: null,
          retryable: false,
        })
      },
      listAssessmentQuestions: async () => [],
    } as never,
    "conversation-1",
    "material-1",
    reference,
    "APPROVE",
    "stable-key",
  )
  assert.deepEqual(outcome, {
    kind: "blocked",
    message: "Tham chiếu đã cũ.",
  })
})

test("same decision retry reuses one key and cannot become a different operation", () => {
  const approve = decisionFingerprint(reference, "APPROVE")
  const first = operationFor(null, approve, () => "key-1")
  const retry = operationFor(first, approve, () => "key-2")
  assert.strictEqual(retry, first)
  assert.notDeepEqual(
    operationFor(
      first,
      decisionFingerprint(reference, "REJECT"),
      () => "key-2",
    ),
    first,
  )
})

test("decision success is retained when question refresh fails", async () => {
  let decisions = 0
  const outcome = await submitQuestionDecision(
    {
      decide: async () => {
        decisions += 1
        return reply()
      },
      listAssessmentQuestions: async () => {
        throw new Error("refresh failed")
      },
    } as never,
    "conversation-1",
    "material-1",
    reference,
    "APPROVE",
    "stable-key",
  )
  assert.equal(outcome.kind, "resolved_refresh_failed")
  assert.equal(decisions, 1)
})

test("recommendation fixture preserves its server reference and builds a valid candidate patch", () => {
  const presentation = JSON.parse(
    readFileSync(
      new URL(
        "../../../../contracts/examples/valid/b7-recommendation-presentation.json",
        import.meta.url,
      ),
      "utf8",
    ),
  )
  const serverReference: ActionReference = {
    action_id: presentation.pending_action.action_id,
    action_version: presentation.pending_action.version,
    target_type: "PENDING_ACTION",
    target_id: presentation.pending_action.action_id,
    target_version: presentation.pending_action.version,
  }
  const parsed = recommendationFromReply({
    request_id: "request-1",
    state: "AWAITING_APPROVAL",
    message: "review",
    action_reference: serverReference,
    questions: [],
    result: { outcome: "DRAFTED", data: presentation },
    error: null,
  })
  assert.deepEqual(parsed?.reference, serverReference)
  assert.equal(
    parsed?.presentation.revision_recommendation?.reason_summary,
    presentation.revision_recommendation.reason_summary,
  )
  assert.deepEqual(
    revisionCandidatePatch(1, "2026-11-20", "09:00", "2026-11-20", "10:00"),
    {
      candidate_patch: {
        start_at: "2026-11-20T02:00:00.000Z",
        deadline_at: "2026-11-20T03:00:00.000Z",
        deadline_precision: "DATETIME",
        deadline_timezone: "Asia/Ho_Chi_Minh",
      },
      expected_candidate_version: 1,
    },
  )
  assert.equal(
    revisionCandidatePatch(1, "2026-11-20", "10:00", "2026-11-20", "09:00"),
    null,
  )
})
