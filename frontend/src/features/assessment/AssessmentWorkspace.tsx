import { useState, type DragEvent, type FormEvent } from "react"
import { api } from "../../api"
import Button from "../../components/ui/Button"
import Card from "../../components/ui/Card"
import {
  assessmentStageState,
  type AssessmentStage,
} from "./assessmentProgress"
import { eligibleQuestions } from "./eligibleQuestions"
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
  hint: string
}

const stages: StageDefinition[] = [
  { id: "materials", label: "Tài liệu", hint: "Tải lên và kiểm tra" },
  { id: "questions", label: "Câu hỏi", hint: "Tạo và xác minh" },
  { id: "practice", label: "Luyện tập", hint: "Làm bài kiểm tra" },
  { id: "results", label: "Kết quả", hint: "Xem thống kê" },
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
  const [statsLoaded, setStatsLoaded] = useState(false)
  const current = material?.material
  const verified = current
    ? eligibleQuestions(questions, current.material_id)
    : []
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
      if (label === "decide") {
        setReference(null)
        setDrafts([])
      }
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
      setNotice(
        response.data.material.status === "READY"
          ? "Tài liệu đã sẵn sàng."
          : "Tài liệu đã nhận; đang chờ xử lý.",
      )
    })
  }

  function generate() {
    if (!current || current.status !== "READY") return
    void run("generate", async () => {
      const reply = await api.generateQuestionDrafts(
        conversationId,
        current.material_id,
        current.topics[0],
        "MCQ",
        5,
        crypto.randomUUID(),
      )
      const presentation = reply.result?.data as ActionPresentation | undefined
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
              (id) => !material?.chunks.some((chunk) => chunk.chunk_id === id),
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
      setNotice(reply.message)
      setStage("questions")
    })
  }

  function decide(decision: "APPROVE" | "REJECT") {
    if (!current || !reference || !drafts.length) return
    const original = reference
    void run("decide", async () => {
      const reply = await api.decide(
        conversationId,
        original,
        decision,
        crypto.randomUUID(),
      )
      if (reply.state !== "SUCCEEDED")
        throw new Error(
          reply.error?.message ??
            "Quyết định chưa được lưu. Hãy xem lại bản nháp mới.",
        )
      setReference(null)
      setDrafts([])
      await loadQuestions(current.material_id)
      setNotice(
        decision === "APPROVE"
          ? "Câu hỏi đã được xác minh."
          : "Đã từ chối bản nháp.",
      )
      if (decision === "APPROVE") setStage("practice")
    })
  }

  function start() {
    if (!current || !verified.length) return
    void run("start", async () => {
      // Only server-listed VERIFIED IDs are sent. The backend checks again.
      const response = await api.createQuizAttempt(
        current.material_id,
        verified.map((item) => item.question_id),
        "MANUAL",
        null,
        crypto.randomUUID(),
      )
      setAttempt(response.data)
      setResult(null)
      setAnswers({})
      setQuizIndex(0)
      setStage("practice")
    })
  }

  function submit() {
    if (!attempt) return
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
    <div className="assessment-workspace">
      <header className="assessment-hero">
        <div>
          <span className="assessment-eyebrow">Không gian đánh giá</span>
          <h1>Học từ tài liệu, kiểm tra bằng dữ liệu thật</h1>
          <p>
            Tải tài liệu, duyệt câu hỏi do hệ thống đề xuất và luyện tập với
            những câu đã được bạn xác minh.
          </p>
        </div>
        <span className="assessment-session-note">Phiên làm việc hiện tại</span>
      </header>

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
                <small>{item.hint}</small>
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
                <Button
                  className="primary"
                  onClick={generate}
                  disabled={
                    Boolean(busy) ||
                    Boolean(reference) ||
                    current.status !== "READY"
                  }
                >
                  Tạo 5 câu nháp
                </Button>
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
                  <div>
                    <strong>Nguồn đối chiếu</strong>
                    <p>
                      {current.filename} ·{" "}
                      {activeDraft.source_chunk_ids
                        .map((id) => {
                          const chunk = material?.chunks.find(
                            (item) => item.chunk_id === id,
                          )
                          return chunk
                            ? `trang ${chunk.page}, đoạn ${chunk.chunk_index + 1}`
                            : "nguồn không xác định"
                        })
                        .join("; ")}
                    </p>
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
                <div className="assessment-decision-bar">
                  <div>
                    <strong>Áp dụng cho cả {drafts.length} câu nháp</strong>
                    <small>Quyết định này cần xác nhận rõ ràng.</small>
                  </div>
                  <Button
                    className="secondary assessment-reject"
                    onClick={() => decide("REJECT")}
                    disabled={Boolean(busy) || !reference}
                  >
                    Từ chối
                  </Button>
                  <Button
                    className="primary"
                    onClick={() => decide("APPROVE")}
                    disabled={Boolean(busy) || !reference}
                  >
                    Xác minh câu hỏi
                  </Button>
                </div>
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
                  ? "Bài làm được chấm điểm xác định bởi máy chủ. Bạn có thể để trống câu chưa chắc chắn."
                  : "Quay lại bước Câu hỏi và xác minh bản nháp trước khi luyện tập."}
              </p>
              {verified.length > 0 && (
                <Button
                  className="primary"
                  onClick={start}
                  disabled={Boolean(busy)}
                >
                  Bắt đầu luyện tập
                </Button>
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
            <section className="assessment-quiz" aria-label="Bài kiểm tra">
              <div className="assessment-quiz-header">
                <div>
                  <span className="assessment-kicker">Luyện tập</span>
                  <h2>
                    Câu {quizIndex + 1} / {attempt.question_ids.length}
                  </h2>
                </div>
                <span>{Object.keys(answers).length} đã trả lời</span>
              </div>
              <div className="assessment-progress" aria-hidden="true">
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
                              [activeQuestion.question_id]: option.option_id,
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
                Câu chưa chọn sẽ được gửi dưới dạng bỏ qua, không tự động chuyển
                thành câu trả lời sai.
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
                {quizIndex < attempt.question_ids.length - 1 ? (
                  <Button
                    className="primary"
                    onClick={() => setQuizIndex((value) => value + 1)}
                  >
                    Câu tiếp theo
                  </Button>
                ) : (
                  <Button
                    className="primary"
                    onClick={submit}
                    disabled={
                      Boolean(busy) ||
                      attempt.question_ids.some(
                        (id) =>
                          !verified.some(
                            (question) => question.question_id === id,
                          ),
                      )
                    }
                  >
                    {busy === "submit" ? "Đang nộp…" : "Nộp bài"}
                  </Button>
                )}
              </div>
            </section>
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
            <div className="assessment-unavailable">
              <strong>Đề xuất ôn tập chưa khả dụng</strong>
              <p>
                Backend hiện chưa cung cấp route đề xuất ôn tập. Không có khuyến
                nghị giả lập được hiển thị.
              </p>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
