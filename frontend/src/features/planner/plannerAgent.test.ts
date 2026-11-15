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

test("free-time commands are read-only while busy operations remain supported", () => {
  const day = toIsoDate(today)
  const existing = [
    { id: `${day}-9`, date: day, hour: 9, kind: "free" as const },
  ]
  const free = runPlannerCommand("rảnh hôm nay từ 9h đến 12h", [], existing)
  assert.equal(free.availability, existing)
  assert.deepEqual(free.tasks, [])
  assert.match(free.reply, /không hỗ trợ.*giờ rảnh/iu)

  const cleared = runPlannerCommand("xóa rảnh hôm nay", [], existing)
  assert.equal(cleared.availability, existing)
  assert.match(cleared.reply, /Chi tiết giờ/)

  let r = runPlannerCommand("bận hôm nay lúc 10h", [], existing)
  assert.equal(r.availability.length, 2)
  assert.equal(r.availability.find((w) => w.hour === 10)?.kind, "busy")

  const added = runPlannerCommand(
    "thêm Ôn bài hôm nay lúc 10h",
    [],
    r.availability,
  )
  assert.equal(added.tasks[0].hour, 11)

  r = runPlannerCommand("xóa bận hôm nay", [], r.availability)
  assert.deepEqual(r.availability, existing)
})

test("parses dd/mm dates", () => {
  const r = runPlannerCommand("thêm Ôn bài lúc 9h ngày 5/11", [])
  assert.match(r.tasks[0]?.date ?? "", /-11-05$/)
})

test("an explicit prefill year preserves a past calendar date", () => {
  const result = runPlannerCommand("thêm Ôn bài lúc 09:15 ngày 9/11/2026", [])
  assert.equal(result.tasks[0]?.date, "2026-11-09")
  assert.equal(result.tasks[0]?.minute, 15)
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

test("plans unscheduled tasks deterministically and reports what does not fit", () => {
  const d = (n: number) => {
    const x = new Date(today)
    x.setDate(x.getDate() + n)
    return toIsoDate(x)
  }
  const mk = (id: number, deadline: string, priority = "Trung bình") =>
    ({
      id: String(id),
      title: `T${id}`,
      time: "",
      done: false,
      effort: 60,
      priority,
      deadline,
    }) as const
  const tasks = [mk(1, d(3)), mk(2, d(1), "Cao"), mk(3, d(-1))]
  const a = runPlannerCommand("lập kế hoạch", tasks as never)
  const b = runPlannerCommand("lập kế hoạch", tasks as never)
  assert.deepEqual(a, b)
  const by = (id: number) => a.tasks.find((t) => t.id === String(id))!
  assert.ok(by(2).date! <= d(1) && by(1).date! <= d(3))
  assert.equal(by(3).date, undefined)
  assert.deepEqual(
    a.issues?.map((i) => i.taskId),
    ["3"],
  )
})

test("preserves a requested non-round demo start exactly", () => {
  const result = runPlannerCommand("thêm Ôn bài hôm nay lúc 09:15", [])
  assert.equal(result.tasks[0].time, "09:15 – 10:15")
  assert.equal(result.tasks[0].minute, 15)
  assert.equal(result.tasks[0].priority, 0.5)
  assert.match(result.reply, /09:15/)
  const conflict = runPlannerCommand(
    "thêm Bài khác hôm nay lúc 09:15",
    result.tasks,
  )
  assert.equal(conflict.tasks.length, 1)
  assert.match(conflict.reply, /09:15/)
  const overlap = runPlannerCommand(
    "thêm Việc khác hôm nay lúc 10h",
    result.tasks,
  )
  assert.equal(overlap.tasks[1].hour, 11)
})
