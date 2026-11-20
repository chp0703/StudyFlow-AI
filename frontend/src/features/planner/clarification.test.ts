import assert from "node:assert/strict"
import test from "node:test"
import {
  buildDemoClarificationQuestions,
  createClarificationDraft,
  formatClarificationFollowUp,
  type PlannerClarification,
} from "./clarification.ts"

test("createClarificationDraft prefills task fields extracted from prompt", () => {
  const draft = createClarificationDraft(
    [
      {
        field: "title",
        message: "Tên công việc là gì?",
        choices: [],
      },
      {
        field: "start_at",
        message: "Thời gian bắt đầu là khi nào?",
        choices: [],
      },
    ],
    "Thêm công việc hạn ngày 13/11/2026, làm khoảng 60 phút",
    "2026-11-15",
  )

  assert.equal(draft.title, "")
  assert.equal(draft["start_at.date"], "2026-11-15")
  assert.equal(draft["start_at.time"], "09:00")
  assert.equal(draft.deadline_date, "2026-11-13")
  assert.equal(draft.estimated_minutes, "60")
  assert.equal(draft.priority, "MEDIUM")
  assert.equal(draft.color, "#6C5CE7")
  assert.equal(draft.description, "")
})

test("createClarificationDraft prefills title and duration in hours when present", () => {
  const draft = createClarificationDraft(
    [
      {
        field: "start_at",
        message: "Thời gian bắt đầu là khi nào?",
        choices: [],
      },
    ],
    "Tạo công việc Báo cáo hạn 20/11 khoảng 3 giờ",
    "2026-11-15",
  )

  assert.equal(draft.title, "Báo cáo")
  assert.equal(draft.deadline_date, "2026-11-20")
  assert.equal(draft.estimated_minutes, "180")
})

test("buildDemoClarificationQuestions skips fields already in prompt", () => {
  const missingTimeOnly = buildDemoClarificationQuestions(
    "thêm Ôn giải tích thứ 3",
    "Cho mình biết tên công việc, ngày và giờ. Ví dụ: thêm Ôn giải tích thứ 3 lúc 19h.",
  )
  assert.deepEqual(
    missingTimeOnly.map((q) => q.field),
    ["start_at"],
  )

  const missingDeadlineOnly = buildDemoClarificationQuestions(
    "tạo công việc Báo cáo",
    "Cho mình biết hạn nộp. Ví dụ: tạo công việc Báo cáo hạn 20/11 3 giờ.",
  )
  assert.deepEqual(
    missingDeadlineOnly.map((q) => q.field),
    ["deadline_date"],
  )
})

test("formatClarificationFollowUp includes edited task fields, priority, color and description", () => {
  const clarification: PlannerClarification = {
    source: "api",
    originalPrompt: "Thêm công việc hạn ngày 13/11/2026, làm khoảng 60 phút",
    message: "Mình cần thêm thông tin.",
    questions: [
      {
        field: "title",
        message: "Tên công việc là gì?",
        choices: [],
      },
      {
        field: "start_at",
        message: "Thời gian bắt đầu là khi nào?",
        choices: [],
      },
    ],
  }

  const ok = formatClarificationFollowUp(clarification, {
    title: "Báo cáo đồ án",
    "start_at.date": "2026-11-16",
    "start_at.time": "14:30",
    deadline_date: "2026-11-18",
    estimated_minutes: "90",
    priority: "HIGH",
    color: "#0EA5E9",
    description: "Nộp PDF lên LMS",
  })
  assert.deepEqual(ok, {
    ok: true,
    text: "tên công việc Báo cáo đồ án, bắt đầu 16/11/2026 lúc 14:30, hạn 18/11/2026, khoảng 90 phút, ưu tiên cao, màu #0EA5E9, mô tả: Nộp PDF lên LMS",
  })

  const missingTitle = formatClarificationFollowUp(clarification, {
    title: "   ",
    "start_at.date": "2026-11-16",
    "start_at.time": "14:30",
  })
  assert.equal(missingTitle.ok, false)
})

test("formatClarificationFollowUp builds demo command from task form", () => {
  const clarification: PlannerClarification = {
    source: "demo",
    originalPrompt: "thêm Ôn giải tích thứ 3",
    message: "Cho mình biết tên công việc, ngày và giờ.",
    questions: [
      {
        field: "start_at",
        message: "Thời gian bắt đầu là khi nào?",
        choices: [],
      },
    ],
  }

  const ok = formatClarificationFollowUp(clarification, {
    title: "Ôn giải tích",
    "start_at.date": "2026-11-17",
    "start_at.time": "19:00",
  })
  assert.deepEqual(ok, {
    ok: true,
    text: "thêm Ôn giải tích 17/11/2026 lúc 19:00",
  })
})
