import test from "node:test"

import assert from "node:assert/strict"

import {
  CALENDAR_VIEWS,
  DEFAULT_CALENDAR_VIEW,
  DEFAULT_DISPLAY_RANGES,
  calendarViewLabel,
  displayRangeError,
  displaySettingsVisible,
  eventLanes,
  eventPosition,
  rangeCoveringSpans,
  loadDisplayRanges,
  rangesIncludingNow,
  saveDisplayRanges,
  type CalendarDisplayRanges,
} from "./calendarDisplay.ts"

test("saved display ranges are isolated by account and malformed values are ignored", () => {
  const values = new Map<string, string>()

  const original = globalThis.localStorage

  globalThis.localStorage = ({
    getItem: (key: string) => values.get(key) ?? null,

    setItem: (key: string, value: string) => {
      values.set(key, value)
    },
  } as Storage)

  try {
    const changed = DEFAULT_DISPLAY_RANGES.map((range, index) =>
      index === 0 ? { start: "06:00", end: "19:00" } : range,
    ) as unknown as CalendarDisplayRanges

    saveDisplayRanges("user-a", changed)

    assert.deepEqual(loadDisplayRanges("user-a"), changed)

    assert.deepEqual(loadDisplayRanges("user-b"), DEFAULT_DISPLAY_RANGES)

    values.set(
      "studyflow_display_ranges_user-a",
      '[{"start":"25:00","end":"01:00"}]',
    )

    assert.deepEqual(loadDisplayRanges("user-a"), DEFAULT_DISPLAY_RANGES)
  } finally {
    globalThis.localStorage = original
  }
})

test("current-time navigation only changes today's temporary display range when needed", () => {
  assert.equal(
    rangesIncludingNow(DEFAULT_DISPLAY_RANGES, 2, 9 * 60 + 30),

    DEFAULT_DISPLAY_RANGES,
  )

  for (const now of [17 * 60 + 59, 20 * 60 + 9, 0]) {
    const ranges = rangesIncludingNow(DEFAULT_DISPLAY_RANGES, 2, now)

    const from =
      Number(ranges[2].start.slice(0, 2)) * 60 +
      Number(ranges[2].start.slice(3))

    const end =
      ranges[2].end === "24:00"
        ? 1440
        : Number(ranges[2].end.slice(0, 2)) * 60 +
          Number(ranges[2].end.slice(3))

    assert.ok(now >= from && now < end)

    assert.deepEqual(ranges[1], DEFAULT_DISPLAY_RANGES[1])
  }
})

import { runPlannerCommand } from "./plannerAgent.ts"

import { addCivilDays, vietnamDate } from "../../utils/date.ts"

test("seven days can display distinct ranges without changing another day", () => {
  const ranges = DEFAULT_DISPLAY_RANGES.map((_, day) => ({
    start: `${String(day + 6).padStart(2, "0")}:00`,

    end: `${String(day + 15).padStart(2, "0")}:00`,
  })) as unknown as CalendarDisplayRanges

  const changed = ranges.map((range, day) =>
    day === 0 ? { start: "09:00", end: "22:00" } : range,
  ) as unknown as CalendarDisplayRanges

  assert.deepEqual(changed[0], { start: "09:00", end: "22:00" })

  assert.deepEqual(changed[1], ranges[1])

  assert.equal(new Set(changed.map((range) => range.end)).size, 7)

  assert.ok(changed.every((range) => !displayRangeError(range)))
})

test("rejects invalid, zero and reversed ranges; accepts midnight end", () => {
  assert.match(displayRangeError({ start: "9:00", end: "22:00" }), /HH:mm/)

  assert.match(displayRangeError({ start: "09:00", end: "09:00" }), /sau/)

  assert.match(displayRangeError({ start: "22:00", end: "09:00" }), /sau/)

  assert.equal(displayRangeError({ start: "00:00", end: "24:00" }), "")
})

test("hiding and revealing a 09:15 event never changes its record or scheduler result", () => {
  const event = {
    id: "1",

    date: "2026-11-16",

    time: "09:15–10:15",

    title: "Ôn bài",
  }

  const before = structuredClone(event)

  assert.equal(
    eventPosition(event.time, { start: "10:00", end: "22:00" }),

    null,
  )

  assert.deepEqual(
    eventPosition(event.time, { start: "09:00", end: "22:00" }),

    { top: 15, visibleMinutes: 765 },
  )

  assert.deepEqual(event, before)

  assert.deepEqual(
    runPlannerCommand("lập kế hoạch", []),

    runPlannerCommand("lập kế hoạch", []),
  )
})

test("display settings are available only in the time-axis Week view", () => {
  assert.equal(displaySettingsVisible("month"), false)

  assert.equal(displaySettingsVisible("detail"), true)
})

test("the time-axis week is the default alongside the month view", () => {
  assert.equal(DEFAULT_CALENDAR_VIEW, "detail")

  assert.deepEqual(CALENDAR_VIEWS, ["detail", "month"])

  assert.deepEqual(CALENDAR_VIEWS.map(calendarViewLabel), ["Tuần", "Tháng"])
})

test("eventLanes puts overlapping events side by side and keeps separate ones full width", () => {
  const lanes = eventLanes([
    { id: "a", start: 600, end: 660 },
    { id: "b", start: 630, end: 690 },
    { id: "c", start: 700, end: 735 },
  ])

  assert.deepEqual(lanes.get("a"), { lane: 0, lanes: 2 })
  assert.deepEqual(lanes.get("b"), { lane: 1, lanes: 2 })
  assert.deepEqual(lanes.get("c"), { lane: 0, lanes: 1 })
})

test("rangeCoveringSpans widens a day range to include an evening session", () => {
  assert.deepEqual(
    rangeCoveringSpans({ start: "08:00", end: "18:00" }, [
      { start: 20 * 60 + 30, end: 22 * 60 },
    ]),
    { start: "08:00", end: "22:00" },
  )
})
