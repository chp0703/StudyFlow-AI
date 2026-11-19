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
  DEFAULT_GENERATION_COUNT,
  defaultQuizQuestionCount,
  decisionFingerprint,
  generateQuestionDraftBatch,
  generationResultMessage,
  MAX_GENERATION_COUNT,
  operationFor,
  quizAnswerSummary,
  quizQuestionCount,
  recommendationFromReply,
  referencedSources,
  revisionCandidatePatch,
  runGenerationOnce,
  submitQuestionDecision,
  uncertainDecisionMessage,
  validGenerationCount,
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

test("generation count follows the approved 1-10 contract", () => {
  assert.equal(DEFAULT_GENERATION_COUNT, 5)
  assert.equal(MAX_GENERATION_COUNT, 10)
  for (const value of [1, 5, 10]) {
    assert.equal(validGenerationCount(value), true)
  }
  for (const value of [0, -1, 1.5, 11, Number.NaN]) {
    assert.equal(validGenerationCount(value), false)
  }
  assert.equal(
    generationResultMessage(5, 5),
    "Đã nhận 5 câu nháp để bạn duyệt.",
  )
  assert.equal(
    generationResultMessage(10, 7),
    "Đã nhận 7 câu nháp từ yêu cầu 10 câu.",
  )
})

test("selected generation count reaches the API and invalid values never do", async () => {
  const calls: unknown[][] = []
  const assessmentApi = {
    generateQuestionDrafts: async (...args: unknown[]) => {
      calls.push(args)
      return {} as never
    },
  }
  for (const count of [1, 5, 10])
    await generateQuestionDraftBatch(
      assessmentApi as never,
      "conversation-1",
      "material-1",
      "topic",
      count,
      `key-${count}`,
    )
  assert.deepEqual(
    calls.map((call) => call[4]),
    [1, 5, 10],
  )
  assert.throws(
    () =>
      generateQuestionDraftBatch(
        assessmentApi as never,
        "conversation-1",
        "material-1",
        "topic",
        11,
        "invalid-key",
      ),
    RangeError,
  )
  assert.equal(calls.length, 3)
})

test("generation lock prevents duplicate paid requests", async () => {
  const lock = { current: false }
  let release = () => {}
  const waiting = new Promise<void>((resolve) => {
    release = resolve
  })
  let requests = 0
  const first = runGenerationOnce(lock, async () => {
    requests += 1
    await waiting
  })
  const duplicate = await runGenerationOnce(lock, async () => {
    requests += 1
  })
  assert.equal(duplicate, false)
  assert.equal(requests, 1)
  release()
  assert.equal(await first, true)
  assert.equal(lock.current, false)
})

test("quiz count defaults to five and stays within availability and contract bounds", () => {
  assert.deepEqual(
    [0, 1, 5, 20, 68].map(defaultQuizQuestionCount),
    [0, 1, 5, 5, 5],
  )
  assert.equal(quizQuestionCount(1, 5), 1)
  assert.equal(quizQuestionCount(5, 5), 5)
  assert.equal(quizQuestionCount(20, 20), 20)
  assert.equal(quizQuestionCount(50, 68), 50)
  for (const count of [0, -1, 1.5, 51, 69])
    assert.equal(quizQuestionCount(count, 68), 0)
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
    50,
    "attempt-key",
  )
  assert.equal(sent.length, 50)
  assert.deepEqual(
    sent,
    Array.from({ length: 50 }, (_, i) => `q-${i}`),
  )
})

test("selected quiz count reaches the request without stale or ineligible IDs", async () => {
  let sent: string[] = []
  await createQuizFromVerified(
    {
      createQuizAttempt: async (_materialId: string, questionIds: string[]) => {
        sent = questionIds
        return { data: {} as never }
      },
    } as never,
    "material-1",
    [
      question("q-1"),
      question("draft", { status: "DRAFT" }),
      question("q-2"),
      question("other", { material_id: "material-2" }),
      question("q-3"),
    ],
    2,
    "attempt-key",
  )
  assert.deepEqual(sent, ["q-1", "q-2"])
})

test("answer summary counts only IDs in the active server attempt", () => {
  const answers = { q1: "A", stale: "B", q3: "C" }
  const before = structuredClone(answers)
  assert.deepEqual(quizAnswerSummary(["q1", "q2", "q3"], answers), {
    total: 3,
    answered: 2,
    unanswered: 1,
  })
  assert.deepEqual(answers, before)
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
