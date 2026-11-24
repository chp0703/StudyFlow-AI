import test from "node:test"
import assert from "node:assert/strict"
import { visibleSegments } from "./workingTime.ts"
import type { ApiTimeWindow } from "../../api/types.ts"

const window = (over: Partial<ApiTimeWindow>): ApiTimeWindow => ({
  window_id: "busy-weekly",
  version: 1,
  kind: "BUSY",
  label: null,
  recurrence: "WEEKLY",
  timezone: "Asia/Ho_Chi_Minh",
  start_at: null,
  end_at: null,
  weekday: 1,
  start_time: "09:15",
  end_time: "11:45",
  valid_from: null,
  valid_until: null,
  archived_at: null,
  ...over,
})

test("visible Busy intervals keep minutes, merge hours, ignore AVAILABILITY, and clip without mutation", () => {
  const windows = [
    window({ window_id: "free", kind: "AVAILABILITY" }),
    window({ start_time: "09:45", end_time: "10:15" }),
    window({
      window_id: "busy",
      kind: "BUSY",
      recurrence: "NONE",
      weekday: null,
      start_time: null,
      end_time: null,
      start_at: "2026-11-09T10:30:00+07:00",
      end_at: "2026-11-09T11:15:00+07:00",
    }),
  ]
  const before = structuredClone(windows)
  assert.deepEqual(visibleSegments("2026-11-09", 600, 720, windows), [
    { start: 600, end: 615, kind: "busy" },
    { start: 630, end: 675, kind: "busy" },
  ])
  assert.deepEqual(windows, before)
  assert.deepEqual(visibleSegments("2026-11-09", 720, 780, windows), [])
})

test("legacy demo busy cells remain visible while AVAILABILITY windows are ignored", () => {
  assert.deepEqual(
    visibleSegments(
      "2026-11-09",
      540,
      660,
      [window({ window_id: "free", kind: "AVAILABILITY" })],
      [{ id: "2026-11-09-9", date: "2026-11-09", hour: 9, kind: "busy" }],
    ),
    [{ start: 540, end: 600, kind: "busy" }],
  )
})
