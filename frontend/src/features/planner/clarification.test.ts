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

  assert.equal(draft["start_at.date"], "")

  assert.equal(draft["start_at.time"], "")

  assert.equal(draft.deadline_date, "2026-11-13")

  assert.equal(draft.estimated_minutes, "60")

  assert.equal(draft.priority, "MEDIUM")

  assert.equal(draft.color, "#6C5CE7")

  assert.equal(draft.description, "")
})

test("task clarification separates clock time, duration and title", () => {
  const questions = [
    { field: "estimated_minutes", message: "Bao lâu?", choices: [] },
  ]

  const evening = createClarificationDraft(
    questions,
    "Học Toán 8h tối mai",
    "2026-11-25",
  )

  assert.equal(evening.title, "Học Toán")

  assert.equal(evening["start_at.date"], "2026-11-26")

  assert.equal(evening["start_at.time"], "20:00")

  assert.equal(evening.estimated_minutes, "")

  const duration = createClarificationDraft(
    questions,
    "Tạo công việc làm bài tập toán vi tích phân trong 2h ngày mai",
    "2026-11-25",
  )

  assert.equal(duration.title, "làm bài tập toán vi tích phân")

  assert.equal(duration["start_at.time"], "")

  assert.equal(duration.estimated_minutes, "120")

  const short = createClarificationDraft(
    questions,
    "tạo cv ôn bai đi",
    "2026-11-25",
  )

  assert.equal(short.title, "ôn bai")

  const teencode = createClarificationDraft(
    questions,
    "lm bt toan mai 9h sang nha, 45p",
    "2026-11-25",
  )

  assert.equal(teencode.title, "làm bài tập toan")

  assert.equal(teencode["start_at.time"], "09:00")

  assert.equal(teencode.estimated_minutes, "45")
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

test("createClarificationDraft recognizes đêm nay and avoids turning 12h into 720 minutes", () => {
  const draft = createClarificationDraft(
    [
      {
        field: "start_at",
        message: "Thời gian bắt đầu là khi nào?",
        choices: [],
      },
      {
        field: "estimated_minutes",
        message: "Ước lượng bao nhiêu phút?",
        choices: [],
      },
    ],
    "Nộp bài trước 12h đêm nay",
    "2026-11-25",
  )

  assert.equal(draft["start_at.date"], "2026-11-25")
  assert.notEqual(draft.estimated_minutes, "720")
})

test("createClarificationDraft prefers the server draft over re-parsing the prompt", () => {
  const questions = [{ field: "start_at", message: "?", choices: [] }]
  const draft = createClarificationDraft(
    questions,
    'Thêm task "Ôn Toán rời rạc" hạn 28/11 lúc 20:00, mất 2 tiếng',
    "2026-11-27",
    {
      title: "Ôn Toán rời rạc",
      deadline_precision: "DATETIME",
      deadline_at: "2026-11-28T13:00:00.000000Z",
      estimated_minutes: 120,
    },
  )
  assert.equal(draft.title, "Ôn Toán rời rạc")
  assert.equal(draft["deadline_at.date"], "2026-11-28")
  assert.equal(draft["deadline_at.time"], "20:00")
  assert.equal(draft.estimated_minutes, "120")
})

test("a datetime server deadline is sent back with its time", () => {
  const questions = [{ field: "start_at", message: "?", choices: [] }]
  const result = formatClarificationFollowUp(
    {
      source: "api",
      originalPrompt: "",
      message: "",
      questions,
      slots: { deadline_precision: "DATETIME" },
    },
    {
      title: "Ôn Toán rời rạc",
      "start_at.date": "2026-11-28",
      "start_at.time": "18:00",
      "deadline_at.date": "2026-11-28",
      "deadline_at.time": "20:00",
      estimated_minutes: "120",
      priority: "MEDIUM",
    },
  )
  assert.ok(result.ok)
  assert.match(result.text, /hạn 28\/11\/2026 lúc 20:00/)
})

test("title extraction drops the task keyword and wrapping quotes", () => {
  const typed = createClarificationDraft(
    [{ field: "start_at", message: "?", choices: [] }],
    'Thêm task "Ôn Toán rời rạc" hạn 28/11',
    "2026-11-27",
  )
  assert.equal(typed.title, "Ôn Toán rời rạc")
})
