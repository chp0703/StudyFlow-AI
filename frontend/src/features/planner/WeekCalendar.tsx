import type { RefObject } from "react"
import type { Task } from "../../types/task"
import type { TaskChange, TimeWindow } from "../../types/planner"
import type { MinuteSegment } from "./workingTime"

type Props = {
  calendarRef: RefObject<HTMLDivElement | null>
  weekDays: Date[]
  week: number
  todayIndex: number
  hours: number[]
  eventAt: (date: Date, hour: number) => Task | undefined
  windowAt: (date: Date, hour: number) => TimeWindow | undefined
  segmentsAt: (date: Date, hour: number) => MinuteSegment[]
  proposedWindows: Set<string>
  prefill: (date: Date, hour: number) => void
  changeOf: Map<Task["id"], TaskChange["kind"]>
  nowHour: number
  nowMinutes: number
}

export default function WeekCalendar({
  calendarRef,
  weekDays,
  week,
  todayIndex,
  hours,
  eventAt,
  windowAt,
  segmentsAt,
  proposedWindows,
  prefill,
  changeOf,
  nowHour,
  nowMinutes,
}: Props) {
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
          <span className="schedule-header-time" aria-hidden="true" />
          {weekDays.map((date, i) => (
            <span
              key={i}
              className={`schedule-day ${
                week === 0 && i === todayIndex ? "is-today" : ""
              }`}
            >
              <strong>{["T2", "T3", "T4", "T5", "T6", "T7", "CN"][i]}</strong>
              <span>{`${String(date.getUTCDate()).padStart(2, "0")}/${String(date.getUTCMonth() + 1).padStart(2, "0")}`}</span>
            </span>
          ))}
        </div>
        {hours.map((hour) => (
          <div className="schedule-row" key={hour}>
            <span className="schedule-hour" aria-hidden="true">
              {`${String(hour).padStart(2, "0")}:00`}
            </span>
            {weekDays.map((d, day) => {
              const event = eventAt(d, hour)

              const win = windowAt(d, hour)
              const segments = segmentsAt(d, hour)
              const timeLabel = (minute: number) =>
                `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`

              return (
                <div
                  className={`schedule-cell ${
                    week === 0 && day === todayIndex ? "today-column" : ""
                  } ${win && proposedWindows.has(win.id) ? "is-proposed" : ""}`}
                  key={day}
                  onClick={event ? undefined : () => prefill(d, hour)}
                >
                  {segments.map((segment) => (
                    <span
                      key={`${segment.start}-${segment.end}-${segment.kind}`}
                      className={`window-segment is-${segment.kind}`}
                      style={{
                        top: `${((segment.start - hour * 60) / 60) * 100}%`,
                        height: `${((segment.end - segment.start) / 60) * 100}%`,
                      }}
                      role="img"
                      aria-label={`${
                        segment.kind === "free" ? "Thời gian học" : "Bận"
                      } ${timeLabel(segment.start)}–${timeLabel(segment.end)}`}
                      title={`${
                        segment.kind === "free" ? "Học" : "Bận"
                      } ${timeLabel(segment.start)}–${timeLabel(segment.end)}`}
                    >
                      {segment.end - segment.start >= 20
                        ? `${
                            segment.kind === "free" ? "Học" : "Bận"
                          } ${timeLabel(segment.start)}–${timeLabel(segment.end)}`
                        : ""}
                    </span>
                  ))}
                  {event && (
                    <div
                      className={`schedule-event study priority-${
                        { Cao: "high", Thấp: "low" }[event.priority] ?? "mid"
                      } ${event.done ? "is-done" : ""} ${
                        changeOf.get(event.id) === "removed"
                          ? "is-removed"
                          : changeOf.has(event.id)
                            ? "is-proposed"
                            : ""
                      }`}
                      data-task-id={event.id}
                      title={`${event.title} · ${event.time}`}
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
                  )}
                  {week === 0 && day === todayIndex && hour === nowHour && (
                    <i
                      className="now-line"
                      style={{ top: `${(nowMinutes / 60) * 100}%` }}
                    />
                  )}
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
