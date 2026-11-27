import { useEffect, useState, type FormEvent } from "react"

import { ArrowRight } from "lucide-react"

import type { CandidateTaskFields, Question } from "../../api/types"

import TaskClarificationFields from "../planner/TaskClarificationFields"

import {
  createClarificationDraft,
  formatClarificationFollowUp,
  usesDeadlineDatetime,
  type ClarificationDraftValues,
} from "../planner/clarification"

const DEMO_TASK_QUESTIONS: Question[] = [
  { field: "title", message: "Tên công việc là gì?", choices: [] },

  { field: "deadline_date", message: "Hạn nộp là ngày nào?", choices: [] },

  {
    field: "estimated_minutes",

    message: "Bạn dự kiến cần bao nhiêu phút?",

    choices: [],
  },
]

export default function AssistantTaskClarificationForm({
  mode,

  originalPrompt,

  questions,

  slots,

  busy = false,

  onSubmitApi,

  onSubmitDemo,

  onCancel,

  externalError,
}: {
  mode: "api" | "demo"

  originalPrompt: string

  questions?: Question[]

  slots?: CandidateTaskFields

  busy?: boolean

  onSubmitApi?: (followUpText: string) => void

  onSubmitDemo?: (values: ClarificationDraftValues) => void

  onCancel?: () => void

  externalError?: string
}) {
  const effectiveQuestions =
    questions && questions.length > 0 ? questions : DEMO_TASK_QUESTIONS

  const draft = () =>
    createClarificationDraft(
      effectiveQuestions,
      originalPrompt,
      undefined,
      slots,
    )

  const [values, setValues] = useState<ClarificationDraftValues>(draft)

  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setValues(draft())

    setError(null)
  }, [originalPrompt, questions, slots])

  const setField = (key: string, value: string) => {
    setValues((prev) => ({ ...prev, [key]: value }))

    if (error) setError(null)
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (busy) return

    const formatted = formatClarificationFollowUp(
      {
        source: mode,

        originalPrompt,

        message: "",

        questions: effectiveQuestions,

        slots,
      },

      values,
    )

    if (!formatted.ok) {
      setError(formatted.error)

      return
    }

    if (mode === "api") {
      onSubmitApi?.(formatted.text)
    } else {
      onSubmitDemo?.(values)
    }
  }

  const missingFields = new Set(effectiveQuestions.map((q) => q.field))

  const useDeadlineDatetime = usesDeadlineDatetime(effectiveQuestions, slots)

  return (
    <form className="assistant-details-form" onSubmit={handleSubmit} noValidate>
      <TaskClarificationFields
        idPrefix="assistant-clarify"
        values={values}
        setField={setField}
        missingFields={missingFields}
        useDeadlineDatetime={useDeadlineDatetime}
        busy={busy}
      />
      {(error || externalError) && (
        <p className="assistant-form-error" role="alert">
          {error || externalError}
        </p>
      )}
      <button className="button primary" type="submit" disabled={busy}>
        {mode === "api" ? "Tiếp tục" : "Xem bản nháp"}{" "}
        <ArrowRight size={16} aria-hidden="true" />
      </button>
      {onCancel && (
        <button
          className="button secondary"
          type="button"
          disabled={busy}
          onClick={onCancel}
        >
          Hủy
        </button>
      )}
    </form>
  )
}
