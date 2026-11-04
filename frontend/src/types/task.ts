export type Task = {
  id: number
  title: string
  course: string
  time: string
  done: boolean
  effort: number
  priority: string
  deadline: string
}

export type StudyFile = {
  name: string
  course: string
  status: string
}
