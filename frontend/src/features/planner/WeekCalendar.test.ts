import test from "node:test"
import assert from "node:assert/strict"
import { createElement } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { createServer } from "vite"
import { DEFAULT_DISPLAY_RANGES } from "./calendarDisplay.ts"

test("calendar renders Free/Busy and proposals behind exact-time events", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { default: WeekCalendar } = await server.ssrLoadModule(
      "/src/features/planner/WeekCalendar.tsx",
    )
    const day = new Date("2026-11-09T12:00:00Z")
    const days = Array.from(
      { length: 7 },
      (_, i) => new Date(day.getTime() + i * 86400000),
    )
    const html = renderToStaticMarkup(
      createElement(WeekCalendar, {
        calendarRef: { current: null },
        weekDays: days,
        week: 1,
        todayIndex: 0,
        ranges: DEFAULT_DISPLAY_RANGES,
        events: [
          {
            id: "task",
            title: "Ôn bài",
            date: "2026-11-09",
            time: "09:15–10:15",
            hour: 9,
            minute: 15,
            effort: 60,
            priority: 0.5,
            done: false,
            deadline: "2026-11-09",
          },
        ],
        windows: [],
        availability: [
          { id: "2026-11-09-9", date: "2026-11-09", hour: 9, kind: "free" },
          { id: "2026-11-09-10", date: "2026-11-09", hour: 10, kind: "busy" },
        ],
        proposedWindowIds: new Set(["2026-11-09-10"]),
        changeOf: new Map([["task", "scheduled"]]),
        prefill: () => {},
        nowHour: 12,
        nowMinutes: 0,
      }),
    )
    assert.match(html, /Rảnh 09:00–10:00/)
    assert.match(html, /Bận 10:00–11:00/)
    assert.match(html, /is-proposed-window/)
    assert.match(html, /data-task-id="task"[^>]*top:60px/)
    assert.match(html, /09:15–10:15/)
    const apiHtml = renderToStaticMarkup(
      createElement(WeekCalendar, {
        calendarRef: { current: null },
        weekDays: days,
        week: 1,
        todayIndex: 0,
        ranges: [
          { start: "10:00", end: "11:00" },
          ...DEFAULT_DISPLAY_RANGES.slice(1),
        ],
        events: [],
        windows: [
          {
            window_id: "api-busy",
            version: 1,
            kind: "BUSY",
            label: null,
            recurrence: "NONE",
            timezone: "Asia/Ho_Chi_Minh",
            start_at: "2026-11-09T09:45:00+07:00",
            end_at: "2026-11-09T10:15:00+07:00",
            weekday: null,
            start_time: null,
            end_time: null,
            valid_from: null,
            valid_until: null,
            archived_at: null,
          },
        ],
        availability: [],
        proposedWindowIds: new Set(),
        changeOf: new Map(),
        prefill: () => {},
        nowHour: 12,
        nowMinutes: 0,
      }),
    )
    assert.match(apiHtml, /Bận 10:00–10:15/)
    assert.doesNotMatch(apiHtml, /Bận 09:45/)
  } finally {
    await server.close()
  }
})
