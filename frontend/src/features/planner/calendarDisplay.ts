export interface CalendarDisplayRange {
  start: string

  end: string
}

export type CalendarDisplayRanges = readonly [CalendarDisplayRange, CalendarDisplayRange, CalendarDisplayRange, CalendarDisplayRange, CalendarDisplayRange, CalendarDisplayRange, CalendarDisplayRange]

export type CalendarView = "detail" | "month"

export const DEFAULT_CALENDAR_VIEW: CalendarView = "detail"

export const CALENDAR_VIEWS: readonly CalendarView[] = ["detail", "month"]

export const calendarViewLabel = (view: CalendarView) =>
  view === "detail" ? "Tuần" : "Tháng"

export const displaySettingsVisible = (view: CalendarView) => view === "detail"

export const DEFAULT_DISPLAY_RANGES: CalendarDisplayRanges = [
  { start: "00:00", end: "24:00" },

  { start: "00:00", end: "24:00" },

  { start: "00:00", end: "24:00" },

  { start: "00:00", end: "24:00" },

  { start: "00:00", end: "24:00" },

  { start: "00:00", end: "24:00" },

  { start: "00:00", end: "24:00" },
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

const legacyRangesKey = (userId: string) => `studyflow_display_ranges_${userId}`

const rangesKey = (userId: string) => `studyflow_display_ranges_v2_${userId}`

export function loadDisplayRanges(userId: string): CalendarDisplayRanges {
  try {
    const saved = localStorage.getItem(rangesKey(userId))
    const value = JSON.parse(
      saved ?? localStorage.getItem(legacyRangesKey(userId)) ?? "null",
    )

    if (
      Array.isArray(value) &&
      value.length === 7 &&
      value.every(
        (range) =>
          range &&
          typeof range.start === "string" &&
          typeof range.end === "string" &&
          !displayRangeError(range),
      )
    )
      return saved === null &&
        value.every(({ start, end }) => start === "08:00" && end === "18:00")
        ? DEFAULT_DISPLAY_RANGES
        : value as unknown as CalendarDisplayRanges
  } catch {
    /* Storage may be unavailable. */
  }

  return DEFAULT_DISPLAY_RANGES
}

export function saveDisplayRanges(
  userId: string,
  ranges: CalendarDisplayRanges,
): void {
  try {
    localStorage.setItem(rangesKey(userId), JSON.stringify(ranges))
  } catch {
    /* The visible setting still works for this session. */
  }
}

export const displayMinutes = (time: string) => clockMinutes(time) ?? 0

const minuteClock = (minutes: number) =>
  `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`

export function rangesIncludingNow(
  ranges: CalendarDisplayRanges,

  todayIndex: number,

  now: number,
): CalendarDisplayRanges {
  const range = ranges[todayIndex]

  const from = displayMinutes(range.start)

  const to = displayMinutes(range.end)

  if (now >= from && now < to) return ranges

  const span = to - from

  const end =
    now < from
      ? Math.min(1440, Math.max(now + 61, span))
      : Math.min(1440, now + 61)

  const start = Math.max(0, Math.min(now - 60, end - span))

  const next = [...ranges] as CalendarDisplayRange[]

  next[todayIndex] = {
    start: minuteClock(start),

    end: minuteClock(end),
  }

  return next as unknown as CalendarDisplayRanges
}

// A source event keeps its clock time; the range only clips what is drawn.

export function eventPosition(time: string, range: CalendarDisplayRange) {
  const start = clockMinutes(time.slice(0, 5))

  const from = displayMinutes(range.start)

  const to = displayMinutes(range.end)

  if (start === null || start < from || start >= to) return null

  return { top: start - from, visibleMinutes: to - start }
}

export interface LanePlacement {
  lane: number

  lanes: number
}

export interface SpanRange {
  start: number

  end: number
}

export interface CalendarSpan {
  id: string

  start: number

  end: number
}

// Sự kiện chồng nhau được chia làn cạnh nhau; mỗi cụm chồng nhau chia đều chiều ngang.
export function eventLanes(
  spans: readonly CalendarSpan[],
): Map<string, LanePlacement> {
  const result = new Map<string, LanePlacement>()

  let cluster: string[] = []

  let laneEnds: number[] = []

  let clusterEnd = -1

  const flush = () => {
    for (const id of cluster)
      result.set(id, {
        lane: result.get(id)?.lane ?? 0,
        lanes: laneEnds.length,
      })

    cluster = []

    laneEnds = []
  }

  for (const span of [...spans].sort(
    (a, b) => a.start - b.start || a.end - b.end,
  )) {
    if (span.start >= clusterEnd) flush()

    let lane = laneEnds.findIndex((end) => end <= span.start)

    if (lane < 0) lane = laneEnds.length

    laneEnds[lane] = span.end

    clusterEnd = cluster.length ? Math.max(clusterEnd, span.end) : span.end

    cluster.push(span.id)

    result.set(span.id, { lane, lanes: 0 })
  }

  flush()

  return result
}

// Mở rộng khung giờ của một ngày (theo giờ tròn) để thấy cả các buổi nằm ngoài khung.
export function rangeCoveringSpans(
  range: CalendarDisplayRange,
  spans: readonly SpanRange[],
): CalendarDisplayRange {
  const from = Math.min(
    displayMinutes(range.start),
    ...spans.map((span) => span.start),
  )

  const to = Math.max(
    displayMinutes(range.end),
    ...spans.map((span) => span.end),
  )

  return {
    start: minuteClock(Math.floor(from / 60) * 60),

    end: minuteClock(Math.min(1440, Math.ceil(to / 60) * 60)),
  }
}
