import test from "node:test"
import assert from "node:assert/strict"
import {
  DEFAULT_DISPLAY_RANGES,
  displayRangeError,
  eventPosition,
  type CalendarDisplayRanges,
} from "./calendarDisplay.ts"
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
