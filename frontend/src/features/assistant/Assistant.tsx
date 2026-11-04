import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react"
import {
  ArrowRight,
  Check,
  History,
  MoreHorizontal,
  Plus,
  Search,
  Send,
  Sparkles,
  Trash2,
  X,
} from "lucide-react"
import { getAssistantReply } from "./assistantService"
import type {
  ActionProposal,
  ChatMessage,
  AssistantScenario,
} from "../../types/assistant"
import {
  appendMessages,
  clearConversations,
  createConversation,
  emptyDraft,
  historyGroup,
  loadHistory,
  openHistoryDatabase,
  putActiveId,
  putConversation,
  removeConversation,
  setProposalStatus,
  type Conversation,
  type Draft,
} from "./conversationHistory"

type ConfirmAction = {
  kind: "delete"
  id: string
  title: string
} | {
  kind: "clear"
}
const groupNames = ["Hôm nay", "Hôm qua", "7 ngày gần đây", "Cũ hơn"] as const
const nowIso = () => new Date().toISOString()
const message = (item: Omit<ChatMessage, "id" | "timestamp">): ChatMessage => ({
  ...item,
  id: crypto.randomUUID(),
  timestamp: nowIso(),
})

export default function Assistant({
  onOpenPlanner,
}: {
  onOpenPlanner: () => void
}) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [emptyInput, setEmptyInput] = useState("")
  const [hydrated, setHydrated] = useState(false)
  const [storageMode, setStorageMode] =
    useState<"loading" | "persistent" | "memory">("loading")
  const [storageError, setStorageError] = useState("")
  const [historyOpen, setHistoryOpen] = useState(false)
  const [historySearch, setHistorySearch] = useState("")
  const [menuId, setMenuId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState("")
  const [renameError, setRenameError] = useState("")
  const [confirm, setConfirm] = useState<ConfirmAction | null>(null)
  const [mobile, setMobile] = useState(
    () => window.matchMedia("(max-width: 800px)").matches,
  )
  const dbRef = useRef<IDBDatabase | null>(null)
  const writeQueue = useRef<Promise<void>>(Promise.resolve())
  const storageEnabled = useRef(false)
  const savedSnapshot = useRef(new Map<string, Conversation>())
  const savedActiveId = useRef<string | null>(null)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)
  const historyTriggerRef = useRef<HTMLButtonElement>(null)
  const historySearchRef = useRef<HTMLInputElement>(null)
  const drawerRef = useRef<HTMLDialogElement>(null)
  const confirmRef = useRef<HTMLDialogElement>(null)
  const actionFocusRef = useRef<HTMLElement | null>(null)
  const composition = useRef(false)
  const submitting = useRef(false)
  const shouldScroll = useRef(true)
  const active =
    conversations.find((conversation) => conversation.id === activeId) ?? null
  const messages = active?.messages ?? []
  const input = active?.draftInput ?? emptyInput
  const draft = active?.workflow.draft ?? emptyDraft()
  const formError = active?.workflow.formError ?? ""
  const activeClarification =
    messages.at(-1)?.category === "CLARIFICATION" ? messages.at(-1)?.id : null

  useEffect(() => {
    const media = window.matchMedia("(max-width: 800px)")
    const update = () => setMobile(media.matches)
    media.addEventListener("change", update)
    return () => media.removeEventListener("change", update)
  }, [])

  useEffect(() => {
    let cancelled = false
    // Development-only failure switch for the storage fallback browser check.
    const opening =
      import.meta.env.DEV &&
      new URLSearchParams(window.location.search).get("historyStorage") ===
        "unavailable"
        ? Promise.reject(new Error("Simulated IndexedDB unavailable"))
        : openHistoryDatabase()
    opening
      .then(async (db) => {
        const loaded = await loadHistory(db)
        if (cancelled) {
          db.close()
          return
        }
        dbRef.current = db
        savedSnapshot.current = new Map(
          loaded.conversations.map((item) => [item.id, item]),
        )
        const selected = loaded.conversations.some(
          (item) => item.id === loaded.activeId,
        )
          ? loaded.activeId
          : null
        savedActiveId.current = selected
        setConversations(loaded.conversations)
        setActiveId(selected)
        storageEnabled.current = true
        setStorageMode("persistent")
        if (loaded.skipped)
          setStorageError(
            `Đã bỏ qua ${loaded.skipped} cuộc trò chuyện không đọc được. Các cuộc trò chuyện khác vẫn an toàn.`,
          )
        setHydrated(true)
      })
      .catch(() => {
        if (cancelled) return
        storageEnabled.current = false
        setStorageMode("memory")
        setStorageError(
          "Không thể mở IndexedDB. Cuộc trò chuyện chỉ được giữ trong phiên này và sẽ mất khi tải lại trang.",
        )
        setHydrated(true)
      })
    return () => {
      cancelled = true
      dbRef.current?.close()
    }
  }, [])

  function reportWriteFailure(error: unknown) {
    storageEnabled.current = false
    setStorageMode("memory")
    const quota =
      error instanceof DOMException && error.name === "QuotaExceededError"
    setStorageError(
      quota
        ? "Bộ nhớ trình duyệt đã đầy. Thay đổi mới chỉ còn trong phiên này. Bạn có thể xuất lịch sử hoặc xóa bớt cuộc trò chuyện."
        : "Không thể lưu lịch sử vào trình duyệt. Thay đổi mới chỉ còn trong phiên này; hãy xuất lịch sử trước khi tải lại trang.",
    )
  }
  function enqueue(
    operation: (db: IDBDatabase) => Promise<void>,
    force = false,
  ) {
    const db = dbRef.current
    if (!db || (!storageEnabled.current && !force)) return
    writeQueue.current = writeQueue.current
      .then(() => operation(db))
      .catch(reportWriteFailure)
  }
  useEffect(() => {
    if (!hydrated) return
    const next = new Map(conversations.map((item) => [item.id, item]))
    for (const [id, item] of next)
      if (savedSnapshot.current.get(id) !== item)
        enqueue((db) => putConversation(db, item))
    for (const id of savedSnapshot.current.keys())
      if (!next.has(id)) enqueue((db) => removeConversation(db, id))
    savedSnapshot.current = next
  }, [conversations, hydrated])
  useEffect(() => {
    if (!hydrated || savedActiveId.current === activeId) return
    savedActiveId.current = activeId
    enqueue((db) => putActiveId(db, activeId))
  }, [activeId, hydrated])
  useEffect(() => {
    const composer = composerRef.current
    if (!composer) return
    composer.style.height = "auto"
    composer.style.height = `${Math.min(composer.scrollHeight, 180)}px`
  }, [input, activeId])
  useEffect(() => {
    if (shouldScroll.current)
      transcriptRef.current?.scrollTo({
        top: transcriptRef.current.scrollHeight,
        behavior: "smooth",
      })
  }, [activeId, messages])
  useEffect(() => {
    if (!historyOpen) return
    if (mobile) {
      const dialog = drawerRef.current
      if (dialog && !dialog.open) dialog.showModal()
      historySearchRef.current?.focus()
      return () => {
        if (dialog?.open) dialog.close()
        historyTriggerRef.current?.focus()
      }
    }
    historySearchRef.current?.focus()
  }, [historyOpen, mobile])
  useEffect(() => {
    const dialog = confirmRef.current
    if (!confirm || !dialog) return
    dialog.showModal()
    return () => {
      if (dialog.open) dialog.close()
      if (actionFocusRef.current?.isConnected) actionFocusRef.current.focus()
      else historySearchRef.current?.focus()
    }
  }, [confirm])

  function patchActive(update: (conversation: Conversation) => Conversation) {
    if (!activeId) return
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === activeId ? update(conversation) : conversation,
      ),
    )
  }
  function setComposer(value: string) {
    if (activeId)
      patchActive((conversation) => ({ ...conversation, draftInput: value }))
    else setEmptyInput(value)
  }
  function send() {
    const text = input.trim()
    if (!hydrated || !text || composition.current || submitting.current) return
    submitting.current = true
    requestAnimationFrame(() => {
      submitting.current = false
    })
    const user = message({ role: "user", category: "MESSAGE", text })
    const assistant = message(getAssistantReply(text))
    const starting = active ?? createConversation(text)
    const updated = appendMessages(starting, [user, assistant])
    shouldScroll.current = true
    setConversations((current) =>
      activeId
        ? current.map((item) => (item.id === activeId ? updated : item))
        : [...current, updated],
    )
    if (!activeId) setActiveId(updated.id)
    setEmptyInput("")
  }
  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing &&
      !composition.current
    ) {
      event.preventDefault()
      send()
    }
  }
  function setDraftField(name: keyof Draft, value: string) {
    patchActive((conversation) => ({
      ...conversation,
      workflow: {
        ...conversation.workflow,
        draft: { ...conversation.workflow.draft, [name]: value },
        formError: "",
      },
    }))
  }
  function submitDraft(
    event: FormEvent<HTMLFormElement>,
    scenario: AssistantScenario,
  ) {
    event.preventDefault()
    if (!active) return
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
      patchActive((conversation) => ({
        ...conversation,
        workflow: {
          ...conversation.workflow,
          formError:
            "Vui lòng điền tất cả thông tin cần thiết trước khi xem bản nháp.",
        },
      }))
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
    const proposed = message({
      role: "assistant",
      category: "PROPOSAL",
      scenario,
      intent: proposal.intent,
      validation: "valid_demo_draft",
      text: "Kiểm tra thông tin bạn đã nhập. Xác nhận ở đây chỉ ghi nhận thao tác trong bản mẫu.",
      proposal,
    })
    patchActive((conversation) => appendMessages(conversation, [proposed]))
  }
  function decide(id: string, status: ActionProposal["status"]) {
    patchActive((conversation) => setProposalStatus(conversation, id, status))
  }
  function newChat() {
    setActiveId(null)
    setEmptyInput("")
    shouldScroll.current = true
    requestAnimationFrame(() => composerRef.current?.focus())
  }
  function selectConversation(id: string) {
    setActiveId(id)
    setMenuId(null)
    setEditingId(null)
    shouldScroll.current = true
    if (mobile) setHistoryOpen(false)
    requestAnimationFrame(() =>
      document.querySelector<HTMLElement>("[data-assistant-heading]")?.focus(),
    )
  }
  function closeHistory() {
    setHistoryOpen(false)
    setMenuId(null)
    requestAnimationFrame(() => historyTriggerRef.current?.focus())
  }
  function rename(id: string) {
    const title = renameValue.trim().replace(/\s+/gu, " ")
    if (!title) {
      setRenameError("Tên cuộc trò chuyện không được để trống.")
      return
    }
    if (title.length > 60) {
      setRenameError("Tên tối đa 60 ký tự.")
      return
    }
    setConversations((current) =>
      current.map((item) =>
        item.id === id
          ? { ...item, title, manuallyRenamed: true, updatedAt: nowIso() }
          : item,
      ),
    )
    setEditingId(null)
    setRenameError("")
  }
  function deleteSelected() {
    if (!confirm) return
    if (confirm.kind === "clear") {
      savedSnapshot.current = new Map()
      savedActiveId.current = null
      enqueue(clearConversations, true)
      setConversations([])
      setActiveId(null)
      setEmptyInput("")
    } else {
      setConversations((current) =>
        current.filter((item) => item.id !== confirm.id),
      )
      if (activeId === confirm.id) {
        setActiveId(null)
        setEmptyInput("")
      }
    }
    setConfirm(null)
    setMenuId(null)
  }
  function exportHistory() {
    const data = JSON.stringify(
      { schemaVersion: 1, exportedAt: nowIso(), conversations },
      null,
      2,
    )
    const url = URL.createObjectURL(
      new Blob([data], { type: "application/json" }),
    )
    const link = document.createElement("a")
    link.href = url
    link.download = "studyflow-conversations.json"
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
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
          onChange={(event) => setDraftField(name, event.target.value)}
          onInput={(event) => setDraftField(name, event.currentTarget.value)}
        />
      </label>
    )
  }
  function clarificationForm(scenario: AssistantScenario) {
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
  const sorted = [...conversations].sort((a, b) =>
    b.updatedAt.localeCompare(a.updatedAt),
  )
  const searched = sorted.filter((item) =>
    `${item.title} ${item.messages.map((entry) => entry.text).join(" ")}`
      .toLocaleLowerCase("vi")
      .includes(historySearch.trim().toLocaleLowerCase("vi")),
  )
  const historyContent = (
    <>
      <div className="history-header">
        <h2>Lịch sử hội thoại</h2>
        <button
          className="button icon-button"
          type="button"
          aria-label="Đóng lịch sử"
          onClick={closeHistory}
        >
          <X size={18} aria-hidden="true" />
        </button>
      </div>
      <label className="history-search">
        <Search size={16} aria-hidden="true" />
        <input
          ref={historySearchRef}
          value={historySearch}
          onChange={(event) => setHistorySearch(event.target.value)}
          placeholder="Tìm cuộc trò chuyện..."
          aria-label="Tìm cuộc trò chuyện"
        />
      </label>
      <div className="history-list">
        {conversations.length === 0 ? (
          <p className="history-empty">
            Chưa có cuộc trò chuyện nào. Hãy bắt đầu bằng cách đặt câu hỏi cho
            StudyFlow AI.
          </p>
        ) : searched.length === 0 ? (
          <p className="history-empty">
            Không tìm thấy cuộc trò chuyện phù hợp.
          </p>
        ) : (
          groupNames.map((group) => {
            const items = searched.filter(
              (item) => historyGroup(item.updatedAt) === group,
            )
            return items.length ? (
              <section className="history-group" key={group} aria-label={group}>
                <h3>{group}</h3>
                {items.map((item) => (
                  <div
                    className={`history-item ${
                      item.id === activeId ? "selected" : ""
                    }`}
                    key={item.id}
                  >
                    {editingId === item.id ? (
                      <form
                        className="history-rename"
                        onSubmit={(event) => {
                          event.preventDefault()
                          rename(item.id)
                        }}
                        onKeyDown={(event) => {
                          if (event.key === "Escape") {
                            event.preventDefault()
                            setEditingId(null)
                            setRenameError("")
                          }
                        }}
                      >
                        <input
                          autoFocus
                          aria-label="Tên cuộc trò chuyện"
                          value={renameValue}
                          maxLength={61}
                          onChange={(event) =>
                            setRenameValue(event.target.value)
                          }
                        />
                        <button
                          className="button icon-button"
                          type="submit"
                          aria-label="Lưu tên"
                        >
                          <Check size={16} />
                        </button>
                        {renameError && (
                          <small role="alert">{renameError}</small>
                        )}
                      </form>
                    ) : (
                      <button
                        className="history-select"
                        type="button"
                        aria-current={item.id === activeId ? "true" : undefined}
                        onClick={() => selectConversation(item.id)}
                      >
                        <strong>{item.title}</strong>
                        <span>{item.messages.at(-1)?.text ?? ""}</span>
                        <time dateTime={item.updatedAt}>
                          {new Date(item.updatedAt).toLocaleDateString(
                            "vi-VN",
                            { day: "numeric", month: "short" },
                          )}
                        </time>
                      </button>
                    )}
                    <div className="history-actions">
                      <button
                        className="button icon-button"
                        type="button"
                        aria-label={`Tùy chọn cho ${item.title}`}
                        aria-expanded={menuId === item.id}
                        onClick={() =>
                          setMenuId(menuId === item.id ? null : item.id)
                        }
                      >
                        <MoreHorizontal size={18} aria-hidden="true" />
                      </button>
                      {menuId === item.id && (
                        <div className="history-menu">
                          <button
                            className="button"
                            type="button"
                            onClick={() => {
                              setEditingId(item.id)
                              setRenameValue(item.title)
                              setRenameError("")
                              setMenuId(null)
                            }}
                          >
                            Đổi tên
                          </button>
                          <button
                            className="button history-danger"
                            type="button"
                            onClick={(event) => {
                              actionFocusRef.current = event.currentTarget
                              setConfirm({
                                kind: "delete",
                                id: item.id,
                                title: item.title,
                              })
                              setMenuId(null)
                            }}
                          >
                            Xóa
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </section>
            ) : null
          })
        )}
      </div>
      <div className="history-footer">
        <p>
          Lịch sử được lưu trên trình duyệt này, chưa đồng bộ với tài khoản.
        </p>
        {conversations.length > 0 && (
          <div>
            <button
              className="button text-button"
              type="button"
              onClick={exportHistory}
            >
              Xuất JSON
            </button>
            <button
              className="button history-danger"
              type="button"
              onClick={(event) => {
                actionFocusRef.current = event.currentTarget
                setConfirm({ kind: "clear" })
              }}
            >
              <Trash2 size={15} aria-hidden="true" /> Xóa toàn bộ lịch sử
            </button>
          </div>
        )}
      </div>
    </>
  )

  return (
    <section
      className={`assistant-shell ${
        messages.length ? "has-messages" : "is-empty"
      } ${historyOpen && !mobile ? "history-visible" : ""}`}
      aria-label="Trợ lý AI bản mẫu"
    >
      <div className="assistant-main">
        <div className="assistant-topline">
          {messages.length > 0 && (
            <h1
              className="assistant-thread-heading"
              data-assistant-heading
              tabIndex={-1}
            >
              {active?.title}
            </h1>
          )}
          <div className="assistant-toolbar">
            <button
              className="button secondary"
              type="button"
              aria-label="Cuộc trò chuyện mới"
              onClick={newChat}
              disabled={!hydrated}
            >
              <Plus size={17} aria-hidden="true" />
              <span>Cuộc trò chuyện mới</span>
            </button>
            <button
              className="button secondary"
              type="button"
              ref={historyTriggerRef}
              aria-label="Lịch sử hội thoại"
              aria-expanded={historyOpen}
              onClick={() =>
                historyOpen ? closeHistory() : setHistoryOpen(true)
              }
              disabled={!hydrated}
            >
              <History size={18} aria-hidden="true" />
              <span>Lịch sử</span>
            </button>
          </div>
        </div>
        {messages.length === 0 ? (
          <div className="assistant-welcome">
            <h1 data-assistant-heading tabIndex={-1}>
              Hôm nay bạn muốn làm gì?
            </h1>
          </div>
        ) : (
          <div
            className="assistant-transcript"
            ref={transcriptRef}
            onScroll={(event) => {
              const element = event.currentTarget
              shouldScroll.current =
                element.scrollHeight -
                  element.scrollTop -
                  element.clientHeight <
                96
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
                          <p className="assistant-caveat">
                            {entry.proposal.caveat}
                          </p>
                          {entry.proposal.status === "awaiting_approval" ? (
                            <div className="assistant-proposal-actions">
                              <button
                                className="button primary"
                                type="button"
                                onClick={() =>
                                  decide(entry.id, "demo_acknowledged")
                                }
                              >
                                <Check size={16} aria-hidden="true" /> Xác nhận
                                bản mẫu
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
                                Bản nháp được khôi phục sau khi tải lại. Hãy xem
                                lại trước khi xác nhận trong bản mẫu; chưa có
                                thao tác nào được thực hiện.
                              </p>
                              <button
                                className="button secondary"
                                type="button"
                                onClick={() =>
                                  decide(entry.id, "awaiting_approval")
                                }
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
              onChange={(event) => setComposer(event.target.value)}
              onCompositionStart={() => {
                composition.current = true
              }}
              onCompositionEnd={() => {
                composition.current = false
              }}
              onKeyDown={onComposerKeyDown}
              rows={1}
              placeholder="Hỏi StudyFlow AI..."
              disabled={!hydrated}
            />
            <div className="assistant-composer-bottom">
              <button
                type="submit"
                aria-label="Gửi tin nhắn"
                disabled={!hydrated || !input.trim()}
              >
                <Send size={18} aria-hidden="true" />
              </button>
            </div>
          </form>
          <p className="assistant-disclaimer">
            {storageMode === "persistent"
              ? "Lịch sử lưu trên trình duyệt này, chưa đồng bộ với tài khoản. Trợ lý vẫn là bản mẫu, không ghi dữ liệu học tập lên máy chủ."
              : storageMode === "memory"
                ? "Chỉ lưu tạm trong phiên này. Trợ lý vẫn là bản mẫu, chưa kết nối AI."
                : "Đang tải lịch sử hội thoại..."}
          </p>
          {storageError && (
            <div className="history-storage-error" role="alert">
              <p>{storageError}</p>
              {conversations.length > 0 && (
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
      </div>
      {historyOpen && !mobile && (
        <aside
          className="assistant-history-panel"
          aria-label="Lịch sử hội thoại"
        >
          {historyContent}
        </aside>
      )}
      {historyOpen && mobile && (
        <dialog
          ref={drawerRef}
          className="assistant-history-drawer"
          aria-label="Lịch sử hội thoại"
          onCancel={(event) => {
            event.preventDefault()
            closeHistory()
          }}
          onClick={(event) => {
            if (event.target === event.currentTarget) closeHistory()
          }}
        >
          <div className="assistant-history-panel">{historyContent}</div>
        </dialog>
      )}
      {confirm && (
        <dialog
          ref={confirmRef}
          className="history-confirm"
          aria-labelledby="history-confirm-title"
          onCancel={(event) => {
            event.preventDefault()
            setConfirm(null)
          }}
        >
          <h2 id="history-confirm-title">
            {confirm.kind === "clear"
              ? "Xóa toàn bộ lịch sử?"
              : "Xóa cuộc trò chuyện?"}
          </h2>
          <p>
            {confirm.kind === "clear"
              ? "Tất cả cuộc trò chuyện trên trình duyệt này sẽ bị xóa vĩnh viễn."
              : `“${confirm.title}” sẽ bị xóa vĩnh viễn khỏi trình duyệt này.`}
          </p>
          <div>
            <button
              className="button secondary"
              type="button"
              onClick={() => setConfirm(null)}
            >
              Giữ lại
            </button>
            <button
              className="button history-delete-confirm"
              type="button"
              onClick={deleteSelected}
            >
              {confirm.kind === "clear" ? "Xóa toàn bộ" : "Xóa cuộc trò chuyện"}
            </button>
          </div>
        </dialog>
      )}
    </section>
  )
}
