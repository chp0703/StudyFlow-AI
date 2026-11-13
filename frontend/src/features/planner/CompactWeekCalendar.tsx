import { useState } from "react"
import type { Task } from "../../types/task"
import type { TaskChange, TimeWindow } from "../../types/planner"
import type { ApiTimeWindow } from "../../api/types"
import { visibleSegments } from "./workingTime"

const weekdays = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
const clock = (minutes: number) =>
  `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`
export const eventStart = (event: Task) =>
  event.time.match(/\d{2}:\d{2}/)?.[0] ??
  `${String(event.hour ?? 0).padStart(2, "0")}:${String(event.minute ?? 0).padStart(2, "0")}`
export const orderedDayEvents = (events: Task[], date: string) =>
  events
    .filter((event) => event.date === date)
    .sort(
      (a, b) =>
        eventStart(a).localeCompare(eventStart(b)) || a.id.localeCompare(b.id),
    )

export default function CompactWeekCalendar({
  weekDays,
  todayKey,
  events,
  windows,
  availability,
  changeOf,
  proposedWindowIds,
}: {
  weekDays: Date[]
  todayKey: string
  events: Task[]
  windows: ApiTimeWindow[]
  availability: TimeWindow[]
  changeOf: Map<string, TaskChange["kind"]>
  proposedWindowIds: Set<string>
}) {
  const [selected, setSelected] = useState(todayKey)
  const [expanded, setExpanded] = useState<string[]>([])
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const keys = weekDays.map((date) => date.toISOString().slice(0, 10))
  const selectedKey = keys.includes(selected) ? selected : keys[0]
  const selectedEvents = orderedDayEvents(events, selectedKey)
  const selectedEvent = selectedEvents.find(
    (event) => event.id === selectedEventId,
  )
  const renderEvent = (event: Task) => {
    const change = changeOf.get(event.id)
    return (
      <button
        type="button"
        key={event.id}
        className={`compact-event${change ? ` is-${change}` : ""}`}
        onClick={() => {
          setSelected(event.date!)
          setSelectedEventId(event.id)
        }}
        aria-label={`${event.title}, ${event.time}`}
        style={
          event.color && /^#[0-9a-fA-F]{6}$/.test(event.color)
            ? { borderLeftColor: event.color }
            : undefined
        }
      >
        <time>{eventStart(event)}</time>
        <strong>{event.title}</strong>
        {change && <small>{change === "removed" ? "Sẽ xóa" : "Đề xuất"}</small>}
      </button>
    )
  }
  const renderWindows = (date: string) =>
    visibleSegments(date, 0, 1440, windows, availability).map((segment) => {
      const label = `${
        segment.kind === "busy" ? "Bận" : "Rảnh"
      } ${clock(segment.start)}–${clock(segment.end)}`
      return (
        <span
          key={`${date}-${segment.start}-${segment.end}`}
          className={`compact-window is-${segment.kind}${
            proposedWindowIds.has(`${date}-${Math.floor(segment.start / 60)}`)
              ? " is-proposed"
              : ""
          }`}
        >
          {label}
        </span>
      )
    })
  return (
    <div className="compact-week" aria-label="Tuần thu gọn">
      <div className="compact-days">
        {keys.map((key, day) => {
          const items = orderedDayEvents(events, key)
          const visible = expanded.includes(key) ? items : items.slice(0, 3)
          return (
            <section
              className={`compact-day${key === todayKey ? " is-today" : ""}${
                selectedKey === key ? " is-selected" : ""
              }`}
              key={key}
            >
              <button
                type="button"
                className="compact-day-select"
                aria-pressed={selectedKey === key}
                onClick={() => setSelected(key)}
              >
                <strong>{weekdays[day]}</strong>
                <span>
                  {String(weekDays[day].getUTCDate()).padStart(2, "0")}/
                  {String(weekDays[day].getUTCMonth() + 1).padStart(2, "0")}
                </span>
              </button>
              <div className="compact-day-content">
                <div className="compact-window-list">{renderWindows(key)}</div>
                {visible.length ? (
                  visible.map(renderEvent)
                ) : (
                  <p className="compact-empty">Chưa có lịch học</p>
                )}
                {items.length > 3 && !expanded.includes(key) && (
                  <button
                    type="button"
                    className="compact-more"
                    onClick={() => {
                      setSelected(key)
                      setExpanded([...expanded, key])
                    }}
                  >
                    +{items.length - 3} lịch khác
                  </button>
                )}
              </div>
            </section>
          )
        })}
      </div>
      <section
        className="compact-agenda"
        aria-label={`Chi tiết ngày ${selectedKey}`}
      >
        <h3>Ngày {selectedKey.split("-").reverse().join("/")}</h3>
        <div className="compact-window-list">{renderWindows(selectedKey)}</div>
        {selectedEvents.length ? (
          selectedEvents.map(renderEvent)
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
    </div>
  )
}
