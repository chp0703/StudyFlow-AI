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
  ListTodo,
  Send,
  Sparkles,
  X,
} from "lucide-react"

import { api } from "../api"

import { apiEnabled } from "../api/config"

import { ApiError, errorText } from "../api/client"

import { proposalFromReply } from "../api/mappers"

import { savePending } from "../api/pending"

import type { OrchestratorReply } from "../api/types"

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
  diffWindows,
  isStale,
} from "../features/planner/proposal"

import TaskPanel from "../features/planner/TaskPanel"

import type { Proposal, TimeWindow } from "../types/planner"

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

  events,

  userId,

  conversationId,

  reload,

  setTasks,

  availability,

  setAvailability,

  proposal,

  setProposal,

  revision,

  setRevision,

  notify,
}: {
  tasks: Task[]

  // Calendar events: one per study block in API mode, the tasks themselves in demo mode.

  events: Task[]

  userId: string

  conversationId: string

  reload: () => Promise<void>

  setTasks: Dispatch<SetStateAction<Task[]>>

  availability: TimeWindow[]

  setAvailability: Dispatch<SetStateAction<TimeWindow[]>>

  proposal: Proposal | null

  setProposal: Dispatch<SetStateAction<Proposal | null>>

  revision: number

  setRevision: Dispatch<SetStateAction<number>>

  notify?: (message: string) => void
}) {
  const [input, setInput] = useState("")

  const [busy, setBusy] = useState(false)

  // A retried send of the same text keeps its idempotency key, so a lost response is never executed twice.

  const attempt = useRef<{ text: string; key: string } | null>(null)

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

  const [taskPanelOpen, setTaskPanelOpen] = useState(() => {
    try {
      const saved = localStorage.getItem("studyflow_task_panel_open")

      return saved !== null ? saved === "true" : true
    } catch {
      return true
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem("studyflow_task_panel_open", String(taskPanelOpen))
    } catch {
      // Ignore storage errors in restricted contexts
    }
  }, [taskPanelOpen])

  const calendarRef = useRef<HTMLDivElement>(null)

  const prevWeek = useRef(0)

  const source = apiEnabled ? events : tasks

  const prevTasks = useRef(source)

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

      const changed = source

        .filter((t) => {
          const old = before.get(t.id)

          return !old || old.date !== t.date || old.hour !== t.hour
        })

        .map((t) => `[data-task-id="${t.id}"]`)

      prevTasks.current = source

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

    { scope: calendarRef, dependencies: [source] },
  )

  // GSAP drives the task panel because CSS transitions are disabled by reduced-motion.

  const pageRef = useRef<HTMLDivElement>(null)

  const panelSeen = useRef(taskPanelOpen)

  useGSAP(
    () => {
      if (panelSeen.current === taskPanelOpen) return

      panelSeen.current = taskPanelOpen

      const [from, to] = taskPanelOpen
        ? [
            { width: 0, opacity: 0, x: 16 },

            { width: 300, opacity: 1, x: 0 },
          ]
        : [
            { width: 300, opacity: 1, x: 0 },

            { width: 0, opacity: 0, x: 16 },
          ]

      const opts = { duration: 0.4, ease: "power3.inOut", clearProps: "all" }

      gsap.fromTo(".task-panel-wrap", from, { ...to, ...opts })

      gsap.fromTo(
        ".planner-page",

        { columnGap: taskPanelOpen ? 0 : 8 },

        { columnGap: taskPanelOpen ? 8 : 0, ...opts },
      )
    },

    { scope: pageRef, dependencies: [taskPanelOpen] },
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

  const shown = proposal ? proposal.next.tasks : source

  const shownWindows = proposal ? proposal.next.availability : availability

  const windowAt = (date: Date, hour: number) =>
    shownWindows.find((w) => w.id === `${toIsoDate(date)}-${hour}`)

  const proposedWindows = new Set(
    proposal?.windowChanges

      .filter((c) => c.kind === "added")

      .map((c) => c.window.id),
  )

  const inputRef = useRef<HTMLInputElement>(null)

  // Clicking an empty cell starts an add command for that slot.

  const prefill = (date: Date, hour: number) => {
    const d = `${date.getDate()}/${date.getMonth() + 1}`

    const text = apiEnabled
      ? `Thêm công việc hạn ngày ${d}, làm khoảng 60 phút`
      : `thêm  lúc ${hour}h ngày ${d}`

    setInput(text)

    requestAnimationFrame(() => {
      inputRef.current?.focus()

      inputRef.current?.setSelectionRange(
        apiEnabled ? text.length : 5,
        apiEnabled ? text.length : 5,
      )
    })
  }

  const changeOf = new Map(proposal?.changes.map((c) => [c.task.id, c.kind]))

  const slotMatch = (task: Task, date: Date, hour: number) =>
    task.date === toIsoDate(date) && task.hour === hour

  const eventAt = (date: Date, hour: number) =>
    shown.find((task) => slotMatch(task, date, hour)) ??
    proposal?.changes.find(
      (c) => c.kind === "removed" && slotMatch(c.task, date, hour),
    )?.task

  const weekEmpty =
    !shown.some(
      (t) => t.date && weekDays.some((d) => toIsoDate(d) === t.date),
    ) &&
    !shownWindows.some((w) => weekDays.some((d) => toIsoDate(d) === w.date))

  const stale = proposal ? isStale(proposal, revision) : false

  // API mode: show what the server answered. A reply that waits for approval becomes the pending proposal.

  const showReply = async (r: OrchestratorReply) => {
    if (r.state === "AWAITING_APPROVAL") {
      const next = proposalFromReply(r, {
        tasks,
        events,
        availability,
        revision,
      })

      setProposal(next)

      setReply(r.message)

      if (next && r.action_reference)
        savePending(userId, {
          conversationId,
          reference: r.action_reference,
        })

      return
    }

    setProposal(null)

    savePending(userId, null)

    const questions = r.questions.map((q) => q.message).join(" ")

    setReply(questions ? `${r.message} ${questions}` : r.message)

    if (r.state === "SUCCEEDED") await reload()
  }

  const sendToServer = async (text: string) => {
    const key =
      attempt.current?.text === text ? attempt.current.key : crypto.randomUUID()

    attempt.current = { text, key }

    setBusy(true)

    try {
      await showReply(await api.sendMessage(conversationId, text, key))

      attempt.current = null

      setInput("")
    } catch (e) {
      setReply(errorText(e))

      // Only a failure that may have reached the server keeps the key for the retry.

      if (e instanceof ApiError && !e.retryable) attempt.current = null
    } finally {
      setBusy(false)
    }
  }

  const send = () => {
    const text = input.trim()

    if (!text || busy) return

    if (apiEnabled) return void sendToServer(text)

    // Commands stack on a pending proposal, but are always diffed against the committed schedule.

    const result = runPlannerCommand(text, shown, shownWindows)

    const changes = diffTasks(tasks, result.tasks)

    const windowChanges = diffWindows(availability, result.availability)

    setReply(result.reply)

    setInput("")

    if (!changes.length && !windowChanges.length) return setProposal(null)

    setProposal({
      id: proposal?.id ?? crypto.randomUUID(),

      createdAt: proposal?.createdAt ?? Date.now(),

      baseRevision: proposal?.baseRevision ?? revision,

      next: { tasks: result.tasks, availability: result.availability },

      changes,

      windowChanges,

      issues: result.issues ?? proposal?.issues ?? [],

      reply: result.reply,
    })
  }

  const decideOnServer = async (decision: "APPROVE" | "REJECT") => {
    if (!proposal?.server || busy) return

    setBusy(true)

    try {
      const r = await api.decide(
        conversationId,
        proposal.server.reference,
        decision,
      )

      setProposal(null)

      savePending(userId, null)

      await reload()

      if (r.state === "AWAITING_APPROVAL") await showReply(r)
      else {
        setReply("")

        showPlannerNotice(r.message)
      }
    } catch (e) {
      setReply(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const approve = () => {
    if (apiEnabled) return void decideOnServer("APPROVE")

    if (!proposal || stale) return

    setTasks(proposal.next.tasks)

    setAvailability(proposal.next.availability)

    setRevision((r) => r + 1)

    setProposal(null)

    setReply("")

    showPlannerNotice("Đã lưu thay đổi vào lịch.")
  }

  const reject = () => {
    if (apiEnabled) return void decideOnServer("REJECT")

    setProposal(null)

    setReply("")
  }

  return (
    <div
      ref={pageRef}
      className={`planner-page ${taskPanelOpen ? "" : "is-tasks-closed"}`}
    >
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
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Nhập yêu cầu lịch học"
                aria-label="Yêu cầu điều chỉnh lịch"
                disabled={busy}
              />
              <Button
                className="primary"
                type="submit"
                aria-label="Gửi yêu cầu"
                disabled={!input.trim() || busy}
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
              <Button
                className={`secondary planner-task-toggle ${
                  taskPanelOpen ? "is-active" : ""
                }`}
                type="button"
                aria-label={
                  taskPanelOpen
                    ? "Đóng danh sách công việc"
                    : "Mở danh sách công việc"
                }
                aria-expanded={taskPanelOpen}
                onClick={() => setTaskPanelOpen((prev) => !prev)}
                title={
                  taskPanelOpen
                    ? "Đóng danh sách công việc"
                    : "Mở danh sách công việc"
                }
              >
                <ListTodo aria-hidden="true" size={15} />
                <span>Công việc</span>
                {shown.length > 0 && (
                  <span className="planner-task-count">{shown.length}</span>
                )}
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
                  {proposal.server ? (
                    proposal.server.title
                  ) : (
                    <>
                      Đề xuất:{" "}
                      {describeChanges(
                        proposal.changes,
                        proposal.windowChanges,
                      ) || "không đổi"}
                    </>
                  )}
                </strong>
                {proposal.server && proposal.server.details.length > 0 && (
                  <span>
                    {proposal.server.details
                      .map((d) => `${d.label}: ${d.value}`)
                      .join(" · ")}
                  </span>
                )}
                <span>
                  {stale
                    ? "Lịch đã thay đổi từ lúc tạo đề xuất (STALE). Hãy từ chối và tạo lại."
                    : reply || proposal.reply}
                </span>
                {proposal.issues.length > 0 && (
                  <details className="proposal-issues">
                    <summary>Chưa xếp được ({proposal.issues.length})</summary>
                    <ul>
                      {proposal.issues.map((i) => (
                        <li key={i.taskId}>
                          {i.code}: {i.message}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </span>
              <Button
                className="secondary proposal-reject"
                onClick={reject}
                disabled={busy}
              >
                <X aria-hidden="true" size={14} /> Từ chối
              </Button>
              <Button
                className="primary proposal-approve"
                onClick={approve}
                disabled={stale || busy}
              >
                <Check aria-hidden="true" size={14} /> Duyệt
              </Button>
            </div>
          ) : (
            reply && <p className="planner-reply">{reply}</p>
          )}
        </div>
        <p className="planner-legend" aria-label="Chú thích">
          <span className="legend-confirmed">Đã xác nhận</span>

          <span className="legend-free">Rảnh</span>
          <span className="legend-busy">Bận</span>
          <span className="legend-proposed">Đề xuất</span>
          <span>
            {weekEmpty ? "Tuần này chưa có việc." : "Bấm ô trống để thêm việc"}
          </span>
        </p>
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
                <span className="schedule-hour" aria-hidden="true">
                  {`${String(hour).padStart(2, "0")}:00`}
                </span>
                {weekDays.map((d, day) => {
                  const event = eventAt(d, hour)

                  const win = windowAt(d, hour)

                  return (
                    <div
                      className={`schedule-cell ${
                        week === 0 && day === todayIndex ? "today-column" : ""
                      } ${win ? `is-${win.kind}` : ""} ${
                        win && proposedWindows.has(win.id) ? "is-proposed" : ""
                      }`}
                      key={day}
                      onClick={event ? undefined : () => prefill(d, hour)}
                    >
                      {win && (
                        <span className="window-tag">
                          {win.kind === "free" ? "Rảnh" : "Bận"}
                        </span>
                      )}
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

      <div
        className="task-panel-wrap"
        aria-hidden={!taskPanelOpen}
        inert={!taskPanelOpen ? true : undefined}
      >
        <TaskPanel
          tasks={apiEnabled ? tasks : shown}
          proposedIds={
            new Set(
              proposal?.server
                ? proposal.server.taskIds
                : proposal?.changes

                    .filter((c) => c.kind !== "removed")

                    .map((c) => c.task.id),
            )
          }
          week={weekDays.map(toIsoDate)}
          onClose={() => setTaskPanelOpen(false)}
        />
      </div>
    </div>
  )
}
