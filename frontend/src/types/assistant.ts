export type IntentCandidate = "CREATE_TASK" | "UPDATE_TASK" | "DELETE_TASK" | "SET_AVAILABILITY" | "GENERATE_STUDY_PLAN" | "RESCHEDULE_STUDY_BLOCK" | "GET_STUDY_PLAN" | "CREATE_STUDY_BLOCK"

export type ResponseCategory = "MESSAGE" | "CLARIFICATION" | "PROPOSAL" | "UNSUPPORTED" | "ERROR"
export type ApprovalStatus = "awaiting_approval" | "review_required" | "cancelled" | "demo_acknowledged"
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
}

export type ChatMessage = {
  id: string
  timestamp: string
  role: "user" | "assistant"
  category: ResponseCategory
  text: string
  scenario?: AssistantScenario
  intent?: IntentCandidate
  validation?: ValidationState
  proposal?: ActionProposal
  error?: {
    code: string
    detail: string
  }
}
