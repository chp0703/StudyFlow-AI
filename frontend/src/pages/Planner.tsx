import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react"

import gsap from "gsap"

import { useGSAP } from "@gsap/react"

import {
  Check,
  ChevronLeft,
  ChevronRight,
  Send,
  Sparkles,
  X,
} from "lucide-react"

import Button from "../components/ui/Button"

import Card from "../components/ui/Card"

import {
  FIRST_HOUR,
  LAST_HOUR,
  runPlannerCommand,
} from "../features/planner/plannerAgent"

import {
  describeChanges,
  diffTasks,
  isStale,
} from "../features/planner/proposal"

import type { Proposal } from "../types/planner"

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

  proposal,

  setProposal,

  revision,

  setRevision,

  notify,
}: {
  tasks: Task[]

  setTasks: Dispatch<SetStateAction<Task[]>>

  proposal: Proposal | null

  setProposal: Dispatch<SetStateAction<Proposal | null>>

  revision: number

  setRevision: Dispatch<SetStateAction<number>>

  notify?: (message: string) => void
}) {
  const [input, setInput] = useState("")

  const [reply, setReply] = useState("")

  const [plannerNotice, setPlannerNotice] = useState("")

  const noticeRef = useRef<HTMLDivElement>(null)

  const noticeTimer = useRef<number>(0)

  const showPlannerNotice = (message: string) => {
    window.clearTimeout(noticeTimer.current)

    setPlannerNotice(message)

    noticeTimer.current = window.setTimeout(() => closePlannerNotice(), 3500)
  }

  const closePlannerNotice = () => {
    window.clearTimeout(noticeTimer.current)

    if (!noticeRef.current) return setPlannerNotice("")

    gsap.to(noticeRef.current, {
      y: 16,

      opacity: 0,

      duration: 0.25,

      ease: "power2.in",

      onComplete: () => setPlannerNotice(""),
    })
  }

  useEffect(() => () => window.clearTimeout(noticeTimer.current), [])

  useGSAP(
    () => {
      if (plannerNotice)
        gsap.fromTo(
          noticeRef.current,

          { y: 24, opacity: 0 },

          { y: 0, opacity: 1, duration: 0.4, ease: "back.out(1.6)" },
        )
    },

    { dependencies: [plannerNotice] },
  )

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

  // Proposed blocks pop in so the pending change is easy to spot before approving.

  useGSAP(
    () => {
      if (proposal)
        gsap.fromTo(
          ".is-proposed",

          { scale: 0.9, opacity: 0.4 },

          {
            scale: 1,

            opacity: 1,

            duration: 0.45,

            ease: "back.out(2)",

            clearProps: "transform,opacity",
          },
        )
    },

    { scope: calendarRef, dependencies: [proposal] },
  )

  // A plain reply (error or no-op) fades away on its own; a proposal stays until decided.

  useEffect(() => {
    if (!reply || proposal) return

    const timer = window.setTimeout(() => setReply(""), 8000)

    return () => window.clearTimeout(timer)
  }, [reply, proposal])

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

  // The calendar shows the proposal's preview while one is pending; committed tasks otherwise.

  const shown = proposal ? proposal.next.tasks : tasks

  const changeOf = new Map(proposal?.changes.map((c) => [c.task.id, c.kind]))

  const slotMatch = (task: Task, date: Date, hour: number) =>
    task.date === toIsoDate(date) && task.hour === hour

  const eventAt = (date: Date, hour: number) =>
    shown.find((task) => slotMatch(task, date, hour)) ??
    proposal?.changes.find(
      (c) => c.kind === "removed" && slotMatch(c.task, date, hour),
    )?.task

  const stale = proposal ? isStale(proposal, revision) : false

  const send = () => {
    const text = input.trim()

    if (!text) return

    // Commands stack on a pending proposal, but are always diffed against the committed schedule.

    const result = runPlannerCommand(text, shown)

    const changes = diffTasks(tasks, result.tasks)

    setReply(result.reply)

    setInput("")

    if (!changes.length) return setProposal(null)

    setProposal({
      id: proposal?.id ?? crypto.randomUUID(),

      createdAt: proposal?.createdAt ?? Date.now(),

      baseRevision: proposal?.baseRevision ?? revision,

      next: { tasks: result.tasks },

      changes,

      reply: result.reply,
    })
  }

  const approve = () => {
    if (!proposal || stale) return

    setTasks(proposal.next.tasks)

    setRevision((r) => r + 1)

    setProposal(null)

    setReply("")

    showPlannerNotice("Đã lưu thay đổi vào lịch.")
  }

  const reject = () => {
    setProposal(null)

    setReply("")
  }

  return (
    <div className="planner-page">
      <Card
        className="dashboard-calendar planner-calendar"
        title="Lịch"
        action={
          <div className="planner-heading-action">
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
        <div className="planner-status" role="status" aria-live="polite">
          {proposal ? (
            <div className={`proposal-bar ${stale ? "is-stale" : ""}`}>
              <Sparkles aria-hidden="true" size={16} />
              <span className="proposal-text">
                <strong>
                  Đề xuất: {describeChanges(proposal.changes) || "không đổi"}
                </strong>
                <span>
                  {stale
                    ? "Lịch đã thay đổi từ lúc tạo đề xuất (STALE_PLAN_VERSION). Hãy từ chối và tạo lại."
                    : reply || proposal.reply}
                </span>
              </span>
              <Button className="secondary proposal-reject" onClick={reject}>
                <X aria-hidden="true" size={14} /> Từ chối
              </Button>
              <Button
                className="primary proposal-approve"
                onClick={approve}
                disabled={stale}
              >
                <Check aria-hidden="true" size={14} /> Duyệt
              </Button>
            </div>
          ) : (
            reply && <p className="planner-reply">{reply}</p>
          )}
        </div>
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
        {plannerNotice && (
          <div className="planner-notice-wrap">
            <div className="planner-notice" ref={noticeRef}>
              <span role="status">{plannerNotice}</span>
              <button
                type="button"
                className="planner-notice-close"
                aria-label="Đóng thông báo"
                onClick={closePlannerNotice}
              >
                <X size={14} aria-hidden="true" />
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
