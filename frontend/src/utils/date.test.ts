import test from "node:test"
import assert from "node:assert/strict"
import {
  addCivilDays,
  civilWeekday,
  vietnamClock,
  vietnamDate,
  vietnamDaysUntil,
} from "./date.ts"

test("Vietnam calendar boundaries preserve the instant across host timezones", () => {
  const before = new Date("2026-11-15T16:59:00Z")
  const monday = new Date("2026-11-15T17:00:00Z")
  assert.equal(vietnamDate(before), "2026-11-15")
  assert.equal(vietnamDate(monday), "2026-11-16")
  assert.equal(vietnamClock(monday), "00:00")
  assert.equal(civilWeekday(vietnamDate(monday)), 0)
  assert.equal(addCivilDays("2026-11-16", 6), "2026-11-22")
  assert.equal(vietnamDaysUntil("2026-11-22", monday), 6)
})
