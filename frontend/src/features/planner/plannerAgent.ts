import type { PlannerIssue, TimeWindow } from "../../types/planner.ts"

import type { Task } from "../../types/task.ts"

import {
  addCivilDays,
  civilWeekday,
  daysUntil,
  vietnamClock,
  vietnamDate,
} from "../../utils/date.ts"

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

const DATE_RE = /(\d{1,2})\/(\d{1,2})(?:\/(\d{4}))?/u

const TIME_RE = /(\d{1,2})(?::([0-5]\d)|\s*(?:h|giờ))/u

type Parsed = {
  date?: string

  hour?: number

  minute?: number

  rest: string
}

function parseWhen(text: string): Parsed {
  const current = vietnamDate()
  let rest = text

  let date: string | undefined

  let hour: number | undefined

  let minute: number | undefined

  const day = DAY_RE.exec(rest)

  if (day) {
    let offset = 0

    if (day[0] === "ngày mai") offset = 1
    else if (day[0] !== "hôm nay") {
      const dow = day[1] ? WEEKDAY_WORDS[day[1]] - 1 : 6

      offset = (dow - civilWeekday(current) + 7) % 7
    }

    date = addCivilDays(current, offset)

    rest = rest.replace(day[0], " ")
  }

  const explicit = DATE_RE.exec(rest)

  if (explicit) {
    // dd/mm dùng năm nay (hoặc năm sau nếu đã qua); dd/mm/yyyy giữ đúng năm.

    const explicitYear = explicit[3] ? Number(explicit[3]) : null
    const year = explicitYear ?? Number(current.slice(0, 4))
    const candidate = addCivilDays(
      `${year}-${explicit[2].padStart(2, "0")}-${explicit[1].padStart(2, "0")}`,
      0,
    )
    date =
      !explicitYear && candidate < current
        ? addCivilDays(
            `${year + 1}-${explicit[2].padStart(2, "0")}-${explicit[1].padStart(2, "0")}`,
            0,
          )
        : candidate

    rest = rest.replace(explicit[0], " ")
  }

  const time = TIME_RE.exec(rest)

  if (time) {
    hour = Number(time[1])
    minute = Number(time[2] ?? 0)

    rest = rest.replace(time[0], " ")
  }

  rest = rest

    .replace(/\b(vào|lúc|ngày|vào lúc)\b/gu, " ")

    .replace(/\s+/g, " ")

    .trim()

  return { date, hour, minute, rest }
}

const label = (hour: number) => `${String(hour).padStart(2, "0")}:00`

const timeRange = (hour: number, minute = 0) => {
  const start = hour * 60 + minute
  const fmt = (value: number) =>
    `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`
  return `${fmt(start)} – ${fmt(start + 60)}`
}

type PlannerCommandResult = {
  tasks: Task[]

  availability: TimeWindow[]

  reply: string

  issues?: PlannerIssue[]
}

const vnDate = (iso: string) => iso.slice(8) + "/" + iso.slice(5, 7)

type Slot = {
  date: string

  hour: number
}

const windowId = (date: string, hour: number) => `${date}-${hour}`

// "9h" -> [9]; "từ 9h đến 12h" -> [9, 10, 11], không bao gồm giờ kết thúc.

function parseHours(text: string): number[] {
  const found = [...text.matchAll(/(\d{1,2})\s*(?:h|giờ)/gu)].map((x) =>
    Number(x[1]),
  )

  if (found.length === 1) return found

  if (found.length >= 2 && found[1] > found[0])
    return Array.from({ length: found[1] - found[0] }, (_, i) => found[0] + i)

  return []
}

// đơn giản hóa: chỉ dùng quy tắc cho lệnh tiếng Việt, chưa có NLP; thay bằng API agent thật sau.

