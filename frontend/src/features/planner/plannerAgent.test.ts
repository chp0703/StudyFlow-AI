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

test("sets, replaces and clears availability; busy hours are skipped", () => {
  const day = toIsoDate(today)
  let r = runPlannerCommand("rảnh hôm nay từ 9h đến 12h", [])
  assert.equal(r.availability.length, 3)
  assert.ok(r.availability.every((w) => w.kind === "free" && w.date === day))

  r = runPlannerCommand("bận hôm nay lúc 10h", [], r.availability)
  assert.equal(r.availability.length, 3)
  assert.equal(r.availability.find((w) => w.hour === 10)?.kind, "busy")

  const added = runPlannerCommand(
    "thêm Ôn bài hôm nay lúc 10h",
    [],
    r.availability,
  )
  assert.equal(added.tasks[0].hour, 11)

  const out = runPlannerCommand(
    "thêm Ôn bài hôm nay lúc 15h",
    [],
    r.availability,
  )
  assert.match(out.reply, /ngoài khung giờ rảnh/)

  r = runPlannerCommand("xóa rảnh hôm nay", [], r.availability)
  assert.equal(r.availability.length, 0)
})

test("parses dd/mm dates", () => {
  const r = runPlannerCommand("thêm Ôn bài lúc 9h ngày 5/11", [])
  assert.match(r.tasks[0]?.date ?? "", /-11-05$/)
})

test("creates an unscheduled task with deadline and effort", () => {
  const r = runPlannerCommand("tạo công việc Báo cáo hạn 20/12 3 giờ", [])
  assert.equal(r.tasks[0].hour, undefined)
  assert.equal(r.tasks[0].effort, 180)
  assert.match(r.tasks[0].deadline, /-12-20$/)
  assert.match(
    runPlannerCommand("tạo công việc Báo cáo hạn 20/12", r.tasks).reply,
    /cùng tên/,
  )
})
