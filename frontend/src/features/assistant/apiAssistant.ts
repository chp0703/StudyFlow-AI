import { errorText } from "../../api/client.ts"

import { summarize } from "../../api/mappers.ts"

import type {
  ActionPresentation,
  ApiTask,
  OrchestratorReply,
} from "../../api/types.ts"

import type {
  ActionProposal,
  ChatMessage,
  IntentCandidate,
} from "../../types/assistant.ts"

type Draft = Omit<ChatMessage, "id" | "timestamp">

const INTENTS: IntentCandidate[] = [
  "CREATE_TASK",
  "SEARCH_TASKS",
  "SET_AVAILABILITY",
  "SET_BUSY_INTERVAL",
  "SET_SCHEDULING_PREFERENCES",
  "GENERATE_STUDY_PLAN",
  "GET_STUDY_PLAN",
]

// A card the user can approve or cancel: what the server says it will do, plus the reference to send back.
export function proposalFromReply(
  reply: OrchestratorReply,
): ActionProposal | null {
  const presentation = reply.result?.data as ActionPresentation | undefined

  if (!reply.action_reference || presentation?.kind !== "ACTION_PRESENTATION")
    return null

  const { title, details } = summarize(presentation)

  const intent = presentation.pending_action.intent as IntentCandidate

  return {
    intent: INTENTS.includes(intent) ? intent : "CREATE_TASK",

    title,

    details,

    caveat: "",

    status: "awaiting_approval",

    reference: reply.action_reference,
  }
}

// Short list of what a read returned (tasks only; plans are shown on the Planner page).
function listing(reply: OrchestratorReply): string {
  const data = reply.result?.data as { items?: ApiTask[] } | undefined

  if (!Array.isArray(data?.items) || data.items.length === 0) return ""

  const lines = data.items
    .slice(0, 5)
    .map(
      (t) =>
        `• ${t.title} — hạn ${t.deadline_date ?? t.deadline_at.slice(0, 10)}`,
    )

  const more =
    data.items.length > 5
      ? `\n… và ${data.items.length - 5} công việc khác.`
      : ""

  return `\n${lines.join("\n")}${more}`
}

export function replyToMessage(reply: OrchestratorReply): Draft {
  if (reply.state === "AWAITING_APPROVAL") {
    const proposal = proposalFromReply(reply)

    return {
      role: "assistant",

      category: "PROPOSAL",

      text: reply.message,

      ...(proposal ? { intent: proposal.intent, proposal } : {}),
    }
  }

  if (reply.state === "NEEDS_CLARIFICATION")
    return {
      role: "assistant",

      category: "CLARIFICATION",

      text: [
        reply.message,
        ...reply.questions.map((q) => `• ${q.message}`),
      ].join("\n"),
    }

  if (reply.state === "ERROR" || reply.error)
    return {
      role: "assistant",

      category: "ERROR",

      text: reply.message,

      error: {
        code: reply.error?.code ?? "INTERNAL_ERROR",
        detail: reply.message,
      },
    }

  return {
    role: "assistant",

    category: "MESSAGE",

    text: `${reply.message}${listing(reply)}`,
  }
}

export function errorToMessage(error: unknown): Draft {
  const code = (error as { code?: string })?.code ?? "INTERNAL_ERROR"

  return {
    role: "assistant",

    category: "ERROR",

    text: errorText(error),

    error: { code, detail: errorText(error) },
  }
}
