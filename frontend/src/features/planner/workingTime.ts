import type { ApiTimeWindow } from "../../api/types"
import type { TimeWindow } from "../../types/planner"
import { civilWeekday } from "../../utils/date.ts"

export const clockMinutes = (value: string) => {
  const [hour, minute] = value.split(":").map(Number)
  return hour * 60 + minute
}

export function intervalError(
  start: string,
  end: string,
  others: Pick<ApiTimeWindow, "start_time" | "end_time">[],
) {
  if (
    !/^([01]\d|2[0-3]):[0-5]\d$/.test(start) ||
    (!/^([01]\d|2[0-3]):[0-5]\d$/.test(end) && end !== "24:00")
  )
    return "Hãy nhập giờ bắt đầu và kết thúc hợp lệ."
  if (clockMinutes(start) >= clockMinutes(end))
    return "Giờ kết thúc phải sau giờ bắt đầu."
  if (
    others.some(
      (item) =>
        item.start_time &&
        item.end_time &&
        clockMinutes(start) < clockMinutes(item.end_time) &&
        clockMinutes(end) > clockMinutes(item.start_time),
    )
  )
    return "Khoảng này trùng với thời gian học đã có."
  return ""
}

export type MinuteSegment = {
  start: number
  end: number
  kind: "free" | "busy"
}

// Exact fragments; a busy interval wins over a working interval at every minute.
export function hourSegments(
  date: string,
  hour: number,
  windows: ApiTimeWindow[],
  legacy: TimeWindow[] = [],
): MinuteSegment[] {
  const start = hour * 60
  const end = start + 60
  const dayStart = Date.parse(`${date}T00:00:00+07:00`)
  const intervals: MinuteSegment[] = []
  for (const window of windows) {
    if (window.archived_at) continue
    let a: number
    let b: number
    if (window.recurrence === "WEEKLY") {
      if (
        window.weekday !== civilWeekday(date) + 1 ||
        (window.valid_from && date < window.valid_from) ||
        (window.valid_until && date >= window.valid_until) ||
        !window.start_time ||
        !window.end_time
      )
        continue
      a = clockMinutes(window.start_time)
      b = clockMinutes(window.end_time)
    } else {
      if (!window.start_at || !window.end_at) continue
      a = (Date.parse(window.start_at) - dayStart) / 60000
      b = (Date.parse(window.end_at) - dayStart) / 60000
    }
    if (a < end && b > start)
      intervals.push({
        start: Math.max(a, start),
        end: Math.min(b, end),
        kind: window.kind === "BUSY" ? "busy" : "free",
      })
  }
  for (const cell of legacy)
    if (cell.date === date && cell.hour === hour)
      intervals.push({ start, end, kind: cell.kind })
  const boundaries = [
    ...new Set([start, end, ...intervals.flatMap((i) => [i.start, i.end])]),
  ].sort((a, b) => a - b)
  const result: MinuteSegment[] = []
  for (let i = 0; i < boundaries.length - 1; i++) {
    const a = boundaries[i]
    const b = boundaries[i + 1]
    const kind = intervals.some(
      (item) => item.kind === "busy" && item.start < b && item.end > a,
    )
      ? "busy"
      : intervals.some(
            (item) => item.kind === "free" && item.start < b && item.end > a,
          )
        ? "free"
        : null
    if (!kind) continue
    const last = result.at(-1)
    if (last?.kind === kind && last.end === a) last.end = b
    else result.push({ start: a, end: b, kind })
  }
  return result
}

export function fullWorkingHour(
  date: string,
  hour: number,
  windows: ApiTimeWindow[],
  legacy: TimeWindow[],
  configured: boolean,
) {
  const segments = hourSegments(date, hour, windows, legacy)
  if (segments.some((s) => s.kind === "busy")) return false
  if (!configured) return true
  return (
    segments.length === 1 &&
    segments[0].kind === "free" &&
    segments[0].start === hour * 60 &&
    segments[0].end === (hour + 1) * 60
  )
}

export type WorkingChange = {
  change_type: "ADD" | "UPDATE" | "ARCHIVE"
  window_id: string | null
  expected_window_version: number | null
  window: Omit<ApiTimeWindow, "window_id" | "version" | "archived_at"> | null
}

export function prepareDemoWorkingChange(
  current: ApiTimeWindow[],
  args: WorkingChange,
  newId: string,
) {
  const source = current.find(
    (item) => item.window_id === args.window_id && !item.archived_at,
  )
  if (
    args.change_type !== "ADD" &&
    (!source || source.version !== args.expected_window_version)
  )
    return null
  if (
    args.change_type === "ADD" &&
    (args.window_id !== null || args.expected_window_version !== null)
  )
    return null
  if (args.change_type !== "ARCHIVE" && !args.window) return null
  if (args.change_type === "ARCHIVE" && args.window !== null) return null
  const next =
    args.change_type === "ADD" && args.window
      ? [
          ...current,
          { ...args.window, window_id: newId, version: 1, archived_at: null },
        ]
      : args.change_type === "UPDATE" && args.window
        ? current.map((item) =>
            item === source
              ? {
                  ...args.window!,
                  window_id: item.window_id,
                  version: item.version + 1,
                  archived_at: null,
                }
              : item,
          )
        : current.filter((item) => item !== source)
  const weekday = args.window?.weekday ?? source?.weekday
  const name = [
    "",
    "Thứ 2",
    "Thứ 3",
    "Thứ 4",
    "Thứ 5",
    "Thứ 6",
    "Thứ 7",
    "Chủ nhật",
  ][weekday ?? 0]
  const before = source ? `${source.start_time}–${source.end_time}` : "chưa có"
  const after = args.window
    ? `${args.window.start_time}–${args.window.end_time}`
    : "không còn khoảng này"
  return {
    windows: next,
    description: `Thời gian học ${name}: ${before} → ${after}. Chỉ lưu khi bạn bấm Duyệt.`,
  }
}
