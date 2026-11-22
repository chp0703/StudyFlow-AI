import { useRef, useState, type Dispatch, type SetStateAction } from "react"

import type { Task } from "../../types/task"

import type { Proposal, TimeWindow } from "../../types/planner"

import { runPlannerCommand } from "./plannerAgent"

import {
  approvalBlocked,
  demoNoOpResult,
  diffTasks,
  diffWindows,
  isStale,
} from "./proposal"

import { api } from "../../api"

import { apiEnabled } from "../../api/config"

import { ApiError, errorText } from "../../api/client"

import { proposalFromReply } from "../../api/mappers"

import { savePending } from "../../api/pending"

import type { ApiTask, ApiTimeWindow, OrchestratorReply } from "../../api/types"
import { confirmedTask } from "./revisionScheduling"

import {
  buildDemoClarificationQuestions,
  type PlannerClarification,
} from "./clarification"

export type PlannerProps = {
  tasks: Task[]

  events: Task[]

  windows?: ApiTimeWindow[]

  userId: string

  conversationId: string

  reload: () => Promise<void>

  setTasks: Dispatch<SetStateAction<Task[]>>

  availability: TimeWindow[]

  setAvailability: Dispatch<SetStateAction<TimeWindow[]>>

  proposal: Proposal | null

  setProposal: Dispatch<SetStateAction<Proposal | null>>

  revision: number

  setRevision: Dispatch<SetStateAction<number>>

  notify?: (message: string) => void

  revisionScheduling?: import("./revisionScheduling").RevisionSchedulingState | null

  onRetryRevisionScheduling?: () => void

  onProposalDecision?: (
    decision: "APPROVE" | "REJECT",
    taskIds: string[],
  ) => void

  onTaskConfirmed?: (task: ApiTask) => void

  onScheduleTask?: (taskId: string) => void

  onStartLearning?: (blockId: string, goal: string) => void
}

export type PlannerFeedback = {
  kind: "info" | "clarification" | "error" | "pending" | "success"

  text: string
}

export const shouldClearPlannerDraft = (state: OrchestratorReply["state"]) =>
  state === "AWAITING_APPROVAL" || state === "SUCCEEDED"