export function runPlannerCommand(
  input: string,

  tasks: Task[],

  availability: TimeWindow[] = [],
): PlannerCommandResult {
  const text = input.trim().toLocaleLowerCase("vi")

  const unchanged = (reply: string) => ({ tasks, availability, reply })

  const slotTaken = (date: string, start: number, ignoreId?: string) =>
    availability.some(
      (window) =>
        window.kind === "busy" &&
        window.date === date &&
        start < window.hour * 60 + 60 &&
        start + 60 > window.hour * 60,
    ) ||
    tasks.some(
      (task) =>
        task.id !== ignoreId &&
        task.date === date &&
        task.hour !== undefined &&
        start < task.hour * 60 + (task.minute ?? 0) + 60 &&
        start + 60 > task.hour * 60 + (task.minute ?? 0),
    )

  const freeHour = (date: string, from: number, ignoreId?: string) => {
    for (let h = from; h <= LAST_HOUR; h++)
      if (!slotTaken(date, h * 60, ignoreId)) return h
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

  // FE-03 chỉ điều khiển trục hiển thị; Demo không nhận lệnh ghi giờ rảnh.
  if (/^(?:xóa|bỏ)?\s*rảnh(?:\s|$)/u.test(text))
    return unchanged(
      "Bản demo không hỗ trợ khai báo hoặc xóa giờ rảnh. Tùy chỉnh giờ hiển thị chỉ áp dụng cho trục thời gian trong Chi tiết giờ.",
    )

  let m = /^(xóa|bỏ)?\s*bận\s+(.+)$/u.exec(text)

  if (m) {
    const { date } = parseWhen(m[2])

    const hours = parseHours(m[2])

    if (!date)
      return unchanged("Cho mình biết ngày. Ví dụ: bận thứ 6 từ 9h đến 12h.")

    if (!m[1] && !hours.length)
      return unchanged("Cho mình biết giờ. Ví dụ: bận thứ 6 từ 9h đến 12h.")

    const range = hours.length
      ? hours
      : Array.from(
          { length: LAST_HOUR - FIRST_HOUR + 1 },

          (_, i) => FIRST_HOUR + i,
        )

    if (range.some((h) => h < FIRST_HOUR || h > LAST_HOUR))
      return unchanged(outOfRange(FIRST_HOUR - 1))

    const ids = new Set(range.map((h) => windowId(date, h)))

    const removing = Boolean(m[1])

    const kept = availability.filter(
      (w) => !ids.has(w.id) || (removing && w.kind !== "busy"),
    )

    const next = removing
      ? kept
      : [
          ...kept,

          ...range.map(
            (hour) =>
              ({
                id: windowId(date, hour),
                date,
                hour,
                kind: "busy",
              }) as TimeWindow,
          ),
        ]

    return {
      tasks,

      availability: next,

      reply: removing
        ? `Đã bỏ khung giờ đã khai báo ngày ${vnDate(date)}.`
        : `Đã đánh dấu ${range.length} giờ bận ngày ${vnDate(date)}.`,
    }
  }

  // "tạo công việc Báo cáo hạn 20/11 3 giờ": tạo việc chưa có lịch để xếp sau.

  // Lập lịch xác định: xếp việc chưa có lịch theo deadline rồi độ ưu tiên, mỗi việc một block 60 phút.

  if (/^(?:lập kế hoạch|xếp lịch|tự xếp)/u.test(text)) {
    const rank = (p: Task["priority"]) =>
      p === 1 || p === "Cao" ? 0 : p === 0.1 || p === "Thấp" ? 2 : 1

    const todo = tasks

      .filter((t) => !t.done && !t.date)

      .sort(
        (a, b) =>
          a.deadline.localeCompare(b.deadline) ||
          rank(a.priority) - rank(b.priority) ||
          Number(a.id) - Number(b.id),
      )

    if (!todo.length)
      return unchanged("Không có công việc chưa xếp. Hãy tạo công việc trước.")

    const placed = new Map<string, Task>()

    const issues: PlannerIssue[] = []

    const taken = (date: string, hour: number) =>
      slotTaken(date, hour * 60) ||
      [...placed.values()].some((t) => t.date === date && t.hour === hour)

    for (const task of todo) {
      let slot: Slot | undefined

      for (let i = 0; i <= daysUntil(task.deadline) && !slot; i++) {
        const date = addCivilDays(vietnamDate(), i)

        for (
          let h = i === 0 ? Number(vietnamClock().slice(0, 2)) + 1 : FIRST_HOUR;
          h <= LAST_HOUR;
          h++
        )
          if (h >= FIRST_HOUR && !taken(date, h)) {
            slot = { date, hour: h }

            break
          }
      }

      if (slot)
        placed.set(task.id, { ...task, ...slot, time: timeRange(slot.hour) })
      else
        issues.push({
          code: "INSUFFICIENT_AVAILABILITY",

          taskId: task.id,

          message: `Không còn giờ trống trước hạn ${vnDate(task.deadline)} cho "${task.title}".`,
        })
    }

    return {
      tasks: tasks.map((t) => placed.get(t.id) ?? t),

      availability,

      issues,

      reply: `Đã xếp ${placed.size}/${todo.length} công việc${
        issues.length
          ? `, chưa xếp được: ${issues.map((i) => tasks.find((t) => t.id === i.taskId)?.title).join(", ")}`
          : ""
      }.`,
    }
  }

  m = /^(?:thêm|tạo)\s+(?:công việc|việc)\s+(.+?)\s+hạn\s+(.+)$/u.exec(text)

  if (m) {
    const effortMatch = /(\d+)\s*giờ/u.exec(m[2])

    const { date } = parseWhen(m[2].replace(effortMatch?.[0] ?? "", " "))

    if (!date)
      return unchanged(
        "Cho mình biết hạn nộp. Ví dụ: tạo công việc Báo cáo hạn 20/11 3 giờ.",
      )

    const title = m[1].charAt(0).toLocaleUpperCase("vi") + m[1].slice(1)

    const dup = tasks.some((t) => t.title.toLocaleLowerCase("vi") === m![1])

    const task: Task = {
      id: String(Math.max(0, ...tasks.map((t) => Number(t.id))) + 1),

      title,

      time: "Chưa xếp",

      done: false,

      effort: effortMatch ? Number(effortMatch[1]) * 60 : 60,

      priority: 0.5,

      deadline: date,
    }

    return {
      tasks: [...tasks, task],

      availability,

      reply: `Đã tạo "${title}", hạn ${vnDate(date)}${
        dup ? " (đã có công việc cùng tên)" : ""
      }.`,
    }
  }

  m = /^(?:thêm|tạo|lên lịch|đặt)\s+(.+)$/u.exec(text)

  if (m) {
    const { date, hour, minute, rest } = parseWhen(m[1])

    if (!rest || !date || hour === undefined)
      return unchanged(
        "Cho mình biết tên công việc, ngày và giờ. Ví dụ: thêm Ôn giải tích thứ 3 lúc 19h.",
      )

    if (outOfRange(hour)) return unchanged(outOfRange(hour))

    if (minute && slotTaken(date, hour * 60 + minute))
      return unchanged(
        `Không thể đặt đúng ${label(hour).slice(0, 2)}:${String(minute).padStart(2, "0")}; giờ này đang bận.`,
      )
    const slot = freeHour(date, hour)

    if (slot === undefined)
      return unchanged(
        "Khung giờ hôm đó đã kín từ giờ bạn chọn, hãy chọn ngày hoặc giờ khác.",
      )

    const title = rest.charAt(0).toLocaleUpperCase("vi") + rest.slice(1)

    const task: Task = {
      id: String(Math.max(0, ...tasks.map((t) => Number(t.id))) + 1),

      title,

      time: timeRange(slot, minute),

      minute,

      done: false,

      effort: 60,

      priority: 0.5,

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

      availability,

      reply: `Đã thêm "${title}" lúc ${timeRange(slot, minute).split(" – ")[0]}${moved}.`,
    }
  }

  m = /^(?:dời|đổi|chuyển|đổi lịch|dời lịch)\s+(.+?)\s+sang\s+(.+)$/u.exec(text)

  if (m) {
    const task = findTask(m[1].trim())

    if (!task)
      return unchanged(
        `Mình không tìm thấy đúng một công việc tên "${m[1].trim()}".`,
      )

    const { date, hour, minute } = parseWhen(m[2])

    const newDate = date ?? task.date

    const newHour = hour ?? task.hour

    if (!newDate || newHour === undefined)
      return unchanged(
        "Cho mình biết ngày và giờ mới. Ví dụ: dời Ôn giải tích sang thứ 5 lúc 9h.",
      )

    if (outOfRange(newHour)) return unchanged(outOfRange(newHour))

    if (
      (minute ?? task.minute) &&
      slotTaken(newDate, newHour * 60 + (minute ?? task.minute ?? 0), task.id)
    )
      return unchanged("Giờ được yêu cầu đang bận; hãy chọn giờ khác.")
    const slot = freeHour(newDate, newHour, task.id)

    if (slot === undefined)
      return unchanged("Khung giờ hôm đó đã kín, hãy chọn ngày hoặc giờ khác.")

    const next: Task = {
      ...task,

      date: newDate,

      hour: slot,

      time: timeRange(slot, minute ?? task.minute),

      minute: minute ?? task.minute,

      deadline: newDate > task.deadline ? newDate : task.deadline,
    }

    return {
      tasks: tasks.map((t) => (t.id === task.id ? next : t)),

      availability,

      reply: `Đã dời "${task.title}" sang ${timeRange(slot, minute ?? task.minute).split(" – ")[0]}.`,
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

      availability,

      reply: `Đã xóa "${task.title}".`,
    }
  }

  return unchanged(
    "Mình hiểu các lệnh: thêm …, dời … sang …, xóa …. Ví dụ: thêm Ôn giải tích thứ 3 lúc 19h.",
  )
}
