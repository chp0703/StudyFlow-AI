import ChatComposer from "./ChatComposer"
import ChatTranscript from "./ChatTranscript"
import ConversationSidebar, { type ConfirmAction } from "./ConversationSidebar"
import { useConversationHistory } from "./useConversationHistory"
import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type ClipboardEvent,
  type DragEvent,
  type FormEvent,
  type KeyboardEvent,
} from "react"

import gsap from "gsap"

import { useGSAP } from "@gsap/react"

import { ArrowRight, History, ArrowLeft, Plus, X } from "lucide-react"

import { getAssistantReply } from "./assistantService"

import { api } from "../../api"

import { apiEnabled } from "../../api/config"

import { errorToMessage, replyToMessage } from "./apiAssistant"

import type {
  ActionProposal,
  ChatAttachment,
  ChatMessage,
  AssistantScenario,
} from "../../types/assistant"

import {
  appendMessages,
  createConversation,
  emptyDraft,
  setProposal as replaceProposal,
  setProposalStatus,
  type Draft,
} from "./conversationHistory"

const nowIso = () => new Date().toISOString()

const message = (item: Omit<ChatMessage, "id" | "timestamp">): ChatMessage => ({
  ...item,

  id: crypto.randomUUID(),

  timestamp: nowIso(),
})

