import { useState, type FormEvent } from "react"
import { api } from "../../api"
import Button from "../../components/ui/Button"
import Card from "../../components/ui/Card"
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
  const current = material?.material
  const verified = current
    ? eligibleQuestions(questions, current.material_id)
    : []

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
      setReference(ref)
      setNotice(reply.message)
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
    })
  }

  return (
    <div className="study-left-col">
      <Card className="study-card study-quiz-card" title="Đánh giá học tập">
        <form onSubmit={upload} className="assessment-stack">
          <p>
            Tải tài liệu TXT, Markdown hoặc PDF (tối đa 10 MB). Đặt một chủ đề
            cho tài liệu.
          </p>
          <label htmlFor="assessment-file">Tài liệu học tập</label>
          <input
            id="assessment-file"
            type="file"
            accept=".txt,.md,.pdf,text/plain,text/markdown,application/pdf"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <label htmlFor="assessment-topic">Chủ đề</label>
          <input
            id="assessment-topic"
            value={topic}
            maxLength={120}
            onChange={(event) => setTopic(event.target.value)}
            required
          />
          <Button
            type="submit"
            className="primary"
            disabled={Boolean(busy) || !file}
          >
            {" "}
            {busy === "upload" ? "Đang tải và xử lý…" : "Tải tài liệu"}{" "}
          </Button>
        </form>
        {error && <p role="alert">{error}</p>}
        {notice && <p role="status">{notice}</p>}
        {current && (
          <div className="assessment-stack">
            <h3>{current.filename}</h3>
            <p>
              Trạng thái: {current.status} · Chủ đề: {current.topics.join(", ")}
            </p>
            <p>
              {current.page_count} trang · {material?.chunks.length ?? 0} đoạn
              nguồn
            </p>
            {current.status === "READY" && (
              <>
                <Button
                  className="secondary"
                  onClick={generate}
                  disabled={Boolean(busy) || Boolean(reference)}
                >
                  Tạo 5 câu hỏi nháp
                </Button>
                <Button
                  className="secondary"
                  onClick={() =>
                    void run("refresh", () =>
                      loadQuestions(current.material_id),
                    )
                  }
                  disabled={Boolean(busy)}
                >
                  Tải lại câu hỏi
                </Button>
              </>
            )}
          </div>
        )}
        {questions.length > 0 && (
          <section className="assessment-stack" aria-label="Trạng thái câu hỏi">
            <h3>Trạng thái câu hỏi</h3>
            {questions.map((question) => (
              <p key={question.question_id}>
                {question.status} · phiên bản {question.version} ·{" "}
                {question.topic}: {question.stem}
              </p>
            ))}
          </section>
        )}
        {drafts.length > 0 && (
          <section className="assessment-stack" aria-label="Duyệt câu hỏi nháp">
            <h3>Kiểm tra bản nháp trước khi xác minh</h3>
            {drafts.map((question) => (
              <article key={question.question_id}>
                <strong>
                  Nháp · phiên bản {question.version} · {question.topic}
                </strong>
                <p>{question.stem}</p>
                <ul>
                  {question.options.map((option) => (
                    <li key={option.option_id}>
                      {option.option_id}: {option.text}
                    </li>
                  ))}
                </ul>
                <p>Đáp án đề xuất: {question.answer_key}</p>
                {question.explanation && (
                  <p>Giải thích: {question.explanation}</p>
                )}
                <p>
                  Nguồn: {current?.filename};{" "}
                  {question.source_chunk_ids
                    .map((id) => {
                      const chunk = material?.chunks.find(
                        (item) => item.chunk_id === id,
                      )
                      return chunk ? `trang ${chunk.page}` : "không xác định"
                    })
                    .join(", ")}
                </p>
              </article>
            ))}
            <Button
              className="primary"
              onClick={() => decide("APPROVE")}
              disabled={Boolean(busy) || !reference}
            >
              Xác minh câu hỏi
            </Button>
            <Button
              className="secondary"
              onClick={() => decide("REJECT")}
              disabled={Boolean(busy) || !reference}
            >
              Từ chối bản nháp
            </Button>
          </section>
        )}
        {current && (
          <section
            className="assessment-stack"
            aria-label="Câu hỏi đã xác minh"
          >
            <h3>Câu hỏi đã xác minh: {verified.length}</h3>
            {verified.length > 0 && !attempt && (
              <Button
                className="primary"
                onClick={start}
                disabled={Boolean(busy)}
              >
                Bắt đầu bài kiểm tra
              </Button>
            )}
          </section>
        )}
        {attempt && !result && (
          <section className="assessment-stack" aria-label="Bài kiểm tra">
            {attempt.question_ids.map((id, index) => {
              const question = verified.find((item) => item.question_id === id)
              if (!question)
                return (
                  <p key={id} role="alert">
                    Câu {index + 1} không còn khả dụng. Hãy tải lại câu hỏi.
                  </p>
                )
              return (
                <fieldset key={id}>
                  <legend>
                    Câu {index + 1}: {question.stem}
                  </legend>
                  {question.options.map((option) => (
                    <label key={option.option_id} className="assessment-option">
                      <input
                        type="radio"
                        name={id}
                        value={option.option_id}
                        checked={answers[id] === option.option_id}
                        onChange={() =>
                          setAnswers((previous) => ({
                            ...previous,
                            [id]: option.option_id,
                          }))
                        }
                      />
                      {option.text}
                    </label>
                  ))}
                </fieldset>
              )
            })}
            <Button
              className="primary"
              onClick={submit}
              disabled={
                Boolean(busy) ||
                attempt.question_ids.some(
                  (id) =>
                    !verified.some((question) => question.question_id === id),
                )
              }
            >
              Nộp bài
            </Button>
          </section>
        )}
        {result && (
          <section aria-label="Kết quả bài kiểm tra">
            <h3>Kết quả</h3>
            <p>
              Đúng {result.attempt.correct_count}/
              {result.attempt.total_questions};{" "}
              {result.attempt.score_percent ?? 0}%.
            </p>
            <p>
              Bỏ qua: {result.attempt.omitted_count}; câu hợp lệ:{" "}
              {result.attempt.valid_response_count}.
            </p>
            <Button
              className="secondary"
              onClick={() => {
                setAttempt(null)
                setResult(null)
              }}
            >
              Làm bài khác
            </Button>
          </section>
        )}
        {current && (
          <Button
            className="secondary"
            onClick={() =>
              void run("stats", async () =>
                setStats(
                  (await api.getTopicStats(current.material_id)).data.items,
                ),
              )
            }
            disabled={Boolean(busy)}
          >
            Xem thống kê chủ đề
          </Button>
        )}
        {stats.length > 0 && (
          <section aria-label="Thống kê chủ đề">
            <h3>Thống kê chủ đề</h3>
            {stats.map((item) => (
              <p key={`${item.material_id}:${item.topic}`}>
                {item.topic}:{" "}
                {item.status === "INSUFFICIENT_DATA"
                  ? "Chưa đủ dữ liệu"
                  : `${item.error_count}/${item.valid_response_count} câu sai (${Math.round((item.error_rate ?? 0) * 100)}%)`}
              </p>
            ))}
            <p>Đề xuất ôn tập từ máy chủ hiện chưa khả dụng.</p>
          </section>
        )}
      </Card>
    </div>
  )
}
