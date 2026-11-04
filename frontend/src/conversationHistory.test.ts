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
import type { ChatMessage } from "./assistantDemo.ts"

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
  await assert.rejects(openHistoryDatabase(undefined), /IndexedDB unavailable/)
})
