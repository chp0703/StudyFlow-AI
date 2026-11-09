import { useRef, useState, type Dispatch, type SetStateAction } from "react"
import type { Task } from "../../types/task"
import type { Proposal, TimeWindow } from "../../types/planner"
import { runPlannerCommand } from "./plannerAgent"
import { diffTasks, diffWindows, isStale } from "./proposal"
import { api } from "../../api"

import { apiEnabled } from "../../api/config"

import { ApiError, errorText } from "../../api/client"

import { proposalFromReply } from "../../api/mappers"

import { savePending } from "../../api/pending"

import type { OrchestratorReply } from "../../api/types"

export type PlannerProps = {
  tasks: Task[]

  events: Task[]

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
  const shown = proposal ? proposal.next.tasks : apiEnabled ? events : tasks
  const shownWindows = proposal ? proposal.next.availability : availability
  const stale = proposal ? isStale(proposal, revision) : false

  // API mode: show what the server answered. A reply that waits for approval becomes the pending proposal.

  const showReply = async (r: OrchestratorReply) => {
    if (r.state === "AWAITING_APPROVAL") {
      const next = proposalFromReply(r, {
        tasks,
        events,
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

  const send = () => {
    const text = input.trim()

    if (!text || busy) return

    if (apiEnabled) return void sendToServer(text)

    // Commands stack on a pending proposal, but are always diffed against the committed schedule.

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

  const decideOnServer = async (decision: "APPROVE" | "REJECT") => {
    if (!proposal?.server || busy) return

    setBusy(true)

    try {
      const r = await api.decide(
        conversationId,
        proposal.server.reference,
        decision,
      )

      setProposal(null)

      savePending(userId, null)

      await reload()

      if (r.state === "AWAITING_APPROVAL") await showReply(r)
      else {
        setReply("")

        showPlannerNotice(r.message)
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
    approve,
    reject,
  }
}
