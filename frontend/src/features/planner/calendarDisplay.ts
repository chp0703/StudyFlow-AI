export interface CalendarDisplayRange {
  start: string
  end: string
}
export type CalendarDisplayRanges = readonly [CalendarDisplayRange, CalendarDisplayRange, CalendarDisplayRange, CalendarDisplayRange, CalendarDisplayRange, CalendarDisplayRange, CalendarDisplayRange]

export const DEFAULT_DISPLAY_RANGES: CalendarDisplayRanges = [
  { start: "08:00", end: "18:00" },
  { start: "08:00", end: "18:00" },
  { start: "08:00", end: "18:00" },
  { start: "08:00", end: "18:00" },
  { start: "08:00", end: "18:00" },
  { start: "08:00", end: "18:00" },
  { start: "08:00", end: "18:00" },
]

export const clockMinutes = (time: string) => {
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(time) && time !== "24:00") return null
  const [hour, minute] = time.split(":").map(Number)
  return hour * 60 + minute
}

export const displayRangeError = ({ start, end }: CalendarDisplayRange) => {
  const from = clockMinutes(start)
  const to = clockMinutes(end)
  if (from === null || from === 1440 || to === null)
    return "Nhập giờ hợp lệ theo dạng HH:mm (kết thúc có thể là 24:00)."
  if (from >= to) return "Giờ kết thúc phải sau giờ bắt đầu."
  return ""
}

export const displayMinutes = (time: string) => clockMinutes(time) ?? 0

// A source event keeps its clock time; the range only clips what is drawn.
export function eventPosition(time: string, range: CalendarDisplayRange) {
  const start = clockMinutes(time.slice(0, 5))
  const from = displayMinutes(range.start)
  const to = displayMinutes(range.end)
  if (start === null || start < from || start >= to) return null
  return { top: start - from, visibleMinutes: to - start }
}
