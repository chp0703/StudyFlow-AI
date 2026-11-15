import test from "node:test"
import assert from "node:assert/strict"
import { createElement } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { createServer } from "vite"
import { addMonths, monthDates } from "./monthGrid.ts"
import type { Task } from "../../types/task.ts"

test("month rows, Monday boundaries, leap February and year transitions", () => {
  assert.equal(monthDates("2021-02").length, 28)
  assert.equal(monthDates("2026-11").length, 42)
  assert.equal(monthDates("2026-12").length, 35)
  assert.equal(monthDates("2024-02").length, 35)
  assert.equal(monthDates("2026-11")[0], "2026-10-26")
  assert.equal(monthDates("2026-11").at(-1), "2026-12-06")
  assert.equal(addMonths("2026-12", 1), "2027-01")
  assert.equal(addMonths("2027-01", -1), "2026-12")
})

test("month renders real minute events, overflow, proposal and Free/Busy without clipping", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { default: MonthCalendar } = await server.ssrLoadModule(
      "/src/features/planner/MonthCalendar.tsx",
    )
    const events: Task[] = ["10:00", "09:15", "11:30"].map((time, index) => ({
      id: String(index),
      title: `Việc ${index}`,
      date: "2026-11-30",
      time: `${time}–12:00`,
      hour: Number(time.slice(0, 2)),
      effort: 60,
      done: false,
      priority: 0.5,
      deadline: "2026-11-30",
      ...(index === 1 ? { color: "#123456" } : {}),
    }))
    events.push({
      id: "next",
      title: "Đầu tháng sau",
      date: "2026-12-01",
      time: "08:30–09:30",
      hour: 8,
      effort: 60,
      done: false,
      priority: 0.5,
      deadline: "2026-12-01",
    })
    const before = structuredClone(events)
    const html = renderToStaticMarkup(
      createElement(MonthCalendar, {
        month: "2026-11",
        todayKey: "2026-11-13",
        selectedDate: "2026-11-30",
        onSelect: () => {},
        events,
        windows: [],
        availability: [
          { id: "2026-11-30-9", date: "2026-11-30", hour: 9, kind: "busy" },
        ],
        changeOf: new Map([["1", "scheduled"]]),
      }),
    )
    assert.equal((html.match(/role="gridcell"/g) ?? []).length, 42)
    assert.match(html, /aria-label="Ngày 30\/11\/2026"/)
    assert.match(html, /Đầu tháng sau/)
    assert.match(html, /\+1 lịch khác/)
    assert.match(html, /09:15/)
    assert.match(html, /border-left-color:#123456/)
    assert.match(html, /is-proposed/)
    assert.match(html, /Bận 09:00–10:00/)
    assert.match(html, /aria-label="Lịch ngày 2026-11-30"/)
    assert.deepEqual(events, before)
  } finally {
    await server.close()
  }
})
