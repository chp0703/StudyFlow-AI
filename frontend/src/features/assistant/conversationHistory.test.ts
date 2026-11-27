import test from "node:test"

import assert from "node:assert/strict"

import {
  appendMessages,
  createConversation,
  historyGroup,
  openHistoryDatabase,
  restoreConversation,
  setProposalStatus,
  titleFromMessage,
} from "./conversationHistory.ts"

import type { ChatMessage } from "../../types/assistant.ts"

const clarification = (id: string): ChatMessage => ({
  id,

  timestamp: "2026-11-04T09:00:00.000Z",

  role: "assistant",

  category: "CLARIFICATION",

  text: "Cần thêm hạn",

  scenario: "task",
})

test("titles are deterministic and bounded", () => {
  assert.equal(
    titleFromMessage("  Lập  lịch\n học tuần sau  "),

    "Lập lịch học tuần sau",
  )

  assert.ok(titleFromMessage("a".repeat(100)).length <= 60)
})

test("conversation drafts and messages stay isolated", () => {
  const a = appendMessages(createConversation("Tạo task OOP"), [
    clarification("a-message"),
  ])

  const b = appendMessages(createConversation("Xem lịch học"), [
    { ...clarification("b-message"), text: "Lịch mẫu", scenario: "view" },
  ])

  const editedA = {
    ...a,

    draftInput: "Hạn thứ sáu",

    workflow: {
      ...a.workflow,

      draft: { ...a.workflow.draft, deadline: "2026-11-06" },
    },
  }

  assert.notEqual(a.id, b.id)

  assert.equal(editedA.workflow.draft.deadline, "2026-11-06")

  assert.equal(b.workflow.draft.deadline, "")

  assert.equal(
    b.messages.some((item) => item.id === "a-message"),

    false,
  )
})

test("restored proposals require review, while cancelled proposals remain cancelled", () => {
  const base = createConversation("Tạo task")

  const proposal: ChatMessage = {
    id: "proposal",

    timestamp: "2026-11-04T09:00:00.000Z",

    role: "assistant",

    category: "PROPOSAL",

    text: "Bản nháp",

    proposal: {
      intent: "CREATE_TASK",

      title: "Task",

      caveat: "Demo",

      details: [],

      status: "awaiting_approval",
    },
  }

  const pending = appendMessages(base, [proposal])

  const restored = restoreConversation(structuredClone(pending))

  assert.equal(restored?.messages[0].proposal?.status, "review_required")

  assert.equal(restored?.workflow.status, "review_required")

  const cancelled = restoreConversation(
    structuredClone(setProposalStatus(pending, "proposal", "cancelled")),
  )

  assert.equal(cancelled?.messages[0].proposal?.status, "cancelled")
})

test("malformed records are rejected without affecting valid records", () => {
  const valid = createConversation("Lập kế hoạch")

  assert.equal(restoreConversation({ schemaVersion: 999, id: "old" }), null)

  assert.equal(restoreConversation({ ...valid, messages: "broken" }), null)

  assert.equal(
    [valid, { schemaVersion: 999 }].map(restoreConversation).filter(Boolean)
      .length,

    1,
  )
})

test("groups use the local calendar and storage absence rejects", async () => {
  const now = new Date(2026, 10, 4, 12)

  assert.equal(
    historyGroup(new Date(2026, 10, 4, 1).toISOString(), now),

    "Hôm nay",
  )

  assert.equal(
    historyGroup(new Date(2026, 10, 3, 23).toISOString(), now),

    "Hôm qua",
  )

  await assert.rejects(
    openHistoryDatabase("demo", undefined),
    /IndexedDB unavailable/,
  )
})

test("history database names are isolated by user", () => {
  const names: string[] = []

  const factory = {
    open(name: string) {
      names.push(name)

      return {
        onupgradeneeded: null,
        onsuccess: null,
        onerror: null,
        onblocked: null,
      }
    },
  } as unknown as IDBFactory

  void openHistoryDatabase("user-a", factory)

  void openHistoryDatabase("user-b", factory)

  void openHistoryDatabase("demo", factory)

  assert.deepEqual(names, [
    "studyflow-assistant-history-user-a",

    "studyflow-assistant-history-user-b",

    "studyflow-assistant-history-demo",
  ])
})

test("attachments are preserved and validated in conversation history", () => {
  const base = createConversation("Tải ảnh bài tập")

  const withAttachment = appendMessages(base, [
    {
      id: "user-attach-1",

      timestamp: "2026-11-04T09:00:00.000Z",

      role: "user",

      category: "MESSAGE",

      text: "Đã gửi tệp bài tập",

      attachments: [
        {
          id: "att-1",

          name: "baitap.png",

          size: "120 KB",

          type: "image",

          dataUrl: "data:image/png;base64,abc",
        },
      ],
    },
  ])

  const restored = restoreConversation(structuredClone(withAttachment))

  assert.equal(restored?.messages[0].attachments?.length, 1)

  assert.equal(restored?.messages[0].attachments?.[0].name, "baitap.png")

  assert.equal(restored?.messages[0].attachments?.[0].type, "image")
})

test("setProposalStatus settles every card of the same action and stale survives restore", () => {
  const reference = {
    action_id: "a1",
    action_version: 1,
    target_type: "PENDING_ACTION",
    target_id: "a1",
    target_version: 1,
  } as const
  const card = (id: string): ChatMessage => ({
    id,
    role: "assistant",
    category: "PROPOSAL",
    text: "x",
    timestamp: "2026-11-27T00:00:00.000Z",
    proposal: {
      intent: "CREATE_TASK",
      title: "ôn Sử",
      caveat: "",
      details: [],
      status: "awaiting_approval",
      reference,
    },
  })
  const base = createConversation("x")
  const next = setProposalStatus(
    { ...base, messages: [card("m1"), card("m2")] },
    "m2",
    "stale",
  )

  assert.deepEqual(
    next.messages.map((m) => m.proposal?.status),
    ["stale", "stale"],
  )
  assert.equal(
    restoreConversation(JSON.parse(JSON.stringify(next)))?.messages[0].proposal
      ?.status,
    "stale",
  )
})
