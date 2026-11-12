import test from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import {
  expandWindows,
  mapTasksAndEvents,
  proposalFromReply,
  summarize,
} from "./mappers.ts"
import type {
  ApiBlock,
  ApiTask,
  ApiTimeWindow,
  OrchestratorReply,
  PlanProposal,
} from "./types.ts"

const example = (name: string) =>
  JSON.parse(
    readFileSync(
      new URL(`../../../contracts/examples/valid/${name}`, import.meta.url),
      "utf8",
    ),
  )

// Contract instants are explicit; display values always use Vietnam time.
const at = (y: number, m: number, d: number, h = 0, min = 0) =>
  new Date(
    `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}T${String(h).padStart(2, "0")}:${String(min).padStart(2, "0")}:00+07:00`,
  ).toISOString()

const task = (over: Partial<ApiTask> = {}): ApiTask => ({
  task_id: "t1",
  title: "Ôn OOP",
  description: "Đọc chương 3",
  course_label: "OOP",
  deadline_at: at(2026, 11, 20),
  deadline_precision: "DATE",
  deadline_date: "2026-11-20",
  estimated_minutes: 120,
  remaining_minutes: 120,
  priority: "HIGH",
  status: "TODO",
  ...over,
})

const block = (
  id: string,
  start: string,
  end: string,
  task_id = "t1",
): ApiBlock => ({
  block_id: id,
  task_id,
  start_at: start,
  end_at: end,
  is_locked: false,
})

test("a task maps to the list shape; a scheduled one gets its first block as slot", () => {
  const first = block("b1", at(2026, 11, 9, 9), at(2026, 11, 9, 10, 30))
  const later = block("b2", at(2026, 11, 10, 14), at(2026, 11, 10, 15))
  const { tasks, events } = mapTasksAndEvents(
    [
      task(),
      task({
        task_id: "t2",
        title: "Khác",
        status: "COMPLETED",
        priority: "LOW",
        course_label: null,
      }),
    ],
    [later, first],
  )
  assert.deepEqual(tasks[0], {
    id: "t1",
    title: "Ôn OOP",
    description: "Đọc chương 3",
    course: "OOP",
    time: "09:00–10:30",
    done: false,
    effort: 120,
    priority: "Cao",
    deadline: "2026-11-20",
    date: "2026-11-09",
    hour: 9,
  })
  assert.equal(tasks[1].done, true)
  assert.equal(tasks[1].date, undefined)
  assert.equal(tasks[1].course, "")
  assert.deepEqual(
    events.map((e) => [e.id, e.title, e.date, e.hour, e.time, e.effort]),
    [
      ["b2", "Ôn OOP", "2026-11-10", 14, "14:00–15:00", 60],
      ["b1", "Ôn OOP", "2026-11-09", 9, "09:00–10:30", 90],
    ],
  )
})

test("a DATETIME deadline uses the Vietnam date of the instant", () => {
  const { tasks } = mapTasksAndEvents(
    [
      task({
        deadline_precision: "DATETIME",
        deadline_date: null,
        deadline_at: at(2026, 11, 6, 17),
      }),
    ],
    [],
  )
  assert.equal(tasks[0].deadline, "2026-11-06")
})

const win = (over: Partial<ApiTimeWindow>): ApiTimeWindow => ({
  window_id: "w",
  version: 1,
  kind: "AVAILABILITY",
  label: null,
  recurrence: "WEEKLY",
  timezone: "Asia/Ho_Chi_Minh",
  start_at: null,
  end_at: null,
  weekday: 1,
  start_time: "09:00",
  end_time: "11:00",
  valid_from: null,
  valid_until: null,
  archived_at: null,
  ...over,
})

test("weekly windows expand to hour cells, clipped to the grid, honouring validity", () => {
  const monday = new Date("2026-11-09T12:00:00Z") // Mon 9 Nov 2026
  const cells = expandWindows([win({ valid_from: "2026-11-01" })], monday, 8)
  assert.deepEqual(
    cells.map((c) => c.id),
    ["2026-11-09-9", "2026-11-09-10", "2026-11-16-9", "2026-11-16-10"],
  )
  assert.equal(
    expandWindows([win({ valid_until: "2026-11-10" })], monday, 8).length,
    2,
  )
  assert.equal(
    expandWindows([win({ end_time: "24:00", start_time: "16:00" })], monday, 1)
      .map((c) => c.hour)
      .join(),
    "16,17",
  )
  assert.equal(
    expandWindows([win({ archived_at: "2026-11-01T00:00:00Z" })], monday, 8)
      .length,
    0,
  )
})

test("a one-off busy interval overrides availability on the same hour", () => {
  const monday = new Date("2026-11-09T12:00:00Z")
  const busy = win({
    window_id: "b",
    kind: "BUSY",
    recurrence: "NONE",
    weekday: null,
    start_time: null,
    end_time: null,
    start_at: at(2026, 11, 9, 10),
    end_at: at(2026, 11, 9, 11),
  })
  const cells = expandWindows([win({}), busy], monday, 1)
  assert.deepEqual(
    cells.map((c) => [c.hour, c.kind]),
    [
      [9, "free"],
      [10, "busy"],
    ],
  )
})

