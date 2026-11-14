import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type RefObject,
} from "react"
import { CircleAlert, Info, LoaderCircle, Send, Sparkles } from "lucide-react"
import Button from "../../components/ui/Button"
import type { PlannerFeedback } from "./usePlanner"
import { composerKeyAction } from "./composerKeyboard"

const DEMO_SUGGESTIONS = [
  "tạo công việc Báo cáo hạn 20/11 3 giờ",
  "lập kế hoạch",
  "thêm Ôn giải tích thứ 3 lúc 9h",
]

const API_SUGGESTIONS = [
  "Tạo công việc Báo cáo hạn 20/11 khoảng 3 giờ",
  "Lập kế hoạch cho các công việc chưa xếp",
]

function Feedback({ feedback }: { feedback: PlannerFeedback }) {
  const Icon =
    feedback.kind === "error" || feedback.kind === "clarification"
      ? CircleAlert
      : feedback.kind === "pending"
        ? Sparkles
        : Info
  return (
    <div
      id="planner-command-feedback"
      className={`planner-command-feedback is-${feedback.kind}`}
      role={
        feedback.kind === "error" || feedback.kind === "clarification"
          ? "alert"
          : "status"
      }
    >
      <Icon size={16} aria-hidden="true" />
      <span>{feedback.text}</span>
    </div>
  )
}

export default function PlannerCommandComposer({
  input,
  setInput,
  send,
  busy,
  apiMode,
  feedback,
  textareaRef,
}: {
  input: string
  setInput: (value: string) => void
  send: () => void
  busy: boolean
  apiMode: boolean
  feedback: PlannerFeedback | null
  textareaRef: RefObject<HTMLTextAreaElement | null>
}) {
  const [expanded, setExpanded] = useState(Boolean(input))
  const composing = useRef(false)
  const suggestions = apiMode ? API_SUGGESTIONS : DEMO_SUGGESTIONS

  useEffect(() => {
    if (input) setExpanded(true)
  }, [input])

  const submit = () => {
    if (!input.trim() || busy) return
    send()
  }

  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    const action = composerKeyAction({
      key: event.key,
      shiftKey: event.shiftKey,
      isComposing: composing.current || event.nativeEvent.isComposing,
      busy,
      hasText: Boolean(input.trim()),
    })
    if (action === "submit") {
      event.preventDefault()
      submit()
    } else if (action === "collapse") {
      event.preventDefault()
      setExpanded(false)
      event.currentTarget.blur()
    }
  }

  return (
    <div className={`planner-command${expanded ? " is-expanded" : ""}`}>
      <form
        className="planner-command-form"
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
      >
        <label
          className={expanded ? "planner-command-label" : "sr-only"}
          htmlFor="planner-command-input"
        >
          Điều chỉnh lịch bằng lệnh
        </label>
        <div className="planner-command-input-row">
          <textarea
            id="planner-command-input"
            ref={textareaRef}
            value={input}
            rows={expanded ? 3 : 1}
            placeholder="Bạn muốn điều chỉnh lịch thế nào?"
            aria-describedby={feedback ? "planner-command-feedback" : undefined}
            aria-expanded={expanded}
            disabled={busy}
            onFocus={() => setExpanded(true)}
            onChange={(event) => setInput(event.target.value)}
            onCompositionStart={() => {
              composing.current = true
            }}
            onCompositionEnd={() => {
              composing.current = false
            }}
            onKeyDown={keyDown}
          />
          <Button
            className="primary planner-command-send"
            type="submit"
            aria-label={busy ? "Đang gửi yêu cầu" : "Gửi yêu cầu"}
            disabled={!input.trim() || busy}
          >
            {busy ? (
              <LoaderCircle
                className="planner-command-spinner"
                size={18}
                aria-hidden="true"
              />
            ) : (
              <Send size={18} aria-hidden="true" />
            )}
          </Button>
        </div>
        {expanded && (
          <div className="planner-command-details">
            <div
              className="planner-command-suggestions"
              aria-label="Lệnh gợi ý"
            >
              {suggestions.map((suggestion) => (
                <button
                  type="button"
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion)
                    requestAnimationFrame(() => {
                      textareaRef.current?.focus()
                      textareaRef.current?.setSelectionRange(
                        suggestion.length,
                        suggestion.length,
                      )
                    })
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
            <div className="planner-command-help">
              <span>
                {apiMode
                  ? "Gửi qua máy chủ StudyFlow; mọi thay đổi vẫn cần bạn duyệt."
                  : "Bản demo dùng bộ phân tích lệnh cục bộ, chưa kết nối AI."}
              </span>
              <span className="planner-command-shortcuts">
                <kbd>Enter</kbd> gửi · <kbd>Shift</kbd>+<kbd>Enter</kbd> xuống
                dòng
              </span>
            </div>
          </div>
        )}
      </form>
      {feedback && <Feedback feedback={feedback} />}
    </div>
  )
}
