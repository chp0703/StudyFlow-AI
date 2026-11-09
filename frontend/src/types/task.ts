export type Task = {
  id: number

  title: string

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
