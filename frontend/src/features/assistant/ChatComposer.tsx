import type {
  ChangeEventHandler,
  ClipboardEventHandler,
  DragEventHandler,
  KeyboardEventHandler,
  RefObject,
} from "react"
import { FileText, Plus, Send, X } from "lucide-react"
import type { ChatAttachment } from "../../types/assistant"

type Props = {
  apiEnabled: boolean
  thinking: boolean
  isDragging: boolean
  setIsDragging: (value: boolean) => void
  handleDrop: DragEventHandler<HTMLFormElement>
  send: () => void
  fileInputRef: RefObject<HTMLInputElement | null>
  handleFileAttach: ChangeEventHandler<HTMLInputElement>
  hydrated: boolean
  attachedFiles: ChatAttachment[]
  removeAttachment: (id: string) => void
  composerRef: RefObject<HTMLTextAreaElement | null>
  input: string
  setComposer: (value: string) => void
  handlePaste: ClipboardEventHandler<HTMLTextAreaElement>
  composition: RefObject<boolean>
  onComposerKeyDown: KeyboardEventHandler<HTMLTextAreaElement>
  storageMode: "loading" | "persistent" | "memory"
  storageError: string
  conversationCount: number
  exportHistory: () => void
}

export default function ChatComposer({
  apiEnabled,
  thinking,
  isDragging,
  setIsDragging,
  handleDrop,
  send,
  fileInputRef,
  handleFileAttach,
  hydrated,
  attachedFiles,
  removeAttachment,
  composerRef,
  input,
  setComposer,
  handlePaste,
  composition,
  onComposerKeyDown,
  storageMode,
  storageError,
  conversationCount,
  exportHistory,
}: Props) {
  return (
    <div className="assistant-composer-wrap">
      <form
        className={`assistant-composer ${isDragging ? "is-dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onSubmit={(event) => {
          event.preventDefault()

          send()
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="sr-only"
          aria-label="Đính kèm ảnh hoặc tệp"
          multiple
          onChange={handleFileAttach}
        />
        <div className="assistant-composer-left">
          <button
            type="button"
            className="assistant-attach-btn"
            aria-label="Đính kèm ảnh hoặc tệp"
            title="Đính kèm ảnh, tệp..."
            onClick={() => fileInputRef.current?.click()}
            disabled={!hydrated || apiEnabled}
          >
            <Plus size={20} aria-hidden="true" />
          </button>
        </div>
        <div className="assistant-composer-body">
          {attachedFiles.length > 0 && (
            <div className="assistant-attached-list">
              {attachedFiles.map((att) => (
                <div key={att.id} className="assistant-attached-chip">
                  {att.type === "image" && att.dataUrl ? (
                    <img
                      src={att.dataUrl}
                      alt={att.name}
                      className="attached-chip-thumb"
                    />
                  ) : (
                    <FileText
                      size={14}
                      className="attached-chip-icon"
                      aria-hidden="true"
                    />
                  )}
                  <span className="attached-chip-name" title={att.name}>
                    {att.name}
                  </span>
                  <span className="attached-chip-size">{att.size}</span>
                  <button
                    type="button"
                    className="attached-chip-remove"
                    aria-label={`Xóa tệp ${att.name}`}
                    onClick={() => removeAttachment(att.id)}
                  >
                    <X size={12} aria-hidden="true" />
                  </button>
                </div>
              ))}
            </div>
          )}
          <label className="sr-only" htmlFor="assistant-input">
            Tin nhắn cho StudyFlow
          </label>
          <textarea
            id="assistant-input"
            ref={composerRef}
            value={input}
            onChange={(event) => setComposer(event.target.value)}
            onPaste={handlePaste}
            onCompositionStart={() => {
              composition.current = true
            }}
            onCompositionEnd={() => {
              composition.current = false
            }}
            onKeyDown={onComposerKeyDown}
            rows={1}
            placeholder={
              attachedFiles.length > 0
                ? "Thêm câu hỏi hoặc ghi chú về tệp đã chọn..."
                : "Hỏi StudyFlow AI..."
            }
            disabled={!hydrated}
          />
          {thinking && (
            <p className="assistant-thinking" role="status">
              Đang xử lý...
            </p>
          )}
        </div>
        <div className="assistant-composer-bottom">
          <button
            type="submit"
            aria-label="Gửi tin nhắn"
            disabled={
              !hydrated ||
              thinking ||
              (!input.trim() && attachedFiles.length === 0)
            }
          >
            <Send size={18} aria-hidden="true" />
          </button>
        </div>
      </form>
      <p className="assistant-disclaimer">
        {apiEnabled
          ? "Lịch sử hội thoại chỉ lưu trên trình duyệt này. Công việc và lịch chỉ được lưu khi bạn xác nhận. Chưa hỗ trợ đính kèm tệp."
          : storageMode === "persistent"
            ? "Lịch sử lưu trên trình duyệt này, chưa đồng bộ với tài khoản. Trợ lý vẫn là bản mẫu, không ghi dữ liệu học tập lên máy chủ."
            : storageMode === "memory"
              ? "Chỉ lưu tạm trong phiên này. Trợ lý vẫn là bản mẫu, chưa kết nối AI."
              : "Đang tải lịch sử hội thoại..."}
      </p>
      {storageError && (
        <div className="history-storage-error" role="alert">
          <p>{storageError}</p>
          {conversationCount > 0 && (
            <button
              className="button text-button"
              type="button"
              onClick={exportHistory}
            >
              Xuất lịch sử JSON
            </button>
          )}
        </div>
      )}
    </div>
  )
}
