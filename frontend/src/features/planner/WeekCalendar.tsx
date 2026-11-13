import type { RefObject } from "react"
import type { Task } from "../../types/task"
import type { TaskChange } from "../../types/planner"
import type { CalendarDisplayRanges } from "./calendarDisplay"
import { displayMinutes, eventPosition } from "./calendarDisplay"

const weekdayNames = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
const pxPerMinute = 0.8

export default function WeekCalendar({
  calendarRef,
  weekDays,
  week,
  todayIndex,
  ranges,
  events,
  changeOf,
  prefill,
  nowHour,
  nowMinutes,
}: {
  calendarRef: RefObject<HTMLDivElement | null>
  weekDays: Date[]
  week: number
  todayIndex: number
  ranges: CalendarDisplayRanges
  events: Task[]
  changeOf: Map<Task["id"], TaskChange["kind"]>
  prefill: (date: Date, hour: number) => void
  nowHour: number
  nowMinutes: number
}) {
  return (
    <div
      ref={calendarRef}
      className="dashboard-calendar-scroll"
      role="region"
      aria-label="Lịch trong tuần"
      tabIndex={0}
    >
      <div className="dashboard-schedule">
        <div className="schedule-header">
          {weekDays.map((date, day) => (
            <div
              key={day}
              className={`schedule-day ${
                week === 0 && day === todayIndex ? "is-today" : ""
              }`}
            >
              <strong>{weekdayNames[day]}</strong>
              <span>{`${String(date.getUTCDate()).padStart(2, "0")}/${String(date.getUTCMonth() + 1).padStart(2, "0")}`}</span>
            </div>
          ))}
        </div>
        <div className="schedule-columns">
          {weekDays.map((date, day) => {
            const range = ranges[day]
            const from = displayMinutes(range.start)
            const to = displayMinutes(range.end)
            const dateKey = date.toISOString().slice(0, 10)
            const ticks = [
              from,
              ...Array.from(
                { length: Math.ceil((to - from) / 60) - 1 },
                (_, i) => from + (i + 1) * 60,
              ),
            ]
            const timeLabel = (minutes: number) =>
              `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`
            const dayEvents = events.filter((event) => event.date === dateKey)
            const now = nowHour * 60 + nowMinutes
            return (
              <section
                key={dateKey}
                className={`schedule-day-column ${
                  week === 0 && day === todayIndex ? "today-column" : ""
                }`}
                aria-label={`${weekdayNames[day]} ${dateKey}, hiển thị ${range.start} đến ${range.end}`}
              >
                <div
                  className="schedule-time-grid"
                  style={{ height: (to - from) * pxPerMinute }}
                >
                  {ticks.map((minute, index) => (
                    <button
                      key={minute}
                      type="button"
                      className="schedule-time-slot"
                      style={{
                        top: (minute - from) * pxPerMinute,
                        height: Math.min(60, to - minute) * pxPerMinute,
                      }}
                      aria-label={`${weekdayNames[day]} ${dateKey} lúc ${timeLabel(minute)}; nhập yêu cầu lịch học`}
                      onClick={() => prefill(date, Math.floor(minute / 60))}
                    >
                      <span>{timeLabel(minute)}</span>
                      {index === 0 && minute % 60 !== 0 && (
                        <span className="schedule-range-start">Bắt đầu</span>
                      )}
                    </button>
                  ))}
                  {dayEvents.map((event) => {
                    const start =
                      event.time.match(/\d{2}:\d{2}/)?.[0] ??
                      `${String(event.hour ?? 0).padStart(2, "0")}:00`
                    const position = eventPosition(start, range)
                    if (!position) return null
                    const duration = Math.min(
                      event.effort,
                      position.visibleMinutes,
                    )
                    return (
                      <div
                        key={event.id}
                        className={`schedule-event priority-${
                          event.priority === 1 || event.priority === "Cao"
                            ? "high"
                            : event.priority === 0.1 ||
                                event.priority === "Thấp"
                              ? "low"
                              : "mid"
                        } ${event.done ? "is-done" : ""} ${
                          changeOf.get(event.id) === "removed"
                            ? "is-removed"
                            : changeOf.has(event.id)
                              ? "is-proposed"
                              : ""
                        }`}
                        data-task-id={event.id}
                        style={{
                          top: position.top * pxPerMinute,
                          height: Math.max(28, duration * pxPerMinute),
                        }}
                        title={`${event.title} · ${event.time}`}
                        tabIndex={0}
                      >
                        <strong>{event.title}</strong>
                        <small>
                          {event.time}
                          {changeOf.get(event.id) === "removed"
                            ? " · Sẽ xóa"
                            : changeOf.has(event.id)
                              ? " · Đề xuất"
                              : ""}
                        </small>
                      </div>
                    )
                  })}
                  {week === 0 &&
                    day === todayIndex &&
                    now >= from &&
                    now < to && (
                      <i
                        className="now-line"
                        aria-label={`Bây giờ ${timeLabel(now)}`}
                        style={{ top: (now - from) * pxPerMinute }}
                      />
                    )}
                </div>
              </section>
            )
          })}
        </div>
      </div>
    </div>
  )
}
