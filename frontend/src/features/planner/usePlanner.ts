import { useState, type Dispatch, type SetStateAction } from "react"
import type { Task } from "../../types/task"
import type { Proposal, TimeWindow } from "../../types/planner"
import { runPlannerCommand } from "./plannerAgent"
import { diffTasks, diffWindows, isStale } from "./proposal"

export type PlannerProps = {
  tasks: Task[]

  setTasks: Dispatch<SetStateAction<Task[]>>

  availability: TimeWindow[]

  setAvailability: Dispatch<SetStateAction<TimeWindow[]>>

  proposal: Proposal | null

  setProposal: Dispatch<SetStateAction<Proposal | null>>

  revision: number

  setRevision: Dispatch<SetStateAction<number>>

  notify?: (message: string) => void
}

export function usePlanner(
  {
    tasks,
    setTasks,
    availability,
    setAvailability,
    proposal,
    setProposal,
    revision,
    setRevision,
  }: PlannerProps,
  showPlannerNotice: (message: string) => void,
) {
  const [input, setInput] = useState("")

  const [reply, setReply] = useState("")

  // Khi có đề xuất chờ duyệt, lịch hiển thị bản xem trước; nếu không thì hiển thị công việc đã xác nhận.
  const shown = proposal ? proposal.next.tasks : tasks

  const shownWindows = proposal ? proposal.next.availability : availability

  const stale = proposal ? isStale(proposal, revision) : false

  const send = () => {
    const text = input.trim()

    if (!text) return

    // Các lệnh tiếp tục sửa đề xuất đang chờ nhưng luôn so sánh với lịch đã xác nhận.

    const result = runPlannerCommand(text, shown, shownWindows)

    const changes = diffTasks(tasks, result.tasks)

    const windowChanges = diffWindows(availability, result.availability)

    setReply(result.reply)

    setInput("")

    if (!changes.length && !windowChanges.length) return setProposal(null)

    setProposal({
      id: proposal?.id ?? crypto.randomUUID(),

      createdAt: proposal?.createdAt ?? Date.now(),

      baseRevision: proposal?.baseRevision ?? revision,

      next: { tasks: result.tasks, availability: result.availability },

      changes,

      windowChanges,

      issues: result.issues ?? proposal?.issues ?? [],

      reply: result.reply,
    })
  }

  const approve = () => {
    if (!proposal || stale) return

    setTasks(proposal.next.tasks)

    setAvailability(proposal.next.availability)

    setRevision((r) => r + 1)

    setProposal(null)

    setReply("")

    showPlannerNotice("Đã lưu thay đổi vào lịch.")
  }

  const reject = () => {
    setProposal(null)

    setReply("")
  }

  return {
    input,
    setInput,
    reply,
    setReply,
    shown,
    shownWindows,
    stale,
    send,
    approve,
    reject,
  }
}
