import Button from "../../components/ui/Button"
import Modal from "../../components/ui/Modal"

type QuizOverviewProps = {
  questionIds: string[]
  answers: Record<string, string>
  currentIndex: number
  busy: boolean
  canSubmit: boolean
  showConfirmation: boolean
  onNavigate: (index: number) => void
  onRequestSubmit: () => void
  onCancelSubmit: () => void
  onConfirmSubmit: () => void
}

export default function QuizOverview({
  questionIds,
  answers,
  currentIndex,
  busy,
  canSubmit,
  showConfirmation,
  onNavigate,
  onRequestSubmit,
  onCancelSubmit,
  onConfirmSubmit,
}: QuizOverviewProps) {
  const answered = questionIds.filter((id) => Boolean(answers[id])).length
  const unanswered = questionIds.length - answered

  return (
    <>
      <details className="assessment-quiz-overview" open>
        <summary>
          <span>Tổng quan bài làm</span>
          <small>
            {answered}/{questionIds.length} đã trả lời
          </small>
        </summary>
        <div className="assessment-quiz-overview-body">
          <dl>
            <div>
              <dt>Tổng số</dt>
              <dd>{questionIds.length}</dd>
            </div>
            <div>
              <dt>Đã trả lời</dt>
              <dd>{answered}</dd>
            </div>
            <div>
              <dt>Chưa trả lời</dt>
              <dd>{unanswered}</dd>
            </div>
            <div>
              <dt>Đang xem</dt>
              <dd>{currentIndex + 1}</dd>
            </div>
          </dl>
          <nav
            className="assessment-question-navigator"
            aria-label="Điều hướng câu hỏi"
          >
            {questionIds.map((questionId, index) => {
              const isAnswered = Boolean(answers[questionId])
              const isCurrent = index === currentIndex
              return (
                <button
                  key={questionId}
                  type="button"
                  className={`${isAnswered ? "is-answered" : ""} ${
                    isCurrent ? "is-current" : ""
                  }`}
                  onClick={() => onNavigate(index)}
                  aria-current={isCurrent ? "true" : undefined}
                  aria-label={`Đi đến câu ${index + 1}, ${
                    isAnswered ? "đã trả lời" : "chưa trả lời"
                  }`}
                >
                  <span aria-hidden="true">{isAnswered ? "✓" : index + 1}</span>
                  <small>Câu {index + 1}</small>
                </button>
              )
            })}
          </nav>
          <div className="assessment-navigator-legend">
            <span>
              <i className="is-answered" />
              Đã trả lời
            </span>
            <span>
              <i />
              Chưa trả lời
            </span>
          </div>
          <Button
            className="primary assessment-submit-action"
            onClick={onRequestSubmit}
            disabled={busy || !canSubmit}
          >
            {busy ? "Đang nộp…" : "Nộp bài"}
          </Button>
        </div>
      </details>

      {showConfirmation && (
        <Modal title="Xác nhận nộp bài" close={onCancelSubmit}>
          <p>
            Bạn đã trả lời {answered}/{questionIds.length} câu. {unanswered} câu
            chưa trả lời sẽ được gửi dưới dạng bỏ qua.
          </p>
          <div className="assessment-submit-confirmation">
            <Button className="secondary" onClick={onCancelSubmit}>
              Quay lại bài làm
            </Button>
            <Button className="primary" onClick={onConfirmSubmit}>
              Xác nhận nộp bài
            </Button>
          </div>
        </Modal>
      )}
    </>
  )
}
