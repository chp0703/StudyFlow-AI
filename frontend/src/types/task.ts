export type Task = {
  id: string

  title: string

  description?: string | null

  time: string

  done: boolean

  effort: number

  priority: string | 0.1 | 0.5 | 1

  color?: string

  deadline: string

  // Khung giờ trên lịch, được gán khi planner agent xếp lịch cho công việc.

  date?: string

  hour?: number

  minute?: number
}

export type StudyFile = {
  // API mode: the server material this row represents (needed to delete it).
  id?: string

  name: string

  course: string

  status: string
}
