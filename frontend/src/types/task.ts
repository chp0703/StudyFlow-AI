export type Task = {
  id: string

  title: string

  course: string

  time: string

  done: boolean

  effort: number

  priority: string

  deadline: string

  // Calendar slot, set when the planner agent schedules the task.

  date?: string

  hour?: number
}

export type StudyFile = {
  name: string

  course: string

  status: string
}
