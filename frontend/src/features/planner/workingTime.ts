import type { ApiTimeWindow } from "../../api/types"
import type { TimeWindow } from "../../types/planner"
import { civilWeekday } from "../../utils/date.ts"

export const clockMinutes = (value: string) => {
  const [hour, minute] = value.split(":").map(Number)
  return hour * 60 + minute
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

export function visibleSegments(
  date: string,
  from: number,
  to: number,
  windows: ApiTimeWindow[],
  legacy: TimeWindow[] = [],
): MinuteSegment[] {
  const result: MinuteSegment[] = []
  for (let hour = Math.floor(from / 60); hour < Math.ceil(to / 60); hour++) {
    for (const segment of hourSegments(date, hour, windows, legacy)) {
      const start = Math.max(from, segment.start)
      const end = Math.min(to, segment.end)
      if (start >= end) continue
      const last = result.at(-1)
      if (last?.kind === segment.kind && last.end === start) last.end = end
      else result.push({ start, end, kind: segment.kind })
    }
  }
  return result
}
