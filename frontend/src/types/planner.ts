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
  code: "INSUFFICIENT_AVAILABILITY"

  message: string

  taskId: number
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
}
