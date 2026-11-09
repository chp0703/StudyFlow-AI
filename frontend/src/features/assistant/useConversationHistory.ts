import { useEffect, useRef, useState } from "react"
import {
  clearConversations,
  loadHistory,
  openHistoryDatabase,
  putActiveId,
  putConversation,
  removeConversation,
  type Conversation,
} from "./conversationHistory"

export function useConversationHistory() {
  const [conversations, setConversations] = useState<Conversation[]>([])

  const [activeId, setActiveId] = useState<string | null>(null)

  const [hydrated, setHydrated] = useState(false)

  const [storageMode, setStorageMode] =
    useState<"loading" | "persistent" | "memory">("loading")

  const [storageError, setStorageError] = useState("")

  const dbRef = useRef<IDBDatabase | null>(null)

  const writeQueue = useRef<Promise<void>>(Promise.resolve())

  const storageEnabled = useRef(false)

  const savedSnapshot = useRef(new Map<string, Conversation>())

  const savedActiveId = useRef<string | null>(null)

  useEffect(() => {
    let cancelled = false

    // Công tắc giả lập lỗi chỉ dành cho phát triển, dùng kiểm tra nhánh lưu trữ dự phòng trên trình duyệt.

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

  function patchActive(update: (conversation: Conversation) => Conversation) {
    if (!activeId) return

    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === activeId ? update(conversation) : conversation,
      ),
    )
  }

  function clearHistory() {
    savedSnapshot.current = new Map()

    savedActiveId.current = null

    enqueue(clearConversations, true)

    setConversations([])

    setActiveId(null)
  }

  return {
    conversations,
    setConversations,
    activeId,
    setActiveId,
    hydrated,
    storageMode,
    storageError,
    clearHistory,
    patchActive,
  }
}
