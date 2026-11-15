import type { RefObject } from "react"
import type { Task } from "../../types/task"
import type { TaskChange, TimeWindow } from "../../types/planner"
import type { CalendarDisplayRanges } from "./calendarDisplay"
import { displayMinutes, eventPosition } from "./calendarDisplay"
import CalendarDisplaySettings from "./CalendarDisplaySettings"
import type { ApiTimeWindow } from "../../api/types"
import { visibleSegments } from "./workingTime"

const weekdayNames = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
const pxPerMinute = 0.8

const timeLabel = (minutes: number) =>
  `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`

const buildTicks = (from: number, to: number) =>
  to <= from
    ? []
    : [
        from,
        ...Array.from(
          { length: Math.max(0, Math.ceil((to - from) / 60) - 1) },
          (_, i) => from + (i + 1) * 60,
        ),
      ]

export default function WeekCalendar({
  calendarRef,
  weekDays,
  week,
  todayIndex,
  ranges,
  onRangesChange,
  events,
  windows,
  availability,
  proposedWindowIds,
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
  onRangesChange?: (ranges: CalendarDisplayRanges) => void
  events: Task[]
  windows: ApiTimeWindow[]
  availability: TimeWindow[]
  proposedWindowIds: Set<string>
  changeOf: Map<Task["id"], TaskChange["kind"]>
  prefill: (date: Date, minuteOfDay: number) => void
  nowHour: number
  nowMinutes: number
}) {
  const gridFrom = Math.min(
    ...ranges.map((range) => displayMinutes(range.start)),
  )
  const gridTo = Math.max(...ranges.map((range) => displayMinutes(range.end)))
  const gridHeight = Math.max(60, (gridTo - gridFrom) * pxPerMinute)
  const axisTicks = buildTicks(gridFrom, gridTo)

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
          <div className="schedule-time-corner">
            {onRangesChange && (
              <CalendarDisplaySettings
                ranges={ranges}
                onChange={onRangesChange}
              />
            )}
          </div>
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
          <div
            className="schedule-time-column"
            aria-hidden="true"
            style={{ height: gridHeight }}
          >
            {axisTicks.map((minute) => (
              <span
                key={minute}
                className="schedule-time-label"
                style={{
                  top: (minute - gridFrom) * pxPerMinute,
                  height: Math.min(60, gridTo - minute) * pxPerMinute,
                }}
              >
                {timeLabel(minute)}
              </span>
            ))}
          </div>
          {weekDays.map((date, day) => {
            const range = ranges[day]
            const from = displayMinutes(range.start)
            const to = displayMinutes(range.end)
            const dateKey = date.toISOString().slice(0, 10)
            const ticks = buildTicks(from, to)
            const dayEvents = events.filter((event) => event.date === dateKey)
            const now = nowHour * 60 + nowMinutes
            const segments = visibleSegments(
              dateKey,
              from,
              to,
              windows,
              availability,
            )
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
                  style={{ height: gridHeight }}
                >
                  {segments.map((segment) => (
                    <div
                      key={`${segment.start}-${segment.end}-${segment.kind}`}
                      className={`calendar-window is-${segment.kind}${
                        proposedWindowIds.has(
                          `${dateKey}-${Math.floor(segment.start / 60)}`,
                        )
                          ? " is-proposed-window"
                          : ""
                      }`}
                      role="img"
                      aria-label={`${
                        segment.kind === "busy" ? "Bận" : "Rảnh"
                      } ${timeLabel(segment.start)}–${timeLabel(segment.end)}`}
                      style={{
                        top: (segment.start - gridFrom) * pxPerMinute,
                        height: (segment.end - segment.start) * pxPerMinute,
                      }}
                    >
                      {segment.end - segment.start >= 30
                        ? `${
                            segment.kind === "busy" ? "Bận" : "Rảnh"
                          } ${timeLabel(segment.start)}–${timeLabel(segment.end)}`
                        : ""}
                    </div>
                  ))}
                  {ticks.map((minute) => (
                    <button
                      key={minute}
                      type="button"
                      className="schedule-time-slot"
                      style={{
                        top: (minute - gridFrom) * pxPerMinute,
                        height: Math.min(60, to - minute) * pxPerMinute,
                      }}
                      aria-label={`${weekdayNames[day]} ${dateKey} lúc ${timeLabel(minute)}; nhập yêu cầu lịch học`}
                      onClick={() => prefill(date, minute)}
                    />
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
                          top: (from - gridFrom + position.top) * pxPerMinute,
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
                        style={{ top: (now - gridFrom) * pxPerMinute }}
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
