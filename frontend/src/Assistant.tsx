import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react"
import {
  ArrowRight,
  CalendarDays,
  Check,
  Clock3,
  Plus,
  Send,
  Sparkles,
  X,
} from "lucide-react"
import {
  demoReply,
  suggestions,
  type ActionProposal,
  type ChatMessage,
  type DemoScenario,
} from "./assistantDemo"

type Draft = {
  title: string
  course: string
  deadline: string
  duration: string
  availability: string
  block: string
  target: string
}
const emptyDraft: Draft = {
  title: "",
  course: "",
  deadline: "",
  duration: "",
  availability: "",
  block: "",
  target: "",
}

export default function Assistant({
  onOpenPlanner,
}: {
  onOpenPlanner: () => void
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [draft, setDraft] = useState<Draft>(emptyDraft)
  const [formError, setFormError] = useState("")
  const nextId = useRef(1)
  const transcriptRef = useRef<HTMLDivElement>(null)
  const shouldScroll = useRef(true)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const activeClarification =
    messages.at(-1)?.category === "CLARIFICATION" ? messages.at(-1)?.id : null

  useEffect(() => {
    if (shouldScroll.current)
      transcriptRef.current?.scrollTo({
        top: transcriptRef.current.scrollHeight,
        behavior: "smooth",
      })
  }, [messages])

  function append(...items: Omit<ChatMessage, "id">[]) {
    shouldScroll.current = true
    setMessages((current) => [
      ...current,
      ...items.map((item) => ({ ...item, id: nextId.current++ })),
    ])
  }

  function send(value = input) {
    const text = value.trim()
    if (!text) return
    setInput("")
    setFormError("")
    setDraft(emptyDraft)
    append({ role: "user", category: "MESSAGE", text }, demoReply(text))
  }

  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault()
      send()
    }
  }

  function submitDraft(
    event: FormEvent<HTMLFormElement>,
    scenario: DemoScenario,
  ) {
    event.preventDefault()
    const missing =
      scenario === "task"
        ? !draft.title.trim() ||
          !draft.course.trim() ||
          !draft.deadline ||
          !draft.duration
        : scenario === "plan"
          ? !draft.title.trim() || !draft.deadline || !draft.availability.trim()
          : !draft.block.trim() || !draft.target
    if (missing) {
      setFormError(
        "Vui lòng điền tất cả thông tin cần thiết trước khi xem bản nháp.",
      )
      return
    }
    const proposal: ActionProposal =
      scenario === "task"
        ? {
            intent: "CREATE_TASK",
            title: "Bản nháp công việc",
            status: "awaiting_approval",
            caveat:
              "Chưa lưu công việc; hạn và thời lượng do bạn nhập, chưa được kiểm tra với lịch thực tế.",
            details: [
              { label: "Công việc", value: draft.title.trim() },
              { label: "Môn học", value: draft.course.trim() },
              { label: "Hạn", value: draft.deadline },
              { label: "Thời lượng", value: `${draft.duration} phút` },
            ],
          }
        : scenario === "plan"
          ? {
              intent: "GENERATE_STUDY_PLAN",
              title: "Yêu cầu lập kế hoạch mẫu",
              status: "awaiting_approval",
              caveat:
                "Đây là tóm tắt yêu cầu, chưa có khung giờ được tính toán hoặc xác thực xung đột.",
              details: [
                { label: "Công việc", value: draft.title.trim() },
                { label: "Hạn", value: draft.deadline },
                { label: "Thời gian rảnh", value: draft.availability.trim() },
              ],
            }
          : {
              intent: "RESCHEDULE_STUDY_BLOCK",
              title: "Đề xuất đổi lịch mẫu",
              status: "awaiting_approval",
              caveat:
                "Chưa xác định buổi học trong cơ sở dữ liệu và chưa kiểm tra thời gian mới có phù hợp hay không.",
              details: [
                { label: "Buổi học", value: draft.block.trim() },
                { label: "Thời gian mong muốn", value: draft.target },
              ],
            }
    setFormError("")
    append({
      role: "assistant",
      category: "PROPOSAL",
      scenario,
      intent: proposal.intent,
      validation: "valid_demo_draft",
      text: "Kiểm tra thông tin bạn đã nhập. Xác nhận ở đây chỉ ghi nhận thao tác trong bản mẫu.",
      proposal,
    })
  }

  function decide(id: number, status: "cancelled" | "demo_acknowledged") {
    setMessages((current) =>
      current.map((message) =>
        message.id === id && message.proposal
          ? { ...message, proposal: { ...message.proposal, status } }
          : message,
      ),
    )
  }

  function newChat() {
    setMessages([])
    setInput("")
    setDraft(emptyDraft)
    setFormError("")
    requestAnimationFrame(() => composerRef.current?.focus())
  }

  function field(
    name: keyof Draft,
    label: string,
    type = "text",
    placeholder = "",
  ) {
    return (
      <label className="assistant-field">
        {label}
        <input
          type={type}
          value={draft[name]}
          placeholder={placeholder}
          onChange={(event) =>
            setDraft((value) => ({ ...value, [name]: event.target.value }))
          }
          onInput={(event) => {
            const value = event.currentTarget.value
            setDraft((current) => ({ ...current, [name]: value }))
          }}
        />
      </label>
    )
  }

  function clarificationForm(scenario: DemoScenario) {
    if (scenario === "view") return null
    return (
      <form
        className="assistant-details-form"
        onSubmit={(event) => submitDraft(event, scenario)}
        noValidate
      >
        <div className="assistant-field-grid">
          {scenario === "task" && (
            <>
              {field("title", "Tên công việc *", "text", "Ví dụ: Làm bài OOP")}
              {field(
                "course",
                "Môn học *",
                "text",
                "Ví dụ: Lập trình hướng đối tượng",
              )}
              {field("deadline", "Hạn hoàn thành *", "date")}
              {field("duration", "Thời lượng dự kiến (phút) *", "number", "60")}
            </>
          )}
          {scenario === "plan" && (
            <>
              {field(
                "title",
                "Công việc cần lên kế hoạch *",
                "text",
                "Ví dụ: Ôn tập giải tích",
              )}
              {field("deadline", "Hạn hoàn thành *", "date")}
              {field(
                "availability",
                "Thời gian bạn có thể học *",
                "text",
                "Ví dụ: Thứ 3 và thứ 5, 19:00–21:00",
              )}
            </>
          )}
          {scenario === "reschedule" && (
            <>
              {field(
                "block",
                "Buổi học cần đổi *",
                "text",
                "Ví dụ: Ôn giải tích, thứ 3 lúc 19:00",
              )}
              {field("target", "Thời gian mới mong muốn *", "datetime-local")}
            </>
          )}
        </div>
        {formError && (
          <p className="assistant-form-error" role="alert">
            {formError}
          </p>
        )}
        <button className="button primary" type="submit">
          Xem bản nháp <ArrowRight size={16} aria-hidden="true" />
        </button>
      </form>
    )
  }

  return (
    <section
      className={`assistant-shell ${
        messages.length ? "has-messages" : "is-empty"
      }`}
      aria-label="Trợ lý AI bản mẫu"
    >
      <div className="assistant-topline">
        <span>
          <Sparkles size={16} aria-hidden="true" /> Bản mẫu tương tác · Chưa kết
          nối AI
        </span>
        <button className="button secondary" onClick={newChat} type="button">
          <Plus size={17} aria-hidden="true" /> Cuộc trò chuyện mới
        </button>
      </div>
      {messages.length === 0 ? (
        <div className="assistant-welcome">
          <div className="assistant-mark">
            <Sparkles size={28} aria-hidden="true" />
          </div>
          <p className="assistant-eyebrow">STUDYFLOW ASSISTANT</p>
          <h2>Hôm nay bạn muốn làm gì?</h2>
          <p>
            Bạn có thể thêm công việc, lên kế hoạch học hoặc điều chỉnh lịch học
            bằng cách trò chuyện với StudyFlow AI.
          </p>
          <div className="assistant-suggestions" aria-label="Gợi ý bắt đầu">
            {suggestions.map(({ scenario, title, prompt }) => (
              <button key={scenario} type="button" onClick={() => send(prompt)}>
                <span className="assistant-suggestion-icon">
                  {scenario === "view" ? (
                    <CalendarDays size={18} />
                  ) : scenario === "reschedule" ? (
                    <Clock3 size={18} />
                  ) : (
                    <Sparkles size={18} />
                  )}
                </span>
                <span>{title}</span>
                <ArrowRight size={16} aria-hidden="true" />
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div
          className="assistant-transcript"
          ref={transcriptRef}
          onScroll={(event) => {
            const el = event.currentTarget
            shouldScroll.current =
              el.scrollHeight - el.scrollTop - el.clientHeight < 96
          }}
          role="log"
          aria-label="Cuộc trò chuyện"
          aria-live="polite"
        >
          <div className="assistant-thread">
            {messages.map((message) => (
              <article
                key={message.id}
                className={`assistant-message ${
                  message.role === "user" ? "from-user" : "from-assistant"
                }`}
              >
                {message.role === "assistant" && (
                  <div className="assistant-avatar" aria-hidden="true">
                    <Sparkles size={16} />
                  </div>
                )}
                <div className="assistant-message-body">
                  <span className="assistant-sender">
                    {message.role === "user" ? "Bạn" : "StudyFlow · Bản mẫu"}
                  </span>
                  <div className="assistant-bubble">
                    {message.category !== "MESSAGE" && (
                      <span
                        className={`assistant-state assistant-state-${message.category.toLowerCase()}`}
                      >
                        {message.category === "CLARIFICATION"
                          ? "Cần thêm thông tin"
                          : message.category === "PROPOSAL"
                            ? "Bản nháp cần xem lại"
                            : message.category === "UNSUPPORTED"
                              ? "Chưa hỗ trợ"
                              : "Có lỗi"}
                      </span>
                    )}
                    <p>{message.text}</p>
                    {message.category === "CLARIFICATION" &&
                      message.scenario &&
                      message.id === activeClarification &&
                      clarificationForm(message.scenario)}
                    {message.scenario === "view" && (
                      <button
                        className="button secondary assistant-inline-action"
                        type="button"
                        onClick={onOpenPlanner}
                      >
                        Mở trang Lập kế hoạch{" "}
                        <ArrowRight size={16} aria-hidden="true" />
                      </button>
                    )}
                    {message.proposal && (
                      <div className="assistant-proposal">
                        <h3>{message.proposal.title}</h3>
                        <dl>
                          {message.proposal.details.map((detail) => (
                            <div key={detail.label}>
                              <dt>{detail.label}</dt>
                              <dd>{detail.value}</dd>
                            </div>
                          ))}
                        </dl>
                        <p className="assistant-caveat">
                          {message.proposal.caveat}
                        </p>
                        {message.proposal.status === "awaiting_approval" ? (
                          <div className="assistant-proposal-actions">
                            <button
                              className="button primary"
                              type="button"
                              onClick={() =>
                                decide(message.id, "demo_acknowledged")
                              }
                            >
                              <Check size={16} aria-hidden="true" /> Xác nhận
                              bản mẫu
                            </button>
                            <button
                              className="button secondary"
                              type="button"
                              onClick={() => decide(message.id, "cancelled")}
                            >
                              <X size={16} aria-hidden="true" /> Hủy
                            </button>
                          </div>
                        ) : (
                          <p className="assistant-result" role="status">
                            {message.proposal.status === "cancelled"
                              ? "Đã hủy bản nháp. Không có thay đổi nào được lưu."
                              : "Đã ghi nhận xác nhận trong bản mẫu. Chưa gửi đến backend và chưa lưu thay đổi."}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      )}
      <div className="assistant-composer-wrap">
        <form
          className="assistant-composer"
          onSubmit={(event) => {
            event.preventDefault()
            send()
          }}
        >
          <label className="sr-only" htmlFor="assistant-input">
            Tin nhắn cho StudyFlow
          </label>
          <textarea
            id="assistant-input"
            ref={composerRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onKeyDown={onComposerKeyDown}
            rows={2}
            placeholder="Hỏi về công việc hoặc kế hoạch học..."
          />
          <div className="assistant-composer-bottom">
            <span>Enter để gửi · Shift + Enter để xuống dòng</span>
            <button
              type="submit"
              aria-label="Gửi tin nhắn"
              disabled={!input.trim()}
            >
              <Send size={18} aria-hidden="true" />
            </button>
          </div>
        </form>
        <p className="assistant-disclaimer">
          Bản mẫu frontend: chưa kết nối AI, chưa đọc dữ liệu cá nhân và không
          lưu thay đổi.
        </p>
      </div>
    </section>
  )
}
