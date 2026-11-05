import type { Task } from "./task"

export type TaskSlot = {
  date?: string

  hour?: number
}

export type TaskChange = {
  kind: "added" | "moved" | "removed"

  task: Task

  // Previous slot, only for "moved".

  from?: TaskSlot
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

  reply: string
}
