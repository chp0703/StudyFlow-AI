import type { RefObject } from "react"
import { Check, MoreHorizontal, Search, Trash2, X } from "lucide-react"
import { historyGroup, type Conversation } from "./conversationHistory"

export type ConfirmAction = {
  kind: "delete"

  id: string

  title: string
} | {
  kind: "clear"
}

const groupNames = ["Hôm nay", "Hôm qua", "7 ngày gần đây", "Cũ hơn"] as const

type Props = {
  conversations: Conversation[]
  historySearch: string
  setHistorySearch: (value: string) => void
  closeHistory: () => void
  historySearchRef: RefObject<HTMLInputElement | null>
  activeId: string | null
  editingId: string | null
  rename: (id: string) => void
  setEditingId: (id: string | null) => void
  renameValue: string
  setRenameValue: (value: string) => void
  renameError: string
  setRenameError: (value: string) => void
  menuId: string | null
  setMenuId: (id: string | null) => void
  selectConversation: (id: string) => void
  actionFocusRef: RefObject<HTMLElement | null>
  setConfirm: (value: ConfirmAction | null) => void
  exportHistory: () => void
}

export default function ConversationSidebar({
  conversations,
  historySearch,
  setHistorySearch,
  closeHistory,
  historySearchRef,
  activeId,
  editingId,
  rename,
  setEditingId,
  renameValue,
  setRenameValue,
  renameError,
  setRenameError,
  menuId,
  setMenuId,
  selectConversation,
  actionFocusRef,
  setConfirm,
  exportHistory,
}: Props) {
  const sorted = [...conversations].sort((a, b) =>
    b.updatedAt.localeCompare(a.updatedAt),
  )

  const searched = sorted.filter((item) =>
    `${item.title} ${item.messages.map((entry) => entry.text).join(" ")}`

      .toLocaleLowerCase("vi")

      .includes(historySearch.trim().toLocaleLowerCase("vi")),
  )

  return (
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
}
