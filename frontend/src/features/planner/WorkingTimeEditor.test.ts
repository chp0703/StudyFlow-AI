import test from "node:test"
import assert from "node:assert/strict"
import { intervalError } from "./workingTime.ts"
import {
  fullWorkingHour,
  hourSegments,
  prepareDemoWorkingChange,
} from "./workingTime.ts"
import type { ApiTimeWindow } from "../../api/types.ts"
import { isStale } from "./proposal.ts"
import type { Proposal } from "../../types/planner.ts"
import { execFileSync } from "node:child_process"

const weekly = (
  weekday: number,
  start_time: string,
  end_time: string,
  kind: ApiTimeWindow["kind"] = "AVAILABILITY",
): ApiTimeWindow => ({
  window_id: `${weekday}-${start_time}-${kind}`,
  version: 1,
  kind,
  label: null,
  recurrence: "WEEKLY",
  timezone: "Asia/Ho_Chi_Minh",
  start_at: null,
  end_at: null,
  weekday,
  start_time,
  end_time,
  valid_from: "2026-11-01",
  valid_until: null,
  archived_at: null,
})

test("weekly working intervals allow separated periods and reject overlap", () => {
  const morning = [{ start_time: "08:00", end_time: "11:00" }]
  assert.equal(intervalError("14:00", "17:30", morning), "")
  assert.equal(intervalError("20:00", "24:00", morning), "")
  assert.match(intervalError("10:30", "12:00", morning), /trùng/)
  assert.match(intervalError("18:00", "17:00", []), /sau/)
  assert.equal(intervalError("11:00", "12:00", morning), "")
  for (const value of ["", "8:00", "24:00", "09:60", "abc"])
    assert.match(intervalError(value, "12:00", []), /hợp lệ/)
  assert.match(intervalError("08:00", "24:01", []), /hợp lệ/)
})

test("Monday to Sunday intervals retain exact minutes, including 24:00", () => {
  for (let weekday = 1; weekday <= 7; weekday++) {
    const date = new Date(Date.UTC(2026, 10, 15 + weekday))
      .toISOString()
      .slice(0, 10)
    const windows = [weekly(weekday, "08:15", "09:45")]
    assert.deepEqual(hourSegments(date, 8, windows), [
      { start: 495, end: 540, kind: "free" },
    ])
    assert.deepEqual(hourSegments(date, 9, windows), [
      { start: 540, end: 585, kind: "free" },
    ])
    assert.equal(fullWorkingHour(date, 8, windows, [], true), false)
    assert.equal(fullWorkingHour(date, 9, windows, [], true), false)
  }
  assert.deepEqual(
    hourSegments("2026-11-16", 23, [weekly(1, "23:00", "24:00")]),
    [{ start: 1380, end: 1440, kind: "free" }],
  )
})

test("busy intervals split working time into exact fragments", () => {
  const date = "2026-11-16"
  const windows = [
    weekly(1, "08:00", "12:00"),
    weekly(1, "09:30", "10:15", "BUSY"),
  ]
  assert.deepEqual(hourSegments(date, 9, windows), [
    { start: 540, end: 570, kind: "free" },
    { start: 570, end: 600, kind: "busy" },
  ])
  assert.deepEqual(hourSegments(date, 10, windows), [
    { start: 600, end: 615, kind: "busy" },
    { start: 615, end: 660, kind: "free" },
  ])
  assert.equal(fullWorkingHour(date, 9, windows, [], true), false)
  assert.equal(fullWorkingHour(date, 8, windows, [], true), true)
  assert.equal(
    fullWorkingHour(
      date,
      13,
      windows,
      [{ id: `${date}-13`, date, hour: 13, kind: "free" }],
      true,
    ),
    true,
  )
  assert.equal(
    fullWorkingHour(
      date,
      8,
      windows,
      [{ id: `${date}-8`, date, hour: 8, kind: "busy" }],
      true,
    ),
    false,
  )
  const fragments = [weekly(1, "08:05", "08:15"), weekly(1, "08:40", "08:50")]
  assert.deepEqual(hourSegments(date, 8, fragments), [
    { start: 485, end: 495, kind: "free" },
    { start: 520, end: 530, kind: "free" },
  ])
})

test("demo preparation is immutable, versioned, and can leave a day empty", () => {
  const input = weekly(1, "08:15", "11:30")
  const add = prepareDemoWorkingChange(
    [],
    {
      change_type: "ADD",
      window_id: null,
      expected_window_version: null,
      window: input,
    },
    "new",
  )!
  assert.equal(add.windows.length, 1)
  assert.match(add.description, /Thứ 2: chưa có → 08:15–11:30/)
  const original = add.windows
  const updated = prepareDemoWorkingChange(
    original,
    {
      change_type: "UPDATE",
      window_id: "new",
      expected_window_version: 1,
      window: weekly(1, "14:00", "17:45"),
    },
    "unused",
  )!
  assert.equal(original[0].start_time, "08:15")
  assert.equal(updated.windows[0].start_time, "14:00")
  assert.equal(updated.windows[0].version, 2)
  assert.equal(
    prepareDemoWorkingChange(
      updated.windows,
      {
        change_type: "ARCHIVE",
        window_id: "new",
        expected_window_version: 1,
        window: null,
      },
      "unused",
    ),
    null,
  )
  const archived = prepareDemoWorkingChange(
    updated.windows,
    {
      change_type: "ARCHIVE",
      window_id: "new",
      expected_window_version: 2,
      window: null,
    },
    "unused",
  )!
  assert.deepEqual(archived.windows, [])
  assert.equal(isStale({ baseRevision: 3 } as Proposal, 4), true)
})

test("weekly segments keep Vietnam dates across host timezones and week transitions", () => {
  const script = `import { hourSegments } from './src/features/planner/workingTime.ts';
const w = ${JSON.stringify(weekly(1, "08:15", "09:45"))};
process.stdout.write(JSON.stringify(['2026-11-09','2026-11-16','2026-11-23','2026-11-15','2026-11-17'].map(d => hourSegments(d, 8, [w]))));`
  const values = ["UTC", "America/Los_Angeles", "Asia/Ho_Chi_Minh"].map((TZ) =>
    execFileSync(process.execPath, ["--input-type=module", "-e", script], {
      cwd: process.cwd(),
      env: { ...process.env, TZ },
      encoding: "utf8",
    }),
  )
  assert.equal(values[0], values[1])
  assert.equal(values[1], values[2])
  const days = JSON.parse(values[0])
  assert.deepEqual(
    days.map((items: unknown[]) => items.length),
    [1, 1, 1, 0, 0],
  )
})
