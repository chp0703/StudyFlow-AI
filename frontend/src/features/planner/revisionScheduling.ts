import type { ApiTask, OrchestratorReply } from "../../api/types"

export type RevisionSchedulingStatus = "finding" | "pending" | "scheduled" | "failed" | "needs_availability" | "blocked"

export type RevisionSchedulingState = {
  taskId: string
  status: RevisionSchedulingStatus
  message: string
}

export type RevisionScheduleArguments = {
  generation_scope: {
    start_at: string
    end_at: string
    selection_mode: "SELECTED_TASKS"
    task_ids: string[]
  }
  policy_overrides: Record<string, never>
}

export type RevisionScheduleAttempt = {
  userId: string
  task: ApiTask
  arguments: RevisionScheduleArguments
  key: string
  running: boolean
  sent: boolean
}

function isApiTask(value: unknown): value is ApiTask {
  if (!value || typeof value !== "object") return false
  const task = value as Partial<ApiTask>
  return (
    typeof task.task_id === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
      task.task_id,
    ) &&
    typeof task.title === "string" &&
    (typeof task.description === "string" || task.description === null) &&
    typeof task.start_at === "string" &&
    (typeof task.available_from_at === "string" ||
      task.available_from_at === null) &&
    typeof task.deadline_at === "string" &&
    (task.deadline_precision === "DATE" ||
      task.deadline_precision === "DATETIME") &&
    (typeof task.deadline_date === "string" || task.deadline_date === null) &&
    task.deadline_timezone === "Asia/Ho_Chi_Minh" &&
    typeof task.estimated_minutes === "number" &&
    typeof task.remaining_minutes === "number" &&
    (task.priority === 0.1 || task.priority === 0.5 || task.priority === 1) &&
    typeof task.color === "string" &&
    (task.status === "TODO" || task.status === "IN_PROGRESS")
  )
}

export function confirmedTask(reply: OrchestratorReply) {
  if (
    reply.state !== "SUCCEEDED" ||
    reply.result?.outcome !== "COMMITTED" ||
    !isApiTask(reply.result.data) ||
    reply.result.data.remaining_minutes <= 0
  )
    return null
  return reply.result.data
}

export const confirmedRevisionTask = confirmedTask

export function revisionScheduleArguments(
  task: ApiTask,
  now = new Date(),
): RevisionScheduleArguments | null {
  const deadline = Date.parse(task.deadline_at)
  const availableFrom = task.available_from_at
    ? Date.parse(task.available_from_at)
    : Number.NaN
  if (task.available_from_at && !Number.isFinite(availableFrom)) return null
  const start =
    Math.ceil(
      Math.max(
        now.getTime(),
        Number.isFinite(availableFrom) ? availableFrom : 0,
      ) / 60_000,
    ) * 60_000

  if (!Number.isFinite(deadline) || start >= deadline) return null

  return {
    generation_scope: {
      start_at: new Date(start).toISOString(),
      end_at: new Date(deadline).toISOString(),
      selection_mode: "SELECTED_TASKS",
      task_ids: [task.task_id],
    },
    policy_overrides: {},
  }
}

export function revisionScheduleAttempt(
  current: RevisionScheduleAttempt | null,
  userId: string,
  task: ApiTask,
  now = new Date(),
  key: string = crypto.randomUUID(),
): RevisionScheduleAttempt | null {
  if (current?.userId === userId && current.task.task_id === task.task_id)
    return current
  const arguments_ = revisionScheduleArguments(task, now)
  return arguments_
    ? { userId, task, arguments: arguments_, key, running: false, sent: false }
    : null
}