test("partial working intervals do not become complete legacy hour cells", () => {
  const monday = new Date("2026-11-09T12:00:00Z")
  assert.deepEqual(
    expandWindows([win({ start_time: "08:15", end_time: "09:45" })], monday, 1),
    [],
  )
  assert.deepEqual(
    expandWindows(
      [win({ start_time: "08:15", end_time: "10:00" })],
      monday,
      1,
    ).map((cell) => cell.hour),
    [9],
  )
})

const proposal = (
  over: Partial<PlanProposal["payload"]> = {},
): PlanProposal => ({
  proposal_id: "p1",
  version: 1,
  status: "PROPOSED",
  base_plan_version: null,
  base_schedule_revision: 4,
  payload: {
    task_summaries: [
      {
        task_id: "t1",
        remaining_minutes: 120,
        retained_future_minutes: 0,
        newly_scheduled_minutes: 60,
        unallocated_minutes: 60,
        reason_codes: ["INSUFFICIENT_AVAILABILITY"],
      },
    ],
    study_blocks: [
      block("n1", at(2026, 11, 11, 9), at(2026, 11, 11, 10)),
      block("keep", at(2026, 11, 9, 9), at(2026, 11, 9, 10)),
    ],
    coverage: "PARTIAL",
    warnings: [{ code: "UNALLOCATED", message: "Thiếu thời gian" }],
    plan_diff: {
      added: ["n1"],
      moved: [],
      removed: ["gone"],
      unchanged: ["keep"],
    },
    ...over,
  },
})

const reply = (data: unknown): OrchestratorReply => ({
  request_id: "r",
  state: "AWAITING_APPROVAL",
  message: "Xem nội dung",
  questions: [],
  error: null,
  action_reference: {
    action_id: "a",
    action_version: 1,
    target_type: "PLAN_PROPOSAL",
    target_id: "p1",
    target_version: 1,
  },
  result: { outcome: "DRAFTED", data },
})

test("a plan proposal becomes a calendar preview with added and removed events", () => {
  const { tasks, events } = mapTasksAndEvents([task()], [
    block("keep", at(2026, 11, 9, 9), at(2026, 11, 9, 10)),
    block("gone", at(2026, 11, 12, 9), at(2026, 11, 12, 10)),
  ])
  const presentation = {
    kind: "ACTION_PRESENTATION",
    pending_action: {
      intent: "GENERATE_STUDY_PLAN",
      state: "AWAITING_APPROVAL",
      action_id: "a",
    },
    candidate: null,
    proposal: proposal(),
    normalized_command: null,
    effective_policy: null,
  }
  const result = proposalFromReply(reply(presentation), {
    tasks,
    events,
    availability: [],
    revision: 4,
  })!
  assert.equal(result.id, "p1")
  assert.equal(result.baseRevision, 4)
  assert.deepEqual(
    result.changes.map((c) => [c.kind, c.task.id]),
    [
      ["scheduled", "n1"],
      ["removed", "gone"],
    ],
  )
  assert.deepEqual(
    result.next.tasks.map((e) => e.id),
    ["n1", "keep"],
  )
  assert.deepEqual(result.server?.taskIds, ["t1"])
  assert.equal(result.server?.reference.target_type, "PLAN_PROPOSAL")
  assert.equal(result.issues[0].message, "Thiếu thời gian")
  assert.deepEqual(result.server?.unscheduled, [
    { title: "Ôn OOP", minutes: 60, reasons: ["INSUFFICIENT_AVAILABILITY"] },
  ])
})

test("the contract's task-confirmation example summarises into rows and a calendar-neutral proposal", () => {
  const body = example("OrchestratorReply.json") as OrchestratorReply
  const presentation = body.result!.data as Parameters<typeof summarize>[0]
  const summary = summarize(presentation)
  assert.match(summary.title, /^Thêm công việc: /)
  assert.ok(
    summary.details.some(
      (d) => d.label === "Thời lượng" && d.value === "60 phút",
    ),
  )
  const preview = proposalFromReply(body, {
    tasks: [],
    events: [],
    availability: [],
    revision: 7,
  })!
  assert.equal(preview.changes.length, 0)
  assert.equal(preview.baseRevision, 7)
  assert.equal(preview.server?.reference.target_type, "TASK_CANDIDATE")
})

test("a reply without a presentation has no proposal", () => {
  assert.equal(
    proposalFromReply({ ...reply(null), action_reference: null }, {
      tasks: [],
      events: [],
      availability: [],
      revision: 0,
    }),
    null,
  )
})

test("an archived weekly interval review names the exact existing interval", () => {
  const summary = summarize(
    {
      kind: "ACTION_PRESENTATION",
      pending_action: {
        intent: "SET_AVAILABILITY",
        state: "AWAITING_APPROVAL",
        action_id: "a",
      },
      candidate: null,
      proposal: null,
      normalized_command: {
        operation: "set_availability",
        arguments: {
          change_type: "ARCHIVE",
          window_id: "w",
          expected_window_version: 1,
          window: null,
        },
      },
      effective_policy: null,
    },
    [win({})],
  )
  assert.equal(summary.title, "Xóa thời gian học")
  assert.deepEqual(summary.details[1], {
    label: "Sẽ xóa",
    value: "Thứ 2 hằng tuần, 09:00–11:00",
  })
})
