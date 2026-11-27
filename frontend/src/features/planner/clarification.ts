import type {
  ActionReference,
  CandidateTaskFields,
  Question,
} from "../../api/types.ts"

import {
  addCivilDays,
  civilWeekday,
  vietnamClock,
  vietnamDate,
} from "../../utils/date.ts"

export type PlannerClarification = {
  source: "api" | "demo"

  originalPrompt: string

  message: string

  questions: Question[]

  reference?: ActionReference

  // Draft the server already extracted; it wins over re-parsing the prompt.
  slots?: CandidateTaskFields
}

export type ClarificationDraftValues = Record<string, string>

export type ClarificationFollowUpResult = {
  ok: true

  text: string
} | {
  ok: false

  error: string
}

export const TASK_COLOR_OPTIONS = [
  { value: "#6C5CE7", label: "Tím · Ôn tập" },

  { value: "#0EA5E9", label: "Xanh dương · Học trên lớp" },

  { value: "#10B981", label: "Xanh lá · Tự học" },

  { value: "#F59E0B", label: "Cam · Dự án" },

  { value: "#EF4444", label: "Đỏ · Hạn nộp" },

  { value: "#EC4899", label: "Hồng · Hoạt động cá nhân" },

  { value: "#C69214", label: "Vàng · Bài tập" },

  { value: "#0D9488", label: "Xanh ngọc · Học nhóm" },

  { value: "#6366F1", label: "Chàm · Kiểm tra" },
] as const

export const TASK_COLOR_SUFFIX = /,\s*màu\s+(#[0-9a-f]{6})\s*$/iu

export function defaultTaskColor(title: string): string {
  const seed = title.trim().toLowerCase()
  if (!seed) return TASK_COLOR_OPTIONS[0].value
  let hash = 0
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0
  }
  return TASK_COLOR_OPTIONS[hash % TASK_COLOR_OPTIONS.length].value
}

export const TASK_PRIORITY_OPTIONS = [
  { value: "HIGH", label: "Cao" },

  { value: "MEDIUM", label: "Trung bình" },

  { value: "LOW", label: "Thấp" },
] as const

const TASK_FIELD_SET = new Set([
  "title",

  "start_at",

  "deadline_date",

  "deadline_at",

  "estimated_minutes",
])

const DEMO_DATE_RE =
  /(?<![\p{L}\p{N}])(?:(?:hôm|sáng|trưa|chiều|tối|đêm)\s+nay|(?:ngày\s+)?mai|thứ\s*(?:2|3|4|5|6|7|hai|ba|tư|năm|sáu|bảy)|chủ nhật|cn)(?![\p{L}\p{N}])|\d{1,2}\/\d{1,2}(?:\/\d{4})?/iu

const DEMO_TIME_RE = /\d{1,2}(?::[0-5]\d|\s*(?:h|giờ))/iu

const WEEKDAY_WORDS: Record<string, number> = {
  "2": 1,

  hai: 1,

  "3": 2,

  ba: 2,

  "4": 3,

  tư: 3,

  "5": 4,

  năm: 4,

  "6": 5,

  sáu: 5,

  "7": 6,

  bảy: 6,
}

export function isTaskClarification(questions: Question[]): boolean {
  return questions.some((q) => TASK_FIELD_SET.has(q.field))
}

function formatDdMmYyyy(isoDate: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate.trim())

  if (!match) return isoDate.trim()

  return `${match[3]}/${match[2]}/${match[1]}`
}

function parseRelativeOrNumericDate(
  raw: string,

  todayIso: string,
): string | null {
  const text = raw.toLowerCase()

  const numeric = /(\d{1,2})\/(\d{1,2})(?:\/(\d{4}))?/.exec(text)

  if (numeric) {
    const explicitYear = numeric[3] ? Number(numeric[3]) : null

    const year = explicitYear ?? Number(todayIso.slice(0, 4))

    const candidate = `${year}-${numeric[2].padStart(2, "0")}-${numeric[1].padStart(2, "0")}`

    if (!explicitYear && candidate < todayIso) {
      return `${year + 1}-${numeric[2].padStart(2, "0")}-${numeric[1].padStart(2, "0")}`
    }

    return candidate
  }

  if (
    /(?<![\p{L}\p{N}])(?:hôm|sáng|trưa|chiều|tối|đêm)\s+nay(?![\p{L}\p{N}])/u.test(
      text,
    )
  )
    return todayIso

  if (/\b(?:ngày\s+)?mai\b/u.test(text)) return addCivilDays(todayIso, 1)

  const weekday =
    /thứ\s*(2|3|4|5|6|7|hai|ba|tư|năm|sáu|bảy)|chủ nhật|\bcn\b/u.exec(text)

  if (weekday) {
    const dow = weekday[1] ? WEEKDAY_WORDS[weekday[1]] - 1 : 6

    const offset = (dow - civilWeekday(todayIso) + 7) % 7

    return addCivilDays(todayIso, offset)
  }

  return null
}

