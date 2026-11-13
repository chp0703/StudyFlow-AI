import { useState } from "react"
import { X } from "lucide-react"
import type { Task } from "../../types/task"
import type { TaskChange, TimeWindow } from "../../types/planner"
import type { ApiTimeWindow } from "../../api/types"
import { eventStart, orderedDayEvents } from "./CompactWeekCalendar"
import { visibleSegments } from "./workingTime"
import { monthDates } from "./monthGrid"

const weekdays = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
const clock = (minutes: number) =>
  `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`
const color = (event: Task) =>
  event.color && /^#[0-9a-fA-F]{6}$/.test(event.color) ? event.color : undefined

export default function MonthCalendar({
  month,
  todayKey,
  selectedDate,
  onSelect,
  events,
  windows,
  availability,
  changeOf,
}: {
  month: string
  todayKey: string
  selectedDate: string | null
  onSelect: (date: string | null) => void
  events: Task[]
  windows: ApiTimeWindow[]
  availability: TimeWindow[]
  changeOf: Map<string, TaskChange["kind"]>
}) {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const dates = monthDates(month)
  const selectedEvents = selectedDate
    ? orderedDayEvents(events, selectedDate)
    : []
  const selectedEvent = selectedEvents.find(
    (event) => event.id === selectedEventId,
  )
  const windowsFor = (date: string) =>
    visibleSegments(date, 0, 1440, windows, availability)
  const select = (date: string) => {
    onSelect(date)
    setSelectedEventId(null)
  }
  return (
    <div
      className="month-calendar"
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          onSelect(null)
          setSelectedEventId(null)
        }
      }}
    >
      <div
        className="month-grid"
        role="grid"
        aria-label={`Tháng ${month.slice(5)}/${month.slice(0, 4)}`}
      >
        {weekdays.map((name) => (
          <div className="month-weekday" role="columnheader" key={name}>
            {name}
          </div>
        ))}
        {dates.map((date) => {
          const items = orderedDayEvents(events, date)
          const segments = windowsFor(date)
          const outside = !date.startsWith(month)
          return (
            <div
              role="gridcell"
              key={date}
              className={`month-cell${outside ? " is-outside" : ""}${
                date === todayKey ? " is-today" : ""
              }${date === selectedDate ? " is-selected" : ""}`}
            >
              <button
                type="button"
                className="month-date"
                aria-label={`Ngày ${date.split("-").reverse().join("/")}${
                  date === todayKey ? ", hôm nay" : ""
                }`}
                aria-pressed={date === selectedDate}
                onClick={() => select(date)}
              >
                {Number(date.slice(-2))}
              </button>
              {segments.length > 0 && (
                <span
                  className="month-window-dots"
                  aria-label={
                    segments.some((segment) => segment.kind === "busy")
                      ? "Có giờ bận"
                      : "Có giờ rảnh"
                  }
                >
                  {segments.some((segment) => segment.kind === "busy")
                    ? "●"
                    : "○"}
                </span>
              )}
              <div className="month-event-list">
                {items.slice(0, 2).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    className={`month-event${
                      changeOf.has(item.id) ? " is-proposed" : ""
                    }${
                      changeOf.get(item.id) === "removed" ? " is-removed" : ""
                    }`}
                    style={
                      color(item) ? { borderLeftColor: color(item) } : undefined
                    }
                    aria-label={`${item.title}, ${item.time}`}
                    onClick={() => {
                      onSelect(date)
                      setSelectedEventId(item.id)
                    }}
                  >
                    <time>{eventStart(item)}</time>
                    <span>{item.title}</span>
                  </button>
                ))}
                {items.length > 2 && (
                  <button
                    type="button"
                    className="month-more"
                    onClick={() => select(date)}
                  >
                    +{items.length - 2} lịch khác
                  </button>
                )}
              </div>
              {items.length > 0 && (
                <span
                  className="month-mobile-count"
                  aria-label={`${items.length} lịch học`}
                >
                  {items.length}
                </span>
              )}
            </div>
          )
        })}
      </div>
      {selectedDate && (
        <section
          className="month-agenda"
          aria-label={`Lịch ngày ${selectedDate}`}
        >
          <div className="month-agenda-heading">
            <h3>Ngày {selectedDate.split("-").reverse().join("/")}</h3>
            <button
              type="button"
              aria-label="Đóng lịch ngày"
              onClick={() => onSelect(null)}
            >
              <X size={16} aria-hidden="true" />
            </button>
          </div>
          <div className="compact-window-list">
            {windowsFor(selectedDate).map((segment) => (
              <span
                key={`${segment.start}-${segment.end}`}
                className={`compact-window is-${segment.kind}`}
              >
                {segment.kind === "busy" ? "Bận" : "Rảnh"}{" "}
                {clock(segment.start)}–{clock(segment.end)}
              </span>
            ))}
          </div>
          {selectedEvents.length ? (
            selectedEvents.map((item) => (
              <button
                type="button"
                key={item.id}
                className={`month-agenda-event${
                  changeOf.has(item.id) ? " is-proposed" : ""
                }`}
                style={
                  color(item) ? { borderLeftColor: color(item) } : undefined
                }
                onClick={() => setSelectedEventId(item.id)}
              >
                <time>{item.time}</time>
                <strong>{item.title}</strong>
                {changeOf.has(item.id) && (
                  <small>
                    {changeOf.get(item.id) === "removed" ? "Sẽ xóa" : "Đề xuất"}
                  </small>
                )}
              </button>
            ))
          ) : (
            <p>Chưa có lịch học trong ngày.</p>
          )}
          {selectedEvent && (
            <div className="compact-event-detail">
              <strong>{selectedEvent.title}</strong>
              <span>
                {selectedEvent.time} · {selectedEvent.effort} phút
              </span>
              {selectedEvent.description && <p>{selectedEvent.description}</p>}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