export function usePlanner(
  {
    tasks,

    events,

    windows,

    userId,

    conversationId,

    reload,

    setTasks,

    availability,

    setAvailability,

    proposal,

    setProposal,

    revision,

    setRevision,

    onProposalDecision,
    onTaskConfirmed,
  }: PlannerProps,

  showPlannerNotice: (message: string) => void,
) {
  const [input, setInput] = useState("")

  const [reply, setReply] = useState("")

  const [feedback, setFeedback] = useState<PlannerFeedback | null>(null)

  const [clarification, setClarification] =
    useState<PlannerClarification | null>(null)

  const [busy, setBusy] = useState(false)

  // Retrying the same message keeps its idempotency key.

  const attempt = useRef<{
    text: string

    key: string
  } | null>(null)

  const shown = proposal ? proposal.next.tasks : apiEnabled ? events : tasks

  const shownWindows = proposal ? proposal.next.availability : availability

  const stale = proposal ? isStale(proposal, revision) : false

  // API mode: show what the server answered. A reply that waits for approval becomes the pending proposal.

  const showReply = async (r: OrchestratorReply, promptText: string) => {
    if (r.state === "AWAITING_APPROVAL") {
      setClarification(null)

      const next = proposalFromReply(r, {
        tasks,

        events,

        windows,

        availability,

        revision,
      })

      setProposal(next)

      setReply(r.message)

      setFeedback({
        kind: "pending",

        text: "Đề xuất đã sẵn sàng. Hãy xem chi tiết rồi chọn Duyệt hoặc Từ chối.",
      })

      if (next && r.action_reference)
        savePending(userId, {
          conversationId,

          reference: r.action_reference,
        })

      return
    }

    const questions = r.questions.map((q) => q.message).join(" ")

    const text = questions ? `${r.message} ${questions}` : r.message

    if (r.state === "NEEDS_CLARIFICATION") {
      setClarification((prev) => ({
        source: "api",

        originalPrompt: prev?.originalPrompt || promptText,

        message: r.message,

        questions: r.questions.length
          ? r.questions
          : [{ field: "details", message: r.message, choices: [] }],
      }))
    } else {
      setClarification(null)
    }

    setFeedback({
      kind:
        r.state === "NEEDS_CLARIFICATION"
          ? "clarification"
          : r.state === "ERROR" || r.error
            ? "error"
            : "info",

      text,
    })

    if (r.state === "SUCCEEDED") await reload()
  }

  const sendToServer = async (text: string) => {
    const key =
      attempt.current?.text === text ? attempt.current.key : crypto.randomUUID()

    attempt.current = { text, key }

    setBusy(true)

    try {
      const response = await api.sendMessage(conversationId, text, key)

      await showReply(response, text)

      attempt.current = null

      if (shouldClearPlannerDraft(response.state)) setInput("")
    } catch (e) {
      setFeedback({ kind: "error", text: errorText(e) })

      // Only a failure that may have reached the server keeps the key for the retry.

      if (e instanceof ApiError && !e.retryable) attempt.current = null
    } finally {
      setBusy(false)
    }
  }

  const sendText = (rawText: string) => {
    const text = rawText.trim()

    if (!text || busy) return

    if (apiEnabled) return void sendToServer(text)

    // Commands stack on a pending proposal, but are always diffed against the committed schedule.

    const result = runPlannerCommand(text, shown, shownWindows)

    const commandChangedTasks = diffTasks(shown, result.tasks)

    const commandChangedWindows = diffWindows(shownWindows, result.availability)

    const changes = diffTasks(tasks, result.tasks)

    const windowChanges = diffWindows(availability, result.availability)

    if (!commandChangedTasks.length && !commandChangedWindows.length) {
      const next = demoNoOpResult(proposal, result.reply)

      setProposal(next.proposal)

      setReply(next.reply)

      const isClarify = /cho mình biết|hãy tạo|ví dụ/iu.test(result.reply)

      if (isClarify) {
        const demoQuestions = buildDemoClarificationQuestions(
          text,

          result.reply,
        )

        setClarification(
          demoQuestions.length
            ? {
                source: "demo",

                originalPrompt: text,

                message: result.reply,

                questions: demoQuestions,
              }
            : null,
        )
      } else {
        setClarification(null)
      }

      setFeedback({
        kind: isClarify ? "clarification" : "error",

        text: result.reply,
      })

      return
    }

    setClarification(null)

    setInput("")

    setReply(result.reply)

    setFeedback({
      kind: "pending",

      text: "Đã tạo bản xem trước. Lịch chỉ thay đổi sau khi bạn duyệt.",
    })

    setProposal({
      id: proposal?.id ?? crypto.randomUUID(),

      createdAt: proposal?.createdAt ?? Date.now(),

      baseRevision: proposal?.baseRevision ?? revision,

      next: {
        tasks: result.tasks,

        availability: result.availability,
      },

      changes,

      windowChanges,

      issues: result.issues ?? proposal?.issues ?? [],

      reply: result.reply,
    })
  }

  const decideOnServer = async (decision: "APPROVE" | "REJECT") => {
    if (
      !proposal?.server ||
      busy ||
      (decision === "APPROVE" && approvalBlocked(proposal, stale))
    )
      return

    setBusy(true)

    const taskIds = proposal.server.taskIds

    try {
      const r = await api.decide(
        conversationId,

        proposal.server.reference,

        decision,
      )

      if (r.state === "AWAITING_APPROVAL") {
        await showReply(r, "")
      } else if (r.state === "SUCCEEDED" && r.result?.outcome === "COMMITTED") {
        setProposal(null)

        savePending(userId, null)

        await reload()

        setReply("")

        setFeedback({ kind: "success", text: r.message })

        showPlannerNotice(r.message)

        onProposalDecision?.(decision, taskIds)

        const task = decision === "APPROVE" ? confirmedTask(r) : null
        if (task) onTaskConfirmed?.(task)
      } else if (decision === "REJECT" && r.state === "SUCCEEDED") {
        setProposal(null)

        savePending(userId, null)

        await reload()

        setReply(r.message)

        setFeedback({ kind: "info", text: r.message })

        onProposalDecision?.(decision, taskIds)
      } else {
        setFeedback({
          kind: "error",

          text: r.error?.message ?? r.message,
        })

        await reload()
      }
    } catch (e) {
      setFeedback({ kind: "error", text: errorText(e) })
    } finally {
      setBusy(false)
    }
  }

  const approve = () => {
    if (apiEnabled) return void decideOnServer("APPROVE")

    if (!proposal || stale) return

    setTasks(proposal.next.tasks)

    setAvailability(proposal.next.availability)

    setRevision((r) => r + 1)

    setProposal(null)

    setReply("")

    setFeedback({ kind: "success", text: "Đã lưu thay đổi vào lịch." })

    showPlannerNotice("Đã lưu thay đổi vào lịch.")
  }

  const reject = () => {
    if (apiEnabled) return void decideOnServer("REJECT")

    setProposal(null)

    setReply("")

    setFeedback({
      kind: "info",

      text: "Đã từ chối đề xuất. Lịch không thay đổi.",
    })
  }

  const send = (color?: string) =>
    sendText(color ? `${input.trim()}, màu ${color}` : input)

  const submitClarification = (followUpText: string) => {
    sendText(followUpText)
  }

  const dismissClarification = () => {
    setClarification(null)
  }

  return {
    busy,

    input,

    setInput,

    reply,

    setReply,

    feedback,

    clarification,

    shown,

    shownWindows,

    stale,

    send,

    submitClarification,

    dismissClarification,

    approve,

    reject,
  }
}
