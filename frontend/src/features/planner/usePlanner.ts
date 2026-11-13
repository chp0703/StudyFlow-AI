import { useRef, useState, type Dispatch, type SetStateAction } from "react"
import type { Task } from "../../types/task"
import type { Proposal, TimeWindow } from "../../types/planner"
import { runPlannerCommand } from "./plannerAgent"
import { demoNoOpResult, diffTasks, diffWindows, isStale } from "./proposal"
import { api } from "../../api"

import { apiEnabled } from "../../api/config"

import { ApiError, errorText } from "../../api/client"

import { proposalFromReply } from "../../api/mappers"

import { savePending } from "../../api/pending"

import type { ApiTimeWindow, OrchestratorReply } from "../../api/types"
import { prepareDemoWorkingChange } from "./workingTime"

export type PlannerProps = {
  tasks: Task[]

  events: Task[]

  windows?: ApiTimeWindow[]

  setWorkingWindows: Dispatch<SetStateAction<ApiTimeWindow[]>>

  workingConfigured: boolean

  setWorkingConfigured: Dispatch<SetStateAction<boolean>>

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
}

export function usePlanner(
  {
    tasks,
    events,
    windows,
    setWorkingWindows,
    workingConfigured,
    setWorkingConfigured,
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
  }: PlannerProps,
  showPlannerNotice: (message: string) => void,
) {
  const [input, setInput] = useState("")
  const [reply, setReply] = useState("")
  const [busy, setBusy] = useState(false)
  // Retrying the same message keeps its idempotency key.
  const attempt = useRef<{
    text: string
    key: string
  } | null>(null)
  const availabilityAttempt = useRef<{
    body: string
    key: string
  } | null>(null)
  const shown = proposal ? proposal.next.tasks : apiEnabled ? events : tasks
  const shownWindows = proposal ? proposal.next.availability : availability
  const stale = proposal ? isStale(proposal, revision) : false

  // API mode: show what the server answered. A reply that waits for approval becomes the pending proposal.

  const showReply = async (r: OrchestratorReply) => {
    if (r.state === "AWAITING_APPROVAL") {
      const next = proposalFromReply(r, {
        tasks,
        events,
        windows,
        availability,
        revision,
      })

      setProposal(next)

      setReply(r.message)

      if (next && r.action_reference)
        savePending(userId, {
          conversationId,
          reference: r.action_reference,
        })

      return
    }

    setProposal(null)

    savePending(userId, null)

    const questions = r.questions.map((q) => q.message).join(" ")

    setReply(questions ? `${r.message} ${questions}` : r.message)

    if (r.state === "SUCCEEDED") await reload()
  }

  const sendToServer = async (text: string) => {
    const key =
      attempt.current?.text === text ? attempt.current.key : crypto.randomUUID()

    attempt.current = { text, key }

    setBusy(true)

    try {
      await showReply(await api.sendMessage(conversationId, text, key))

      attempt.current = null

      setInput("")
    } catch (e) {
      setReply(errorText(e))

      // Only a failure that may have reached the server keeps the key for the retry.

      if (e instanceof ApiError && !e.retryable) attempt.current = null
    } finally {
      setBusy(false)
    }
  }

  const prepareAvailability = async (
    args: Parameters<typeof api.prepareAvailability>[1],
  ) => {
    if (busy || proposal) return false
    if (!apiEnabled) {
      const change = prepareDemoWorkingChange(
        windows ?? [],
        args,
        crypto.randomUUID(),
      )
      if (!change) {
        setReply("Khoảng học đã thay đổi. Hãy mở lại rồi thử tiếp.")
        return false
      }
      setProposal({
        id: crypto.randomUUID(),
        createdAt: Date.now(),
        baseRevision: revision,
        next: {
          tasks,
          availability,
          weeklyWindows: change.windows,
          workingConfigured: true,
        },
        changes: [],
        windowChanges: [],
        issues: [],
        reply: change.description,
      })
      setReply(change.description)
      return true
    }
    setBusy(true)
    try {
      const body = JSON.stringify(args)
      const key =
        availabilityAttempt.current?.body === body
          ? availabilityAttempt.current.key
          : crypto.randomUUID()
      availabilityAttempt.current = { body, key }
      const prepared = await api.prepareAvailability(conversationId, args, key)
      await showReply(prepared)
      availabilityAttempt.current = null
      return prepared.state === "AWAITING_APPROVAL"
    } catch (error) {
      setReply(errorText(error))
      if (error instanceof ApiError && !error.retryable)
        availabilityAttempt.current = null
      return false
    } finally {
      setBusy(false)
    }
  }

  const send = () => {
    const text = input.trim()

    if (!text || busy) return

    if (apiEnabled) return void sendToServer(text)

    // Commands stack on a pending proposal, but are always diffed against the committed schedule.

    const result = runPlannerCommand(
      text,
      shown,
      shownWindows,
      proposal?.next.weeklyWindows ?? windows ?? [],
      proposal?.next.workingConfigured ?? workingConfigured,
    )

    const changes = diffTasks(tasks, result.tasks)

    const windowChanges = diffWindows(availability, result.availability)

    setInput("")

    if (!changes.length && !windowChanges.length) {
      const next = demoNoOpResult(proposal, result.reply)
      setProposal(next.proposal)
      setReply(next.reply)
      if (next.notice) showPlannerNotice(next.notice)
      return
    }

    setReply(result.reply)

    setProposal({
      id: proposal?.id ?? crypto.randomUUID(),

      createdAt: proposal?.createdAt ?? Date.now(),

      baseRevision: proposal?.baseRevision ?? revision,

      next: {
        tasks: result.tasks,
        availability: result.availability,
        weeklyWindows: proposal?.next.weeklyWindows ?? windows,
        workingConfigured:
          proposal?.next.workingConfigured ?? workingConfigured,
      },

      changes,

      windowChanges,

      issues: result.issues ?? proposal?.issues ?? [],

      reply: result.reply,
    })
  }

  const decideOnServer = async (decision: "APPROVE" | "REJECT") => {
    if (!proposal?.server || busy || (stale && decision === "APPROVE")) return

    setBusy(true)

    try {
      const r = await api.decide(
        conversationId,
        proposal.server.reference,
        decision,
      )

      if (r.state === "AWAITING_APPROVAL") {
        await showReply(r)
      } else if (r.state === "SUCCEEDED" && r.result?.outcome === "COMMITTED") {
        setProposal(null)
        savePending(userId, null)
        await reload()
        setReply("")
        showPlannerNotice(r.message)
      } else if (decision === "REJECT" && r.state === "SUCCEEDED") {
        setProposal(null)
        savePending(userId, null)
        await reload()
        setReply(r.message)
      } else {
        setReply(r.error?.message ?? r.message)
        await reload()
      }
    } catch (e) {
      setReply(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const approve = () => {
    if (apiEnabled) return void decideOnServer("APPROVE")

    if (!proposal || stale) return

    setTasks(proposal.next.tasks)

    setAvailability(proposal.next.availability)

    if (proposal.next.weeklyWindows)
      setWorkingWindows(proposal.next.weeklyWindows)

    if (proposal.next.workingConfigured !== undefined)
      setWorkingConfigured(proposal.next.workingConfigured)

    setRevision((r) => r + 1)

    setProposal(null)

    setReply("")

    showPlannerNotice("Đã lưu thay đổi vào lịch.")
  }

  const reject = () => {
    if (apiEnabled) return void decideOnServer("REJECT")

    setProposal(null)

    setReply("")
  }

  return {
    busy,
    input,
    setInput,
    reply,
    setReply,
    shown,
    shownWindows,
    stale,
    send,
    prepareAvailability,
    approve,
    reject,
  }
}
