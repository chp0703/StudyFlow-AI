// Hand-written mirrors of the F1 v1.1 contract DTOs the UI reads (contracts/schemas/f1.schema.json).

export type ApiTask = {
  task_id: string

  title: string

  description: string | null

  course_label: string | null

  deadline_at: string

  deadline_precision: "DATE" | "DATETIME"

  deadline_date: string | null

  estimated_minutes: number

  remaining_minutes: number

  priority: "LOW" | "NORMAL" | "HIGH"

  status: "TODO" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED"
}

export type ApiTimeWindow = {
  window_id: string

  version: number

  kind: "AVAILABILITY" | "BUSY"

  label: string | null

  recurrence: "NONE" | "WEEKLY"

  timezone: string

  start_at: string | null

  end_at: string | null

  weekday: number | null

  start_time: string | null

  end_time: string | null

  valid_from: string | null

  valid_until: string | null

  archived_at: string | null
}

export type ApiBlock = {
  block_id: string

  task_id: string

  start_at: string

  end_at: string

  is_locked: boolean
}

export type PlanRef = {
  plan_id: string

  version: number
}

export type PlanWarning = {
  code: string

  message: string
}

export type Choice = {
  label: string

  value: string
}

export type PendingActionRef = {
  intent: string

  state: string

  action_id: string
}

export type Page<T,> = {
  items: T[]

  next_cursor: string | null
}

export type PlanView = {
  kind: "PLAN_VIEW"

  plan: PlanRef | null

  study_blocks: ApiBlock[]
}

export type PlanProposal = {
  proposal_id: string

  version: number

  status: "PROPOSED" | "APPROVED" | "REJECTED" | "STALE"

  base_plan_version: number | null

  base_schedule_revision: number

  payload: {
    study_blocks: ApiBlock[]

    task_summaries: {
      task_id: string
      remaining_minutes: number
      retained_future_minutes: number
      newly_scheduled_minutes: number
      unallocated_minutes: number
      reason_codes: string[]
    }[]

    coverage: "FULL" | "PARTIAL"

    warnings: PlanWarning[]

    plan_diff: {
      added: string[]

      moved: string[]

      removed: string[]

      unchanged: string[]
    }
  }
}

export type ActionReference = {
  action_id: string

  action_version: number

  target_type: "TASK_CANDIDATE" | "PENDING_ACTION" | "PLAN_PROPOSAL"

  target_id: string

  target_version: number
}

export type Question = {
  field: string

  message: string

  choices: Choice[]
}

export type ActionPresentation = {
  kind: "ACTION_PRESENTATION"

  pending_action: PendingActionRef

  candidate: { slots: Record<string, unknown> } | null

  proposal: PlanProposal | null

  normalized_command: {
    operation: string

    arguments: Record<string, unknown>
  } | null

  effective_policy: Record<string, unknown> | null
}

export type ToolResult = {
  outcome: string

  data: unknown
}

export type ApiErrorBody = {
  code: string

  message: string

  field: string | null

  retryable: boolean
}

export type OrchestratorReply = {
  request_id: string

  state: "NEEDS_CLARIFICATION" | "AWAITING_APPROVAL" | "SUCCEEDED" | "ERROR"

  message: string

  action_reference: ActionReference | null

  questions: Question[]

  result: ToolResult | null

  error: ApiErrorBody | null
}

export type ListResult<T,> = {
  data: Page<T>
}
