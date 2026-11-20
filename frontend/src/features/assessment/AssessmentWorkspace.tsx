import {
  useEffect,
  useRef,
  useState,
  type DragEvent,
  type FormEvent,
} from "react"
import { api } from "../../api"
import { ApiError } from "../../api/client"
import Button from "../../components/ui/Button"
import Card from "../../components/ui/Card"
import DecisionActions from "./DecisionActions"
import QuizOverview from "./QuizOverview"
import {
  assessmentStageState,
  type AssessmentStage,
} from "./assessmentProgress"
import { eligibleQuestions } from "./eligibleQuestions"
import {
  createQuizFromVerified,
  DEFAULT_GENERATION_COUNT,
  defaultQuizQuestionCount,
  decisionFingerprint,
  generateQuestionDraftBatch,
  generationResultMessage,
  MAX_GENERATION_COUNT,
  MAX_QUIZ_QUESTION_COUNT,
  operationFor,
  quizAnswerSummary,
  quizQuestionCount,
  referencedSources,
  recommendationFromReply,
  revisionCandidatePatch,
  submitQuestionDecision,
  runGenerationOnce,
  uncertainDecisionMessage,
  type PendingOperation,
} from "./assessmentWorkflow"
import type {
  ActionPresentation,
  ActionReference,
  AssessmentMaterialDetailData,
  QuestionDraft,
  QuizAttempt,
  QuizAttemptSubmissionData,
  TopicStatsItem,
} from "../../api/types"

const allowedTypes = ["text/plain", "text/markdown", "application/pdf"] as const
const maxBytes = 10 * 1024 * 1024
type StageDefinition = {
  id: AssessmentStage
  label: string
}

const stages: StageDefinition[] = [
  { id: "materials", label: "Tài liệu" },
  { id: "questions", label: "Câu hỏi" },
  { id: "practice", label: "Luyện tập" },
  { id: "results", label: "Kết quả" },
]

function formatBytes(bytes: number) {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function materialMime(file: File) {
  if (file.name.toLowerCase().endsWith(".md")) return "text/markdown"
  if (file.name.toLowerCase().endsWith(".txt")) return "text/plain"
  if (file.name.toLowerCase().endsWith(".pdf")) return "application/pdf"
  return null
}

function readBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error("Không đọc được tệp."))
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] ?? "")
    reader.readAsDataURL(file)
  })
}

