import test from "node:test"
import assert from "node:assert/strict"
import { runPlannerCommand } from "./plannerAgent.ts"
import { toIsoDate, today } from "../../utils/date.ts"

test("adds, moves around conflicts, and deletes", () => {
  const day = toIsoDate(today)
  let r = runPlannerCommand("thêm Ôn giải tích hôm nay lúc 9h", [])
  assert.equal(r.tasks.length, 1)
  assert.equal(r.tasks[0].hour, 9)
  assert.equal(r.tasks[0].date, day)

  r = runPlannerCommand("thêm Làm bài tập hôm nay lúc 9h", r.tasks)
  assert.equal(r.tasks[1].hour, 10)

  r = runPlannerCommand("dời ôn giải tích sang ngày mai lúc 14h", r.tasks)
  assert.equal(r.tasks[0].hour, 14)
  assert.notEqual(r.tasks[0].date, day)

  r = runPlannerCommand("xóa làm bài tập", r.tasks)
  assert.equal(r.tasks.length, 1)
})

test("rejects missing info and out-of-range hours", () => {
  assert.equal(runPlannerCommand("thêm Ôn bài", []).tasks.length, 0)
  assert.equal(
    runPlannerCommand("thêm Ôn bài hôm nay lúc 22h", []).tasks.length,
    0,
  )
  assert.match(runPlannerCommand("hello", []).reply, /lệnh/)
})
