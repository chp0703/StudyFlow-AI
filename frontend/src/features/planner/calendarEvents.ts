import type { Task } from "../../types/task"

export const eventStart = (event: Task) =>
  event.time.match(/\d{2}:\d{2}/)?.[0] ??
  `${String(event.hour ?? 0).padStart(2, "0")}:${String(event.minute ?? 0).padStart(2, "0")}`

export const orderedDayEvents = (events: Task[], date: string) =>
  events
    .filter((event) => event.date === date)
    .sort(
      (a, b) =>
        eventStart(a).localeCompare(eventStart(b)) || a.id.localeCompare(b.id),
    )
