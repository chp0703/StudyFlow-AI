import type { ActionReference } from "../api/types"

import type { Task } from "./task"

export type TaskSlot = {
  date?: string

  hour?: number
}

export type TaskChange = {
  kind: "added" | "scheduled" | "moved" | "removed"

  task: Task

  // Previous slot, only for "moved" (a "scheduled" task had none).

  from?: TaskSlot
}

// Codes follow SRS §12; only the ones the planner can raise today.

export type PlannerIssue = {
  code: string

  message: string

  taskId: string
}

// An hour the user declared free or busy; id is "<date>-<hour>" so one hour has one window.

export type TimeWindow = {
  id: string

  date: string

  hour: number

  kind: "free" | "busy"
}

export type WindowChange = {
  kind: "added" | "removed"

  window: TimeWindow
}

export type PlannerState = {
  tasks: Task[]

  availability: TimeWindow[]
}

// A pending schedule change. Nothing is committed until the user approves it.

export type Proposal = {
  id: string

  createdAt: number

  // Schedule revision the proposal was built on; approval is rejected if it moved on.

  baseRevision: number

  next: PlannerState

  changes: TaskChange[]

  windowChanges: WindowChange[]

  issues: PlannerIssue[]

  reply: string

  // Set in API mode: the server-issued action this proposal asks the user to decide on.

  server?: {
    reference: ActionReference

    title: string

    details: { label: string; value: string }[]

    // Tasks touched by the proposal (calendar events are keyed by block id, the task list by task id).

    taskIds: string[]
  }
}
