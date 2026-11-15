import test from "node:test"
import assert from "node:assert/strict"
import {
  approvalBlocked,
  demoNoOpResult,
  describeChanges,
  diffTasks,
  isStale,
} from "./proposal.ts"
import { runPlannerCommand } from "./plannerAgent.ts"
import type { Task } from "../../types/task.ts"
import type { Proposal } from "../../types/planner.ts"

const task = (id: number, date?: string, hour?: number): Task => ({
  id: String(id),
  title: `T${id}`,
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

test("a no-op command keeps a pending task proposal for explicit approval", () => {
  const pending = {
    id: "task",
    createdAt: 0,
    baseRevision: 0,
    changes: [{ kind: "added" as const, task: task(1) }],
    windowChanges: [],
    issues: [],
    reply: "Đề xuất thêm công việc",
    next: { tasks: [task(1)], availability: [] },
  } satisfies Proposal
  const response = runPlannerCommand("không hợp lệ", [], []).reply
  const result = demoNoOpResult(pending, response)
  assert.equal(result.proposal, pending)
  assert.equal(result.notice, response)
  assert.deepEqual(demoNoOpResult(null, response), {
    proposal: null,
    reply: response,
    notice: null,
  })
})

test("unsupported free-time commands keep the pending proposal intact", () => {
  const pending = {
    id: "task",
    createdAt: 0,
    baseRevision: 0,
    changes: [{ kind: "added" as const, task: task(1) }],
    windowChanges: [],
    issues: [],
    reply: "Đề xuất thêm công việc",
    next: { tasks: [task(1)], availability: [] },
  } satisfies Proposal
  for (const command of ["rảnh hôm nay từ 9h đến 12h", "xóa rảnh hôm nay"]) {
    const response = runPlannerCommand(
      command,
      pending.next.tasks,
      pending.next.availability,
    )
    assert.deepEqual(response.tasks, pending.next.tasks)
    assert.deepEqual(response.availability, pending.next.availability)
    assert.equal(demoNoOpResult(pending, response.reply).proposal, pending)
  }
})

test("unresolved server proposals are blocked independently of stale state", () => {
  const unresolved = {
    baseRevision: 1,
    server: { approvalError: "Không thể xác minh" },
  } as Proposal
  assert.equal(approvalBlocked(unresolved, false), true)
  assert.equal(approvalBlocked({ baseRevision: 1 } as Proposal, false), false)
  assert.equal(approvalBlocked({ baseRevision: 1 } as Proposal, true), true)
})

test("an invalid command is a no-op against the pending preview", () => {
  const base: Task[] = []
  const preview: Task[] = [task(1, "2026-11-20", 9)]
  const result = runPlannerCommand("không hợp lệ", preview, [])

  assert.deepEqual(diffTasks(preview, result.tasks), [])
  assert.equal(diffTasks(base, result.tasks).length, 1)
  assert.match(result.reply, /Ví dụ/)
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
