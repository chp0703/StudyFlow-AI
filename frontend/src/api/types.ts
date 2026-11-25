// Hand-written mirrors of the F1 v1.1 contract DTOs the UI reads (contracts/schemas/f1.schema.json).

export type ApiTask = {
  task_id: string

  title: string

  description: string | null

  start_at: string

  available_from_at: string | null

  deadline_at: string

  deadline_precision: "DATE" | "DATETIME"

  deadline_date: string | null

  deadline_timezone: "Asia/Ho_Chi_Minh"

  estimated_minutes: number

  remaining_minutes: number

  priority: 0.1 | 0.5 | 1

  color: string

  status: "TODO" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED"
}

export type ApiTimeWindow = {
  window_id: string

  version: number

  kind: "AVAILABILITY" | "BUSY"

  label: string | null

  recurrence: "NONE" | "WEEKLY"

  timezone: string

  start_at: string | null

  end_at: string | null

  weekday: number | null

  start_time: string | null

  end_time: string | null

  valid_from: string | null

  valid_until: string | null

  archived_at: string | null
}

export type ApiBlock = {
  block_id: string

  task_id: string

  start_at: string

  end_at: string

  is_locked: boolean
}

export type PlanRef = {
  plan_id: string

  version: number
}

export type PlanWarning = {
  code: string

  message: string
}

export type Choice = {
  label: string

  value: string
}

export type PendingActionRef = {
  intent: string

  state: string

  action_id: string

  version: number
}

export type Page<T,> = {
  items: T[]

  next_cursor: string | null
}

export type PlanView = {
  kind: "PLAN_VIEW"

  plan: PlanRef | null

  study_blocks: ApiBlock[]
}

export type PlanProposal = {
  proposal_id: string

  version: number

  status: "PROPOSED" | "APPROVED" | "REJECTED" | "STALE"

  base_plan_version: number | null

  base_schedule_revision: number

  payload: {
    study_blocks: ApiBlock[]

    task_summaries: {
      task_id: string

      remaining_minutes: number

      retained_future_minutes: number

      newly_scheduled_minutes: number

      unallocated_minutes: number

      reason_codes: string[]
    }[]

    coverage: "FULL" | "PARTIAL"

    warnings: PlanWarning[]

    plan_diff: {
      added: string[]

      moved: string[]

      removed: string[]

      unchanged: string[]
    }
  }
}

export type ActionReference = {
  action_id: string

  action_version: number

  target_type: "TASK_CANDIDATE" | "PENDING_ACTION" | "PLAN_PROPOSAL"

  target_id: string

  target_version: number
}

export type DailyMaterialStatus = "UPLOADED" | "INDEXING" | "READY" | "FAILED"

export type DailyLearningMaterial = {
  material_id: string
  owner_id: string
  course_label: string | null
  filename: string
  mime_type: "application/pdf" | "text/plain" | "text/markdown"
  sha256: string
  byte_size: number
  page_count: number | null
  status: DailyMaterialStatus
  error_code: "INVALID_DOCUMENT" | "INDEX_TIMEOUT" | "INDEX_UNAVAILABLE" | null
  created_at: string
}

export type DailyLearningCitation = {
  chunk_id: string
  material_id: string
  page: number
  material_deleted: boolean
}

export type DailyLearningTurn = {
  turn_id: string
  session_id: string
  owner_id: string
  ordinal: number
  role: "USER" | "ASSISTANT"
  kind: "ASK" | "HINT"
  hint_level: 1 | 2 | 3 | null
  content: string
  citations: DailyLearningCitation[]
  supported: boolean | null
  model: string | null
  prompt_version: string | null
}

export type DailyLearningSession = {
  session_id: string
  owner_id: string
  conversation_id: string
  goal: string
  material_ids: string[]
  planner_block_id: string | null
  status: "ACTIVE" | "SUMMARY_PENDING" | "CLOSED"
  version: number
  created_at: string
  expires_at: string
}