export default function Assistant({
  onOpenPlanner,

  onServerChange,

  // Called after the server may have changed tasks or the schedule (API mode).
}: {
  onOpenPlanner: () => void

  onServerChange?: () => void
}) {
  const [thinking, setThinking] = useState(false)
  const {
    conversations,
    setConversations,
    activeId,
    setActiveId,
    hydrated,
    storageMode,
    storageError,
    clearHistory,
    patchActive,
  } = useConversationHistory()

  const [emptyInput, setEmptyInput] = useState("")

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

  const composerRef = useRef<HTMLTextAreaElement>(null)

  const transcriptRef = useRef<HTMLDivElement>(null)

  const historyPanelRef = useRef<HTMLElement>(null)

  const welcomeRef = useRef<HTMLHeadingElement>(null)

  const [panelShown, setPanelShown] = useState(false)

  const seenMessages = useRef({ first: "", count: 0 })

  const historyTriggerRef = useRef<HTMLButtonElement>(null)

  const historySearchRef = useRef<HTMLInputElement>(null)

  const drawerRef = useRef<HTMLDialogElement>(null)

  const confirmRef = useRef<HTMLDialogElement>(null)

  const actionFocusRef = useRef<HTMLElement | null>(null)

  const composition = useRef(false)

  const submitting = useRef(false)

  const shouldScroll = useRef(true)

  const [attachedFiles, setAttachedFiles] = useState<ChatAttachment[]>([])

  const [isDragging, setIsDragging] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  const processFiles = (fileList: File[]) => {
    if (!fileList.length || apiEnabled) return

    fileList.forEach((file) => {
      const isImg = file.type.startsWith("image/")
      const sizeStr =
        file.size > 1024 * 1024
          ? `${(file.size / (1024 * 1024)).toFixed(1)} MB`
          : `${Math.max(1, Math.round(file.size / 1024))} KB`

      setAttachedFiles((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          name: file.name,
          size: sizeStr,
          type: isImg ? "image" : "file",
        },
      ])
    })
  }

  const handleFileAttach = (e: ChangeEvent<HTMLInputElement>) => {
    processFiles(Array.from(e.target.files || []))
    e.target.value = ""
  }

  const handlePaste = (e: ClipboardEvent<HTMLTextAreaElement>) => {
    const items = Array.from(e.clipboardData.files || [])
    if (items.length > 0) {
      processFiles(items)
    }
  }

  const handleDrop = (e: DragEvent<HTMLFormElement>) => {
    e.preventDefault()
    setIsDragging(false)
    const items = Array.from(e.dataTransfer.files || [])
    if (items.length > 0) {
      processFiles(items)
    }
  }

  const removeAttachment = (id: string) => {
    setAttachedFiles((prev) => prev.filter((item) => item.id !== id))
  }

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

  // Tiêu đề chào hiện dần từ trái, sau đó dải màu chuyển động chậm.

  useGSAP(
    () => {
      const heading = welcomeRef.current

      if (!heading) return

      gsap.fromTo(
        heading,

        { clipPath: "inset(0 100% 0 0)", y: 18, letterSpacing: "0.04em" },

        {
          clipPath: "inset(0 0% 0 0)",

          y: 0,

          letterSpacing: "-0.045em",

          duration: 1,

          ease: "power3.out",

          clearProps: "clipPath,transform,letterSpacing",
        },
      )

      gsap.set(heading, { backgroundSize: "200% 100%" })

      gsap.fromTo(
        heading,

        { backgroundPosition: "0% 50%" },

        {
          backgroundPosition: "100% 50%",

          duration: 5,

          ease: "sine.inOut",

          repeat: -1,

          yoyo: true,
        },
      )
    },

    { dependencies: [messages.length === 0], revertOnUpdate: true },
  )

  // Tin nhắn mới trượt lên; đổi hội thoại không chạy hiệu ứng cho toàn bộ lịch sử tin nhắn.

  useGSAP(
    () => {
      const seen = seenMessages.current

      const added = messages.length - seen.count

      if (
        added > 0 &&
        (messages[0]?.id === seen.first || (seen.count === 0 && added <= 2))
      ) {
        const items = gsap.utils.toArray<HTMLElement>(".assistant-message")

        gsap.from(items.slice(-added), {
          y: 14,

          opacity: 0,

          duration: 0.4,

          ease: "power2.out",

          stagger: 0.08,

          clearProps: "transform,opacity",
        })
      }

      seenMessages.current = {
        first: messages[0]?.id ?? "",

        count: messages.length,
      }
    },

    { scope: transcriptRef, dependencies: [messages] },
  )

  // Khung lịch sử desktop mở rộng từ mép phải và thu lại để vùng chat đổi chiều rộng mượt hơn.

  useGSAP(
    () => {
      if (mobile) return setPanelShown(false)

      const panel = historyPanelRef.current

      if (!historyOpen && !panelShown) return

      // Giữ nội dung đủ chiều rộng trong lúc khung chứa đang thay đổi chiều rộng bằng hiệu ứng.

      const fixed = () => gsap.set(panel?.children ?? [], { minWidth: 304 })

      const release = "width,minWidth,opacity,overflow"

      if (historyOpen) {
        setPanelShown(true)

        fixed()

        gsap.fromTo(
          panel,

          { width: 0, minWidth: 0, opacity: 0, overflow: "hidden" },

          {
            width: 304,

            minWidth: 304,

            opacity: 1,

            duration: 0.4,

            ease: "power3.out",

            clearProps: release,

            onComplete: () => {
              gsap.set(panel?.children ?? [], { clearProps: "minWidth" })
            },
          },
        )
      } else {
        fixed()

        gsap.to(panel, {
          width: 0,

          minWidth: 0,

          opacity: 0,

          overflow: "hidden",

          duration: 0.35,

          ease: "power3.inOut",

          onComplete: () => setPanelShown(false),
        })
      }
    },

    { dependencies: [historyOpen, mobile] },
  )

  // Khi mở hội thoại khác, cho tin nhắn hiện dần thay vì đổi tức thì.

  const prevActiveId = useRef(activeId)

  useGSAP(
    () => {
      const switched =
        prevActiveId.current && activeId && prevActiveId.current !== activeId

      prevActiveId.current = activeId

      if (switched) {
        gsap.from(".assistant-thread", {
          opacity: 0,

          y: 16,

          duration: 0.45,

          ease: "power2.out",

          clearProps: "transform,opacity",
        })
      }
    },

    { scope: transcriptRef, dependencies: [activeId] },
  )

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

  function setComposer(value: string) {
    if (activeId)
      patchActive((conversation) => ({ ...conversation, draftInput: value }))
    else setEmptyInput(value)
  }

  function send() {
    const text = input.trim()

    if (
      !hydrated ||
      (!text && attachedFiles.length === 0) ||
      composition.current ||
      submitting.current
    )
      return

    submitting.current = true

    requestAnimationFrame(() => {
      submitting.current = false
    })

    if (apiEnabled) {
      if (text && !thinking) void sendApi(text)

      return
    }

    const currentAttachments = [...attachedFiles]

    setAttachedFiles([])

    const user = message({
      role: "user",
      category: "MESSAGE",
      text:
        text ||
        (currentAttachments.length > 0
          ? `Đã chọn ${currentAttachments.length} tệp để hiển thị (chưa tải lên).`
          : ""),
      ...(currentAttachments.length > 0
        ? { attachments: currentAttachments }
        : {}),
    })

    const assistant = message(getAssistantReply(text, currentAttachments))

    const starting =
      active ??
      createConversation(
        text ||
          (currentAttachments[0]
            ? `Tệp: ${currentAttachments[0].name}`
            : "Cuộc trò chuyện mới"),
      )

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
        ? !draft.title.trim() || !draft.deadline || !draft.duration
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

                { label: "Thời gian học", value: draft.availability.trim() },
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

  // API mode: the message goes to the server; its reply (question, approval card, result or error) is the answer.

  const attempt = useRef<{
    key: string
    text: string
    id: string
  } | null>(null)

  function appendAssistant(
    conversationId: string,
    item: ReturnType<typeof message>,
  ) {
    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === conversationId
          ? appendMessages(conversation, [item])
          : conversation,
      ),
    )

    shouldScroll.current = true
  }

  async function sendApi(text: string) {
    const user = message({ role: "user", category: "MESSAGE", text })

    const starting = active ?? createConversation(text)

    const updated = appendMessages(starting, [user])

    shouldScroll.current = true

    setConversations((current) =>
      activeId
        ? current.map((item) => (item.id === activeId ? updated : item))
        : [...current, updated],
    )

    if (!activeId) setActiveId(updated.id)

    setEmptyInput("")

    setThinking(true)

    // Sending the same text again after a failure reuses the key, so a lost response never runs twice.

    const same =
      attempt.current?.id === starting.id && attempt.current.text === text

    const key = same ? attempt.current!.key : crypto.randomUUID()

    attempt.current = { key, text, id: starting.id }

    try {
      const reply = await api.sendMessage(starting.id, text, key)

      attempt.current = null

      appendAssistant(starting.id, message(replyToMessage(reply)))

      if (reply.state === "SUCCEEDED") onServerChange?.()
    } catch (error) {
      appendAssistant(starting.id, message(errorToMessage(error)))
    } finally {
      setThinking(false)
    }
  }

  async function decideApi(
    entry: ChatMessage,
    status: ActionProposal["status"],
  ) {
    const reference = entry.proposal?.reference

    if (!reference || !active || thinking) return

    const conversationId = active.id

    setThinking(true)

    try {
      if (status === "awaiting_approval") {
        // After a reload the stored card is only a reference; the server rebuilds what it would do.
        const reply = await api.reviewAction(
          conversationId,
          reference.action_id,
          reference.action_version,
        )

        const fresh = replyToMessage(reply).proposal

        if (fresh)
          setConversations((current) =>
            current.map((conversation) =>
              conversation.id === conversationId
                ? replaceProposal(conversation, entry.id, fresh)
                : conversation,
            ),
          )

        return
      }

      const reply = await api.decide(
        conversationId,
        reference,
        status === "cancelled" ? "REJECT" : "APPROVE",
      )

      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === conversationId
            ? setProposalStatus(
                conversation,
                entry.id,
                status === "cancelled" ? "cancelled" : "approved",
              )
            : conversation,
        ),
      )

      appendAssistant(conversationId, message(replyToMessage(reply)))

      onServerChange?.()
    } catch (error) {
      appendAssistant(conversationId, message(errorToMessage(error)))
    } finally {
      setThinking(false)
    }
  }

  function decide(id: string, status: ActionProposal["status"]) {
    const entry = messages.find((item) => item.id === id)

    if (apiEnabled && entry?.proposal?.reference)
      return void decideApi(entry, status)

    patchActive((conversation) => setProposalStatus(conversation, id, status))
  }

  function newChat() {
    setActiveId(null)

    setEmptyInput("")

    setAttachedFiles([])

    shouldScroll.current = true

    requestAnimationFrame(() => composerRef.current?.focus())
  }

  function selectConversation(id: string) {
    setActiveId(id)

    setAttachedFiles([])

    setMenuId(null)

    setEditingId(null)

    shouldScroll.current = true

    setHistoryOpen(false)

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
      clearHistory()

      setEmptyInput("")

      closeHistory()
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

  const historyContent = (
    <ConversationSidebar
      conversations={conversations}
      historySearch={historySearch}
      setHistorySearch={setHistorySearch}
      closeHistory={closeHistory}
      historySearchRef={historySearchRef}
      activeId={activeId}
      editingId={editingId}
      rename={rename}
      setEditingId={setEditingId}
      renameValue={renameValue}
      setRenameValue={setRenameValue}
      renameError={renameError}
      setRenameError={setRenameError}
      menuId={menuId}
      setMenuId={setMenuId}
      selectConversation={selectConversation}
      actionFocusRef={actionFocusRef}
      setConfirm={setConfirm}
      exportHistory={exportHistory}
    />
  )

  return (
    <section
      className={`assistant-shell ${
        messages.length ? "has-messages" : "is-empty"
      } ${historyOpen && !mobile ? "history-visible" : ""}`}
      aria-label={apiEnabled ? "Trợ lý AI" : "Trợ lý AI bản mẫu"}
    >
      <div className="assistant-main">
        <div className="assistant-topline">
          {messages.length > 0 && (
            <button
              className="button secondary assistant-back"
              type="button"
              aria-label="Quay lại trang chủ"
              onClick={newChat}
            >
              <ArrowLeft size={17} aria-hidden="true" />
              <span>Quay lại</span>
            </button>
          )}
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
            <h1 ref={welcomeRef} data-assistant-heading tabIndex={-1}>
              Hôm nay bạn muốn làm gì?
            </h1>
          </div>
        ) : (
          <ChatTranscript
            messages={messages}
            transcriptRef={transcriptRef}
            shouldScroll={shouldScroll}
            activeClarification={activeClarification}
            clarificationForm={clarificationForm}
            onOpenPlanner={onOpenPlanner}
            decide={decide}
            apiEnabled={apiEnabled}
            thinking={thinking}
          />
        )}
        <ChatComposer
          apiEnabled={apiEnabled}
          thinking={thinking}
          isDragging={isDragging}
          setIsDragging={setIsDragging}
          handleDrop={handleDrop}
          send={send}
          fileInputRef={fileInputRef}
          handleFileAttach={handleFileAttach}
          hydrated={hydrated}
          attachedFiles={attachedFiles}
          removeAttachment={removeAttachment}
          composerRef={composerRef}
          input={input}
          setComposer={setComposer}
          handlePaste={handlePaste}
          composition={composition}
          onComposerKeyDown={onComposerKeyDown}
          storageMode={storageMode}
          storageError={storageError}
          conversationCount={conversations.length}
          exportHistory={exportHistory}
        />
      </div>
      {(historyOpen || panelShown) && !mobile && (
        <aside
          ref={historyPanelRef}
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
