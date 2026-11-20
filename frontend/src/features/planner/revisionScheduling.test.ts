import assert from "node:assert/strict"
import test from "node:test"
import type { ApiTask, OrchestratorReply } from "../../api/types.ts"
import {
  confirmedRevisionTask,
  revisionScheduleArguments,
  revisionScheduleAttempt,
} from "./revisionScheduling.ts"

const task: ApiTask = {
  task_id: "task-server-1",
  title: "Ôn tập: Cơ sở lập trình",
  description: "Ôn lại vòng lặp",
  start_at: "2026-11-20T03:00:00Z",
  available_from_at: "2026-11-20T04:30:15Z",
  deadline_at: "2026-11-22T16:59:00Z",
  deadline_precision: "DATETIME",
  deadline_date: null,
  deadline_timezone: "Asia/Ho_Chi_Minh",
  estimated_minutes: 60,
  remaining_minutes: 60,
  priority: 0.5,
  color: "#596CF0",
  status: "TODO",
}

const confirmedReply = (data: unknown): OrchestratorReply => ({
  request_id: "req-1",
  state: "SUCCEEDED",
  message: "Đã xác nhận",
  action_reference: null,
  questions: [],
  result: { outcome: "COMMITTED", data },
  error: null,
})

test("only a committed confirmed task can trigger revision scheduling", () => {
  assert.equal(
    confirmedRevisionTask(confirmedReply(task))?.task_id,
    task.task_id,
  )
  assert.equal(
    confirmedRevisionTask({
      ...confirmedReply(task),
      state: "AWAITING_APPROVAL",
    }),
    null,
  )
  assert.equal(
    confirmedRevisionTask({
      ...confirmedReply(task),
      result: { outcome: "REJECTED", data: task },
    }),
    null,
  )
})

test("scope selects the server task and never starts before now or availability", () => {
  const arguments_ = revisionScheduleArguments(
    task,
    new Date("2026-11-20T04:00:30Z"),
  )!
  assert.deepEqual(arguments_.generation_scope.task_ids, ["task-server-1"])
  assert.equal(arguments_.generation_scope.selection_mode, "SELECTED_TASKS")
  assert.equal(arguments_.generation_scope.start_at, "2026-11-20T04:31:00.000Z")
  assert.equal(arguments_.generation_scope.end_at, "2026-11-22T16:59:00.000Z")
  assert.equal(
    revisionScheduleArguments(task, new Date("2026-11-23T00:00:00Z")),
    null,
  )
})

test("a concurrent trigger and a retry preserve the exact request and key", () => {
  const first = revisionScheduleAttempt(
    null,
    "user-1",
    task,
    new Date("2026-11-20T04:00:00Z"),
    "stable-key",
  )!
  first.running = true
  const repeated = revisionScheduleAttempt(
    first,
    "user-1",
    task,
    new Date("2026-11-20T05:00:00Z"),
    "different-key",
  )
  assert.equal(repeated, first)
  assert.equal(repeated?.key, "stable-key")
  assert.equal(repeated?.arguments, first.arguments)
  assert.equal(repeated?.sent, false)
})