function parseTimeFromText(raw: string): string | null {
  const withoutDuration = raw.replace(
    /(?:trong|khoảng|tầm|dự kiến|hết)\s*\d+(?:[.,]\d+)?\s*(?:h\b|giờ|tiếng)(?:\s*rưỡi)?/giu,
    " ",
  )

  const m =
    /(\d{1,2})(?::([0-5]\d)|\s*(?:h|giờ|r)(?:\s*([0-5]\d)|\s*(rưỡi)|\s*kém\s*(\d{1,2}))?)(?:\s*(sáng|chiều|tối|đêm))?/iu.exec(
      withoutDuration,
    )

  if (!m) return null

  let hour = Number(m[1])

  let minute = Number(
    m[2] ?? m[3] ?? (m[4] || /^\d{1,2}\s*r\b/iu.test(m[0]) ? "30" : "0"),
  )

  if (m[5]) {
    hour -= 1
    minute = 60 - Number(m[5])
  }

  if ((m[6] === "chiều" || m[6] === "tối" || m[6] === "đêm") && hour < 12)
    hour += 12

  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null

  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`
}

function parseDurationMinutes(raw: string): string | null {
  const minMatch = /(\d+)\s*(?:phút|p\b|min)/iu.exec(raw)

  if (minMatch) return String(Number(minMatch[1]))

  const hourMatch =
    /(?:(?:khoảng|dự kiến|tầm|trong|hết)\s+\d+(?:[.,]\d+)?\s*(?:giờ|tiếng|h\b)|\d+(?:[.,]\d+)?\s*tiếng(?:\s+rưỡi)?)/iu.exec(
      raw,
    )

  if (hourMatch) {
    const hours =
      Number(hourMatch[0].match(/\d+(?:[.,]\d+)?/)?.[0].replace(",", ".")) +
      (/rưỡi/iu.test(hourMatch[0]) ? 0.5 : 0)

    if (Number.isFinite(hours) && hours > 0) {
      return String(Math.round(hours * 60))
    }
  }

  return null
}

function extractTaskTitle(prompt: string): string {
  let text = prompt.trim()

  text = text.replace(/\blm\s+bt\b/giu, "làm bài tập")

  text = text.replace(
    /^(?:thêm|tạo|lên lịch|đặt)\s+(?:(?:công việc|việc|nhiệm vụ|cv|task)(?![\p{L}\p{N}]))?\s*/iu,

    "",
  )

  // Remove trailing clauses starting with deadline / duration / start / priority / description

  text = text.replace(
    /(?:,|\s)+(?:hạn(?:\s+nộp|\s+hoàn thành)?|deadline|bắt đầu|lúc|khoảng|dự kiến|trong|làm khoảng|ưu tiên|màu|mô tả)\b.*$/iu,

    "",
  )

  text = text.replace(DEMO_DATE_RE, " ").replace(DEMO_TIME_RE, " ")

  text = text.replace(
    /(?<![\p{L}\p{N}])(?:sáng|sang|chiều|tối|toi|đêm|t|nha|nhé|đi)(?![\p{L}\p{N}])/giu,
    " ",
  )

  text = text.replace(/\d+\s*(?:p|phút|tiếng)(?![\p{L}\p{N}])/giu, " ")

  text = text.replace(/\s+/g, " ")

  text = text.replace(/^[,.\-:\s"“”]+|[,.\-:\s"“”]+$/g, "").trim()

  return text
}

export function extractTaskDraftFromPrompt(
  prompt: string,

  questions: Question[],

  todayIso: string = vietnamDate(),
): ClarificationDraftValues {
  const missing = new Set(questions.map((q) => q.field))

  // Deadline clause

  const deadlineClause =
    /(?:hạn(?:\s+nộp|\s+hoàn thành)?|deadline)\s*(?:ngày\s*)?([^,;]+)/iu.exec(
      prompt,
    )

  const parsedDeadline = deadlineClause
    ? parseRelativeOrNumericDate(deadlineClause[1], todayIso)
    : null

  // Start clause (avoid matching deadline date)

  const promptWithoutDeadline = deadlineClause
    ? prompt.replace(deadlineClause[0], " ")
    : prompt

  const parsedStartDate = parseRelativeOrNumericDate(
    promptWithoutDeadline,

    todayIso,
  )

  const parsedStartTime = parseTimeFromText(promptWithoutDeadline)

  const parsedDuration = parseDurationMinutes(prompt)

  const parsedTitle = missing.has("title") ? "" : extractTaskTitle(prompt)

  let priority = "MEDIUM"

  if (/ưu tiên\s*cao|khẩn|gấp/iu.test(prompt)) priority = "HIGH"
  else if (/ưu tiên\s*thấp/iu.test(prompt)) priority = "LOW"

  return {
    title: parsedTitle,

    "start_at.date": parsedStartDate ?? "",

    "start_at.time": parsedStartTime ?? "",

    deadline_date: parsedDeadline ?? (missing.has("deadline_date") ? "" : ""),

    "deadline_at.date": parsedDeadline ?? "",

    "deadline_at.time": parsedDeadline ? "23:59" : "",

    estimated_minutes: parsedDuration ?? "",

    priority,

    color:
      prompt.match(TASK_COLOR_SUFFIX)?.[1].toUpperCase() ??
      defaultTaskColor(parsedTitle),

    description: "",
  }
}

const PRIORITY_BY_SLOT = { 1: "HIGH", 0.5: "MEDIUM", 0.1: "LOW" } as const

// Server slots are UTC instants; the form edits Vietnam civil date + time.
function instantParts(iso: string | null | undefined) {
  const instant = iso ? new Date(iso) : null
  if (!instant || Number.isNaN(instant.getTime())) return null
  return { date: vietnamDate(instant), time: vietnamClock(instant) }
}

export function usesDeadlineDatetime(
  questions: Question[],
  slots?: CandidateTaskFields,
): boolean {
  return (
    questions.some((q) => q.field === "deadline_at") ||
    slots?.deadline_precision === "DATETIME"
  )
}

function applyServerSlots(
  values: ClarificationDraftValues,
  slots: CandidateTaskFields,
): ClarificationDraftValues {
  const next = { ...values }
  if (slots.title?.trim()) next.title = slots.title
  const start = instantParts(slots.start_at)
  if (start) {
    next["start_at.date"] = start.date
    next["start_at.time"] = start.time
  }
  if (slots.deadline_precision === "DATETIME") {
    const deadline = instantParts(slots.deadline_at)
    if (deadline) {
      next["deadline_at.date"] = deadline.date
      next["deadline_at.time"] = deadline.time
    }
    next.deadline_date = ""
  } else if (slots.deadline_date) {
    next.deadline_date = slots.deadline_date
  }
  if (typeof slots.estimated_minutes === "number")
    next.estimated_minutes = String(slots.estimated_minutes)
  if (slots.priority != null) next.priority = PRIORITY_BY_SLOT[slots.priority]
  if (slots.color) next.color = slots.color.toUpperCase()
  if (slots.description) next.description = slots.description
  return next
}

export function createClarificationDraft(
  questions: Question[],

  originalPrompt: string = "",

  todayIso: string = vietnamDate(),

  slots?: CandidateTaskFields,
): ClarificationDraftValues {
  if (isTaskClarification(questions)) {
    const parsed = extractTaskDraftFromPrompt(
      originalPrompt,
      questions,
      todayIso,
    )
    return slots ? applyServerSlots(parsed, slots) : parsed
  }

  const values: ClarificationDraftValues = {}

  for (const q of questions) {
    if (q.field === "date") {
      values[q.field] = todayIso
    } else if (q.field === "start_time") {
      values[q.field] = "09:00"
    } else if (q.field === "end_time") {
      values[q.field] = "11:00"
    } else if (q.choices.length > 0) {
      values[q.field] = q.choices[0].value
    } else {
      values[q.field] = ""
    }
  }

  return values
}

export function buildDemoClarificationQuestions(
  prompt: string,

  reply: string,
): Question[] {
  const lower = reply.toLowerCase()

  if (lower.includes("hạn nộp")) {
    return [
      {
        field: "deadline_date",

        message: "Hạn nộp là ngày nào?",

        choices: [],
      },
    ]
  }

  if (lower.includes("tên công việc, ngày và giờ")) {
    const title = extractTaskTitle(prompt)

    const questions: Question[] = []

    if (!title) {
      questions.push({
        field: "title",

        message: "Tên công việc là gì?",

        choices: [],
      })
    }

    if (!DEMO_DATE_RE.test(prompt) || !DEMO_TIME_RE.test(prompt)) {
      questions.push({
        field: "start_at",

        message: "Thời gian bắt đầu là khi nào?",

        choices: [],
      })
    }

    return questions
  }

  if (lower.includes("cho mình biết ngày")) {
    return [
      {
        field: "date",

        message: "Ngày áp dụng là ngày nào?",

        choices: [],
      },
    ]
  }

  if (lower.includes("cho mình biết giờ")) {
    return [
      {
        field: "start_time",

        message: "Từ mấy giờ?",

        choices: [],
      },

      {
        field: "end_time",

        message: "Đến mấy giờ?",

        choices: [],
      },
    ]
  }

  return []
}

export function formatClarificationFollowUp(
  clarification: PlannerClarification,

  values: ClarificationDraftValues,
): ClarificationFollowUpResult {
  if (isTaskClarification(clarification.questions)) {
    const missing = new Set(clarification.questions.map((q) => q.field))

    const title = (values.title ?? "").trim()

    const startDate = (values["start_at.date"] ?? "").trim()

    const startTime = (values["start_at.time"] ?? "").trim()

    const deadlineDate = (values.deadline_date ?? "").trim()

    const deadlineAtDate = (values["deadline_at.date"] ?? "").trim()

    const deadlineAtTime = (values["deadline_at.time"] ?? "").trim()

    const minutesRaw = (values.estimated_minutes ?? "").trim()

    const priority = (values.priority ?? "").trim()

    const color = (values.color ?? "").trim()

    const description = (values.description ?? "").trim()

    if (!title) {
      return { ok: false, error: "Vui lòng nhập tên công việc." }
    }

    if (missing.has("start_at") && (!startDate || !startTime)) {
      return {
        ok: false,

        error: "Vui lòng chọn đầy đủ ngày và giờ bắt đầu.",
      }
    }

    if (missing.has("deadline_date") && !deadlineDate) {
      return { ok: false, error: "Vui lòng chọn hạn hoàn thành." }
    }

    const datetimeDeadline = usesDeadlineDatetime(
      clarification.questions,
      clarification.slots,
    )

    if (datetimeDeadline && (!deadlineAtDate || !deadlineAtTime)) {
      return {
        ok: false,

        error: "Vui lòng chọn đầy đủ ngày và giờ hạn hoàn thành.",
      }
    }

    if (minutesRaw) {
      const minutes = Number(minutesRaw)

      if (!Number.isFinite(minutes) || minutes <= 0) {
        return {
          ok: false,

          error: "Thời lượng dự kiến phải là số phút lớn hơn 0.",
        }
      }
    } else if (missing.has("estimated_minutes")) {
      return {
        ok: false,

        error: "Vui lòng nhập thời lượng dự kiến (phút).",
      }
    }

    if (clarification.source === "demo") {
      const colorSuffix = color ? `, màu ${color}` : ""

      if (startDate && startTime) {
        return {
          ok: true,

          text: `thêm ${title} ${formatDdMmYyyy(startDate)} lúc ${startTime}${colorSuffix}`,
        }
      }

      if (deadlineDate) {
        const dur = minutesRaw ? ` ${minutesRaw} phút` : ""

        return {
          ok: true,

          text: `tạo công việc ${title} hạn ${formatDdMmYyyy(deadlineDate)}${dur}${colorSuffix}`,
        }
      }
    }

    const parts: string[] = [`tên công việc ${title}`]

    if (startDate && startTime) {
      parts.push(`bắt đầu ${formatDdMmYyyy(startDate)} lúc ${startTime}`)
    }

    if (datetimeDeadline && deadlineAtDate && deadlineAtTime) {
      parts.push(`hạn ${formatDdMmYyyy(deadlineAtDate)} lúc ${deadlineAtTime}`)
    } else if (deadlineDate) {
      parts.push(`hạn ${formatDdMmYyyy(deadlineDate)}`)
    }

    if (minutesRaw) {
      parts.push(`khoảng ${Math.round(Number(minutesRaw))} phút`)
    }

    if (priority === "HIGH") parts.push("ưu tiên cao")
    else if (priority === "LOW") parts.push("ưu tiên thấp")

    if (color) parts.push(`màu ${color}`)

    if (description) parts.push(`mô tả: ${description}`)

    return { ok: true, text: parts.join(", ") }
  }

  const parts: string[] = []

  for (const q of clarification.questions) {
    const field = q.field

    const raw = (values[field] ?? "").trim()

    if (!raw) {
      return {
        ok: false,

        error: `Vui lòng điền: ${q.message}`,
      }
    }

    if (field === "date") {
      parts.push(formatDdMmYyyy(raw))
    } else if (field === "start_time") {
      parts.push(
        clarification.source === "demo" &&
          clarification.questions.some((item) => item.field === "end_time")
          ? `từ ${raw}`
          : `lúc ${raw}`,
      )
    } else if (field === "end_time") {
      parts.push(`đến ${raw}`)
    } else {
      parts.push(raw)
    }
  }

  const addition = parts.join(", ").trim()

  if (!addition) {
    return { ok: false, error: "Vui lòng điền thông tin còn thiếu." }
  }

  if (clarification.source === "demo") {
    return {
      ok: true,

      text: `${clarification.originalPrompt.trim()} ${addition}`.trim(),
    }
  }

  return { ok: true, text: addition }
}
