import type {
  ActionPresentation,
  ApiBlock,
  ApiTask,
  ApiTimeWindow,
  OrchestratorReply,
} from "./types.ts"

import { FIRST_HOUR, LAST_HOUR } from "../features/planner/plannerAgent.ts"

import type {
  PlannerIssue,
  Proposal,
  TaskChange,
  TimeWindow,
} from "../types/planner.ts"

import type { Task } from "../types/task.ts"

import { toIsoDate } from "../utils/date.ts"

// Times are shown in the browser's local zone; the backend default zone is Asia/Ho_Chi_Minh.

const PRIORITY: Record<ApiTask["priority"], string> = {
  HIGH: "Cao",

  NORMAL: "Trung bình",

  LOW: "Thấp",
}

const pad = (n: number) => String(n).padStart(2, "0")

const clock = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`

export const blockLabel = (block: Pick<ApiBlock, "start_at" | "end_at">) =>
  `${clock(new Date(block.start_at))}–${clock(new Date(block.end_at))}`

const minutesBetween = (a: string, b: string) =>
  Math.round((new Date(b).getTime() - new Date(a).getTime()) / 60000)

export function deadlineDate(task: ApiTask): string {
  return task.deadline_date ?? toIsoDate(new Date(task.deadline_at))
}

// A task for the list. Its first block (if any) gives the "confirmed" calendar slot.
export function mapTask(task: ApiTask, firstBlock?: ApiBlock): Task {
  const start = firstBlock ? new Date(firstBlock.start_at) : undefined

  return {
    id: task.task_id,

    title: task.title,

    course: task.course_label ?? "",

    time: firstBlock ? blockLabel(firstBlock) : "",

    done: task.status === "COMPLETED",

    effort: task.estimated_minutes,

    priority: PRIORITY[task.priority] ?? PRIORITY.NORMAL,

    deadline: deadlineDate(task),

    ...(start ? { date: toIsoDate(start), hour: start.getHours() } : {}),
  }
}

// One calendar event per study block; its id is the block id, its title the task's.
export function blockEvent(block: ApiBlock, task: Task | undefined): Task {
  const start = new Date(block.start_at)

  return {
    id: block.block_id,

    title: task?.title ?? "Công việc",

    course: task?.course ?? "",

    time: blockLabel(block),

    done: task?.done ?? false,

    effort: minutesBetween(block.start_at, block.end_at),

    priority: task?.priority ?? PRIORITY.NORMAL,

    deadline: task?.deadline ?? toIsoDate(start),

    date: toIsoDate(start),

    hour: start.getHours(),
  }
}

export type MappedData = {
  tasks: Task[]

  events: Task[]
}

export function mapTasksAndEvents(
  apiTasks: ApiTask[],
  blocks: ApiBlock[],
): MappedData {
  const firstBlock = new Map<string, ApiBlock>()

  for (const b of [...blocks].sort((x, y) =>
    x.start_at.localeCompare(y.start_at),
  ))
    if (!firstBlock.has(b.task_id)) firstBlock.set(b.task_id, b)

  const tasks = apiTasks.map((t) => mapTask(t, firstBlock.get(t.task_id)))

  const byId = new Map(tasks.map((t) => [t.id, t]))

  return {
    tasks,

    events: blocks.map((b) => blockEvent(b, byId.get(b.task_id))),
  }
}

const toMinutes = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number)

  return h * 60 + m
}

// Free/busy cells (one per grid hour) for `days` days from `from`. Busy wins over free on the same hour.
export function expandWindows(
  windows: ApiTimeWindow[],
  from: Date,
  days: number,
): TimeWindow[] {
  const cells = new Map<string, TimeWindow>()

  for (let i = 0; i < days; i++) {
    const day = new Date(
      from.getFullYear(),
      from.getMonth(),
      from.getDate() + i,
    )

    const date = toIsoDate(day)

    const weekday = day.getDay() || 7

    for (let hour = FIRST_HOUR; hour <= LAST_HOUR; hour++) {
      const cellStart = new Date(
        day.getFullYear(),
        day.getMonth(),
        day.getDate(),
        hour,
      )

      const cellEnd = new Date(cellStart.getTime() + 3600000)

      for (const w of windows) {
        if (w.archived_at) continue

        const hit =
          w.recurrence === "WEEKLY"
            ? w.weekday === weekday &&
              (!w.valid_from || date >= w.valid_from) &&
              (!w.valid_until || date <= w.valid_until) &&
              toMinutes(w.start_time ?? "00:00") < (hour + 1) * 60 &&
              toMinutes(w.end_time ?? "00:00") > hour * 60
            : new Date(w.start_at ?? 0) < cellEnd &&
              new Date(w.end_at ?? 0) > cellStart

        if (!hit) continue

        const kind = w.kind === "BUSY" ? "busy" : "free"

        const id = `${date}-${hour}`

        if (cells.get(id)?.kind !== "busy")
          cells.set(id, { id, date, hour, kind })
      }
    }
  }

  return [...cells.values()]
}

const CHANGE_FROM = (e: Task) => ({ date: e.date, hour: e.hour })

// The pending proposal as the calendar understands it. Non-plan proposals carry no calendar change.
export function proposalFromReply(
  reply: OrchestratorReply,
  ctx: {
    tasks: Task[]
    events: Task[]
    availability: TimeWindow[]
    revision: number
  },
): Proposal | null {
  const reference = reply.action_reference

  const presentation = reply.result?.data as ActionPresentation | undefined

  if (
    !reference ||
    !presentation ||
    presentation.kind !== "ACTION_PRESENTATION"
  )
    return null

  const summary = summarize(presentation)

  const server = {
    reference,
    title: summary.title,
    details: summary.details,
    taskIds: [] as string[],
  }

  const plan = presentation.proposal

  if (!plan)
    return {
      id: reference.action_id,
      createdAt: Date.now(),
      baseRevision: ctx.revision,
      next: { tasks: ctx.events, availability: ctx.availability },
      changes: [],
      windowChanges: [],
      issues: [],
      reply: reply.message,
      server,
    }

  const byId = new Map(ctx.tasks.map((t) => [t.id, t]))

  const nextEvents = plan.payload.study_blocks.map((b) =>
    blockEvent(b, byId.get(b.task_id)),
  )

  const current = new Map(ctx.events.map((e) => [e.id, e]))

  const next = new Map(nextEvents.map((e) => [e.id, e]))

  const diff = plan.payload.plan_diff

  const changes: TaskChange[] = [
    ...diff.added.flatMap((id) =>
      next.has(id) ? [{ kind: "scheduled" as const, task: next.get(id)! }] : [],
    ),

    ...diff.moved.flatMap((id) =>
      next.has(id)
        ? [
            {
              kind: "moved" as const,
              task: next.get(id)!,
              from: current.has(id) ? CHANGE_FROM(current.get(id)!) : undefined,
            },
          ]
        : [],
    ),

    ...diff.removed.flatMap((id) =>
      current.has(id)
        ? [{ kind: "removed" as const, task: current.get(id)! }]
        : [],
    ),
  ]

  server.taskIds = [
    ...new Set(
      plan.payload.study_blocks
        .filter(
          (b) =>
            diff.added.includes(b.block_id) || diff.moved.includes(b.block_id),
        )
        .map((b) => b.task_id),
    ),
  ]

  const issues: PlannerIssue[] = plan.payload.warnings.map((w, i) => ({
    code: w.code,
    message: w.message,
    taskId: `${w.code}-${i}`,
  }))

  return {
    id: plan.proposal_id,
    createdAt: Date.now(),
    baseRevision: plan.base_schedule_revision,
    next: { tasks: nextEvents, availability: ctx.availability },
    changes,
    windowChanges: [],
    issues,
    reply: reply.message,
    server,
  }
}

export type Summary = {
  title: string

  details: DetailRow[]
}

export type DetailRow = {
  label: string

  value: string
}

const WEEKDAYS = [
  "",
  "Thứ 2",
  "Thứ 3",
  "Thứ 4",
  "Thứ 5",
  "Thứ 6",
  "Thứ 7",
  "Chủ nhật",
]

function windowDetails(args: Record<string, unknown>): DetailRow[] {
  const w = (args.window ?? {}) as Partial<ApiTimeWindow>

  const when =
    w.recurrence === "WEEKLY"
      ? `${WEEKDAYS[w.weekday ?? 0] ?? ""} hằng tuần, ${w.start_time}–${w.end_time}`
      : `${w.start_at ? new Date(w.start_at).toLocaleString("vi-VN") : "?"} – ${
          w.end_at ? new Date(w.end_at).toLocaleString("vi-VN") : "?"
        }`

  return [
    { label: "Loại", value: w.kind === "BUSY" ? "Giờ bận" : "Giờ rảnh" },

    { label: "Thời gian", value: when },
  ]
}

// Title and rows describing what an approval would do, from the server-issued presentation.
export function summarize(
  p: ActionPresentation,
): Summary {
  if (p.proposal) {
    const diff = p.proposal.payload.plan_diff

    return {
      title: "Kế hoạch học được đề xuất",
      details: [
        {
          label: "Khối học",
          value: String(p.proposal.payload.study_blocks.length),
        },
        {
          label: "Thêm / dời / xóa",
          value: `${diff.added.length} / ${diff.moved.length} / ${diff.removed.length}`,
        },
        {
          label: "Mức phủ",
          value: p.proposal.payload.coverage === "FULL" ? "Đầy đủ" : "Một phần",
        },
      ],
    }
  }

  if (p.candidate) {
    const s = p.candidate.slots as Record<string, string | number | null>

    return {
      title: `Thêm công việc: ${s.title ?? ""}`,
      details: [
        { label: "Môn học", value: String(s.course_label ?? "Chưa có") },
        {
          label: "Hạn nộp",
          value: String(s.deadline_date ?? s.deadline_at ?? "Chưa có"),
        },
        {
          label: "Thời lượng",
          value: s.estimated_minutes
            ? `${s.estimated_minutes} phút`
            : "Chưa có",
        },
        { label: "Ưu tiên", value: String(s.priority ?? "NORMAL") },
      ],
    }
  }

  const command = p.normalized_command

  if (command?.operation === "set_scheduling_preferences")
    return {
      title: "Cập nhật tùy chọn lập lịch",
      details: Object.entries(p.effective_policy ?? {}).map(
        ([label, value]) => ({ label, value: String(value) }),
      ),
    }

  if (command)
    return {
      title:
        command.operation === "set_busy_interval"
          ? "Thêm giờ bận"
          : "Thêm giờ rảnh",
      details: windowDetails(command.arguments),
    }

  return { title: "Thao tác đang chờ", details: [] }
}
