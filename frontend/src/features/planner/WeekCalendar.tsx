import { calendarEventColors } from "./calendarEvents"

import { TASK_COLOR_OPTIONS } from "./clarification.ts"

import type { CSSProperties, RefObject } from "react"

import type { Task } from "../../types/task"

import type { TaskChange, TimeWindow } from "../../types/planner"

import type { CalendarDisplayRanges } from "./calendarDisplay"

import {
  displayMinutes,
  eventLanes,
  eventPosition,
  rangeCoveringSpans,
} from "./calendarDisplay"

import CalendarDisplaySettings from "./CalendarDisplaySettings"

import type { ApiTimeWindow } from "../../api/types"

import { sourceRange, visibleSegments } from "./workingTime"

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

  highlightNow,

  onSelectEvent,
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

  highlightNow?: boolean

  onSelectEvent?: (event: Task) => void
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

            const startOf = (event: Task) =>
              event.time.match(/\d{2}:\d{2}/)?.[0] ??
              `${String(event.hour ?? 0).padStart(2, "0")}:00`

            const placed = dayEvents.flatMap((event) => {
              const position = eventPosition(startOf(event), range)

              return position ? [{ event, position }] : []
            })

            const outside = dayEvents
              .filter((event) => !placed.some((item) => item.event === event))
              .map((event) => {
                const start = displayMinutes(startOf(event))

                return { start, end: start + event.effort }
              })

            const lanes = eventLanes(
              placed.map(({ event, position }) => ({
                id: event.id,

                start: from + position.top,

                // Khối được vẽ cao tối thiểu 28px (~35 phút) nên tính chồng theo chiều cao thật.
                end:
                  from +
                  position.top +
                  Math.max(35, Math.min(event.effort, position.visibleMinutes)),
              })),
            )

            const now = nowHour * 60 + nowMinutes

            const daySegments = visibleSegments(
              dateKey,
              0,
              24 * 60,
              windows,
              availability,
            )
            const hiddenWindows = daySegments.filter(
              (segment) => segment.start < from || segment.end > to,
            )
            const hiddenLabel = [
              outside.length && `${outside.length} buổi`,
              hiddenWindows.length && `${hiddenWindows.length} khung giờ`,
            ]
              .filter(Boolean)
              .join(", ")
            const segments = daySegments.flatMap((segment) => {
              const start = Math.max(segment.start, from)
              const end = Math.min(segment.end, to)
              return start < end ? [{ ...segment, start, end }] : []
            })

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
                      key={`${segment.start}-${segment.end}`}
                      className={`calendar-window is-busy${
                        proposedWindowIds.has(
                          `${dateKey}-${Math.floor(segment.start / 60)}`,
                        )
                          ? " is-proposed-window"
                          : ""
                      }`}
                      role="img"
                      aria-label={`Bận ${timeLabel(sourceRange(dateKey, segment, windows)?.start ?? segment.start)}–${timeLabel(sourceRange(dateKey, segment, windows)?.end ?? segment.end)}`}
                      style={{
                        top: (segment.start - gridFrom) * pxPerMinute,

                        height: (segment.end - segment.start) * pxPerMinute,
                      }}
                    >
                      {segment.end - segment.start >= 30
                        ? `Bận ${timeLabel(sourceRange(dateKey, segment, windows)?.start ?? segment.start)}–${timeLabel(sourceRange(dateKey, segment, windows)?.end ?? segment.end)}`
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
                  {hiddenLabel &&
                    (onRangesChange ? (
                      <button
                        type="button"
                        className="schedule-hidden-events"
                        title="Mở rộng khung giờ để xem các mục ngoài khung"
                        onClick={() =>
                          onRangesChange(
                            ranges.map((item, index) =>
                              index === day
                                ? rangeCoveringSpans(item, [
                                    ...outside,
                                    ...hiddenWindows,
                                  ])
                                : item,
                            ) as unknown as CalendarDisplayRanges,
                          )
                        }
                      >
                        {hiddenLabel} ngoài khung · Hiện
                      </button>
                    ) : (
                      <span className="schedule-hidden-events">
                        {hiddenLabel} ngoài khung
                      </span>
                    ))}
                  {placed.map(({ event, position }) => {
                    const slot = lanes.get(event.id) ?? { lane: 0, lanes: 1 }

                    const duration = Math.min(
                      event.effort,

                      position.visibleMinutes,
                    )

                    const colors = calendarEventColors(event.color)

                    const colorLabel = TASK_COLOR_OPTIONS.find(
                      (option) =>
                        option.value === colors?.["--evt"].toUpperCase(),
                    )?.label

                    return (
                      <button
                        type="button"
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
                        style={
                          {
                            top: (from - gridFrom + position.top) * pxPerMinute,

                            left: `calc(${(slot.lane / slot.lanes) * 100}% + 4px)`,

                            width: `calc(${100 / slot.lanes}% - 8px)`,

                            right: "auto",

                            height: Math.max(28, duration * pxPerMinute),

                            ...colors,
                          } as CSSProperties
                        }
                        title={[event.title, event.time, colorLabel]

                          .filter(Boolean)

                          .join(" · ")}
                        onClick={() => onSelectEvent?.(event)}
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
                      </button>
                    )
                  })}
                  {week === 0 &&
                    day === todayIndex &&
                    now >= from &&
                    now < to && (
                      <i
                        className={`now-line${
                          highlightNow ? " is-highlighted" : ""
                        }`}
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
