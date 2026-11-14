export const today = new Date()

today.setHours(12, 0, 0, 0)

export const toIsoDate = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`

export const daysUntil = (iso: string) => vietnamDaysUntil(iso)

export const formatShortDate = (iso: string) =>
  new Date(`${iso}T12:00:00Z`).toLocaleDateString("vi-VN", {
    day: "numeric",
    month: "long",
    timeZone: "Asia/Ho_Chi_Minh",
  })

export const PLANNER_TIMEZONE = "Asia/Ho_Chi_Minh"

const parts = (instant: Date) =>
  Object.fromEntries(
    new Intl.DateTimeFormat("en-US", {
      timeZone: PLANNER_TIMEZONE,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(instant)
      .map((part) => [part.type, part.value]),
  )

export const vietnamDate = (instant: Date = new Date()) => {
  const { year, month, day } = parts(instant)
  return `${year}-${month}-${day}`
}

export const vietnamClock = (instant: Date = new Date()) => {
  const { hour, minute } = parts(instant)
  return `${hour}:${minute}`
}

// Civil dates use UTC arithmetic; YYYY-MM-DD is never parsed as a local instant.
export const addCivilDays = (iso: string, days: number) => {
  const [year, month, day] = iso.split("-").map(Number)
  return new Date(Date.UTC(year, month - 1, day + days))
    .toISOString()
    .slice(0, 10)
}

export const civilWeekday = (iso: string) => {
  const [year, month, day] = iso.split("-").map(Number)
  return (new Date(Date.UTC(year, month - 1, day)).getUTCDay() + 6) % 7
}

export const vietnamDaysUntil = (iso: string, now = new Date()) => {
  const start = Date.parse(`${vietnamDate(now)}T00:00:00Z`)
  const end = Date.parse(`${iso}T00:00:00Z`)
  return Math.round((end - start) / 86400000)
}
