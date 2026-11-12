import type { ActionReference } from "../api/types"
import type { ApiTimeWindow } from "../api/types"

import type { Task } from "./task"

export type TaskSlot = {
  date?: string

  hour?: number
}

export type TaskChange = {
  kind: "added" | "scheduled" | "moved" | "removed"

  task: Task

  // Khung giờ trước đó, chỉ dành cho "moved"; công việc "scheduled" trước đó chưa có khung giờ.

  from?: TaskSlot
}

// Mã theo SRS §12; chỉ gồm các mã planner hiện có thể phát sinh.

export type PlannerIssue = {
  code: string

  message: string

  taskId: string
}

// Một giờ người dùng khai báo rảnh/bận; id là "<date>-<hour>" để mỗi giờ chỉ có một khung.

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

  weeklyWindows?: ApiTimeWindow[]

  workingConfigured?: boolean
}

// Thay đổi lịch đang chờ. Chỉ ghi nhận khi người dùng phê duyệt.

export type Proposal = {
  id: string

  createdAt: number

  // Phiên bản sửa đổi của lịch lúc tạo đề xuất; từ chối duyệt nếu lịch đã thay đổi.

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

    details: Array<{
      label: string
      value: string
    }>

    // Tasks touched by the proposal (calendar events are keyed by block id, the task list by task id).

    taskIds: string[]

    coverage?: "FULL" | "PARTIAL"

    unchangedBlockIds?: string[]

    unscheduled?: Array<{
      title: string
      minutes: number
      reasons: string[]
    }>
  }
}
