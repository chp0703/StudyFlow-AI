import { useState, type Dispatch, type SetStateAction } from "react"

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

const HINT =
  "Ví dụ: thêm Ôn giải tích thứ 3 lúc 19h · dời Ôn giải tích sang thứ 5 lúc 9h · xóa Ôn giải tích"

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
}: {
  tasks: Task[]

  setTasks: Dispatch<SetStateAction<Task[]>>
}) {
  const [input, setInput] = useState("")

  const [reply, setReply] = useState(HINT)

  const [week, setWeek] = useState(0)

  const weekLabel =
    week === 0 ? "Tuần này" : week > 0 ? `+${week} tuần` : `${week} tuần`

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

    setInput("")
  }

  return (
    <div className="planner-page">
      <Card className="planner-chat">
        <div className="planner-chat-title">
          <h2>Trợ lý lập kế hoạch</h2>
          <p role="status" aria-live="polite" title={reply}>
            {reply}
          </p>
        </div>
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
            <Send aria-hidden="true" size={16} />
          </Button>
        </form>
      </Card>
      <Card
        className="dashboard-calendar planner-calendar"
        title="Lịch"
        action={
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
        }
      >
        <div
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
