import type { ActionReference } from "../api/types"

export type IntentCandidate = "SEARCH_TASKS" | "SET_BUSY_INTERVAL" | "SET_SCHEDULING_PREFERENCES" | "CREATE_TASK" | "UPDATE_TASK" | "DELETE_TASK" | "SET_AVAILABILITY" | "GENERATE_STUDY_PLAN" | "RESCHEDULE_STUDY_BLOCK" | "GET_STUDY_PLAN" | "CREATE_STUDY_BLOCK"

export type ResponseCategory = "MESSAGE" | "CLARIFICATION" | "PROPOSAL" | "UNSUPPORTED" | "ERROR"

export type ApprovalStatus = "awaiting_approval" | "review_required" | "cancelled" | "demo_acknowledged" | "approved"

export type AssistantScenario = "task" | "plan" | "view" | "reschedule"

export type ValidationState = "missing_information" | "valid_demo_draft"

export type ActionProposal = {
  intent: IntentCandidate

  title: string

  details: {
    label: string

    value: string
  }[]

  caveat: string

  status: ApprovalStatus

  // API mode: the server-issued action this card decides on. Without it the card is a local demo.

  reference?: ActionReference
}

export type ChatAttachment = {
  id: string

  name: string

  size: string

  type: "image" | "file"

  dataUrl?: string
}

export type ChatMessage = {
  id: string

  timestamp: string

  role: "user" | "assistant"

  category: ResponseCategory

  text: string

  attachments?: ChatAttachment[]

  scenario?: AssistantScenario

  intent?: IntentCandidate

  validation?: ValidationState

  proposal?: ActionProposal

  error?: {
    code: string

    detail: string
  }
}