export type DailyLearningSummaryDraft = {
  summary: string
  topics: string[]
  duration_minutes: number
}

export type DailyLearningSummaryData = {
  operation: "save_session_outcome"
  session: DailyLearningSession
  draft: DailyLearningSummaryDraft
  action_reference: ActionReference
}

export type DailyLearningPlannerContext = {
  block_id: string
  task_id: string
  task_title: string
  start_at: string
  end_at: string
  suggested_goal: string
}

export type Question = {
  field: string

  message: string

  choices: Choice[]
}

export type ActionPresentation = {
  kind: "ACTION_PRESENTATION"

  pending_action: PendingActionRef

  candidate: ApiTaskCandidate | null

  proposal: PlanProposal | null

  normalized_command: {
    operation: string

    arguments: Record<string, unknown>
  } | null

  effective_policy: Record<string, unknown> | null

  question_drafts?: QuestionDraftBatchData | null

  revision_recommendation?: RevisionRecommendation | null

  revision_source_chunks?: MaterialChunk[] | null
}

export type ToolResult = {
  outcome: string

  data: unknown

  warnings?: {
    code: string

    message: string

    field: string | null

    details: Record<string, unknown>
  }[]
}

export type ApiErrorBody = {
  code: string

  message: string

  field: string | null

  retryable: boolean
}

export type OrchestratorReply = {
  request_id: string

  state: "NEEDS_CLARIFICATION" | "AWAITING_APPROVAL" | "SUCCEEDED" | "ERROR"

  message: string

  action_reference: ActionReference | null

  questions: Question[]

  result: ToolResult | null

  error: ApiErrorBody | null
}

export type ListResult<T,> = {
  data: Page<T>
}

// Optional BE-04 extension 1.0.0. Source content is draft data, never approval.

export type IngestionSource = {
  ingestion_version: "1.0.0"

  source_id: string

  user_id: string

  conversation_id: string

  filename: string

  mime_type: string

  size_bytes: number

  sha256: string

  status: "UPLOADED" | "EXTRACTING" | "READY" | "FAILED"

  lease_version: number

  created_at: string

  extraction: {
    parser: "document-v1" | "vision-v1" | "calendar-v1"

    model: string | null

    prompt_version: "be04-1"

    extracted_at: string

    usage: {
      input_tokens: number

      output_tokens: number
    }

    intents: Array<{
      intent: "CREATE_TASK" | "SET_BUSY_INTERVAL"

      slots: Record<string, unknown>

      raw_expressions: Record<string, string>

      ambiguities: Array<{
        code: string

        message: string

        field: string | null
      }>
    }>
  } | null

  error_code: "INVALID_PARAMETER" | "SERVICE_UNAVAILABLE" | "INTERNAL_ERROR" | null
}

// Optional F2 Assessment extension 1.0.0. Generated questions are drafts until verified via /v1/decisions.

export type QuestionDraftStatus = "DRAFT" | "VERIFIED" | "REJECTED"

export type QuestionType = "MCQ" | "TRUE_FALSE"

export type QuizAttemptOrigin = "MANUAL" | "SESSION_HANDOFF"

export type QuizAttemptStatus = "IN_PROGRESS" | "SUBMITTED"

export type QuizResponseValidity = "VALID" | "OMITTED" | "INVALID"

export type TopicStatsStatus = "AVAILABLE" | "INSUFFICIENT_DATA"

export type LearningMaterial = {
  assessment_version: "1.0.0"

  material_id: string

  user_id: string

  conversation_id: string

  filename: string

  mime_type: "text/plain" | "text/markdown" | "application/pdf"

  size_bytes: number

  sha256: string

  page_count: number

  char_count: number

  topics: string[]

  status: "UPLOADED" | "READY" | "FAILED"

  error_code: "INVALID_PARAMETER" | "SERVICE_UNAVAILABLE" | "INTERNAL_ERROR" | null

  created_at: string

  updated_at: string
}

export type MaterialChunk = {
  chunk_id: string

  material_id: string

  user_id: string

  page: number

  topic: string

  chunk_index: number

  text: string

  created_at: string
}