export default function AssessmentWorkspace() {
  const [conversationId] = useState(() => crypto.randomUUID())
  const [file, setFile] = useState<File | null>(null)
  const [topic, setTopic] = useState("")
  const [material, setMaterial] = useState<AssessmentMaterialDetailData | null>(
    null,
  )
  const [questions, setQuestions] = useState<QuestionDraft[]>([])
  const [drafts, setDrafts] = useState<QuestionDraft[]>([])
  const [reference, setReference] = useState<ActionReference | null>(null)
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null)
  const [result, setResult] = useState<QuizAttemptSubmissionData | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [stats, setStats] = useState<TopicStatsItem[]>([])
  const [busy, setBusy] = useState("")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [stage, setStage] = useState<AssessmentStage>("materials")
  const [isDragging, setIsDragging] = useState(false)
  const [reviewIndex, setReviewIndex] = useState(0)
  const [quizIndex, setQuizIndex] = useState(0)
  const [generationCount, setGenerationCount] = useState(
    DEFAULT_GENERATION_COUNT,
  )
  const [selectedQuizCount, setSelectedQuizCount] = useState(0)
  const [showSubmitConfirmation, setShowSubmitConfirmation] = useState(false)
  const [statsLoaded, setStatsLoaded] = useState(false)
  const [decisionState, setDecisionState] =
    useState<"idle" | "uncertain" | "blocked">("idle")
  const [questionRefreshNeeded, setQuestionRefreshNeeded] = useState(false)
  const decisionOperation = useRef<PendingOperation & {
    decision: "APPROVE" | "REJECT"
  } | null>(null)
  const decisionInFlight = useRef(false)
  const generationInFlight = useRef(false)
  const [recommendation, setRecommendation] =
    useState<ActionPresentation | null>(null)
  const [recommendationReference, setRecommendationReference] =
    useState<ActionReference | null>(null)
  const [recommendationState, setRecommendationState] =
    useState<"ready" | "insufficient" | "awaiting_review" | "candidate_details" | "candidate_review" | "confirmed" | "rejected" | "stale">(
      "ready",
    )
  const [suggestedMinutes, setSuggestedMinutes] = useState("60")
  const [recommendationPriority, setRecommendationPriority] =
    useState<"0.1" | "0.5" | "1">("0.5")
  const [candidateTimes, setCandidateTimes] = useState({
    startDate: "",
    startTime: "09:00",
    deadlineDate: "",
    deadlineTime: "23:59",
  })
  const recommendationOperation = useRef<PendingOperation & {
    decision?: "APPROVE" | "REJECT"
  } | null>(null)
  const current = material?.material
  const verified = current
    ? eligibleQuestions(questions, current.material_id)
    : []
  const maxSelectableQuizCount = Math.min(
    MAX_QUIZ_QUESTION_COUNT,
    verified.length,
  )
  const stageState = assessmentStageState({
    materialReady: current?.status === "READY",
    verifiedCount: verified.length,
    hasAttempt: Boolean(attempt),
    hasResult: Boolean(result),
    statsLoaded,
  })
  const activeDraft = drafts[reviewIndex]
  const activeQuestionId = attempt?.question_ids[quizIndex]
  const activeQuestion = activeQuestionId
    ? verified.find((item) => item.question_id === activeQuestionId)
    : null
  const answerSummary = quizAnswerSummary(attempt?.question_ids ?? [], answers)
  const observedTopic = stats.find((item) => item.topic === current?.topics[0])
  const hasRecommendationEvidence = Boolean(
    observedTopic?.status === "AVAILABLE" && observedTopic.error_count > 0,
  )

  useEffect(() => {
    setSelectedQuizCount(defaultQuizQuestionCount(verified.length))
  }, [current?.material_id, verified.length])

  function selectFile(nextFile: File | null) {
    setFile(nextFile)
    setError("")
  }

  function dropFile(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    setIsDragging(false)
    selectFile(event.dataTransfer.files[0] ?? null)
  }

  async function run(label: string, operation: () => Promise<void>) {
    setBusy(label)
    setError("")
    setNotice("")
    try {
      await operation()
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Thao tác thất bại. Vui lòng thử lại.",
      )
    } finally {
      setBusy("")
    }
  }

  async function loadQuestions(materialId: string) {
    setQuestions(await api.listAssessmentQuestions({ material_id: materialId }))
  }

  function upload(event: FormEvent) {
    event.preventDefault()
    if (!file) return
    const mimeType = materialMime(file)
    if (!mimeType || !allowedTypes.includes(mimeType)) {
      setError("Chỉ hỗ trợ TXT, Markdown hoặc PDF.")
      return
    }
    if (file.size > maxBytes || file.size === 0) {
      setError("Tệp cần có nội dung và không quá 10 MB.")
      return
    }
    const confirmedTopic = topic.trim()
    if (!confirmedTopic || confirmedTopic.length > 120) {
      setError("Nhập một chủ đề từ 1 đến 120 ký tự.")
      return
    }
    void run("upload", async () => {
      const response = await api.uploadAssessmentMaterial(
        conversationId,
        file.name,
        mimeType,
        await readBase64(file),
        [confirmedTopic],
        crypto.randomUUID(),
      )
      setMaterial(response.data)
      setQuestions([])
      setDrafts([])
      setReference(null)
      setAttempt(null)
      setResult(null)
      setStats([])
      setStatsLoaded(false)
      setReviewIndex(0)
      setQuizIndex(0)
      setDecisionState("idle")
      decisionOperation.current = null
      setQuestionRefreshNeeded(false)
      setRecommendation(null)
      setRecommendationReference(null)
      setRecommendationState("ready")
      recommendationOperation.current = null
      setNotice(
        response.data.material.status === "READY"
          ? "Tài liệu đã sẵn sàng."
          : "Tài liệu đã nhận; đang chờ xử lý.",
      )
    })
  }

  function generate() {
    if (!current || current.status !== "READY") return
    void runGenerationOnce(generationInFlight, () =>
      run("generate", async () => {
        const reply = await generateQuestionDraftBatch(
          api,
          conversationId,
          current.material_id,
          current.topics[0],
          generationCount,
          crypto.randomUUID(),
        )
        const presentation = reply.result
          ?.data as ActionPresentation | undefined
        const batch = presentation?.question_drafts
        const ref = reply.action_reference
        if (
          reply.state !== "AWAITING_APPROVAL" ||
          !batch?.items.length ||
          !ref ||
          ref.target_type !== "PENDING_ACTION" ||
          ref.target_id !== ref.action_id ||
          ref.target_version !== ref.action_version ||
          ref.action_version < 1 ||
          ref.action_id !== presentation?.pending_action.action_id ||
          batch.items.some(
            (item) =>
              item.status !== "DRAFT" ||
              item.material_id !== current.material_id ||
              item.topic !== current.topics[0] ||
              item.version < 1 ||
              item.source_chunk_ids.some(
                (id) =>
                  !material?.chunks.some((chunk) => chunk.chunk_id === id),
              ),
          )
        ) {
          throw new Error(
            "Không thể xác định an toàn bản nháp cần duyệt. Hãy tải lại và tạo yêu cầu mới.",
          )
        }
        setDrafts(batch.items)
        setReviewIndex(0)
        setReference(ref)
        setNotice(generationResultMessage(generationCount, batch.items.length))
        setStage("questions")
      }),
    )
  }

  async function decide(decision: "APPROVE" | "REJECT") {
    if (!current || !reference || !drafts.length || decisionInFlight.current)
      return
    const fingerprint = decisionFingerprint(reference, decision)
    if (
      decisionOperation.current &&
      decisionOperation.current.fingerprint !== fingerprint
    ) {
      setError(
        "Không thể đổi quyết định khi kết quả lần gửi trước chưa rõ. Hãy thử lại đúng quyết định cũ hoặc kiểm tra trạng thái.",
      )
      return
    }

    const operation = operationFor(
      decisionOperation.current,
      fingerprint,
    ) as PendingOperation & { decision: "APPROVE" | "REJECT" }
    operation.decision = decision
    decisionOperation.current = operation
    decisionInFlight.current = true
    setBusy("decide")
    setError("")
    setNotice("")
    const outcome = await submitQuestionDecision(
      api,
      conversationId,
      current.material_id,
      reference,
      decision,
      operation.key,
    )
    decisionInFlight.current = false
    setBusy("")

    if (outcome.kind === "uncertain") {
      setDecisionState("uncertain")
      setError(outcome.message)
      return
    }
    if (outcome.kind === "blocked") {
      setDecisionState("blocked")
      setError(outcome.message)
      return
    }

    decisionOperation.current = null
    setDecisionState("idle")
    setReference(null)
    setDrafts([])
    setReviewIndex(0)
    setNotice(
      decision === "APPROVE"
        ? "Câu hỏi đã được xác minh."
        : "Đã từ chối bản nháp.",
    )
    if (outcome.kind === "resolved_refresh_failed") {
      setQuestionRefreshNeeded(true)
      setError(
        "Quyết định đã được lưu, nhưng chưa tải lại được danh sách câu hỏi. Hãy làm mới; không cần gửi lại quyết định.",
      )
      return
    }
    setQuestions(outcome.questions)
    setQuestionRefreshNeeded(false)
    if (decision === "APPROVE") setStage("practice")
  }

  async function reconcileDecision() {
    if (!current || !drafts.length) return
    await run("reconcile", async () => {
      const saved = await api.listAssessmentQuestions({
        material_id: current.material_id,
      })
      setQuestions(saved)
      const draftIds = new Set(drafts.map((draft) => draft.question_id))
      const unresolved = saved.some(
        (item) => draftIds.has(item.question_id) && item.status === "DRAFT",
      )
      if (unresolved) {
        setDecisionState("blocked")
        throw new Error(
          "Bản nháp vẫn đang chờ duyệt trên máy chủ. Giữ nguyên dữ liệu để tránh gửi một quyết định khác.",
        )
      }
      decisionOperation.current = null
      setDecisionState("idle")
      setReference(null)
      setDrafts([])
      setReviewIndex(0)
      setNotice("Đã đồng bộ trạng thái duyệt từ máy chủ.")
    })
  }

  function start() {
    const count = quizQuestionCount(selectedQuizCount, verified.length)
    if (!current || !count) return
    void run("start", async () => {
      // Only server-listed VERIFIED IDs are sent. The backend checks again.
      const response = await createQuizFromVerified(
        api,
        current.material_id,
        questions,
        count,
        crypto.randomUUID(),
      )
      setAttempt(response.data)
      setResult(null)
      setAnswers({})
      setQuizIndex(0)
      setShowSubmitConfirmation(false)
      setStage("practice")
    })
  }

  async function requestRecommendation() {
    if (!current || busy || !hasRecommendationEvidence) return
    const minutes = Number(suggestedMinutes)
    if (!Number.isInteger(minutes) || minutes < 15 || minutes > 240) {
      setError("Thời lượng ôn tập phải từ 15 đến 240 phút.")
      return
    }
    const priority = Number(recommendationPriority) as 0.1 | 0.5 | 1
    const fingerprint = JSON.stringify({
      materialId: current.material_id,
      topic: current.topics[0],
      minutes,
      priority,
    })
    if (
      recommendationOperation.current &&
      recommendationOperation.current.fingerprint !== fingerprint
    ) {
      setError(
        "Kết quả yêu cầu trước chưa rõ. Giữ nguyên thời lượng và ưu tiên để thử lại an toàn.",
      )
      return
    }
    const operation = operationFor(recommendationOperation.current, fingerprint)
    recommendationOperation.current = operation
    setBusy("recommendation")
    setError("")
    setNotice("")
    try {
      const reply = await api.createRevisionRecommendation(
        conversationId,
        current.material_id,
        current.topics[0],
        minutes,
        priority,
        operation.key,
      )
      const created = recommendationFromReply(reply)
      if (!created)
        throw new Error(
          "Máy chủ chưa trả về đề xuất ôn tập có thể xác nhận an toàn.",
        )
      recommendationOperation.current = null
      setRecommendation(created.presentation)
      setRecommendationReference(created.reference)
      setRecommendationState("awaiting_review")
      setNotice("Đề xuất ôn tập đã sẵn sàng để bạn xem xét.")
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 422) {
        recommendationOperation.current = null
        setRecommendationState("insufficient")
        setError(
          "Chưa đủ bằng chứng sai hợp lệ để tạo đề xuất ôn tập cho chủ đề này.",
        )
      } else if (!(cause instanceof ApiError) || cause.retryable) {
        setError(
          "Chưa xác nhận được kết quả tạo đề xuất. Bạn có thể thử lại an toàn với cùng lựa chọn.",
        )
      } else {
        recommendationOperation.current = null
        setError(cause.message)
      }
    } finally {
      setBusy("")
    }
  }

  async function decideRecommendation(decision: "APPROVE" | "REJECT") {
    if (!recommendationReference || busy) return
    const fingerprint = decisionFingerprint(recommendationReference, decision)
    if (
      recommendationOperation.current &&
      recommendationOperation.current.fingerprint !== fingerprint
    ) {
      setError(
        "Không thể đổi quyết định khi kết quả lần gửi trước chưa rõ. Hãy thử lại đúng quyết định cũ.",
      )
      return
    }
    const operation = operationFor(
      recommendationOperation.current,
      fingerprint,
    ) as PendingOperation & { decision?: "APPROVE" | "REJECT" }
    operation.decision = decision
    recommendationOperation.current = operation
    setBusy("recommendation-decision")
    setError("")
    try {
      const reply = await api.decide(
        conversationId,
        recommendationReference,
        decision,
        operation.key,
      )
      const presentation = reply.result?.data as ActionPresentation | undefined

      if (recommendationState === "candidate_review") {
        if (reply.state !== "SUCCEEDED")
          throw new Error(
            reply.error?.message ?? "Chưa xác nhận được công việc ôn tập.",
          )
        recommendationOperation.current = null
        setRecommendationReference(null)
        setRecommendationState(
          decision === "APPROVE" ? "confirmed" : "rejected",
        )
        setNotice(
          decision === "APPROVE"
            ? "Công việc ôn tập đã được xác nhận. Lịch học chưa bị thay đổi."
            : "Đã hủy công việc ôn tập nháp.",
        )
        return
      }

      if (decision === "REJECT") {
        if (reply.state !== "SUCCEEDED")
          throw new Error(reply.error?.message ?? "Chưa từ chối được đề xuất.")
        recommendationOperation.current = null
        setRecommendationReference(null)
        setRecommendationState("rejected")
        setNotice("Đã từ chối đề xuất ôn tập.")
        return
      }

      if (
        reply.state !== "NEEDS_CLARIFICATION" ||
        !presentation?.candidate ||
        presentation.pending_action.state !== "AWAITING_CLARIFICATION"
      )
        throw new Error(
          "Đề xuất đã được chấp nhận nhưng chưa nhận được biểu mẫu công việc hợp lệ.",
        )
      recommendationOperation.current = null
      setRecommendation(presentation)
      setRecommendationReference(null)
      setRecommendationState("candidate_details")
      setNotice(
        "Đề xuất đã được chấp nhận. Hãy bổ sung thời gian trước khi xác nhận công việc.",
      )
    } catch (cause) {
      if (!(cause instanceof ApiError) || cause.retryable) {
        setError(uncertainDecisionMessage)
      } else {
        setRecommendationState("stale")
        setError(cause.message)
      }
    } finally {
      setBusy("")
    }
  }

  async function reviewRecommendationCandidate(event: FormEvent) {
    event.preventDefault()
    const candidate = recommendation?.candidate
    const pending = recommendation?.pending_action
    if (!candidate || !pending || typeof pending.version !== "number" || busy)
      return
    const patch = revisionCandidatePatch(
      candidate.version,
      candidateTimes.startDate,
      candidateTimes.startTime,
      candidateTimes.deadlineDate,
      candidateTimes.deadlineTime,
    )
    if (!patch) {
      setError("Chọn thời gian bắt đầu trước hạn hoàn thành.")
      return
    }
    const fingerprint = JSON.stringify({
      actionId: pending.action_id,
      actionVersion: pending.version,
      patch,
    })
    if (
      recommendationOperation.current &&
      recommendationOperation.current.fingerprint !== fingerprint
    ) {
      setError(
        "Kết quả cập nhật trước chưa rõ. Giữ nguyên thời gian để thử lại an toàn.",
      )
      return
    }
    const operation = operationFor(recommendationOperation.current, fingerprint)
    recommendationOperation.current = operation
    setBusy("candidate-review")
    setError("")
    try {
      const reply = await api.reviewAction(
        conversationId,
        pending.action_id,
        pending.version,
        operation.key,
        patch,
      )
      const presentation = reply.result?.data as ActionPresentation | undefined
      const nextReference = reply.action_reference
      if (
        reply.state !== "AWAITING_APPROVAL" ||
        !presentation?.candidate ||
        !nextReference ||
        nextReference.target_type !== "TASK_CANDIDATE" ||
        nextReference.target_id !== presentation.candidate.candidate_id ||
        nextReference.target_version !== presentation.candidate.version
      )
        throw new Error(
          "Máy chủ chưa trả về công việc ôn tập có thể xác nhận an toàn.",
        )
      recommendationOperation.current = null
      setRecommendation(presentation)
      setRecommendationReference(nextReference)
      setRecommendationState("candidate_review")
      setNotice("Công việc nháp đã sẵn sàng để xác nhận lần cuối.")
    } catch (cause) {
      if (!(cause instanceof ApiError) || cause.retryable) {
        setError(
          "Chưa xác nhận được kết quả cập nhật công việc. Bạn có thể thử lại an toàn.",
        )
      } else {
        recommendationOperation.current = null
        setRecommendationState("stale")
        setError(cause.message)
      }
    } finally {
      setBusy("")
    }
  }

  function submit() {
    if (!attempt) return
    setShowSubmitConfirmation(false)
    void run("submit", async () => {
      for (const questionId of attempt.question_ids) {
        await api.saveQuizResponse(
          attempt.attempt_id,
          questionId,
          answers[questionId] ?? null,
          crypto.randomUUID(),
        )
      }
      const submission = await api.submitQuizAttempt(
        attempt.attempt_id,
        crypto.randomUUID(),
      )
      setResult(submission.data)
      setAttempt(submission.data.attempt)
      if (current)
        setStats((await api.getTopicStats(current.material_id)).data.items)
      setStatsLoaded(Boolean(current))
      setStage("results")
    })
  }

  return (
    <div
      className={`assessment-workspace ${
        attempt && !result ? "is-quiz-active" : ""
      }`}
    >
      <nav className="assessment-steps" aria-label="Các bước đánh giá">
        {stages.map((item, index) => {
          const state = stageState[item.id]
          return (
            <button
              key={item.id}
              type="button"
              className={`assessment-step ${
                stage === item.id ? "is-active" : ""
              } ${state.completed ? "is-complete" : ""}`}
              onClick={() => state.available && setStage(item.id)}
              disabled={!state.available}
              aria-current={stage === item.id ? "step" : undefined}
            >
              <span className="assessment-step-number">
                {state.completed ? "✓" : index + 1}
              </span>
              <span>
                <strong>{item.label}</strong>
              </span>
            </button>
          )
        })}
      </nav>

      {busy && (
        <div className="assessment-banner is-loading" role="status">
          <span className="assessment-spinner" aria-hidden="true" />
          Đang xử lý yêu cầu. Vui lòng giữ trang này mở…
        </div>
      )}
      {error && (
        <div className="assessment-banner is-error" role="alert">
          <strong>Chưa thể hoàn tất.</strong> {error}
        </div>
      )}
      {notice && !busy && (
        <div className="assessment-banner is-success" role="status">
          {notice}
        </div>
      )}

      {stage === "materials" && (
        <div className="assessment-layout">
          <Card className="study-card assessment-panel">
            <div className="assessment-section-heading">
              <span className="assessment-kicker">Bước 1</span>
              <h2>Thêm tài liệu học tập</h2>
              <p>Hệ thống hiện hỗ trợ TXT, Markdown và PDF, tối đa 10 MB.</p>
            </div>
            <form onSubmit={upload} className="assessment-form">
              <label
                htmlFor="assessment-file"
                className={`assessment-dropzone ${
                  isDragging ? "is-dragging" : ""
                }`}
                onDragEnter={(event) => {
                  event.preventDefault()
                  setIsDragging(true)
                }}
                onDragOver={(event) => event.preventDefault()}
                onDragLeave={() => setIsDragging(false)}
                onDrop={dropFile}
              >
                <span className="assessment-upload-icon" aria-hidden="true">
                  ↑
                </span>
                <strong>Thả tệp vào đây hoặc chọn từ máy</strong>
                <span>TXT, MD, PDF · tối đa 10 MB</span>
                <input
                  id="assessment-file"
                  type="file"
                  accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
                  onChange={(event) =>
                    selectFile(event.target.files?.[0] ?? null)
                  }
                />
              </label>
              {file && (
                <div className="assessment-file-preview">
                  <span aria-hidden="true">▤</span>
                  <div>
                    <strong title={file.name}>{file.name}</strong>
                    <small>{formatBytes(file.size)}</small>
                  </div>
                  <button type="button" onClick={() => selectFile(null)}>
                    Xóa
                  </button>
                </div>
              )}
              <label className="assessment-field" htmlFor="assessment-topic">
                <span>Chủ đề chính</span>
                <input
                  id="assessment-topic"
                  value={topic}
                  maxLength={120}
                  placeholder="Ví dụ: Cấu trúc dữ liệu và giải thuật"
                  onChange={(event) => setTopic(event.target.value)}
                  required
                />
                <small>Dùng để nhóm câu hỏi và thống kê kết quả.</small>
              </label>
              <Button
                type="submit"
                className="primary assessment-primary-action"
                disabled={Boolean(busy) || !file}
              >
                {busy === "upload" ? "Đang tải và xử lý…" : "Tải tài liệu"}
              </Button>
            </form>
          </Card>

          <aside
            className="assessment-summary-card"
            aria-label="Tóm tắt tài liệu"
          >
            <span className="assessment-kicker">Tài liệu hiện tại</span>
            {current ? (
              <>
                <h2 title={current.filename}>{current.filename}</h2>
                <span
                  className={`assessment-status is-${current.status.toLowerCase()}`}
                >
                  {current.status}
                </span>
                <dl className="assessment-metadata">
                  <div>
                    <dt>Chủ đề</dt>
                    <dd>{current.topics.join(", ")}</dd>
                  </div>
                  <div>
                    <dt>Số trang</dt>
                    <dd>{current.page_count}</dd>
                  </div>
                  <div>
                    <dt>Đoạn nguồn</dt>
                    <dd>{material?.chunks.length ?? 0}</dd>
                  </div>
                  <div>
                    <dt>Đã xác minh</dt>
                    <dd>{verified.length} câu</dd>
                  </div>
                </dl>
                {current.status === "READY" ? (
                  <Button
                    className="secondary"
                    onClick={() => setStage("questions")}
                  >
                    Tiếp tục với câu hỏi
                  </Button>
                ) : (
                  <p className="assessment-help">
                    {current.status === "FAILED"
                      ? "Xử lý thất bại. Hãy chọn lại tệp hợp lệ."
                      : "Tài liệu đang được xử lý; các bước tiếp theo chưa khả dụng."}
                  </p>
                )}
              </>
            ) : (
              <div className="assessment-empty">
                <span aria-hidden="true">◫</span>
                <h2>Chưa có tài liệu</h2>
                <p>
                  Tóm tắt và hành động tiếp theo sẽ xuất hiện sau khi tải lên.
                </p>
              </div>
            )}
          </aside>
        </div>
      )}

      {stage === "questions" && current && (
        <div className="assessment-stage-grid">
          <Card className="study-card assessment-panel">
            <div className="assessment-section-heading is-row">
              <div>
                <span className="assessment-kicker">Bước 2</span>
                <h2>Duyệt câu hỏi</h2>
                <p>Chỉ câu hỏi được xác minh mới có thể vào bài luyện tập.</p>
              </div>
              <div className="assessment-actions">
                {questionRefreshNeeded && (
                  <Button
                    className="secondary"
                    onClick={() =>
                      void run("refresh", async () => {
                        await loadQuestions(current.material_id)
                        setQuestionRefreshNeeded(false)
                        setNotice("Đã tải lại danh sách câu hỏi.")
                      })
                    }
                    disabled={Boolean(busy)}
                  >
                    Tải lại sau khi duyệt
                  </Button>
                )}
                <Button
                  className="secondary"
                  onClick={() =>
                    void run("refresh", () =>
                      loadQuestions(current.material_id),
                    )
                  }
                  disabled={Boolean(busy)}
                >
                  Làm mới
                </Button>
                <div className="assessment-generation-controls">
                  <label htmlFor="assessment-generation-count">
                    <span>Số câu muốn tạo</span>
                    <select
                      id="assessment-generation-count"
                      value={generationCount}
                      onChange={(event) =>
                        setGenerationCount(Number(event.target.value))
                      }
                      disabled={Boolean(busy) || Boolean(reference)}
                    >
                      {Array.from(
                        { length: MAX_GENERATION_COUNT },
                        (_, index) => index + 1,
                      ).map((count) => (
                        <option key={count} value={count}>
                          {count}
                        </option>
                      ))}
                    </select>
                    <small>Tối đa 10 câu mỗi lần</small>
                  </label>
                  <Button
                    className="primary"
                    onClick={generate}
                    disabled={
                      Boolean(busy) ||
                      Boolean(reference) ||
                      current.status !== "READY"
                    }
                  >
                    {busy === "generate"
                      ? "Đang tạo câu hỏi…"
                      : `Tạo ${generationCount} câu hỏi`}
                  </Button>
                </div>
              </div>
            </div>

            {activeDraft ? (
              <section
                className="assessment-review"
                aria-label="Duyệt câu hỏi nháp"
              >
                <div className="assessment-review-toolbar">
                  <span>
                    Nháp {reviewIndex + 1}/{drafts.length}
                  </span>
                  <span className="assessment-status is-draft">DRAFT</span>
                </div>
                <h3>{activeDraft.stem}</h3>
                <div className="assessment-review-options">
                  {activeDraft.options.map((option) => (
                    <div
                      key={option.option_id}
                      className={
                        option.option_id === activeDraft.answer_key
                          ? "is-answer"
                          : ""
                      }
                    >
                      <span>{option.option_id}</span>
                      <p>{option.text}</p>
                    </div>
                  ))}
                </div>
                <div className="assessment-evidence-grid">
                  <div>
                    <strong>Giải thích</strong>
                    <p>{activeDraft.explanation || "Chưa có giải thích."}</p>
                  </div>
                  <div className="assessment-source-list">
                    <strong>Nguồn đối chiếu</strong>
                    {referencedSources(activeDraft, material?.chunks ?? []).map(
                      ({ chunkId, chunk }) => (
                        <details key={chunkId}>
                          <summary>
                            {chunk
                              ? `${current.filename} · trang ${chunk.page}, đoạn ${chunk.chunk_index + 1}`
                              : `Không tìm thấy đoạn nguồn ${chunkId}`}
                          </summary>
                          {chunk ? (
                            <p>{chunk.text}</p>
                          ) : (
                            <p>
                              Máy chủ không trả về nội dung cho mã nguồn này.
                              Không có văn bản thay thế được tạo.
                            </p>
                          )}
                        </details>
                      ),
                    )}
                  </div>
                </div>
                <div className="assessment-review-navigation">
                  <Button
                    className="secondary"
                    onClick={() =>
                      setReviewIndex((value) => Math.max(0, value - 1))
                    }
                    disabled={reviewIndex === 0}
                  >
                    Câu trước
                  </Button>
                  <div className="assessment-dots" aria-hidden="true">
                    {drafts.map((item, index) => (
                      <span
                        key={item.question_id}
                        className={index === reviewIndex ? "is-active" : ""}
                      />
                    ))}
                  </div>
                  <Button
                    className="secondary"
                    onClick={() =>
                      setReviewIndex((value) =>
                        Math.min(drafts.length - 1, value + 1),
                      )
                    }
                    disabled={reviewIndex === drafts.length - 1}
                  >
                    Câu sau
                  </Button>
                </div>
                <DecisionActions
                  count={drafts.length}
                  state={decisionState}
                  pendingDecision={decisionOperation.current?.decision ?? null}
                  busy={Boolean(busy)}
                  referencePresent={Boolean(reference)}
                  onDecision={(decision) => void decide(decision)}
                  onReconcile={() => void reconcileDecision()}
                />
              </section>
            ) : (
              <div className="assessment-empty is-compact">
                <span aria-hidden="true">?</span>
                <h3>Chưa có bản nháp cần duyệt</h3>
                <p>Tạo câu hỏi mới hoặc làm mới để xem các câu đã lưu.</p>
              </div>
            )}
          </Card>

          <aside className="assessment-question-list">
            <div className="assessment-list-heading">
              <h2>Câu hỏi đã lưu</h2>
              <span>{questions.length}</span>
            </div>
            {questions.length ? (
              questions.map((question, index) => (
                <article key={question.question_id}>
                  <span
                    className={`assessment-status is-${question.status.toLowerCase()}`}
                  >
                    {question.status}
                  </span>
                  <strong>Câu {index + 1}</strong>
                  <p>{question.stem}</p>
                  <small>
                    {question.topic} · phiên bản {question.version}
                  </small>
                </article>
              ))
            ) : (
              <p className="assessment-help">Chưa có câu hỏi trên máy chủ.</p>
            )}
          </aside>
        </div>
      )}

      {stage === "practice" && current && (
        <Card className="study-card assessment-panel assessment-practice">
          {!attempt && (
            <div className="assessment-empty assessment-practice-intro">
              <span aria-hidden="true">✓</span>
              <h2>
                {verified.length
                  ? `${verified.length} câu đã sẵn sàng`
                  : "Chưa có câu hỏi VERIFIED"}
              </h2>
              <p>
                {verified.length
                  ? verified.length > 50
                    ? `Hiện có ${verified.length} câu hỏi đã xác minh. Bài luyện tập này sử dụng tối đa 50 câu.`
                    : "Bài làm được chấm điểm xác định bởi máy chủ. Bạn có thể để trống câu chưa chắc chắn."
                  : "Quay lại bước Câu hỏi và xác minh bản nháp trước khi luyện tập."}
              </p>
              {verified.length > 0 && (
                <div className="assessment-quiz-size-control">
                  <div>
                    <strong>Đã xác minh: {verified.length} câu</strong>
                    <span>
                      Bạn sẽ làm {selectedQuizCount}/{verified.length} câu đã
                      xác minh.
                    </span>
                  </div>
                  <label htmlFor="assessment-quiz-count">
                    <span>Số câu luyện tập</span>
                    <select
                      id="assessment-quiz-count"
                      value={selectedQuizCount}
                      onChange={(event) =>
                        setSelectedQuizCount(Number(event.target.value))
                      }
                      disabled={Boolean(busy)}
                    >
                      {Array.from(
                        { length: maxSelectableQuizCount },
                        (_, index) => index + 1,
                      ).map((count) => (
                        <option key={count} value={count}>
                          {count}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Button
                    className="primary"
                    onClick={start}
                    disabled={Boolean(busy) || selectedQuizCount < 1}
                  >
                    {busy === "start"
                      ? "Đang tạo bài…"
                      : `Bắt đầu ${selectedQuizCount} câu`}
                  </Button>
                </div>
              )}
              {!verified.length && (
                <Button
                  className="secondary"
                  onClick={() => setStage("questions")}
                >
                  Quay lại duyệt câu hỏi
                </Button>
              )}
            </div>
          )}
          {attempt && !result && (
            <>
              <div className="assessment-quiz-dashboard">
                <section
                  className="assessment-quiz assessment-quiz-main"
                  aria-label="Câu hỏi hiện tại"
                >
                  <div className="assessment-quiz-header">
                    <div>
                      <span className="assessment-kicker">Luyện tập</span>
                      <h2>
                        Câu {quizIndex + 1} / {attempt.question_ids.length}
                      </h2>
                    </div>
                    <span>
                      {answerSummary.answered}/{answerSummary.total} đã trả lời
                    </span>
                  </div>
                  <div
                    className="assessment-progress"
                    role="progressbar"
                    aria-label={`Tiến độ câu hỏi: câu ${quizIndex + 1} trên ${attempt.question_ids.length}`}
                    aria-valuemin={1}
                    aria-valuemax={attempt.question_ids.length}
                    aria-valuenow={quizIndex + 1}
                  >
                    <span
                      style={{
                        width: `${((quizIndex + 1) / attempt.question_ids.length) * 100}%`,
                      }}
                    />
                  </div>
                  {activeQuestion ? (
                    <fieldset>
                      <legend>{activeQuestion.stem}</legend>
                      <div className="assessment-quiz-options">
                        {activeQuestion.options.map((option) => (
                          <label
                            key={option.option_id}
                            className={
                              answers[activeQuestion.question_id] ===
                              option.option_id
                                ? "is-selected"
                                : ""
                            }
                          >
                            <input
                              type="radio"
                              name={activeQuestion.question_id}
                              value={option.option_id}
                              checked={
                                answers[activeQuestion.question_id] ===
                                option.option_id
                              }
                              onChange={() =>
                                setAnswers((previous) => ({
                                  ...previous,
                                  [activeQuestion.question_id]:
                                    option.option_id,
                                }))
                              }
                            />
                            <span>{option.option_id}</span>
                            <p>{option.text}</p>
                          </label>
                        ))}
                      </div>
                    </fieldset>
                  ) : (
                    <p role="alert">
                      Câu hỏi không còn khả dụng. Hãy tải lại danh sách.
                    </p>
                  )}
                  <p className="assessment-help">
                    Câu chưa chọn sẽ được gửi dưới dạng bỏ qua, không tự động
                    chuyển thành câu trả lời sai.
                  </p>
                  <div className="assessment-quiz-navigation">
                    <Button
                      className="secondary"
                      onClick={() =>
                        setQuizIndex((value) => Math.max(0, value - 1))
                      }
                      disabled={quizIndex === 0}
                    >
                      Câu trước
                    </Button>
                    <Button
                      className="primary"
                      onClick={() =>
                        setQuizIndex((value) =>
                          Math.min(attempt.question_ids.length - 1, value + 1),
                        )
                      }
                      disabled={quizIndex === attempt.question_ids.length - 1}
                    >
                      Câu tiếp theo
                    </Button>
                  </div>
                </section>

                <QuizOverview
                  questionIds={attempt.question_ids}
                  answers={answers}
                  currentIndex={quizIndex}
                  busy={busy === "submit"}
                  canSubmit={attempt.question_ids.every((id) =>
                    verified.some((question) => question.question_id === id),
                  )}
                  showConfirmation={showSubmitConfirmation}
                  onNavigate={setQuizIndex}
                  onRequestSubmit={() => setShowSubmitConfirmation(true)}
                  onCancelSubmit={() => setShowSubmitConfirmation(false)}
                  onConfirmSubmit={submit}
                />
              </div>
            </>
          )}
        </Card>
      )}

      {stage === "results" && current && (
        <div className="assessment-results">
          {result ? (
            <Card className="study-card assessment-panel">
              <div className="assessment-result-hero">
                <div>
                  <span className="assessment-kicker">Kết quả gần nhất</span>
                  <h2>
                    {result.attempt.score_percent === null
                      ? "—"
                      : `${result.attempt.score_percent}%`}
                  </h2>
                  <p>Điểm do máy chủ chấm từ câu trả lời hợp lệ.</p>
                </div>
                <dl>
                  <div>
                    <dt>Đúng</dt>
                    <dd>{result.attempt.correct_count}</dd>
                  </div>
                  <div>
                    <dt>Sai</dt>
                    <dd>{result.attempt.incorrect_count}</dd>
                  </div>
                  <div>
                    <dt>Bỏ qua</dt>
                    <dd>{result.attempt.omitted_count}</dd>
                  </div>
                  <div>
                    <dt>Hợp lệ</dt>
                    <dd>{result.attempt.valid_response_count}</dd>
                  </div>
                </dl>
              </div>
              <div className="assessment-result-actions">
                <Button
                  className="secondary"
                  onClick={() => {
                    setAttempt(null)
                    setResult(null)
                    setStage("practice")
                  }}
                >
                  Làm bài khác
                </Button>
              </div>
            </Card>
          ) : (
            <div className="assessment-empty assessment-results-empty">
              <span aria-hidden="true">◔</span>
              <h2>Chưa có kết quả bài làm</h2>
              <p>
                Hoàn thành một bài luyện tập để xem số câu đúng, sai và bỏ qua.
              </p>
              {verified.length > 0 && (
                <Button
                  className="primary"
                  onClick={() => setStage("practice")}
                >
                  Đi đến luyện tập
                </Button>
              )}
            </div>
          )}

          <Card className="study-card assessment-panel">
            <div className="assessment-section-heading is-row">
              <div>
                <span className="assessment-kicker">Theo chủ đề</span>
                <h2>Thống kê lỗi</h2>
                <p>Chỉ hiển thị dữ liệu máy chủ đã quan sát.</p>
              </div>
              <Button
                className="secondary"
                onClick={() =>
                  void run("stats", async () => {
                    setStats(
                      (await api.getTopicStats(current.material_id)).data.items,
                    )
                    setStatsLoaded(true)
                  })
                }
                disabled={Boolean(busy)}
              >
                Tải thống kê
              </Button>
            </div>
            {!statsLoaded ? (
              <p className="assessment-help">
                Chọn “Tải thống kê” để xem dữ liệu mới nhất.
              </p>
            ) : stats.length ? (
              <div className="assessment-stats-list">
                {stats.map((item) => (
                  <article key={`${item.material_id}:${item.topic}`}>
                    <div>
                      <strong>{item.topic}</strong>
                      <span
                        className={`assessment-status ${
                          item.status === "INSUFFICIENT_DATA"
                            ? "is-pending"
                            : "is-ready"
                        }`}
                      >
                        {item.status === "INSUFFICIENT_DATA"
                          ? "CHƯA ĐỦ DỮ LIỆU"
                          : "ĐÃ QUAN SÁT"}
                      </span>
                    </div>
                    {item.status === "INSUFFICIENT_DATA" ? (
                      <p>
                        Cần thêm câu trả lời hợp lệ trước khi tính tỷ lệ lỗi.
                      </p>
                    ) : (
                      <p>
                        <strong>
                          {Math.round((item.error_rate ?? 0) * 100)}%
                        </strong>{" "}
                        tỷ lệ lỗi · {item.error_count}/
                        {item.valid_response_count} câu sai
                      </p>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <p className="assessment-help">
                Máy chủ chưa trả về thống kê cho tài liệu này.
              </p>
            )}
            <section
              className="assessment-recommendation"
              aria-labelledby="assessment-recommendation-heading"
            >
              <div>
                <span className="assessment-kicker">Ôn tập thích ứng</span>
                <h3 id="assessment-recommendation-heading">Đề xuất ôn tập</h3>
                <p>
                  Máy chủ tạo đề xuất từ kết quả đã chấm. Mọi công việc vẫn cần
                  bạn xác nhận rõ ràng và chưa tự động thay đổi lịch.
                </p>
              </div>

              {!recommendation && (
                <>
                  {!statsLoaded ? (
                    <p className="assessment-help">
                      Tải thống kê để kiểm tra bằng chứng trước khi yêu cầu đề
                      xuất.
                    </p>
                  ) : recommendationState === "insufficient" ? (
                    <div className="assessment-recommendation-state">
                      <strong>Máy chủ báo chưa đủ dữ liệu</strong>
                      <p>
                        Chưa có đủ câu trả lời sai hợp lệ để tạo đề xuất. Đây
                        không phải lỗi kết nối; hãy luyện tập thêm rồi tải lại
                        thống kê.
                      </p>
                    </div>
                  ) : !hasRecommendationEvidence ? (
                    <div className="assessment-recommendation-state">
                      <strong>Chưa đủ bằng chứng</strong>
                      <p>
                        Cần ít nhất một câu trả lời sai hợp lệ trong chủ đề đã
                        xác nhận. Trạng thái này khác với lỗi kết nối API.
                      </p>
                    </div>
                  ) : (
                    <form
                      className="assessment-recommendation-form"
                      onSubmit={(event) => {
                        event.preventDefault()
                        void requestRecommendation()
                      }}
                    >
                      <label>
                        <span>Thời lượng đề xuất</span>
                        <select
                          value={suggestedMinutes}
                          onChange={(event) =>
                            setSuggestedMinutes(event.target.value)
                          }
                          disabled={Boolean(busy)}
                        >
                          {[30, 45, 60, 90, 120, 180, 240].map((minutes) => (
                            <option key={minutes} value={minutes}>
                              {minutes} phút
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        <span>Mức ưu tiên</span>
                        <select
                          value={recommendationPriority}
                          onChange={(event) =>
                            setRecommendationPriority(
                              event.target.value as "0.1" | "0.5" | "1",
                            )
                          }
                          disabled={Boolean(busy)}
                        >
                          <option value="0.1">Thấp</option>
                          <option value="0.5">Trung bình</option>
                          <option value="1">Cao</option>
                        </select>
                      </label>
                      <Button
                        className="primary"
                        type="submit"
                        disabled={Boolean(busy)}
                      >
                        {busy === "recommendation"
                          ? "Đang tạo đề xuất…"
                          : "Đề xuất ôn tập"}
                      </Button>
                    </form>
                  )}
                </>
              )}

              {recommendation?.revision_recommendation && (
                <article className="assessment-recommendation-review">
                  <div className="assessment-recommendation-summary">
                    <span className="assessment-status is-pending">
                      {recommendation.revision_recommendation.status}
                    </span>
                    <h4>{recommendation.revision_recommendation.topic}</h4>
                    <p>
                      {recommendation.revision_recommendation.reason_summary}
                    </p>
                    <dl>
                      <div>
                        <dt>Bằng chứng</dt>
                        <dd>
                          {
                            recommendation.revision_recommendation.evidence
                              .error_count
                          }
                          /
                          {
                            recommendation.revision_recommendation.evidence
                              .valid_response_count
                          }{" "}
                          câu sai
                        </dd>
                      </div>
                      <div>
                        <dt>Thời lượng</dt>
                        <dd>
                          {
                            recommendation.revision_recommendation
                              .suggested_minutes
                          }{" "}
                          phút
                        </dd>
                      </div>
                      <div>
                        <dt>Độ tin cậy</dt>
                        <dd>
                          {
                            recommendation.revision_recommendation
                              .confidence_limit.level
                          }
                        </dd>
                      </div>
                    </dl>
                    <ul>
                      {recommendation.revision_recommendation.confidence_limit.limitations.map(
                        (limitation) => (
                          <li key={limitation}>{limitation}</li>
                        ),
                      )}
                    </ul>
                  </div>

                  {(recommendation.revision_source_chunks ?? []).map(
                    (chunk) => (
                      <details key={chunk.chunk_id}>
                        <summary>
                          {current.filename} · trang {chunk.page}, đoạn{" "}
                          {chunk.chunk_index + 1}
                        </summary>
                        <p>{chunk.text}</p>
                      </details>
                    ),
                  )}

                  {recommendationState === "awaiting_review" && (
                    <div className="assessment-decision-bar">
                      <div>
                        <strong>Đề xuất đang chờ bạn duyệt</strong>
                        <small>
                          Chấp nhận chỉ tạo TaskCandidate nháp; chưa tạo lịch.
                        </small>
                      </div>
                      <Button
                        className="secondary assessment-reject"
                        onClick={() => void decideRecommendation("REJECT")}
                        disabled={
                          Boolean(busy) ||
                          recommendationOperation.current?.decision ===
                            "APPROVE"
                        }
                      >
                        Từ chối đề xuất
                      </Button>
                      <Button
                        className="primary"
                        onClick={() => void decideRecommendation("APPROVE")}
                        disabled={
                          Boolean(busy) ||
                          recommendationOperation.current?.decision === "REJECT"
                        }
                      >
                        Chấp nhận đề xuất
                      </Button>
                    </div>
                  )}

                  {recommendationState === "candidate_details" && (
                    <form
                      className="assessment-candidate-form"
                      onSubmit={reviewRecommendationCandidate}
                    >
                      <h4>Bổ sung thời gian cho công việc nháp</h4>
                      <div>
                        <label>
                          <span>Ngày bắt đầu</span>
                          <input
                            type="date"
                            value={candidateTimes.startDate}
                            onChange={(event) =>
                              setCandidateTimes((value) => ({
                                ...value,
                                startDate: event.target.value,
                              }))
                            }
                            required
                          />
                        </label>
                        <label>
                          <span>Giờ bắt đầu</span>
                          <input
                            type="time"
                            value={candidateTimes.startTime}
                            onChange={(event) =>
                              setCandidateTimes((value) => ({
                                ...value,
                                startTime: event.target.value,
                              }))
                            }
                            required
                          />
                        </label>
                        <label>
                          <span>Ngày hoàn thành</span>
                          <input
                            type="date"
                            value={candidateTimes.deadlineDate}
                            onChange={(event) =>
                              setCandidateTimes((value) => ({
                                ...value,
                                deadlineDate: event.target.value,
                              }))
                            }
                            required
                          />
                        </label>
                        <label>
                          <span>Giờ hoàn thành</span>
                          <input
                            type="time"
                            value={candidateTimes.deadlineTime}
                            onChange={(event) =>
                              setCandidateTimes((value) => ({
                                ...value,
                                deadlineTime: event.target.value,
                              }))
                            }
                            required
                          />
                        </label>
                      </div>
                      <Button
                        className="primary"
                        type="submit"
                        disabled={Boolean(busy)}
                      >
                        Xem công việc trước khi xác nhận
                      </Button>
                    </form>
                  )}

                  {recommendationState === "candidate_review" &&
                    recommendation.candidate && (
                      <div className="assessment-decision-bar">
                        <div>
                          <strong>
                            {recommendation.candidate.slots.title ??
                              "Công việc ôn tập"}
                          </strong>
                          <small>
                            Xác nhận sẽ lưu công việc vào Planner nhưng không tự
                            động xếp lịch.
                          </small>
                        </div>
                        <Button
                          className="secondary assessment-reject"
                          onClick={() => void decideRecommendation("REJECT")}
                          disabled={
                            Boolean(busy) ||
                            recommendationOperation.current?.decision ===
                              "APPROVE"
                          }
                        >
                          Hủy công việc
                        </Button>
                        <Button
                          className="primary"
                          onClick={() => void decideRecommendation("APPROVE")}
                          disabled={
                            Boolean(busy) ||
                            recommendationOperation.current?.decision ===
                              "REJECT"
                          }
                        >
                          Xác nhận công việc
                        </Button>
                      </div>
                    )}

                  {recommendationState === "confirmed" && (
                    <p className="assessment-recommendation-state">
                      Công việc ôn tập đã được xác nhận; lịch học vẫn chưa thay
                      đổi.
                    </p>
                  )}
                  {recommendationState === "rejected" && (
                    <p className="assessment-recommendation-state">
                      Đề xuất hoặc công việc nháp đã bị từ chối.
                    </p>
                  )}
                  {recommendationState === "stale" && (
                    <p className="assessment-recommendation-state" role="alert">
                      Thao tác đã cũ hoặc không còn chờ duyệt. Hãy tải lại dữ
                      liệu trước khi tạo đề xuất mới.
                    </p>
                  )}
                </article>
              )}
            </section>
          </Card>
        </div>
      )}
    </div>
  )
}
