import { useEffect, useMemo, useRef, useState, type FormEvent } from "react"
import {
  BookOpenCheck,
  CircleAlert,
  Lightbulb,
  LoaderCircle,
  RotateCcw,
  Send,
  Sparkles,
} from "lucide-react"
import { api } from "../../api"
import { ApiError } from "../../api/client"
import type {
  DailyLearningMaterial,
  DailyLearningSession as Session,
  DailyLearningSummaryData,
  DailyLearningTurn,
} from "../../api/types"
import Button from "../../components/ui/Button"
import Card from "../../components/ui/Card"
import CitationChip from "./CitationChip"
import {
  applyServerHintLevel,
  hintButtonLabel,
  initialHintState,
  resetHintState,
} from "./hintState"
import { learningError, mapLearningTurn } from "./learningApi"
import {
  clearLearningSessionId,
  loadLearningSessionId,
  saveLearningSessionId,
} from "./sessionRecovery"
import SessionSummaryModal from "./SessionSummaryModal"

type TurnAttempt = {
  kind: "ASK" | "HINT"
  text?: string
  key: string
}

export default function LearningSession({
  userId,
  selectedMaterials,
  materials,
  plannerBlockId,
  initialGoal,
}: {
  userId: string
  selectedMaterials: DailyLearningMaterial[]
  materials: DailyLearningMaterial[]
  plannerBlockId: string | null
  initialGoal: string
}) {
  const [goal, setGoal] = useState(initialGoal)
  const [contextReady, setContextReady] = useState(!plannerBlockId)
  const [session, setSession] = useState<Session | null>(null)
  const [turns, setTurns] = useState<DailyLearningTurn[]>([])
  const [input, setInput] = useState("")
  const [hint, setHint] = useState(initialHintState)
  const [busy, setBusy] = useState("")
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")
  const [expired, setExpired] = useState(false)
  const [summary, setSummary] = useState<DailyLearningSummaryData | null>(null)
  const [summaryError, setSummaryError] = useState("")
  const createKey = useRef("")
  const turnAttempt = useRef<TurnAttempt | null>(null)
  const summaryKey = useRef("")
  const decisionAttempt = useRef<{
    decision: "APPROVE" | "REJECT"
    key: string
  } | null>(null)
  const transcriptEnd = useRef<HTMLDivElement>(null)
  const materialsById = useMemo(
    () =>
      new Map(materials.map((material) => [material.material_id, material])),
    [materials],
  )

  useEffect(() => {
    setGoal(initialGoal)
    if (!plannerBlockId) {
      setContextReady(true)
      return
    }
    let active = true
    setContextReady(false)
    setError("")
    void api
      .getLearningPlannerContext(plannerBlockId)
      .then((context) => {
        if (!active) return
        setGoal(context.suggested_goal)
        setContextReady(true)
      })
      .catch((cause) => {
        if (active)
          setError(
            `Không thể xác minh buổi học từ Planner. ${learningError(cause)}`,
          )
      })
    return () => {
      active = false
    }
  }, [initialGoal, plannerBlockId])

  useEffect(() => {
    let active = true
    let recovered: string | null = null
    try {
      recovered = loadLearningSessionId(localStorage, userId)
    } catch {}
    if (!recovered) return
    setBusy("recover")
    void api
      .getLearningSession(recovered)
      .then((data) => {
        if (!active) return
        if (new Date(data.session.expires_at).getTime() <= Date.now()) {
          setExpired(true)
          try {
            clearLearningSessionId(localStorage, userId)
          } catch {}
          return
        }
        setSession(data.session)
        setTurns(data.turns)
        setGoal(data.session.goal)
        const lastHint = [...data.turns]
          .reverse()
          .find((turn) => turn.role === "ASSISTANT" && turn.kind === "HINT")
        if (lastHint?.hint_level)
          setHint(applyServerHintLevel(initialHintState(), lastHint.hint_level))
      })
      .catch((cause) => {
        if (!active) return
        if (cause instanceof ApiError && cause.status === 404) {
          setExpired(true)
          try {
            clearLearningSessionId(localStorage, userId)
          } catch {}
        } else setError(learningError(cause))
      })
      .finally(() => {
        if (active) setBusy("")
      })
    return () => {
      active = false
    }
  }, [userId])

  useEffect(() => {
    transcriptEnd.current?.scrollIntoView({ block: "nearest" })
  }, [turns, busy])

  async function createSession() {
    const confirmedGoal = goal.trim()
    if (!confirmedGoal) {
      setError("Hãy nhập mục tiêu hôm nay.")
      return
    }
    if (confirmedGoal.length > 1000) {
      setError("Mục tiêu không được vượt quá 1000 ký tự.")
      return
    }
    if (!selectedMaterials.length) {
      setError("Hãy chọn ít nhất một tài liệu đã sẵn sàng.")
      return
    }
    if (plannerBlockId && !contextReady) {
      setError("Chưa xác minh được buổi học từ Planner.")
      return
    }
    if (!createKey.current) createKey.current = crypto.randomUUID()
    setBusy("create")
    setError("")
    try {
      const created = await api.createLearningSession(
        confirmedGoal,
        selectedMaterials.map((material) => material.material_id),
        plannerBlockId,
        createKey.current,
      )
      setSession(created)
      setTurns([])
      setExpired(false)
      setHint(initialHintState())
      createKey.current = ""
      try {
        saveLearningSessionId(localStorage, userId, created.session_id)
      } catch {}
    } catch (cause) {
      setError(learningError(cause))
    } finally {
      setBusy("")
    }
  }

  async function submitTurn(attempt: TurnAttempt) {
    if (!session || busy) return
    if (attempt.kind === "ASK") setHint(resetHintState())
    setBusy("turn")
    setError("")
    setNotice("")
    try {
      const result = await api.addLearningTurn(
        session.session_id,
        attempt.kind,
        attempt.text,
        attempt.key,
      )
      setTurns((current) => [
        ...current,
        result.user_turn,
        result.assistant_turn,
      ])
      if (attempt.kind === "ASK") setInput("")
      if (attempt.kind === "HINT") {
        const next = applyServerHintLevel(
          hint,
          result.assistant_turn.hint_level,
        )
        setHint(next)
        if (!next.valid)
          setNotice(
            "Máy chủ trả mức gợi ý không hợp lệ; giao diện giữ mức hiện tại.",
          )
      }
      turnAttempt.current = null
    } catch (cause) {
      setError(learningError(cause))
    } finally {
      setBusy("")
    }
  }

  function ask(event: FormEvent) {
    event.preventDefault()
    const text = input.trim()
    if (!text || !session || busy) return
    turnAttempt.current = { kind: "ASK", text, key: crypto.randomUUID() }
    void submitTurn(turnAttempt.current)
  }

  function requestHint() {
    if (!session || busy || hint.exhausted) return
    turnAttempt.current = { kind: "HINT", key: crypto.randomUUID() }
    void submitTurn(turnAttempt.current)
  }

  async function prepareSummary() {
    if (!session || busy) return
    if (!summaryKey.current) summaryKey.current = crypto.randomUUID()
    setBusy("summary")
    setError("")
    try {
      const result = await api.prepareLearningSummary(
        session.session_id,
        summaryKey.current,
      )
      setSummary(result)
      setSession(result.session)
      setSummaryError("")
      summaryKey.current = ""
    } catch (cause) {
      setError(learningError(cause))
    } finally {
      setBusy("")
    }
  }

  async function decide(decision: "APPROVE" | "REJECT") {
    if (!summary || busy) return
    if (decisionAttempt.current?.decision !== decision)
      decisionAttempt.current = { decision, key: crypto.randomUUID() }
    setBusy("decision")
    setSummaryError("")
    try {
      const reply = await api.decideLearningOutcome(
        summary.session.conversation_id,
        summary.action_reference,
        decision,
        decisionAttempt.current.key,
      )
      if (reply.state !== "SUCCEEDED") {
        if (reply.error?.code?.startsWith("STALE")) {
          setSummary(null)
          setSession((current) =>
            current ? { ...current, status: "ACTIVE" } : current,
          )
          setError("Bản tóm tắt đã cũ. Hãy tạo lại để xem trước khi lưu.")
        } else setSummaryError(reply.error?.message ?? reply.message)
        return
      }
      decisionAttempt.current = null
      setSummary(null)
      if (decision === "APPROVE") {
        setSession((current) =>
          current ? { ...current, status: "CLOSED" } : current,
        )
        setNotice("Kết quả phiên học đã được lưu sau xác nhận của bạn.")
        try {
          clearLearningSessionId(localStorage, userId)
        } catch {}
      } else {
        setSession((current) =>
          current ? { ...current, status: "ACTIVE" } : current,
        )
        setNotice("Đã quay lại phiên học; bản nháp chưa được lưu.")
      }
    } catch (cause) {
      const message = learningError(cause)
      if (cause instanceof ApiError && cause.status === 409) {
        setSummary(null)
        setSession((current) =>
          current ? { ...current, status: "ACTIVE" } : current,
        )
        setError("Tham chiếu xác nhận đã cũ. Hãy tạo lại bản tóm tắt.")
      } else setSummaryError(message)
    } finally {
      setBusy("")
    }
  }

  function newSession() {
    setSession(null)
    setTurns([])
    setHint(initialHintState())
    setExpired(false)
    setNotice("")
    setError("")
    try {
      clearLearningSessionId(localStorage, userId)
    } catch {}
  }

  const turnViews = turns.map((turn) => mapLearningTurn(turn, materialsById))
  const active = session?.status === "ACTIVE"

  return (
    <Card
      className="study-card learning-session-card"
      title="Phiên học cùng AI"
      action={
        session && active ? (
          <Button
            className="secondary learning-compact-action"
            disabled={Boolean(busy) || !turns.length}
            onClick={() => void prepareSummary()}
          >
            <BookOpenCheck size={15} aria-hidden="true" />
            Kết thúc phiên học
          </Button>
        ) : undefined
      }
    >
      <div className="learning-session-body">
        {!session ? (
          <div className="learning-session-setup">
            <div className="learning-hero-icon">
              <Sparkles aria-hidden="true" />
            </div>
            <div>
              <h3>Bắt đầu với một mục tiêu rõ ràng</h3>
              <p>Trợ lý chỉ trả lời dựa trên tài liệu bạn đã chọn.</p>
            </div>
            {expired && (
              <p className="learning-expired" role="status">
                Phiên đã hết hạn lưu (30 ngày). Hãy tạo phiên mới.
              </p>
            )}
            <label className="learning-goal-field">
              <span>Mục tiêu hôm nay</span>
              <textarea
                value={goal}
                maxLength={1000}
                rows={3}
                placeholder="Ví dụ: Hiểu cách áp dụng định lý Bayes"
                onChange={(event) => setGoal(event.target.value)}
              />
              <small>{goal.length}/1000 ký tự</small>
            </label>
            <p className="learning-selected-summary">
              {selectedMaterials.length
                ? `${selectedMaterials.length} tài liệu sẵn sàng được chọn.`
                : "Chọn ít nhất một tài liệu sẵn sàng ở bên trái."}
            </p>
            <Button
              className="primary learning-start-button"
              disabled={Boolean(busy) || !contextReady}
              onClick={() => void createSession()}
            >
              {busy === "create" || busy === "recover" ? (
                <LoaderCircle className="learning-spin" aria-hidden="true" />
              ) : (
                <Sparkles aria-hidden="true" />
              )}
              {busy === "recover" ? "Đang khôi phục…" : "Tạo phiên học"}
            </Button>
          </div>
        ) : (
          <>
            <header className="learning-session-context">
              <div>
                <span>Mục tiêu hôm nay</span>
                <strong>{session.goal}</strong>
              </div>
              <span>{session.material_ids.length} tài liệu</span>
            </header>
            <div
              className="learning-transcript"
              role="log"
              aria-live="polite"
              aria-label="Lịch sử phiên học"
            >
              {!turnViews.length && (
                <div className="learning-state is-empty">
                  <Sparkles aria-hidden="true" />
                  <strong>Hãy đặt câu hỏi đầu tiên</strong>
                  <span>Câu trả lời có căn cứ sẽ kèm trích dẫn trang.</span>
                </div>
              )}
              {turnViews.map((turn) => (
                <article
                  key={turn.turn_id}
                  className={`learning-bubble is-${turn.role.toLocaleLowerCase()} ${
                    turn.kind === "HINT" ? "is-hint" : ""
                  } ${turn.supported === false ? "is-unsupported" : ""}`}
                >
                  <span className="learning-bubble-label">
                    {turn.role === "USER"
                      ? "Bạn"
                      : turn.kind === "HINT"
                        ? `Gợi ý mức ${turn.hint_level}`
                        : "Trợ lý học tập"}
                  </span>
                  {turn.supported === false ? (
                    <div className="learning-unsupported">
                      <CircleAlert size={17} aria-hidden="true" />
                      <div>
                        <strong>
                          Tài liệu hiện có chưa đủ căn cứ để trả lời.
                        </strong>
                        <p>{turn.content}</p>
                      </div>
                    </div>
                  ) : (
                    <p>{turn.content}</p>
                  )}
                  {turn.citations.length > 0 && (
                    <div
                      className="learning-citations"
                      aria-label="Nguồn trích dẫn"
                    >
                      {turn.citations.map((citation) => (
                        <CitationChip
                          key={`${citation.chunk_id}-${citation.page}`}
                          citation={citation}
                        />
                      ))}
                    </div>
                  )}
                </article>
              ))}
              {busy === "turn" && (
                <div
                  className="learning-bubble is-assistant is-loading"
                  role="status"
                >
                  <LoaderCircle className="learning-spin" aria-hidden="true" />
                  Đang xử lý dựa trên tài liệu…
                </div>
              )}
              <div ref={transcriptEnd} />
            </div>
            {active ? (
              <form className="learning-composer" onSubmit={ask}>
                <label className="sr-only" htmlFor="learning-question">
                  Câu hỏi cho trợ lý học tập
                </label>
                <textarea
                  id="learning-question"
                  value={input}
                  maxLength={4000}
                  rows={2}
                  placeholder="Nhập câu hỏi về tài liệu…"
                  disabled={Boolean(busy)}
                  onChange={(event) => setInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (
                      event.key === "Enter" &&
                      !event.shiftKey &&
                      !event.nativeEvent.isComposing
                    ) {
                      event.preventDefault()
                      event.currentTarget.form?.requestSubmit()
                    }
                  }}
                />
                <div className="learning-composer-actions">
                  <Button
                    className="secondary"
                    type="button"
                    disabled={Boolean(busy) || hint.exhausted || !turns.length}
                    onClick={requestHint}
                  >
                    <Lightbulb size={16} aria-hidden="true" />
                    {hintButtonLabel(hint)}
                  </Button>
                  <Button
                    className="primary"
                    type="submit"
                    disabled={Boolean(busy) || !input.trim()}
                  >
                    <Send size={16} aria-hidden="true" />
                    Gửi
                  </Button>
                </div>
              </form>
            ) : (
              <div className="learning-closed-state">
                <span>Phiên học đã kết thúc.</span>
                <Button className="secondary" onClick={newSession}>
                  <RotateCcw size={15} aria-hidden="true" />
                  Tạo phiên mới
                </Button>
              </div>
            )}
          </>
        )}
        {(error || notice) && (
          <div
            className={`learning-session-message ${
              error ? "is-error" : "is-success"
            }`}
            role={error ? "alert" : "status"}
          >
            <span>{error || notice}</span>
            {error && turnAttempt.current && (
              <button
                type="button"
                disabled={Boolean(busy)}
                onClick={() => void submitTurn(turnAttempt.current!)}
              >
                Thử lại
              </button>
            )}
          </div>
        )}
      </div>
      {summary && (
        <SessionSummaryModal
          summary={summary}
          busy={busy === "decision"}
          error={summaryError}
          close={() => void decide("REJECT")}
          decide={(decision) => void decide(decision)}
        />
      )}
    </Card>
  )
}