export type AssessmentMaterialDetailData = {
  material: LearningMaterial

  chunks: MaterialChunk[]
}

export type QuestionOption = {
  option_id: string

  text: string
}

export type QuestionDraft = {
  assessment_version: "1.0.0"

  question_id: string

  user_id: string

  conversation_id: string

  material_id: string

  version: number

  topic: string

  question_type: QuestionType

  stem: string

  options: QuestionOption[]

  answer_key: string

  explanation: string | null

  source_chunk_ids: string[]

  status: QuestionDraftStatus

  model: string | null

  prompt_version: string

  verified_at: string | null

  created_at: string

  updated_at: string
}

export type QuestionDraftBatchData = {
  items: QuestionDraft[]

  source_chunks?: MaterialChunk[]
}

export type QuizAttempt = {
  assessment_version: "1.0.0"

  attempt_id: string

  user_id: string

  material_id: string

  origin: QuizAttemptOrigin

  session_outcome_id: string | null

  status: QuizAttemptStatus

  question_ids: string[]

  total_questions: number

  valid_response_count: number

  correct_count: number

  incorrect_count: number

  omitted_count: number

  score_percent: number | null

  started_at: string

  submitted_at: string | null

  created_at: string

  updated_at: string
}

export type QuizResponse = {
  response_id: string

  attempt_id: string

  question_id: string

  user_id: string

  selected_option_id: string | null

  validity: QuizResponseValidity

  is_correct: boolean | null

  graded_at: string | null

  created_at: string

  updated_at: string
}

export type QuizAttemptSubmissionData = {
  attempt: QuizAttempt

  responses: QuizResponse[]
}

export type TopicStatsItem = {
  material_id: string

  topic: string

  status: TopicStatsStatus

  valid_response_count: number

  error_count: number

  error_rate: number | null

  last_attempt_at: string | null
}

export type TopicStatsData = {
  assessment_version: "1.0.0"

  material_id: string | null

  items: TopicStatsItem[]
}

export type RecommendationEvidence = {
  attempt_ids: string[]

  chunk_ids: string[]

  valid_response_count: number

  error_count: number

  error_rate: number
}

export type ConfidenceLimit = {
  level: "LOW" | "MEDIUM" | "HIGH"

  limitations: string[]
}

export type RevisionRecommendation = {
  assessment_version: "1.0.0"

  recommendation_id: string

  user_id: string

  conversation_id: string

  material_id: string

  topic: string

  priority: 0.1 | 0.5 | 1

  suggested_minutes: number

  reason_summary: string

  evidence: RecommendationEvidence

  confidence_limit: ConfidenceLimit

  pending_action_id: string

  candidate_id: string | null

  status: "PROPOSED" | "ACCEPTED" | "REJECTED"

  created_at: string

  updated_at: string
}

export type CandidateTaskFields = {
  title?: string | null

  description?: string | null

  start_at?: string | null

  available_from_at?: string | null

  deadline_at?: string | null

  deadline_precision?: "DATE" | "DATETIME" | null

  deadline_date?: string | null

  deadline_timezone?: "Asia/Ho_Chi_Minh" | null

  estimated_minutes?: number | null

  priority?: 0.1 | 0.5 | 1 | null

  color?: string | null
}

export type CandidateReviewPatch = {
  candidate_patch: CandidateTaskFields

  expected_candidate_version: number
}

export type ApiTaskCandidate = {
  candidate_id: string

  user_id: string

  conversation_id: string

  version: number

  status: "DRAFT" | "CONFIRMED" | "CANCELLED"

  slots: CandidateTaskFields

  raw_expressions: Record<string, string>

  field_sources: Record<string, {
    source: "USER_MESSAGE" | "CONFIRMED_CONTEXT" | "SYSTEM_DEFAULT" | "DERIVED"
    reference: string | null
  }>

  source_message_id: string

  confirmed_task_id: string | null

  created_at: string

  updated_at: string
}
