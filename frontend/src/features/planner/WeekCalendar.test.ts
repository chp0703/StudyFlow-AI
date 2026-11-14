import test from "node:test"
import assert from "node:assert/strict"
import { createElement } from "react"
import {
  Children,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from "react"
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

const findSlot = (node: ReactNode, label: string): ReactElement | null => {
  if (!isValidElement(node)) return null
  const props = node.props as Record<string, unknown>
  if (node.type === "button" && props["aria-label"] === label) return node
  for (const child of Children.toArray(props.children as ReactNode)) {
    const found = findSlot(child, label)
    if (found) return found
  }
  return null
}

test("slot clicks preserve exact minutes through Planner prefill without submitting", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { default: WeekCalendar } = await server.ssrLoadModule(
      "/src/features/planner/WeekCalendar.tsx",
    )
    const { prefillPlannerCommand } = await server.ssrLoadModule(
      "/src/features/planner/plannerPrefill.ts",
    )
    const originalRaf = globalThis.requestAnimationFrame
    globalThis.requestAnimationFrame = (((callback: FrameRequestCallback) => {
      callback(0)
      return 1
    }) as typeof requestAnimationFrame)
    try {
      const focusCalls: string[] = []
      const selections: number[][] = []
      const textarea = {
        focus: () => {
          focusCalls.push("focus")
        },
        setSelectionRange: (start: number, end: number) => {
          selections.push([start, end])
        },
      } as unknown as HTMLTextAreaElement
      const drafts: string[] = []
      let mutations = 0
      const starts = ["08:00", "09:15", "10:30", "16:45"]
      const monday = new Date("2026-11-30T12:00:00Z")
      const days = Array.from(
        { length: 7 },
        (_, i) => new Date(monday.getTime() + i * 86400000),
      )

      for (const [index, start] of starts.entries()) {
        const minute = Number(start.slice(0, 2)) * 60 + Number(start.slice(3))
        const endMinute = minute + 60
        const end = `${String(Math.floor(endMinute / 60)).padStart(2, "0")}:${String(endMinute % 60).padStart(2, "0")}`
        const ranges = DEFAULT_DISPLAY_RANGES.map((range, day) =>
          day === index ? { start, end } : range,
        )
        const tree = WeekCalendar({
          calendarRef: { current: null },
          weekDays: days,
          week: 1,
          todayIndex: 0,
          ranges,
          events: [],
          windows: [],
          availability: [],
          proposedWindowIds: new Set(),
          changeOf: new Map(),
          prefill: (date: Date, minuteOfDay: number) =>
            prefillPlannerCommand(
              date,
              minuteOfDay,
              false,
              (value: string) => drafts.push(value),
              textarea,
            ),
          nowHour: 12,
          nowMinutes: 0,
        })
        const dateKey = days[index].toISOString().slice(0, 10)
        const slot = findSlot(
          tree,
          `${["T2", "T3", "T4", "T5"][index]} ${dateKey} lúc ${start}; nhập yêu cầu lịch học`,
        )
        assert.ok(slot)
        ;(slot.props as { onClick: () => void }).onClick()
        assert.match(drafts.at(-1) ?? "", new RegExp(`${start}.*ngày`))
      }

      assert.match(drafts[1], /09:15 ngày 1\/12\/2026/)
      assert.equal(focusCalls.length, starts.length)
      assert.deepEqual(
        selections,
        starts.map(() => [5, 5]),
      )
      assert.equal(mutations, 0)

      const nextWeek = days.map(
        (date) => new Date(date.getTime() + 7 * 86400000),
      )
      const navigationDrafts: string[] = []
      prefillPlannerCommand(
        nextWeek[0],
        9 * 60 + 15,
        false,
        (value: string) => navigationDrafts.push(value),
        null,
      )
      assert.match(navigationDrafts[0], /09:15 ngày 7\/12\/2026/)

      const apiDrafts: string[] = []
      prefillPlannerCommand(
        days[0],
        9 * 60 + 15,
        true,
        (value: string) => apiDrafts.push(value),
        null,
      )
      assert.doesNotMatch(apiDrafts[0], /09:15|bắt đầu/iu)
    } finally {
      globalThis.requestAnimationFrame = originalRaf
    }
  } finally {
    await server.close()
  }
})
