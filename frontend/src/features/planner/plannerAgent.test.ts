import test from "node:test"
import assert from "node:assert/strict"
import { runPlannerCommand } from "./plannerAgent.ts"
import { toIsoDate, today } from "../../utils/date.ts"
import { addCivilDays, civilWeekday, vietnamDate } from "../../utils/date.ts"
import type { ApiTimeWindow } from "../../api/types.ts"

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

test("demo scheduler only uses complete hour blocks within configured weekly time", () => {
  const tomorrow = addCivilDays(vietnamDate(), 1)
  const weekday = civilWeekday(tomorrow) + 1
  const window = (
    start_time: string,
    end_time: string,
    kind: ApiTimeWindow["kind"] = "AVAILABILITY",
  ): ApiTimeWindow => ({
    window_id: `${kind}-${start_time}`,
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
    valid_from: vietnamDate(),
    valid_until: null,
    archived_at: null,
  })
  const task = {
    id: "weekly-demo",
    title: "Ôn bài",
    course: "",
    time: "",
    done: false,
    effort: 60,
    priority: "Trung bình",
    deadline: tomorrow,
  }
  const partial = runPlannerCommand(
    "lập kế hoạch",
    [task],
    [],
    [window("08:15", "09:45")],
    true,
  )
  assert.equal(partial.tasks[0].hour, undefined)
  assert.equal(partial.issues?.length, 1)
  const [, month, day] = tomorrow.split("-")
  const manual = runPlannerCommand(
    `thêm Ôn bài lúc 8h ngày ${Number(day)}/${Number(month)}`,
    [],
    [],
    [window("08:15", "09:45")],
    true,
  )
  assert.equal(manual.tasks.length, 0)
  const full = runPlannerCommand(
    "lập kế hoạch",
    [task],
    [],
    [window("08:15", "10:00")],
    true,
  )
  assert.equal(full.tasks[0].hour, 9)
  const busy = runPlannerCommand(
    "lập kế hoạch",
    [task],
    [],
    [window("08:00", "10:00"), window("09:30", "09:45", "BUSY")],
    true,
  )
  assert.equal(busy.tasks[0].hour, 8)
  const empty = runPlannerCommand("lập kế hoạch", [task], [], [], true)
  assert.equal(empty.tasks[0].hour, undefined)
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
      course: "",
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
