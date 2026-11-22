import { TASK_COLOR_OPTIONS } from "./clarification"
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
import type { RevisionSchedulingState } from "./revisionScheduling"
import Button from "../../components/ui/Button"

import { daysUntil, formatShortDate } from "../../utils/date"
import { presentTaskDescription } from "./taskPresentation"

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

// Nháp nếu thuộc đề xuất đang chờ; ngoài ra đã xác nhận nếu có trên lịch, còn lại là chưa xếp lịch.

export function statusOf(task: Task, proposedIds: Set<string>): Status {
  if (proposedIds.has(task.id)) return "draft"

  return task.date && task.hour !== undefined ? "confirmed" : "unscheduled"
}

export default function TaskPanel({
  tasks,

  proposedIds,

  week,

  onClose,

  revisionScheduling,

  onRetryRevisionScheduling,
  onScheduleTask,
  onSetupAvailability,
}: {
  tasks: Task[]

  proposedIds: Set<string>

  week?: string[]

  onClose?: () => void

  revisionScheduling?: RevisionSchedulingState | null

  onRetryRevisionScheduling?: () => void

  onScheduleTask?: (taskId: string) => void

  onSetupAvailability?: () => void
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
        <ul
          className="task-panel-list"
          role="region"
          aria-label="Danh sách công việc"
          tabIndex={0}
        >
          {rows.map((t) => {
            const { label, Icon } = STATUS[statusOf(t, proposedIds)]

            const left = daysUntil(t.deadline)
            const colorLabel = TASK_COLOR_OPTIONS.find(
              (option) => option.value === t.color?.toUpperCase(),
            )?.label
            const scheduling =
              revisionScheduling?.taskId === t.id ? revisionScheduling : null
            const description = presentTaskDescription(t.description)
            const status = statusOf(t, proposedIds)

            return (
              <li
                key={t.id}
                style={
                  t.color && /^#[0-9a-fA-F]{6}$/.test(t.color)
                    ? { borderLeft: `4px solid ${t.color}` }
                    : undefined
                }
              >
                <strong>{t.title}</strong>
                {description &&
                  (description.summary.length > 110 ||
                  description.summary.includes("\n") ? (
                    <details className="task-panel-description">
                      <summary>{description.summary}</summary>
                      <span>{description.summary}</span>
                    </details>
                  ) : (
                    <span className="task-panel-description-text">
                      {description.summary}
                    </span>
                  ))}
                <span className="task-panel-meta">
                  <CalendarClock aria-hidden="true" size={13} />
                  {t.date
                    ? `${formatShortDate(t.date)} · ${t.time}`
                    : `${formatShortDate(t.deadline)}${
                        left >= 0 ? ` · còn ${left} ngày` : " · quá hạn"
                      }`}{" "}
                  · {t.effort} phút
                </span>
                <span className="task-panel-tags">
                  {colorLabel && (
                    <span className="priority-badge">{colorLabel}</span>
                  )}
                  <span className="priority-badge">{t.priority}</span>
                  <span className={`status-chip is-${status}`}>
                    <Icon aria-hidden="true" size={13} />
                    {scheduling?.status === "finding"
                      ? "Đang tìm lịch học phù hợp…"
                      : scheduling?.status === "pending"
                        ? "Đang chờ xác nhận lịch"
                        : scheduling?.status === "scheduled"
                          ? "Đã xếp lịch"
                          : scheduling?.status === "failed"
                            ? "Chưa tìm được khung giờ phù hợp"
                            : scheduling?.status === "needs_availability"
                              ? "Cần thiết lập giờ rảnh"
                              : scheduling?.status === "blocked"
                                ? "Đang có đề xuất chờ duyệt"
                                : label}
                  </span>
                  {(scheduling?.status === "failed" ||
                    scheduling?.status === "blocked") &&
                    onRetryRevisionScheduling && (
                      <Button
                        className="secondary task-panel-retry"
                        onClick={onRetryRevisionScheduling}
                      >
                        Thử lại
                      </Button>
                    )}
                  {scheduling?.status === "needs_availability" &&
                    onSetupAvailability && (
                      <Button
                        className="secondary task-panel-retry"
                        onClick={onSetupAvailability}
                      >
                        Thiết lập giờ học mặc định
                      </Button>
                    )}
                  {status === "unscheduled" &&
                    !scheduling &&
                    onScheduleTask && (
                      <Button
                        className="secondary task-panel-retry"
                        onClick={() => onScheduleTask(t.id)}
                      >
                        Tìm giờ học
                      </Button>
                    )}
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
