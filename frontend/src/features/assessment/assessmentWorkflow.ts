import { ApiError } from "../../api/client.ts"
import type { Endpoints } from "../../api/endpoints.ts"
import type {
  ActionPresentation,
  ActionReference,
  CandidateReviewPatch,
  MaterialChunk,
  OrchestratorReply,
  QuestionDraft,
} from "../../api/types.ts"
import { eligibleQuestions } from "./eligibleQuestions.ts"

export const uncertainDecisionMessage =
  "Chưa xác nhận được kết quả duyệt. Bản nháp vẫn được giữ lại. Bạn có thể thử lại an toàn."

export type PendingOperation = {
  fingerprint: string
  key: string
}

export const DEFAULT_GENERATION_COUNT = 5
export const MAX_GENERATION_COUNT = 10
export const MAX_QUIZ_QUESTION_COUNT = 50
export const MIN_REVISION_MINUTES = 15
export const MAX_REVISION_MINUTES = 240

export function revisionMinutes(value: string) {
  if (!/^\d+$/.test(value)) return null
  const minutes = Number(value)
  return minutes >= MIN_REVISION_MINUTES && minutes <= MAX_REVISION_MINUTES
    ? minutes
    : null
}

export function revisionMinutesError(value: string) {
  if (!value) return "Nhập thời lượng ôn tập."
  if (!/^\d+$/.test(value)) return "Thời lượng phải là số phút nguyên."
  return revisionMinutes(value) === null
    ? "Thời lượng ôn tập phải từ 15 đến 240 phút."
    : ""
}

export function validGenerationCount(value: number) {
  return Number.isInteger(value) && value >= 1 && value <= MAX_GENERATION_COUNT
}

export function defaultQuizQuestionCount(available: number) {
  return Math.min(
    DEFAULT_GENERATION_COUNT,
    Math.max(0, available),
    MAX_QUIZ_QUESTION_COUNT,
  )
}

export function quizQuestionCount(value: number, available: number) {
  const maximum = Math.min(Math.max(0, available), MAX_QUIZ_QUESTION_COUNT)
  return Number.isInteger(value) && value >= 1 && value <= maximum ? value : 0
}

export function generationResultMessage(requested: number, actual: number) {
  return actual === requested
    ? `Đã nhận ${actual} câu nháp để bạn duyệt.`
    : `Đã nhận ${actual} câu nháp từ yêu cầu ${requested} câu.`
}

export function generateQuestionDraftBatch(
  assessmentApi: Pick<Endpoints, "generateQuestionDrafts">,
  conversationId: string,
  materialId: string,
  topic: string,
  count: number,
  idempotencyKey: string,
) {
  if (!validGenerationCount(count))
    throw new RangeError("Question count must be an integer from 1 to 10.")
  return assessmentApi.generateQuestionDrafts(
    conversationId,
    materialId,
    topic,
    "MCQ",
    count,
    idempotencyKey,
  )
}

export async function runGenerationOnce(
  lock: { current: boolean },
  operation: () => Promise<void>,
) {
  if (lock.current) return false
  lock.current = true
  try {
    await operation()
    return true
  } finally {
    lock.current = false
  }
}

export function operationFor(
  existing: PendingOperation | null,
  fingerprint: string,
  createKey: () => string = () => crypto.randomUUID(),
): PendingOperation {
  return existing?.fingerprint === fingerprint
    ? existing
    : { fingerprint, key: createKey() }
}

export function decisionFingerprint(
  reference: ActionReference,
  decision: "APPROVE" | "REJECT",
) {
  return JSON.stringify({ reference, decision })
}

export function attemptQuestionIds(
  questions: QuestionDraft[],
  materialId: string,
  selectedCount = MAX_QUIZ_QUESTION_COUNT,
) {
  return eligibleQuestions(questions, materialId)
    .slice(0, Math.min(MAX_QUIZ_QUESTION_COUNT, Math.max(0, selectedCount)))
    .map((question) => question.question_id)
}

