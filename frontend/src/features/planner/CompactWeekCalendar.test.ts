import test from "node:test"
import assert from "node:assert/strict"
import { createElement } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { createServer } from "vite"
import type { Task } from "../../types/task.ts"

test("compact week shows seven Vietnam dates, sorted exact times, Free/Busy and more", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const {
      default: CompactWeekCalendar,
      orderedDayEvents,
      eventStart,
    } = await server.ssrLoadModule(
      "/src/features/planner/CompactWeekCalendar.tsx",
    )
    const monday = Date.parse("2026-11-09T12:00:00Z")
    const weekDays = Array.from(
      { length: 7 },
      (_, day) => new Date(monday + day * 86400000),
    )
    const events: Task[] = ["11:00", "09:15", "10:00", "13:00"].map(
      (time, index) => ({
        id: String(index),
        title: `Việc ${index}`,
        date: "2026-11-09",
        time: `${time}–14:00`,
        hour: Number(time.slice(0, 2)),
        effort: 60,
        done: false,
        priority: 0.5,
        deadline: "2026-11-09",
        ...(index === 1 ? { color: "#123456" } : {}),
      }),
    )
    const before = structuredClone(events)
    const html = renderToStaticMarkup(
      createElement(CompactWeekCalendar, {
        weekDays,
        todayKey: "2026-11-09",
        events,
        windows: [],
        availability: [
          { id: "2026-11-09-9", date: "2026-11-09", hour: 9, kind: "busy" },
        ],
        changeOf: new Map([["1", "scheduled"]]),
        proposedWindowIds: new Set(),
      }),
    )
    assert.equal((html.match(/class="compact-day(?: |")/g) ?? []).length, 7)
    assert.match(html, /T2.*09\/11/)
    assert.match(html, /CN.*15\/11/)
    assert.deepEqual(orderedDayEvents(events, "2026-11-09").map(eventStart), [
      "09:15",
      "10:00",
      "11:00",
      "13:00",
    ])
    assert.match(html, /border-left-color:#123456/)
    assert.match(html, /\+1 lịch khác/)
    assert.match(html, /Bận 09:00–10:00/)
    assert.match(html, /is-scheduled/)
    assert.match(html, /aria-label="Chi tiết ngày 2026-11-09"/)
    assert.deepEqual(events, before)
  } finally {
    await server.close()
  }
})
