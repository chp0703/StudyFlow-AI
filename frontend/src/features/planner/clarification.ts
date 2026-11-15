import type { Question } from "../../api/types.ts"
import { addCivilDays, civilWeekday, vietnamDate } from "../../utils/date.ts"

export type PlannerClarification = {
  source: "api" | "demo"
  originalPrompt: string
  message: string
  questions: Question[]
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
  { value: "#6C5CE7", label: "Tím" },
  { value: "#0EA5E9", label: "Xanh dương" },
  { value: "#10B981", label: "Xanh lá" },
  { value: "#F59E0B", label: "Vàng cam" },
  { value: "#EF4444", label: "Đỏ" },
  { value: "#EC4899", label: "Hồng" },
] as const

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
  /hôm nay|ngày mai|thứ\s*(?:2|3|4|5|6|7|hai|ba|tư|năm|sáu|bảy)|chủ nhật|\bcn\b|\d{1,2}\/\d{1,2}(?:\/\d{4})?/iu
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
  if (text.includes("hôm nay")) return todayIso
  if (text.includes("ngày mai")) return addCivilDays(todayIso, 1)
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
  const m = /(\d{1,2})(?::([0-5]\d)|\s*(?:h|giờ)(?:\s*([0-5]\d))?)/iu.exec(raw)
  if (!m) return null
  const hour = Number(m[1])
  const minute = Number(m[2] ?? m[3] ?? "0")
  if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`
}

function parseDurationMinutes(raw: string): string | null {
  const minMatch =
    /(?:khoảng|dự kiến|tầm|trong)?\s*(\d+)\s*(?:phút|p\b|min)/iu.exec(raw)
  if (minMatch) return String(Number(minMatch[1]))
  const hourMatch =
    /(?:khoảng|dự kiến|tầm|trong)?\s*(\d+(?:[.,]\d+)?)\s*(?:giờ|tiếng|h\b)(?!\s*\d)/iu.exec(
      raw,
    )
  if (hourMatch) {
    const hours = Number(hourMatch[1].replace(",", "."))
    if (Number.isFinite(hours) && hours > 0) {
      return String(Math.round(hours * 60))
    }
  }
  return null
}

function extractTaskTitle(prompt: string): string {
  let text = prompt.trim()
  text = text.replace(
    /^(?:thêm|tạo|lên lịch|đặt)\s+(?:công việc|việc|nhiệm vụ)?\s*/iu,
    "",
  )
  // Remove trailing clauses starting with deadline / duration / start / priority / description
  text = text.replace(
    /(?:,|\s)+(?:hạn(?:\s+nộp|\s+hoàn thành)?|deadline|bắt đầu|lúc|khoảng|dự kiến|làm khoảng|ưu tiên|màu|mô tả)\b.*$/iu,
    "",
  )
  text = text.replace(DEMO_DATE_RE, " ").replace(DEMO_TIME_RE, " ")
  text = text.replace(/^[,.\-:\s]+|[,.\-:\s]+$/g, "").trim()
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
    "start_at.date": parsedStartDate ?? todayIso,
    "start_at.time": parsedStartTime ?? "09:00",
    deadline_date: parsedDeadline ?? (missing.has("deadline_date") ? "" : ""),
    "deadline_at.date": parsedDeadline ?? todayIso,
    "deadline_at.time": "23:59",
    estimated_minutes:
      parsedDuration ?? (missing.has("estimated_minutes") ? "60" : ""),
    priority,
    color: TASK_COLOR_OPTIONS[0].value,
    description: "",
  }
}

export function createClarificationDraft(
  questions: Question[],
  originalPrompt: string = "",
  todayIso: string = vietnamDate(),
): ClarificationDraftValues {
  if (isTaskClarification(questions)) {
    return extractTaskDraftFromPrompt(originalPrompt, questions, todayIso)
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
    if (missing.has("deadline_at") && (!deadlineAtDate || !deadlineAtTime)) {
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
      if (startDate && startTime) {
        return {
          ok: true,
          text: `thêm ${title} ${formatDdMmYyyy(startDate)} lúc ${startTime}`,
        }
      }
      if (deadlineDate) {
        const dur = minutesRaw ? ` ${minutesRaw} phút` : ""
        return {
          ok: true,
          text: `tạo công việc ${title} hạn ${formatDdMmYyyy(deadlineDate)}${dur}`,
        }
      }
    }

    const parts: string[] = [`tên công việc ${title}`]
    if (startDate && startTime) {
      parts.push(`bắt đầu ${formatDdMmYyyy(startDate)} lúc ${startTime}`)
    }
    if (missing.has("deadline_at") && deadlineAtDate && deadlineAtTime) {
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
