import type { PlannerIssue, TimeWindow } from "../../types/planner.ts"

import type { Task } from "../../types/task.ts"

import { daysUntil, toIsoDate, today } from "../../utils/date.ts"

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

const DATE_RE = /(\d{1,2})\/(\d{1,2})/u

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

  const explicit = DATE_RE.exec(rest)

  if (explicit) {
    // dd/mm: this year, or next year if that day has already passed.

    const d = new Date(
      today.getFullYear(),

      Number(explicit[2]) - 1,

      Number(explicit[1]),
    )

    if (d < new Date(today.getFullYear(), today.getMonth(), today.getDate()))
      d.setFullYear(d.getFullYear() + 1)

    date = toIsoDate(d)

    rest = rest.replace(explicit[0], " ")
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

// "9h" -> [9]; "từ 9h đến 12h" -> [9, 10, 11] (end hour is exclusive).

function parseHours(text: string): number[] {
  const found = [...text.matchAll(/(\d{1,2})\s*(?:h|giờ)/gu)].map((x) =>
    Number(x[1]),
  )

  if (found.length === 1) return found

  if (found.length >= 2 && found[1] > found[0])
    return Array.from({ length: found[1] - found[0] }, (_, i) => found[0] + i)

  return []
}

// shortcut: rule-based Vietnamese commands only, no NLP; replace with a real agent API later.

export function runPlannerCommand(
  input: string,

  tasks: Task[],

  availability: TimeWindow[] = [],
): PlannerCommandResult {
  const text = input.trim().toLocaleLowerCase("vi")

  const unchanged = (reply: string) => ({ tasks, availability, reply })

  const isBusy = (date: string, hour: number) =>
    availability.some((w) => w.id === windowId(date, hour) && w.kind === "busy")

  const freeHour = (date: string, from: number, ignoreId?: string) => {
    for (let h = from; h <= LAST_HOUR; h++)
      if (
        !isBusy(date, h) &&
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

  // Availability: "rảnh thứ 6 từ 9h đến 12h", "bận ngày mai lúc 14h", "xóa rảnh/bận thứ 6".

  // Soft warning only: a day with declared free hours prefers them, but other hours are allowed.

  const outsideFree = (date: string, hour: number) => {
    const free = availability.filter(
      (w) => w.date === date && w.kind === "free",
    )

    return free.length && !free.some((w) => w.hour === hour)
      ? " (ngoài khung giờ rảnh bạn khai báo)"
      : ""
  }

  let m = /^(xóa|bỏ)?\s*(rảnh|bận)\s+(.+)$/u.exec(text)

  if (m) {
    const kind = m[2] === "rảnh" ? "free" : "busy"

    const { date } = parseWhen(m[3])

    const hours = parseHours(m[3])

    if (!date)
      return unchanged("Cho mình biết ngày. Ví dụ: rảnh thứ 6 từ 9h đến 12h.")

    if (!m[1] && !hours.length)
      return unchanged("Cho mình biết giờ. Ví dụ: rảnh thứ 6 từ 9h đến 12h.")

    const range = hours.length
      ? hours
      : Array.from(
          { length: LAST_HOUR - FIRST_HOUR + 1 },

          (_, i) => FIRST_HOUR + i,
        )

    if (range.some((h) => h < FIRST_HOUR || h > LAST_HOUR))
      return unchanged(outOfRange(FIRST_HOUR - 1))

    const ids = new Set(range.map((h) => windowId(date, h)))

    const kept = availability.filter((w) => !ids.has(w.id))

    const next = m[1]
      ? kept
      : [
          ...kept,

          ...range.map(
            (hour) =>
              ({ id: windowId(date, hour), date, hour, kind }) as TimeWindow,
          ),
        ]

    return {
      tasks,

      availability: next,

      reply: m[1]
        ? `Đã bỏ khung giờ đã khai báo ngày ${vnDate(date)}.`
        : `Đã đánh dấu ${range.length} giờ ${m[2]} ngày ${vnDate(date)}.`,
    }
  }

  // "tạo công việc Báo cáo hạn 20/11 3 giờ": an unscheduled task, placed later.

  // Deterministic plan: unscheduled tasks by deadline then priority, one 60-minute block each.

  if (/^(?:lập kế hoạch|xếp lịch|tự xếp)/u.test(text)) {
    const rank = (p: string) => ({ Cao: 0, Thấp: 2 })[p] ?? 1

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
      isBusy(date, hour) ||
      tasks.some((t) => t.date === date && t.hour === hour) ||
      [...placed.values()].some((t) => t.date === date && t.hour === hour)

    for (const task of todo) {
      let slot: Slot | undefined

      for (let i = 0; i <= daysUntil(task.deadline) && !slot; i++) {
        const d = new Date(today)

        d.setDate(d.getDate() + i)

        const date = toIsoDate(d)

        const free = availability.filter(
          (w) => w.date === date && w.kind === "free",
        )

        for (
          let h = i === 0 ? new Date().getHours() + 1 : FIRST_HOUR;
          h <= LAST_HOUR;
          h++
        )
          if (
            h >= FIRST_HOUR &&
            !taken(date, h) &&
            (!free.length || free.some((w) => w.hour === h))
          ) {
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

      course: "Chưa phân loại",

      time: "Chưa xếp",

      done: false,

      effort: effortMatch ? Number(effortMatch[1]) * 60 : 60,

      priority: "Trung bình",

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
      id: String(Math.max(0, ...tasks.map((t) => Number(t.id))) + 1),

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

      availability,

      reply: `Đã thêm "${title}" lúc ${label(slot)}${moved}${outsideFree(date, slot)}.`,
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

      availability,

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

      availability,

      reply: `Đã xóa "${task.title}".`,
    }
  }

  return unchanged(
    "Mình hiểu các lệnh: thêm …, dời … sang …, xóa …. Ví dụ: thêm Ôn giải tích thứ 3 lúc 19h.",
  )
}
