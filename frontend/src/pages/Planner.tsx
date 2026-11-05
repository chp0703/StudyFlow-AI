import { useRef, useState, type Dispatch, type SetStateAction } from "react"

import gsap from "gsap"

import { useGSAP } from "@gsap/react"

import { ChevronLeft, ChevronRight, Send } from "lucide-react"

import Button from "../components/ui/Button"

import Card from "../components/ui/Card"

import {
  FIRST_HOUR,
  LAST_HOUR,
  runPlannerCommand,
} from "../features/planner/plannerAgent"

import type { Task } from "../types/task"

import { today, toIsoDate } from "../utils/date"

const todayIndex = (today.getDay() + 6) % 7

const nowHour = new Date().getHours()

const nowMinutes = new Date().getMinutes()

const hours = Array.from(
  { length: LAST_HOUR - FIRST_HOUR + 1 },

  (_, i) => i + FIRST_HOUR,
)

export default function Planner({
  tasks,

  setTasks,

  notify,
}: {
  tasks: Task[]

  setTasks: Dispatch<SetStateAction<Task[]>>

  notify?: (message: string) => void
}) {
  const [input, setInput] = useState("")

  const [reply, setReply] = useState("")

  const [week, setWeek] = useState(0)

  const calendarRef = useRef<HTMLDivElement>(null)

  const prevWeek = useRef(0)

  const prevTasks = useRef(tasks)

  // Changing week slides the calendar content in from the direction of travel.

  useGSAP(
    () => {
      const dir = Math.sign(week - prevWeek.current)

      prevWeek.current = week

      if (dir) {
        gsap.from(".schedule-day, .schedule-event", {
          x: dir * 28,

          opacity: 0,

          duration: 0.35,

          ease: "power2.out",

          clearProps: "transform,opacity",
        })
      }
    },

    { scope: calendarRef, dependencies: [week] },
  )

  // Events the agent just added or moved pop in, so the change is easy to spot.

  useGSAP(
    () => {
      const before = new Map(prevTasks.current.map((t) => [t.id, t]))

      const changed = tasks

        .filter((t) => {
          const old = before.get(t.id)

          return !old || old.date !== t.date || old.hour !== t.hour
        })

        .map((t) => `[data-task-id="${t.id}"]`)

      prevTasks.current = tasks

      if (changed.length) {
        gsap.fromTo(
          changed.join(","),

          { scale: 0.85, opacity: 0.3 },

          {
            scale: 1,

            opacity: 1,

            duration: 0.5,

            ease: "back.out(2)",

            clearProps: "transform,opacity",
          },
        )
      }
    },

    { scope: calendarRef, dependencies: [tasks] },
  )

  // Today's date, shifted by whole weeks so it tracks the week being viewed.

  const weekLabel = new Date(
    today.getFullYear(),

    today.getMonth(),

    today.getDate() + week * 7,
  ).toLocaleDateString("vi-VN", {
    day: "2-digit",

    month: "2-digit",

    year: "numeric",
  })

  const monday = new Date(today)

  monday.setDate(monday.getDate() - todayIndex + week * 7)

  const weekDays = Array.from(
    { length: 7 },

    (_, i) =>
      new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i),
  )

  const eventAt = (date: Date, hour: number) =>
    tasks.find((task) => task.date === toIsoDate(date) && task.hour === hour)

  const send = () => {
    const text = input.trim()

    if (!text) return

    const result = runPlannerCommand(text, tasks)

    setTasks(result.tasks)

    setReply(result.reply)

    notify?.(result.reply)

    setInput("")
  }

  return (
    <div className="planner-page">
      <Card
        className="dashboard-calendar planner-calendar"
        title="Lịch"
        action={
          <div className="planner-heading-action">
            <span className="sr-only" role="status" aria-live="polite">
              {reply}
            </span>
            <form
              className="planner-chat-form"
              onSubmit={(e) => {
                e.preventDefault()

                send()
              }}
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Nhập yêu cầu lịch học của bạn..."
                aria-label="Yêu cầu điều chỉnh lịch"
              />
              <Button
                className="primary"
                type="submit"
                aria-label="Gửi yêu cầu"
                disabled={!input.trim()}
              >
                <Send aria-hidden="true" size={14} />
              </Button>
            </form>

            <div className="dashboard-calendar-controls">
              <span className="calendar-week-label">{weekLabel}</span>
              {week !== 0 && (
                <Button
                  className="secondary calendar-today-btn"
                  onClick={() => setWeek(0)}
                >
                  Hôm nay
                </Button>
              )}
              <Button
                className="icon-button"
                aria-label="Tuần trước"
                onClick={() => setWeek(week - 1)}
              >
                <ChevronLeft aria-hidden="true" size={18} />
              </Button>
              <Button
                className="icon-button"
                aria-label="Tuần sau"
                onClick={() => setWeek(week + 1)}
              >
                <ChevronRight aria-hidden="true" size={18} />
              </Button>
            </div>
          </div>
        }
      >
        <div
          ref={calendarRef}
          className="dashboard-calendar-scroll"
          role="region"
          aria-label="Lịch trong tuần"
          tabIndex={0}
        >
          <div className="dashboard-schedule">
            <div className="schedule-header">
              {weekDays.map((_, i) => (
                <span
                  key={i}
                  className={`schedule-day ${
                    week === 0 && i === todayIndex ? "is-today" : ""
                  }`}
                >
                  <strong>
                    {["T2", "T3", "T4", "T5", "T6", "T7", "CN"][i]}
                  </strong>
                </span>
              ))}
            </div>
            {hours.map((hour) => (
              <div className="schedule-row" key={hour}>
                {weekDays.map((d, day) => {
                  const event = eventAt(d, hour)

                  return (
                    <div
                      className={`schedule-cell ${
                        week === 0 && day === todayIndex ? "today-column" : ""
                      }`}
                      key={day}
                    >
                      {event && (
                        <div
                          className={`schedule-event study priority-${
                            { Cao: "high", Thấp: "low" }[event.priority] ??
                            "mid"
                          } ${event.done ? "is-done" : ""}`}
                          data-task-id={event.id}
                          title={`${event.title} · ${event.time}`}
                        >
                          <strong>{event.title}</strong>
                          <small>{event.time}</small>
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
      </Card>
    </div>
  )
}
