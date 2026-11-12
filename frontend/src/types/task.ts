export type Task = {
  id: string

  title: string

  description?: string | null

  course: string

  time: string

  done: boolean

  effort: number

  priority: string

  deadline: string

  // Khung giờ trên lịch, được gán khi planner agent xếp lịch cho công việc.

  date?: string

  hour?: number
}

export type StudyFile = {
  name: string

  course: string

  status: string
}
