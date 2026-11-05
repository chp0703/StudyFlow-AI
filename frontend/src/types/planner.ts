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

// A pending schedule change. Nothing is committed until the user approves it.
export type Proposal = {
  id: string

  createdAt: number

  // Schedule revision the proposal was built on; approval is rejected if it moved on.
  baseRevision: number

  next: { tasks: Task[] }

  changes: TaskChange[]

  reply: string
}
