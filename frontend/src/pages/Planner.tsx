import WeekCalendar from "../features/planner/WeekCalendar"
import ProposalReview from "../features/planner/ProposalReview"
import WorkingTimeEditor from "../features/planner/WorkingTimeEditor"
import { usePlanner, type PlannerProps } from "../features/planner/usePlanner"
import { useEffect, useRef, useState } from "react"

import gsap from "gsap"

import { useGSAP } from "@gsap/react"

import { ChevronLeft, ChevronRight, ListTodo, Send, X } from "lucide-react"

import Button from "../components/ui/Button"

import Card from "../components/ui/Card"

import { FIRST_HOUR, LAST_HOUR } from "../features/planner/plannerAgent"

import { apiEnabled } from "../api/config"

import TaskPanel from "../features/planner/TaskPanel"

import type { Task } from "../types/task"

import {
  addCivilDays,
  civilWeekday,
  vietnamClock,
  vietnamDate,
} from "../utils/date"

const hours = Array.from(
  { length: LAST_HOUR - FIRST_HOUR + 1 },

  (_, i) => i + FIRST_HOUR,
)

export default function Planner({
  tasks,

  events,

  windows = [],

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
}: PlannerProps) {
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

  const {
    busy,
    input,
    setInput,
    reply,
    setReply,
    shown,
    shownWindows,
    stale,
    send,
    prepareAvailability,
    approve,
    reject,
  } = usePlanner(
    {
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
    },
    showPlannerNotice,
  )

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
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  const todayKey = vietnamDate(now)
  const todayIndex = civilWeekday(todayKey)
  const [nowHour, nowMinutes] = vietnamClock(now).split(":").map(Number)

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
      // Bỏ qua lỗi lưu trữ trong môi trường bị hạn chế quyền
    }
  }, [taskPanelOpen])

  const calendarRef = useRef<HTMLDivElement>(null)

  const prevWeek = useRef(0)

  const source = apiEnabled ? events : tasks

  const prevTasks = useRef(source)

  // Khi đổi tuần, nội dung lịch trượt vào theo hướng di chuyển.

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

  // Sự kiện agent vừa thêm hoặc dời hiện bật lên để người dùng dễ nhận ra thay đổi.

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

  // GSAP điều khiển khung công việc vì reduced-motion vô hiệu hóa CSS transition.

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

  // Block đề xuất hiện bật lên để người dùng dễ thấy thay đổi trước khi duyệt.

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

  // Phản hồi thông thường (lỗi hoặc không thay đổi) tự mờ đi; đề xuất giữ lại đến khi có quyết định.

  useEffect(() => {
    if (!reply || proposal) return

    const timer = window.setTimeout(() => setReply(""), 8000)

    return () => window.clearTimeout(timer)
  }, [reply, proposal])

  // Ngày hôm nay dịch theo số tuần nguyên để theo đúng tuần đang xem.

  const weekLabel = addCivilDays(todayKey, week * 7)
    .split("-")
    .reverse()
    .join("/")
  const mondayKey = addCivilDays(todayKey, -todayIndex + week * 7)
  const weekDays = Array.from(
    { length: 7 },
    (_, i) => new Date(`${addCivilDays(mondayKey, i)}T12:00:00Z`),
  )
  const dateOf = (date: Date) => vietnamDate(date)

  const windowAt = (date: Date, hour: number) =>
    shownWindows.find((w) => w.id === `${dateOf(date)}-${hour}`)

  const proposedWindows = new Set(
    proposal?.windowChanges

      .filter((c) => c.kind === "added")

      .map((c) => c.window.id),
  )

  const inputRef = useRef<HTMLInputElement>(null)

  // Nhấn ô trống để bắt đầu lệnh thêm vào khung giờ đó.

  const prefill = (date: Date, hour: number) => {
    const [, month, day] = dateOf(date).split("-")
    const d = `${Number(day)}/${Number(month)}`

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
    task.date === dateOf(date) && task.hour === hour

  const eventAt = (date: Date, hour: number) =>
    shown.find((task) => slotMatch(task, date, hour)) ??
    proposal?.changes.find(
      (c) => c.kind === "removed" && slotMatch(c.task, date, hour),
    )?.task

  const weekEmpty =
    !shown.some((t) => t.date && weekDays.some((d) => dateOf(d) === t.date)) &&
    !shownWindows.some((w) => weekDays.some((d) => dateOf(d) === w.date))

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
        <ProposalReview
          proposal={proposal}
          stale={stale}
          busy={busy}
          reply={reply}
          approve={approve}
          reject={reject}
        />
        {apiEnabled && (
          <WorkingTimeEditor
            windows={windows}
            busy={busy}
            pending={!!proposal}
            prepare={prepareAvailability}
          />
        )}
        <p className="planner-legend" aria-label="Chú thích">
          <span className="legend-confirmed">Đã xác nhận</span>

          <span className="legend-free">Thời gian học</span>
          <span className="legend-busy">Bận</span>
          <span className="legend-proposed">Đề xuất</span>
          <span>
            {weekEmpty ? "Tuần này chưa có việc." : "Bấm ô trống để thêm việc"}
          </span>
        </p>
        <WeekCalendar
          calendarRef={calendarRef}
          weekDays={weekDays}
          week={week}
          todayIndex={todayIndex}
          hours={hours}
          eventAt={eventAt}
          windowAt={windowAt}
          proposedWindows={proposedWindows}
          prefill={prefill}
          changeOf={changeOf}
          nowHour={nowHour}
          nowMinutes={nowMinutes}
        />
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
          week={weekDays.map(dateOf)}
          onClose={() => setTaskPanelOpen(false)}
        />
      </div>
    </div>
  )
}
