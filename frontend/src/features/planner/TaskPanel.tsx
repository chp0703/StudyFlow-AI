import { useState } from "react"

import {
  CalendarClock,
  CircleCheck,
  CircleDashed,
  FilePen,
  Search,
  X,
} from "lucide-react"

import Card from "../../components/ui/Card"

import type { Task } from "../../types/task"

import { daysUntil, formatShortDate } from "../../utils/date"

type Status = "draft" | "confirmed" | "unscheduled"

type Filter = {
  value: "all" | Status

  label: string
}

const FILTERS: Filter[] = [
  { value: "all", label: "Tất cả" },

  { value: "draft", label: "Nháp" },

  { value: "confirmed", label: "Đã xác nhận" },

  { value: "unscheduled", label: "Chưa xếp" },
]

const STATUS = {
  draft: { label: "Nháp", Icon: FilePen },

  confirmed: { label: "Đã xác nhận", Icon: CircleCheck },

  unscheduled: { label: "Chưa xếp", Icon: CircleDashed },
}

// Draft = part of the pending proposal; otherwise confirmed if placed on the calendar, else unscheduled.

export function statusOf(task: Task, proposedIds: Set<string>): Status {
  if (proposedIds.has(task.id)) return "draft"

  return task.date && task.hour !== undefined ? "confirmed" : "unscheduled"
}

export default function TaskPanel({
  tasks,

  proposedIds,

  week,

  onClose,
}: {
  tasks: Task[]

  proposedIds: Set<string>

  week?: string[]

  onClose?: () => void
}) {
  const [query, setQuery] = useState("")

  const [filter, setFilter] = useState<"all" | Status>("all")

  const [weekOnly, setWeekOnly] = useState(false)

  const rows = tasks

    .filter(
      (t) =>
        t.title

          .toLocaleLowerCase("vi")

          .includes(query.trim().toLocaleLowerCase("vi")) &&
        (filter === "all" || statusOf(t, proposedIds) === filter) &&
        (!weekOnly || !week || week.includes(t.date ?? t.deadline)),
    )

    .sort((a, b) => a.deadline.localeCompare(b.deadline))

  return (
    <Card
      className="task-panel"
      title="Công việc"
      action={
        onClose ? (
          <button
            type="button"
            className="task-panel-close"
            aria-label="Đóng danh sách công việc"
            title="Đóng danh sách công việc"
            onClick={onClose}
          >
            <X size={15} aria-hidden="true" />
          </button>
        ) : undefined
      }
    >
      <div className="task-panel-body">
        <div className="search-wrap task-panel-search-wrap">
          <Search
            size={14}
            className="task-panel-search-icon"
            aria-hidden="true"
          />
          <input
            className="task-panel-search"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm công việc..."
            aria-label="Tìm công việc"
          />
        </div>
        <div
          className="task-panel-filters"
          role="group"
          aria-label="Lọc theo trạng thái"
        >
          {FILTERS.map((f) => (
            <button
              key={f.value}
              type="button"
              className={filter === f.value ? "is-active" : ""}
              aria-pressed={filter === f.value}
              onClick={() => setFilter(f.value)}
            >
              {f.label}
            </button>
          ))}
          {week && (
            <button
              type="button"
              className={weekOnly ? "is-active" : ""}
              aria-pressed={weekOnly}
              onClick={() => setWeekOnly((v) => !v)}
            >
              Tuần đang xem
            </button>
          )}
        </div>
        <ul className="task-panel-list">
          {rows.map((t) => {
            const { label, Icon } = STATUS[statusOf(t, proposedIds)]

            const left = daysUntil(t.deadline)

            return (
              <li key={t.id}>
                <strong>{t.title}</strong>
                <span className="task-panel-meta">
                  <CalendarClock aria-hidden="true" size={13} />
                  {formatShortDate(t.deadline)}
                  {left >= 0 ? ` · còn ${left} ngày` : " · quá hạn"} ·{" "}
                  {t.effort} phút
                </span>
                <span className="task-panel-tags">
                  <span className="priority-badge">{t.priority}</span>
                  <span
                    className={`status-chip is-${statusOf(t, proposedIds)}`}
                  >
                    <Icon aria-hidden="true" size={13} /> {label}
                  </span>
                </span>
              </li>
            )
          })}
        </ul>
        {!rows.length && (
          <p className="task-panel-empty">
            {tasks.length
              ? "Không có công việc phù hợp."
              : "Chưa có công việc."}
          </p>
        )}
      </div>
    </Card>
  )
}
