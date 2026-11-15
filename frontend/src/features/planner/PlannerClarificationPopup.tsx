import { useEffect, useId, useRef, useState, type FormEvent } from "react"
import { Send, Sparkles, X } from "lucide-react"
import Button from "../../components/ui/Button"
import {
  createClarificationDraft,
  formatClarificationFollowUp,
  isTaskClarification,
  type ClarificationDraftValues,
  type PlannerClarification,
} from "./clarification"
import TaskClarificationFields from "./TaskClarificationFields"

const FIELD_LABELS: Record<string, string> = {
  date: "Ngày áp dụng",
  start_time: "Giờ bắt đầu",
  end_time: "Giờ kết thúc",
  intent: "Yêu cầu của bạn",
}

export default function PlannerClarificationPopup({
  clarification,
  busy,
  onDismiss,
  onSubmit,
}: {
  clarification: PlannerClarification
  busy: boolean
  onDismiss: () => void
  onSubmit: (followUpText: string) => void
}) {
  const titleId = useId()
  const formRef = useRef<HTMLFormElement>(null)
  const [values, setValues] = useState<ClarificationDraftValues>(() =>
    createClarificationDraft(
      clarification.questions,
      clarification.originalPrompt,
    ),
  )
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setValues(
      createClarificationDraft(
        clarification.questions,
        clarification.originalPrompt,
      ),
    )
    setError(null)
    requestAnimationFrame(() => {
      const firstInput =
        formRef.current?.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
          "input, select, textarea",
        )
      firstInput?.focus()
    })
  }, [clarification])

  const setField = (key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }))
    if (error) setError(null)
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (busy) return
    const formatted = formatClarificationFollowUp(clarification, values)
    if (!formatted.ok) {
      setError(formatted.error)
      return
    }
    onSubmit(formatted.text)
  }

  const missingFields = new Set(clarification.questions.map((q) => q.field))
  const isTaskForm = isTaskClarification(clarification.questions)
  const useDeadlineDatetime = missingFields.has("deadline_at")

  return (
    <section
      className={`planner-clarification-popup${
        isTaskForm ? " is-task-form" : ""
      }`}
      role="dialog"
      aria-modal="false"
      aria-labelledby={titleId}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.stopPropagation()
          onDismiss()
        }
      }}
    >
      <div className="planner-clarification-head">
        <div className="planner-clarification-title-wrap">
          <Sparkles size={16} aria-hidden="true" />
          <h3 id={titleId} className="planner-clarification-title">
            {isTaskForm ? "Chi tiết công việc" : "Bổ sung thông tin còn thiếu"}
          </h3>
        </div>
        <button
          type="button"
          className="planner-clarification-close"
          onClick={onDismiss}
          aria-label="Đóng hộp thoại bổ sung thông tin"
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>

      <p className="planner-clarification-context">
        Đã điền sẵn từ yêu cầu: <span>“{clarification.originalPrompt}”</span>
      </p>

      <form
        ref={formRef}
        className="planner-clarification-form"
        onSubmit={handleSubmit}
        noValidate
      >
        {isTaskForm ? (
          <TaskClarificationFields
            idPrefix="planner-clarify"
            values={values}
            setField={setField}
            missingFields={missingFields}
            useDeadlineDatetime={useDeadlineDatetime}
            busy={busy}
          />
        ) : (
          <div className="planner-clarification-fields">
            {clarification.questions.map((q) => {
              const label = FIELD_LABELS[q.field] ?? q.message
              const fieldId = `planner-clarify-${q.field}`

              if (q.field === "date") {
                return (
                  <label
                    key={q.field}
                    htmlFor={fieldId}
                    className="planner-clarification-field"
                  >
                    <span className="planner-clarification-label">{label}</span>
                    <input
                      id={fieldId}
                      type="date"
                      value={values[q.field] ?? ""}
                      disabled={busy}
                      onChange={(e) => setField(q.field, e.target.value)}
                    />
                  </label>
                )
              }

              if (q.field === "start_time" || q.field === "end_time") {
                return (
                  <label
                    key={q.field}
                    htmlFor={fieldId}
                    className="planner-clarification-field"
                  >
                    <span className="planner-clarification-label">{label}</span>
                    <input
                      id={fieldId}
                      type="time"
                      value={values[q.field] ?? ""}
                      disabled={busy}
                      onChange={(e) => setField(q.field, e.target.value)}
                    />
                  </label>
                )
              }

              return (
                <div key={q.field} className="planner-clarification-field">
                  <label
                    htmlFor={fieldId}
                    className="planner-clarification-label"
                  >
                    {label}
                  </label>
                  {q.choices.length > 0 && (
                    <div className="planner-clarification-choices">
                      {q.choices.map((choice) => (
                        <button
                          key={choice.value}
                          type="button"
                          className={`planner-clarification-choice${
                            values[q.field] === choice.value
                              ? " is-selected"
                              : ""
                          }`}
                          disabled={busy}
                          onClick={() => setField(q.field, choice.value)}
                        >
                          {choice.label}
                        </button>
                      ))}
                    </div>
                  )}
                  <input
                    id={fieldId}
                    type="text"
                    placeholder={q.message}
                    value={values[q.field] ?? ""}
                    disabled={busy}
                    onChange={(e) => setField(q.field, e.target.value)}
                  />
                </div>
              )
            })}
          </div>
        )}

        {error && (
          <p className="planner-clarification-error" role="alert">
            {error}
          </p>
        )}

        <div className="planner-clarification-actions">
          <Button type="button" onClick={onDismiss} disabled={busy}>
            Hủy
          </Button>
          <Button type="submit" className="primary" disabled={busy}>
            <Send size={14} aria-hidden="true" />
            Tiếp tục
          </Button>
        </div>
      </form>
    </section>
  )
}
