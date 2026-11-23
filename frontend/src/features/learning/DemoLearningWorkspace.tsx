import { useRef, useState, type FormEvent, type KeyboardEvent } from "react"
import {
  BookOpen,
  FileText,
  MessageSquareText,
  Send,
  Sparkles,
  Upload,
} from "lucide-react"
import Button from "../../components/ui/Button"
import Card from "../../components/ui/Card"

type MobileView = "materials" | "session"

const exampleQuestions = [
  "Tóm tắt các ý chính trong tài liệu",
  "Giải thích khái niệm khó nhất",
  "Gợi ý câu hỏi để tự kiểm tra",
]

export default function DemoLearningWorkspace() {
  const [files, setFiles] = useState<string[]>([])
  const [goal, setGoal] = useState("")
  const [input, setInput] = useState("")
  const [notice, setNotice] = useState("")
  const [mobileView, setMobileView] = useState<MobileView>("session")
  const uploadRef = useRef<HTMLInputElement>(null)

  function explainDemoLimit(event: FormEvent) {
    event.preventDefault()
    if (!input.trim()) return
    setNotice(
      "Cần kết nối API và có tài liệu READY để gửi câu hỏi có dẫn nguồn.",
    )
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  return (
    <div className="daily-learning-shell">
      <div
        className="learning-mobile-switcher"
        role="group"
        aria-label="Khu vực phiên học"
      >
        <button
          type="button"
          aria-pressed={mobileView === "materials"}
          onClick={() => setMobileView("materials")}
        >
          <BookOpen size={16} aria-hidden="true" />
          Tài liệu
        </button>
        <button
          type="button"
          aria-pressed={mobileView === "session"}
          onClick={() => setMobileView("session")}
        >
          <MessageSquareText size={16} aria-hidden="true" />
          Phiên học
        </button>
      </div>
      <div className="daily-learning-workspace is-demo">
        <input
          ref={uploadRef}
          className="hidden"
          type="file"
          accept=".pdf,.txt,.md"
          multiple
          onChange={(event) => {
            setFiles(Array.from(event.target.files ?? [], (file) => file.name))
            setNotice("Tệp chỉ được hiển thị cục bộ, chưa được tải lên.")
            event.target.value = ""
          }}
        />
        <Card
          className={`study-card learning-materials-card ${
            mobileView !== "materials" ? "is-mobile-hidden" : ""
          }`}
          title="Tài liệu của bạn"
          action={
            <Button
              className="secondary learning-compact-action"
              onClick={() => uploadRef.current?.click()}
            >
              <Upload size={15} aria-hidden="true" />
              Thêm tài liệu
            </Button>
          }
        >
          <div className="learning-card-body">
            <div className="learning-card-intro">
              <p>Nguồn được chọn sẽ giới hạn phạm vi trả lời của trợ lý.</p>
            </div>
            {files.length ? (
              <ul className="learning-material-list">
                {files.map((name) => (
                  <li key={name} className="learning-demo-material">
                    <span className="learning-file-icon">
                      <FileText size={17} aria-hidden="true" />
                    </span>
                    <span className="learning-file-copy">
                      <strong title={name}>{name}</strong>
                      <span>Chỉ hiển thị trong phiên demo</span>
                    </span>
                    <span className="learning-status is-demo" role="status">
                      Chưa tải lên
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="learning-state is-empty learning-material-empty">
                <span className="learning-empty-icon">
                  <FileText aria-hidden="true" />
                </span>
                <strong>Thêm tài liệu để bắt đầu</strong>
                <span>
                  Hỗ trợ PDF, TXT và Markdown. Demo không đọc hoặc gửi tệp đi.
                </span>
                <Button
                  className="secondary"
                  onClick={() => uploadRef.current?.click()}
                >
                  <Upload size={16} aria-hidden="true" />
                  Chọn tệp minh hoạ
                </Button>
              </div>
            )}
            <p className="learning-selection-count" role="status">
              <strong>0 tài liệu sẵn sàng</strong>
              <span> · Chưa kết nối kho tài liệu thật</span>
            </p>
          </div>
        </Card>

        <Card
          className={`study-card learning-session-card ${
            mobileView !== "session" ? "is-mobile-hidden" : ""
          }`}
          title="Trợ lý học tập"
        >
          <div className="learning-session-body">
            <div className="learning-mode-note" role="note">
              <span className="learning-mode-dot" aria-hidden="true" />
              Chế độ demo · Chưa kết nối AI và tài liệu thật
            </div>
            <div className="learning-session-setup learning-demo-setup">
              <div className="learning-setup-heading">
                <span className="learning-hero-icon">
                  <Sparkles aria-hidden="true" />
                </span>
                <div>
                  <h3>Sẵn sàng học cùng bạn</h3>
                  <p>
                    Chọn tài liệu và đặt mục tiêu để bắt đầu phiên học có dẫn
                    nguồn.
                  </p>
                </div>
              </div>
              <label className="learning-goal-field">
                <span>Mục tiêu hôm nay</span>
                <textarea
                  value={goal}
                  maxLength={1000}
                  rows={2}
                  placeholder="Ví dụ: Hiểu cách áp dụng định lý Bayes vào bài tập"
                  onChange={(event) => setGoal(event.target.value)}
                />
                <small>{goal.length}/1000 ký tự</small>
              </label>
              <div className="learning-start-row">
                <p className="learning-selected-summary">
                  Cần ít nhất 1 tài liệu READY để bắt đầu.
                </p>
                <Button
                  className="primary learning-start-button"
                  disabled
                  title="Chế độ demo không tạo phiên học trên máy chủ"
                >
                  <Sparkles size={17} aria-hidden="true" />
                  Bắt đầu phiên học
                </Button>
              </div>
            </div>

            <div className="learning-demo-preview">
              <span className="learning-demo-preview-label">Gợi ý câu hỏi</span>
              <div className="learning-question-suggestions">
                {exampleQuestions.map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => {
                      setInput(question)
                      setNotice("")
                    }}
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>

            <form className="learning-composer" onSubmit={explainDemoLimit}>
              {notice && (
                <p className="learning-composer-note" role="status">
                  {notice}
                </p>
              )}
              <div className="learning-composer-box">
                <label className="sr-only" htmlFor="demo-learning-question">
                  Câu hỏi minh hoạ
                </label>
                <textarea
                  id="demo-learning-question"
                  value={input}
                  rows={1}
                  placeholder="Hỏi về tài liệu của bạn…"
                  onChange={(event) => {
                    setInput(event.target.value)
                    setNotice("")
                    event.currentTarget.style.height = "auto"
                    event.currentTarget.style.height = `${Math.min(
                      event.currentTarget.scrollHeight,
                      128,
                    )}px`
                  }}
                  onKeyDown={handleComposerKeyDown}
                />
                <div className="learning-composer-actions">
                  <Button className="secondary" type="button" disabled>
                    Gợi ý
                  </Button>
                  <Button
                    className="primary learning-send-button"
                    type="submit"
                    disabled={!input.trim()}
                    aria-label="Gửi câu hỏi minh hoạ"
                  >
                    <Send size={17} aria-hidden="true" />
                    <span>Gửi</span>
                  </Button>
                </div>
              </div>
              <small>Enter để gửi · Shift+Enter để xuống dòng</small>
            </form>
          </div>
        </Card>
      </div>
    </div>
  )
}
