import type { Task } from "../../types/task.ts"
import { toIsoDate, today } from "../../utils/date.ts"

export const FIRST_HOUR = 8
export const LAST_HOUR = 17

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
const DAY_RE =
  /hôm nay|ngày mai|thứ (2|3|4|5|6|7|hai|ba|tư|năm|sáu|bảy)|chủ nhật|\bcn\b/u
const TIME_RE = /(\d{1,2})\s*(?:h|giờ|:\d{2})/u

type Parsed = {
  date?: string
  hour?: number
  rest: string
}

function parseWhen(text: string): Parsed {
  let rest = text
  let date: string | undefined
  let hour: number | undefined
  const day = DAY_RE.exec(rest)
  if (day) {
    let offset = 0
    if (day[0] === "ngày mai") offset = 1
    else if (day[0] !== "hôm nay") {
      const dow = day[1] ? WEEKDAY_WORDS[day[1]] : 0
      offset = (dow - today.getDay() + 7) % 7
    }
    const d = new Date(today)
    d.setDate(d.getDate() + offset)
    date = toIsoDate(d)
    rest = rest.replace(day[0], " ")
  }
  const time = TIME_RE.exec(rest)
  if (time) {
    hour = Number(time[1])
    rest = rest.replace(time[0], " ")
  }
  rest = rest
    .replace(/\b(vào|lúc|ngày|vào lúc)\b/gu, " ")
    .replace(/\s+/g, " ")
    .trim()
  return { date, hour, rest }
}

const label = (hour: number) => `${String(hour).padStart(2, "0")}:00`
const timeRange = (hour: number) => `${label(hour)} – ${label(hour + 1)}`

type PlannerCommandResult = {
  tasks: Task[]
  reply: string
}

// shortcut: rule-based Vietnamese commands only, no NLP; replace with a real agent API later.
export function runPlannerCommand(
  input: string,
  tasks: Task[],
): PlannerCommandResult {
  const text = input.trim().toLocaleLowerCase("vi")
  const unchanged = (reply: string) => ({ tasks, reply })
  const freeHour = (date: string, from: number, ignoreId?: number) => {
    for (let h = from; h <= LAST_HOUR; h++)
      if (
        !tasks.some((t) => t.id !== ignoreId && t.date === date && t.hour === h)
      )
        return h
  }
  const findTask = (name: string) => {
    const matches = tasks.filter((t) =>
      t.title.toLocaleLowerCase("vi").includes(name),
    )
    return matches.length === 1 ? matches[0] : undefined
  }
  const outOfRange = (hour: number) =>
    hour < FIRST_HOUR || hour > LAST_HOUR
      ? `Lịch chỉ xếp từ ${label(FIRST_HOUR)} đến ${label(LAST_HOUR)}.`
      : ""

  let m = /^(?:thêm|tạo|lên lịch|đặt)\s+(.+)$/u.exec(text)
  if (m) {
    const { date, hour, rest } = parseWhen(m[1])
    if (!rest || !date || hour === undefined)
      return unchanged(
        "Cho mình biết tên công việc, ngày và giờ. Ví dụ: thêm Ôn giải tích thứ 3 lúc 19h.",
      )
    if (outOfRange(hour)) return unchanged(outOfRange(hour))
    const slot = freeHour(date, hour)
    if (slot === undefined)
      return unchanged(
        "Khung giờ hôm đó đã kín từ giờ bạn chọn, hãy chọn ngày hoặc giờ khác.",
      )
    const title = rest.charAt(0).toLocaleUpperCase("vi") + rest.slice(1)
    const task: Task = {
      id: Math.max(0, ...tasks.map((t) => t.id)) + 1,
      title,
      course: "Chưa phân loại",
      time: timeRange(slot),
      done: false,
      effort: 60,
      priority: "Trung bình",
      deadline: date,
      date,
      hour: slot,
    }
    const moved =
      slot !== hour
        ? ` (${label(hour)} đã có việc nên mình xếp sang ${label(slot)})`
        : ""
    return {
      tasks: [...tasks, task],
      reply: `Đã thêm "${title}" lúc ${label(slot)}${moved}.`,
    }
  }

  m = /^(?:dời|đổi|chuyển|đổi lịch|dời lịch)\s+(.+?)\s+sang\s+(.+)$/u.exec(text)
  if (m) {
    const task = findTask(m[1].trim())
    if (!task)
      return unchanged(
        `Mình không tìm thấy đúng một công việc tên "${m[1].trim()}".`,
      )
    const { date, hour } = parseWhen(m[2])
    const newDate = date ?? task.date
    const newHour = hour ?? task.hour
    if (!newDate || newHour === undefined)
      return unchanged(
        "Cho mình biết ngày và giờ mới. Ví dụ: dời Ôn giải tích sang thứ 5 lúc 9h.",
      )
    if (outOfRange(newHour)) return unchanged(outOfRange(newHour))
    const slot = freeHour(newDate, newHour, task.id)
    if (slot === undefined)
      return unchanged("Khung giờ hôm đó đã kín, hãy chọn ngày hoặc giờ khác.")
    const next: Task = {
      ...task,
      date: newDate,
      hour: slot,
      time: timeRange(slot),
      deadline: newDate > task.deadline ? newDate : task.deadline,
    }
    return {
      tasks: tasks.map((t) => (t.id === task.id ? next : t)),
      reply: `Đã dời "${task.title}" sang ${label(slot)}.`,
    }
  }

  m = /^(?:xóa|hủy|bỏ)\s+(.+)$/u.exec(text)
  if (m) {
    const task = findTask(m[1].trim())
    if (!task)
      return unchanged(
        `Mình không tìm thấy đúng một công việc tên "${m[1].trim()}".`,
      )
    return {
      tasks: tasks.filter((t) => t.id !== task.id),
      reply: `Đã xóa "${task.title}".`,
    }
  }

  return unchanged(
    "Mình hiểu các lệnh: thêm …, dời … sang …, xóa …. Ví dụ: thêm Ôn giải tích thứ 3 lúc 19h.",
  )
}
