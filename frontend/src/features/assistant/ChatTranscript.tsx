import type { ReactNode, RefObject } from "react"
import { ArrowRight, Check, FileText, Sparkles, X } from "lucide-react"
import type {
  ApprovalStatus,
  AssistantScenario,
  ChatMessage,
} from "../../types/assistant"

type Props = {
  messages: ChatMessage[]
  transcriptRef: RefObject<HTMLDivElement | null>
  shouldScroll: RefObject<boolean>
  activeClarification: string | null | undefined
  clarificationForm: (scenario: AssistantScenario) => ReactNode
  onOpenPlanner: () => void
  decide: (id: string, status: ApprovalStatus) => void
}

export default function ChatTranscript({
  messages,
  transcriptRef,
  shouldScroll,
  activeClarification,
  clarificationForm,
  onOpenPlanner,
  decide,
}: Props) {
  return (
    <div
      className="assistant-transcript"
      ref={transcriptRef}
      onScroll={(event) => {
        const element = event.currentTarget

        shouldScroll.current =
          element.scrollHeight - element.scrollTop - element.clientHeight < 96
      }}
      role="log"
      aria-label="Cuộc trò chuyện"
      aria-live="polite"
    >
      <div className="assistant-thread">
        {messages.map((entry) => (
          <article
            key={entry.id}
            className={`assistant-message ${
              entry.role === "user" ? "from-user" : "from-assistant"
            }`}
          >
            {entry.role === "assistant" && (
              <div className="assistant-avatar" aria-hidden="true">
                <Sparkles size={16} />
              </div>
            )}
            <div className="assistant-message-body">
              <span className="assistant-sender">
                {entry.role === "user" ? "Bạn" : "StudyFlow · Bản mẫu"}
              </span>
              <div className="assistant-bubble">
                {entry.category !== "MESSAGE" && (
                  <span
                    className={`assistant-state assistant-state-${entry.category.toLowerCase()}`}
                  >
                    {entry.category === "CLARIFICATION"
                      ? "Cần thêm thông tin"
                      : entry.category === "PROPOSAL"
                        ? "Bản nháp cần xem lại"
                        : entry.category === "UNSUPPORTED"
                          ? "Chưa hỗ trợ"
                          : "Có lỗi"}
                  </span>
                )}
                {entry.attachments && entry.attachments.length > 0 && (
                  <div className="assistant-message-attachments">
                    {entry.attachments.map((att) => (
                      <div key={att.id} className="assistant-attachment-card">
                        {att.type === "image" && att.dataUrl ? (
                          <img
                            src={att.dataUrl}
                            alt={att.name}
                            className="assistant-attachment-img-preview"
                          />
                        ) : (
                          <>
                            <FileText size={16} aria-hidden="true" />
                            <span
                              className="assistant-attachment-name"
                              title={att.name}
                            >
                              {att.name}
                            </span>
                            <span className="assistant-attachment-size">
                              {att.size}
                            </span>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                <p>{entry.text}</p>
                {entry.category === "CLARIFICATION" &&
                  entry.scenario &&
                  entry.id === activeClarification &&
                  clarificationForm(entry.scenario)}
                {entry.scenario === "view" && (
                  <button
                    className="button secondary assistant-inline-action"
                    type="button"
                    onClick={onOpenPlanner}
                  >
                    Mở trang Lập kế hoạch{" "}
                    <ArrowRight size={16} aria-hidden="true" />
                  </button>
                )}
                {entry.proposal && (
                  <div className="assistant-proposal">
                    <h3>{entry.proposal.title}</h3>
                    <dl>
                      {entry.proposal.details.map((detail) => (
                        <div key={detail.label}>
                          <dt>{detail.label}</dt>
                          <dd>{detail.value}</dd>
                        </div>
                      ))}
                    </dl>
                    <p className="assistant-caveat">{entry.proposal.caveat}</p>
                    {entry.proposal.status === "awaiting_approval" ? (
                      <div className="assistant-proposal-actions">
                        <button
                          className="button primary"
                          type="button"
                          onClick={() => decide(entry.id, "demo_acknowledged")}
                        >
                          <Check size={16} aria-hidden="true" /> Xác nhận bản
                          mẫu
                        </button>
                        <button
                          className="button secondary"
                          type="button"
                          onClick={() => decide(entry.id, "cancelled")}
                        >
                          <X size={16} aria-hidden="true" /> Hủy
                        </button>
                      </div>
                    ) : entry.proposal.status === "review_required" ? (
                      <div className="assistant-review">
                        <p role="status">
                          Bản nháp được khôi phục sau khi tải lại. Hãy xem lại
                          trước khi xác nhận trong bản mẫu; chưa có thao tác nào
                          được thực hiện.
                        </p>
                        <button
                          className="button secondary"
                          type="button"
                          onClick={() => decide(entry.id, "awaiting_approval")}
                        >
                          Xem lại bản nháp
                        </button>
                      </div>
                    ) : (
                      <p className="assistant-result" role="status">
                        {entry.proposal.status === "cancelled"
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
  )
}
