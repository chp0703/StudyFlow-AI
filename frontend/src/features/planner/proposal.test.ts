import test from "node:test"
import assert from "node:assert/strict"
import {
  demoNoOpResult,
  describeChanges,
  diffTasks,
  hasPendingWeeklyChange,
  isStale,
} from "./proposal.ts"
import { prepareDemoWorkingChange } from "./workingTime.ts"
import { runPlannerCommand } from "./plannerAgent.ts"
import type { Task } from "../../types/task.ts"
import type { Proposal } from "../../types/planner.ts"

const task = (id: number, date?: string, hour?: number): Task => ({
  id: String(id),
  title: `T${id}`,
  course: "c",
  time: "",
  done: false,
  effort: 60,
  priority: "Trung bình",
  deadline: "2026-11-30",
  date,
  hour,
})

test("diffTasks reports added, moved and removed tasks", () => {
  const base = [task(1, "2026-11-06", 9), task(2, "2026-11-06", 10)]
  const next = [task(1, "2026-11-07", 9), task(3, "2026-11-06", 11)]
  const changes = diffTasks(base, next)
  assert.deepEqual(
    changes.map((c) => [c.kind, c.task.id]),
    [
      ["moved", "1"],
      ["added", "3"],
      ["removed", "2"],
    ],
  )
  assert.equal(describeChanges(changes), "Thêm 1 · Dời 1 · Xóa 1")
  assert.equal(diffTasks(base, base).length, 0)
})

test("a proposal is stale once the schedule revision moved on", () => {
  const p = { baseRevision: 2 } as Proposal
  assert.equal(isStale(p, 2), false)
  assert.equal(isStale(p, 3), true)
})

test("a no-op chat command leaves a weekly-only proposal pending for explicit approval", () => {
  const change = prepareDemoWorkingChange(
    [],
    {
      change_type: "ADD",
      window_id: null,
      expected_window_version: null,
      window: {
        kind: "AVAILABILITY",
        label: null,
        recurrence: "WEEKLY",
        timezone: "Asia/Ho_Chi_Minh",
        start_at: null,
        end_at: null,
        weekday: 1,
        start_time: "08:15",
        end_time: "11:30",
        valid_from: "2026-11-01",
        valid_until: null,
      },
    },
    "weekly",
  )!
  const savedWindows: typeof change.windows = []
  const pending = {
    id: "weekly",
    createdAt: 0,
    baseRevision: 0,
    changes: [],
    windowChanges: [],
    issues: [],
    reply: change.description,
    next: { tasks: [], availability: [], weeklyWindows: change.windows },
  } satisfies Proposal
  const command = runPlannerCommand(
    "không hợp lệ",
    [],
    [],
    change.windows,
    true,
  )
  assert.deepEqual(diffTasks([], command.tasks), [])
  assert.deepEqual(command.availability, [])
  const result = demoNoOpResult(pending, command.reply)
  assert.equal(result.proposal, pending)
  assert.equal(result.reply, change.description)
  assert.equal(result.notice, command.reply)
  assert.deepEqual(savedWindows, [])
  assert.deepEqual(result.proposal?.next.weeklyWindows, change.windows)
  assert.deepEqual(demoNoOpResult(null, command.reply), {
    proposal: null,
    reply: command.reply,
    notice: null,
  })
  assert.equal(hasPendingWeeklyChange(pending), true)
  assert.equal(
    hasPendingWeeklyChange({
      ...pending,
      next: { tasks: [], availability: [] },
    }),
    false,
  )
})

test("diffWindows reports new, changed and removed windows", async () => {
  const { diffWindows } = await import("./proposal.ts")
  const w = (hour: number, kind: "free" | "busy") => ({
    id: `d-${hour}`,
    date: "d",
    hour,
    kind,
  })
  const out = diffWindows([w(9, "free"), w(10, "free")], [
    w(9, "busy"),
    w(11, "free"),
  ])
  assert.deepEqual(
    out.map((c) => [c.kind, c.window.hour]),
    [
      ["added", 9],
      ["added", 11],
      ["removed", 10],
    ],
  )
})
