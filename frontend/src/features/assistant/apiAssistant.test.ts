import test from "node:test"

import assert from "node:assert/strict"

import { readFileSync } from "node:fs"

import { ApiError } from "../../api/client.ts"

import { errorToMessage, replyToMessage } from "./apiAssistant.ts"

import type { OrchestratorReply } from "../../api/types.ts"

const example = (name: string) =>
  JSON.parse(
    readFileSync(
      new URL(`../../../../contracts/examples/valid/${name}`, import.meta.url),

      "utf8",
    ),
  )

const base = {
  request_id: "r",

  action_reference: null,

  questions: [],

  result: null,

  error: null,
}

test("an awaiting-approval reply becomes a card that carries the server reference", () => {
  const reply = example("OrchestratorReply.json") as OrchestratorReply

  const message = replyToMessage(reply)

  assert.equal(message.category, "PROPOSAL")

  assert.equal(message.intent, "CREATE_TASK")

  assert.equal(message.proposal?.status, "awaiting_approval")

  assert.deepEqual(message.proposal?.reference, reply.action_reference)

  assert.match(message.proposal!.title, /^Thêm công việc: /)
})

test("clarification lists the questions; errors keep their code", () => {
  const ask = replyToMessage(
    {
      ...base,

      state: "NEEDS_CLARIFICATION",

      message: "Cần thêm thông tin.",

      questions: [
        { field: "title", message: "Tên công việc là gì?", choices: [] },
      ],
    },

    "Thêm công việc hạn 20/11 khoảng 60 phút",
  )

  assert.equal(ask.category, "CLARIFICATION")

  assert.equal(ask.text, "Cần thêm thông tin.\n• Tên công việc là gì?")

  assert.equal(ask.scenario, undefined)

  assert.deepEqual(ask.clarification, {
    originalPrompt: "Thêm công việc hạn 20/11 khoảng 60 phút",

    questions: [
      { field: "title", message: "Tên công việc là gì?", choices: [] },
    ],
  })

  const err = replyToMessage({
    ...base,

    state: "ERROR",

    message: "Lỗi",

    error: {
      code: "ACTION_REVIEW_REQUIRED",

      message: "Lỗi",

      field: null,

      retryable: false,
    },
  })

  assert.equal(err.category, "ERROR")

  assert.equal(err.error?.code, "ACTION_REVIEW_REQUIRED")
})

test("a task search shows the first five titles", () => {
  const items = Array.from({ length: 7 }, (_, i) => ({
    task_id: `t${i}`,

    title: `Việc ${i}`,

    deadline_date: "2026-11-20",

    deadline_at: "2026-11-20T00:00:00Z",
  }))

  const message = replyToMessage({
    ...base,

    state: "SUCCEEDED",

    message: "Tìm thấy 7 công việc.",

    result: { outcome: "READ", data: { items, next_cursor: null } },
  })

  assert.equal(message.category, "MESSAGE")

  assert.match(message.text, /• Việc 0 — hạn 2026-11-20/)

  assert.match(message.text, /và 2 công việc khác/)

  assert.doesNotMatch(message.text, /Việc 5/)
})

test("a failed call is shown with the Vietnamese text for its code", () => {
  const message = errorToMessage(
    new ApiError(409, {
      code: "STALE_PROPOSAL",

      message: "x",

      field: null,

      retryable: false,
    }),
  )

  assert.equal(message.category, "ERROR")

  assert.match(message.text, /Lịch đã thay đổi/)

  assert.equal(message.error?.code, "STALE_PROPOSAL")
})

test("quiz, revision and outcome approvals keep their own intent instead of CREATE_TASK", () => {
  const reply = example("OrchestratorReply.json") as OrchestratorReply

  for (const intent of ["VERIFY_QUESTION_DRAFTS", "ACCEPT_REVISION_RECOMMENDATION", "SAVE_SESSION_OUTCOME"]) {
    const data = reply.result!.data as { pending_action: { intent: string } }

    const other = {
      ...reply,
      result: { ...reply.result!, data: { ...data, pending_action: { ...data.pending_action, intent } } },
    } as OrchestratorReply

    assert.equal(replyToMessage(other).intent, intent)
  }
})

test("an approved question batch is a plain success, not a task listing", () => {
  const reply = {
    ...base,

    state: "SUCCEEDED",

    message: "Đã xác nhận bộ câu hỏi.",

    result: {
      schema_version: "1.1",

      request_id: "r",

      outcome: "COMMITTED",

      data: { items: [{ question_id: "q-1", stem: "Câu hỏi" }], source_chunks: [] },

      error: null,

      warnings: [],
    },
  } as unknown as OrchestratorReply

  const message = replyToMessage(reply)

  assert.equal(message.category, "MESSAGE")

  assert.match(message.text, /Đã xác nhận bộ câu hỏi\./)
})
