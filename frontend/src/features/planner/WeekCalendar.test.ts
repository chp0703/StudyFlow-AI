import test, { after, before } from "node:test"

import assert from "node:assert/strict"

import { createElement } from "react"

import {
  Children,
  isValidElement,
  type ReactElement,
  type ReactNode,
} from "react"

import { renderToStaticMarkup } from "react-dom/server"

import { createServer, type ViteDevServer } from "vite"

import { DEFAULT_DISPLAY_RANGES } from "./calendarDisplay.ts"

let server: ViteDevServer

before(async () => {
  server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
})

after(async () => {
  await server.close()
})

test("calendar renders Busy windows and proposals behind exact-time events", async () => {
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

        onRangesChange: () => {},

        events: [
          {
            id: "task",

            title: "Ôn bài",

            color: "#6c5ce7",

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
          { id: "2026-11-09-7", date: "2026-11-09", hour: 7, kind: "busy" },

          { id: "2026-11-09-10", date: "2026-11-09", hour: 10, kind: "busy" },
        ],

        proposedWindowIds: new Set(["2026-11-09-10"]),

        changeOf: new Map([["task", "scheduled"]]),

        prefill: () => {},

        nowHour: 12,

        nowMinutes: 0,
      }),
    )

    assert.match(html, /Bận 07:00–08:00/)

    assert.match(html, /lúc 00:00; nhập yêu cầu lịch học/)

    assert.match(html, /lúc 23:00; nhập yêu cầu lịch học/)

    assert.doesNotMatch(html, /ngoài khung · Hiện/)

    assert.doesNotMatch(html, /Rảnh/)

    assert.match(html, /Bận 10:00–11:00/)

    assert.match(html, /is-proposed-window/)

    assert.match(html, /--evt:#6c5ce7/)

    assert.match(html, /--evt-ink:color-mix\(in srgb, #6c5ce7 45%, black\)/)

    assert.match(html, /Tím · Ôn tập/)

    assert.match(html, /data-task-id="task"[^>]*top:444px/)

    assert.match(html, /09:15–10:15/)

    assert.equal(html.match(/class="schedule-time-column"/g)?.length, 1)

    assert.equal(html.match(/class="schedule-time-label"/g)?.length, 24)

    assert.doesNotMatch(
      html,

      /<button[^>]*class="schedule-time-slot"[^>]*>[^<]+</,
    )

    assert.match(
      html,

      /class="schedule-time-corner"[\s\S]*aria-label="Tùy chỉnh giờ hiển thị"/,
    )

    assert.doesNotMatch(
      html,

      /class="calendar-settings-toggle"[^>]*>[^<]*Tùy chỉnh giờ hiển thị/,
    )

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
          {
            window_id: "api-free",

            version: 1,

            kind: "AVAILABILITY",

            label: null,

            recurrence: "NONE",

            timezone: "Asia/Ho_Chi_Minh",

            start_at: "2026-11-09T10:15:00+07:00",

            end_at: "2026-11-09T10:45:00+07:00",

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

    assert.match(apiHtml, /Bận 09:45–10:15/)

    assert.doesNotMatch(apiHtml, /Rảnh/)
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
})

test("short 25m and 45m cards use compact single-row class and sticky header reveals hidden or clipped events", async () => {
    const { default: WeekCalendar } = await server.ssrLoadModule(
      "/src/features/planner/WeekCalendar.tsx",
    )
    const monday = new Date("2026-11-23T12:00:00Z")
    const days = Array.from(
      { length: 7 },
      (_, i) => new Date(monday.getTime() + i * 86400000),
    )
    const narrowedRanges = DEFAULT_DISPLAY_RANGES.map((range, index) =>
      index === 3 ? { start: "08:00", end: "18:00" } : range,
    )
    const expanded: unknown[] = []
    const tree = WeekCalendar({
      calendarRef: { current: null },
      weekDays: days,
      week: 0,
      todayIndex: 4,
      ranges: narrowedRanges as unknown as typeof DEFAULT_DISPLAY_RANGES,
      onRangesChange: (next: unknown) => expanded.push(next),
      events: [
        {
          id: "s-45",
          title: "Ôn Chương 1",
          date: "2026-11-28",
          time: "09:00–09:45",
          hour: 9,
          effort: 45,
          priority: 0.5,
          done: false,
          deadline: "2026-11-28",
        },
        {
          id: "s-90",
          title: "Ôn Chương 2",
          date: "2026-11-28",
          time: "09:55–11:25",
          hour: 9,
          effort: 90,
          priority: 0.5,
          done: false,
          deadline: "2026-11-28",
        },
        {
          id: "s-25",
          title: "Ôn Chương 3",
          date: "2026-11-28",
          time: "11:35–12:00",
          hour: 11,
          effort: 25,
          priority: 0.1,
          done: false,
          deadline: "2026-11-28",
        },
        {
          id: "late-clipped",
          title: "Học Lý",
          date: "2026-11-26",
          time: "17:30–19:00",
          hour: 17,
          effort: 90,
          priority: 0.5,
          done: false,
          deadline: "2026-11-26",
        },
        {
          id: "late-hidden",
          title: "Học Hóa",
          date: "2026-11-26",
          time: "20:30–22:00",
          hour: 20,
          effort: 90,
          priority: 1,
          done: false,
          deadline: "2026-11-26",
        },
      ],
      windows: [],
      availability: [],
      proposedWindowIds: new Set(),
      changeOf: new Map(),
      prefill: () => {},
      nowHour: 12,
      nowMinutes: 0,
    })
    const html = renderToStaticMarkup(tree)

    // 25m and 45m cards get compact 1-row class; 90m stays standard 2-row
    assert.match(html, /is-compact[^"]*"[^>]*data-task-id="s-25"/)
    assert.match(html, /is-compact[^"]*"[^>]*data-task-id="s-45"/)
    assert.doesNotMatch(html, /is-compact[^"]*"[^>]*data-task-id="s-90"/)

    // Sticky day header shows both completely outside (20:30) and end-clipped (17:30-19:00) events
    assert.match(html, /schedule-header[\s\S]*2 buổi ngoài khung · Hiện[\s\S]*schedule-columns/)

    // Clicking the reveal button expands only Thursday to cover up to 22:00
    const findHiddenBtn = (node: ReactNode): ReactElement | null => {
      if (!isValidElement(node)) return null
      const props = node.props as Record<string, unknown>
      if (node.type === "button" && props.className === "schedule-hidden-events") return node
      for (const child of Children.toArray(props.children as ReactNode)) {
        const hit = findHiddenBtn(child)
        if (hit) return hit
      }
      return null
    }
    const btn = findHiddenBtn(tree)
    assert.ok(btn)
    ;(btn.props as { onClick: () => void }).onClick()
    const nextRanges = expanded[0] as Array<{ start: string; end: string }>
    assert.deepEqual(nextRanges[3], { start: "08:00", end: "22:00" })
})
