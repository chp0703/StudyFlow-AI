import { useRef, useState, type FormEvent } from "react"
import { CircleAlert, FileText, Send, Upload } from "lucide-react"
import Button from "../../components/ui/Button"
import Card from "../../components/ui/Card"

type DemoMessage = {
  id: string
  role: "user" | "assistant"
  text: string
}

export default function DemoLearningWorkspace() {
  const [files, setFiles] = useState<string[]>([])
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<DemoMessage[]>([])
  const uploadRef = useRef<HTMLInputElement>(null)

  function ask(event: FormEvent) {
    event.preventDefault()
    const text = input.trim()
    if (!text) return
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", text },
      {
        id: crypto.randomUUID(),
        role: "assistant",
        text: "Demo – không đọc tài liệu. Tài liệu hiện có chưa đủ căn cứ để trả lời.",
      },
    ])
    setInput("")
  }

  return (
    <div className="daily-learning-workspace is-demo">
      <input
        ref={uploadRef}
        className="hidden"
        type="file"
        accept=".pdf,.txt,.md"
        multiple
        onChange={(event) => {
          setFiles(Array.from(event.target.files ?? [], (file) => file.name))
          event.target.value = ""
        }}
      />
      <Card
        className="study-card learning-materials-card"
        title="Tài liệu học"
        action={
          <Button
            className="primary learning-compact-action"
            onClick={() => uploadRef.current?.click()}
          >
            <Upload size={15} aria-hidden="true" />
            Chọn tệp
          </Button>
        }
      >
        <div className="learning-card-body">
          <div className="learning-demo-banner" role="note">
            Bản demo cục bộ — tệp không được tải lên, đọc hoặc lập chỉ mục.
          </div>
          {files.length ? (
            <ul className="learning-material-list">
              {files.map((name) => (
                <li key={name}>
                  <span className="learning-file-icon">
                    <FileText size={17} aria-hidden="true" />
                  </span>
                  <span className="learning-file-copy">
                    <strong>{name}</strong>
                    <span>Chỉ hiển thị trong phiên demo</span>
                  </span>
                  <span className="learning-status is-demo" role="status">
                    Chưa tải lên
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="learning-state is-empty">
              <FileText aria-hidden="true" />
              <strong>Chưa chọn tệp demo</strong>
              <span>Tệp chỉ được hiển thị tên, không được gửi đi.</span>
            </div>
          )}
        </div>
      </Card>
      <Card
        className="study-card learning-session-card"
        title="Phiên học cùng AI"
      >
        <div className="learning-session-body">
          <div className="learning-demo-banner" role="note">
            Demo – không đọc tài liệu, không gọi AI thật và không tạo trích dẫn.
          </div>
          <div
            className="learning-transcript"
            role="log"
            aria-live="polite"
            aria-label="Hội thoại minh hoạ"
          >
            {!messages.length && (
              <div className="learning-state is-empty">
                <CircleAlert aria-hidden="true" />
                <strong>Nội dung minh hoạ</strong>
                <span>Hãy gửi câu hỏi để xem trạng thái không đủ căn cứ.</span>
              </div>
            )}
            {messages.map((message) => (
              <article
                key={message.id}
                className={`learning-bubble is-${message.role} ${
                  message.role === "assistant" ? "is-unsupported" : ""
                }`}
              >
                <span className="learning-bubble-label">
                  {message.role === "user" ? "Bạn" : "Trợ lý học tập"}
                </span>
                <p>{message.text}</p>
              </article>
            ))}
          </div>
          <form className="learning-composer" onSubmit={ask}>
            <label className="sr-only" htmlFor="demo-learning-question">
              Câu hỏi minh hoạ
            </label>
            <textarea
              id="demo-learning-question"
              value={input}
              rows={2}
              placeholder="Nhập câu hỏi minh hoạ…"
              onChange={(event) => setInput(event.target.value)}
            />
            <div className="learning-composer-actions">
              <Button className="secondary" type="button" disabled>
                Gợi ý cần kết nối API
              </Button>
              <Button
                className="primary"
                type="submit"
                disabled={!input.trim()}
              >
                <Send size={16} aria-hidden="true" />
                Gửi demo
              </Button>
            </div>
          </form>
        </div>
      </Card>
    </div>
  )
}
