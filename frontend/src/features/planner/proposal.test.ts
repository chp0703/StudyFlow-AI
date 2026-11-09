import test from "node:test"
import assert from "node:assert/strict"
import { describeChanges, diffTasks, isStale } from "./proposal.ts"
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
