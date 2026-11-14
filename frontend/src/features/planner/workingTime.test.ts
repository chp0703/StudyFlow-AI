import test from "node:test"
import assert from "node:assert/strict"
import { visibleSegments } from "./workingTime.ts"
import type { ApiTimeWindow } from "../../api/types.ts"

const window = (over: Partial<ApiTimeWindow>): ApiTimeWindow => ({
  window_id: "free",
  version: 1,
  kind: "AVAILABILITY",
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

test("visible Free/Busy intervals keep minutes, merge hours, and clip without mutation", () => {
  const windows = [
    window({}),
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
    { start: 600, end: 630, kind: "free" },
    { start: 630, end: 675, kind: "busy" },
    { start: 675, end: 705, kind: "free" },
  ])
  assert.deepEqual(windows, before)
  assert.deepEqual(visibleSegments("2026-11-09", 720, 780, windows), [])
})

test("legacy demo cells remain visible and Busy overrides Free", () => {
  assert.deepEqual(
    visibleSegments("2026-11-09", 540, 660, [window({})], [
      { id: "2026-11-09-9", date: "2026-11-09", hour: 9, kind: "busy" },
    ]),
    [
      { start: 540, end: 600, kind: "busy" },
      { start: 600, end: 660, kind: "free" },
    ],
  )
})