export function createQuizFromVerified(
  assessmentApi: Pick<Endpoints, "createQuizAttempt">,
  materialId: string,
  questions: QuestionDraft[],
  selectedCount: number,
  idempotencyKey: string,
) {
  return assessmentApi.createQuizAttempt(
    materialId,
    attemptQuestionIds(questions, materialId, selectedCount),
    "MANUAL",
    null,
    idempotencyKey,
  )
}

export function quizAnswerSummary(
  questionIds: string[],
  answers: Record<string, string>,
) {
  const answered = questionIds.filter((id) => Boolean(answers[id])).length
  return {
    total: questionIds.length,
    answered,
    unanswered: questionIds.length - answered,
  }
}

export function referencedSources(
  draft: QuestionDraft,
  chunks: MaterialChunk[],
) {
  const byId = new Map(chunks.map((chunk) => [chunk.chunk_id, chunk]))
  return draft.source_chunk_ids.map((chunkId) => ({
    chunkId,
    chunk: byId.get(chunkId) ?? null,
  }))
}

export function recommendationFromReply(reply: OrchestratorReply) {
  const presentation = reply.result?.data as ActionPresentation | undefined
  const reference = reply.action_reference
  if (
    reply.state !== "AWAITING_APPROVAL" ||
    !presentation?.revision_recommendation ||
    !reference ||
    typeof presentation.pending_action.version !== "number" ||
    reference.target_type !== "PENDING_ACTION" ||
    reference.action_id !== presentation.pending_action.action_id ||
    reference.action_version !== presentation.pending_action.version
  )
    return null
  return { presentation, reference }
}

type DecisionApi = Pick<Endpoints, "decide" | "listAssessmentQuestions">

export type QuestionDecisionOutcome = {
  kind: "resolved"
  questions: QuestionDraft[]
} | { kind: "resolved_refresh_failed" } | {
  kind: "uncertain"
  message: string
} | {
  kind: "blocked"
  message: string
}

export async function submitQuestionDecision(
  assessmentApi: DecisionApi,
  conversationId: string,
  materialId: string,
  reference: ActionReference,
  decision: "APPROVE" | "REJECT",
  idempotencyKey: string,
): Promise<QuestionDecisionOutcome> {
  let reply
  try {
    reply = await assessmentApi.decide(
      conversationId,
      reference,
      decision,
      idempotencyKey,
    )
  } catch (error) {
    if (!(error instanceof ApiError) || error.retryable)
      return { kind: "uncertain", message: uncertainDecisionMessage }
    return { kind: "blocked", message: error.message }
  }

  if (reply.state !== "SUCCEEDED") {
    if (reply.error?.retryable)
      return { kind: "uncertain", message: uncertainDecisionMessage }
    return {
      kind: "blocked",
      message:
        reply.error?.message ??
        "Máy chủ không chấp nhận quyết định này. Hãy kiểm tra lại trạng thái trước khi tiếp tục.",
    }
  }

  try {
    return {
      kind: "resolved",
      questions: await assessmentApi.listAssessmentQuestions({
        material_id: materialId,
      }),
    }
  } catch {
    return { kind: "resolved_refresh_failed" }
  }
}

function vietnamInstant(date: string, time: string) {
  return new Date(`${date}T${time}:00+07:00`).toISOString()
}

export function revisionCandidatePatch(
  candidateVersion: number,
  startDate: string,
  startTime: string,
  deadlineDate: string,
  deadlineTime: string,
): CandidateReviewPatch | null {
  if (!startDate || !startTime || !deadlineDate || !deadlineTime) return null
  const startAt = vietnamInstant(startDate, startTime)
  const deadlineAt = vietnamInstant(deadlineDate, deadlineTime)
  if (startAt >= deadlineAt) return null
  return {
    candidate_patch: {
      start_at: startAt,
      deadline_at: deadlineAt,
      deadline_precision: "DATETIME",
      deadline_timezone: "Asia/Ho_Chi_Minh",
    },
    expected_candidate_version: candidateVersion,
  }
}
