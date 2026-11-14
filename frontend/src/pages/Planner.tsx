import WeekCalendar from "../features/planner/WeekCalendar"
import CompactWeekCalendar from "../features/planner/CompactWeekCalendar"
import MonthCalendar from "../features/planner/MonthCalendar"
import { addMonths } from "../features/planner/monthGrid"
import ProposalReview from "../features/planner/ProposalReview"
import CalendarDisplaySettings from "../features/planner/CalendarDisplaySettings"
import PlannerCommandComposer from "../features/planner/PlannerCommandComposer"
import { prefillPlannerCommand } from "../features/planner/plannerPrefill"
import {
  DEFAULT_DISPLAY_RANGES,
  displaySettingsVisible,
  type CalendarDisplayRanges,
} from "../features/planner/calendarDisplay"
import { usePlanner, type PlannerProps } from "../features/planner/usePlanner"
import { useEffect, useRef, useState } from "react"

import gsap from "gsap"

import { useGSAP } from "@gsap/react"

import { ChevronLeft, ChevronRight, ListTodo, X } from "lucide-react"

import Button from "../components/ui/Button"

import Card from "../components/ui/Card"

import { apiEnabled } from "../api/config"

import TaskPanel from "../features/planner/TaskPanel"

import type { Task } from "../types/task"

import {
  addCivilDays,
  civilWeekday,
  vietnamClock,
  vietnamDate,
} from "../utils/date"

export default function Planner({
  tasks,

  events,

  windows,

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
    feedback,
    shown,
    stale,
    send,
    approve,
    reject,
  } = usePlanner(
    {
      tasks,
      events,
      windows,
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
  const [calendarView, setCalendarView] =
    useState<"compact" | "detail" | "month">("compact")
  const [month, setMonth] = useState(() => vietnamDate().slice(0, 7))
  const [selectedMonthDate, setSelectedMonthDate] = useState<string | null>(
    null,
  )
  const [displayRanges, setDisplayRanges] = useState<CalendarDisplayRanges>(
    DEFAULT_DISPLAY_RANGES,
  )
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

  const pageRef = useRef<HTMLDivElement>(null)

  const prevWeek = useRef(0)

  const source = apiEnabled ? events : tasks

  const prevTasks = useRef(source)

  // Khi đổi tuần, nội dung lịch trượt vào theo hướng di chuyển.

  useGSAP(
    () => {
      const dir = Math.sign(week - prevWeek.current)

      prevWeek.current = week

      const targets = pageRef.current?.querySelectorAll(
        ".schedule-day, .schedule-event",
      )

      if (dir && targets?.length) {
        gsap.from(targets, {
          x: dir * 28,

          opacity: 0,

          duration: 0.35,

          ease: "power2.out",

          clearProps: "transform,opacity",
        })
      }
    },

    { scope: pageRef, dependencies: [week] },
  )

  // Sự kiện agent vừa thêm hoặc dời hiện bật lên để người dùng dễ nhận ra thay đổi.

  useGSAP(
    () => {
      const before = new Map(prevTasks.current.map((t) => [t.id, t]))

      const changed = new Set(
        source

          .filter((t) => {
            const old = before.get(t.id)

            return !old || old.date !== t.date || old.hour !== t.hour
          })

          .map((t) => t.id),
      )

      const targets = Array.from(
        pageRef.current?.querySelectorAll<HTMLElement>("[data-task-id]") ?? [],
      ).filter((element) => changed.has(element.dataset.taskId ?? ""))

      prevTasks.current = source

      if (targets.length) {
        gsap.fromTo(
          targets,

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

    { scope: pageRef, dependencies: [source] },
  )

  // GSAP điều khiển khung công việc vì reduced-motion vô hiệu hóa CSS transition.

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

      const panel = pageRef.current?.querySelector(".task-panel-wrap")

      if (!panel || !pageRef.current) return

      gsap.fromTo(panel, from, { ...to, ...opts })

      gsap.fromTo(
        pageRef.current,

        { columnGap: taskPanelOpen ? 0 : 8 },

        { columnGap: taskPanelOpen ? 8 : 0, ...opts },
      )
    },

    { scope: pageRef, dependencies: [taskPanelOpen] },
  )

  // Block đề xuất hiện bật lên để người dùng dễ thấy thay đổi trước khi duyệt.

  useGSAP(
    () => {
      const targets = pageRef.current?.querySelectorAll(".is-proposed")

      if (proposal && targets?.length)
        gsap.fromTo(
          targets,

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

    { scope: pageRef, dependencies: [proposal] },
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
  const chooseView = (view: "compact" | "detail" | "month") => {
    if (view === "month" && calendarView !== "month") {
      setMonth(mondayKey.slice(0, 7))
      setSelectedMonthDate(null)
    }
    if (calendarView === "month" && view !== "month") {
      const date = selectedMonthDate ?? `${month}-01`
      const monday = addCivilDays(date, -civilWeekday(date))
      const todayMonday = addCivilDays(todayKey, -todayIndex)
      setWeek(
        Math.round(
          (Date.parse(`${monday}T00:00:00Z`) -
            Date.parse(`${todayMonday}T00:00:00Z`)) /
            (7 * 86400000),
        ),
      )
    }
    setCalendarView(view)
  }
  const weekDays = Array.from(
    { length: 7 },
    (_, i) => new Date(`${addCivilDays(mondayKey, i)}T12:00:00Z`),
  )
  const dateOf = (date: Date) => vietnamDate(date)

  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Nhấn ô trống để bắt đầu lệnh thêm vào khung giờ đó.

  const prefill = (date: Date, minuteOfDay: number) =>
    prefillPlannerCommand(
      date,
      minuteOfDay,
      apiEnabled,
      setInput,
      inputRef.current,
    )

  const changeOf = new Map(proposal?.changes.map((c) => [c.task.id, c.kind]))

  const calendarEvents = [
    ...shown,
    ...(proposal?.changes
      .filter((change) => change.kind === "removed")
      .map((change) => change.task) ?? []),
  ]
  const weekEmpty = !calendarEvents.some(
    (event) =>
      event.date && weekDays.some((date) => dateOf(date) === event.date),
  )

  return (
    <div
      ref={pageRef}
      className={`planner-page ${
        calendarView !== "detail" ? "is-compact" : ""
      } ${taskPanelOpen ? "" : "is-tasks-closed"}`}
    >
      <Card
        className="dashboard-calendar planner-calendar"
        title="Lịch"
        action={
          <div className="planner-heading-action">
            <PlannerCommandComposer
              input={input}
              setInput={setInput}
              send={send}
              busy={busy}
              apiMode={apiEnabled}
              feedback={feedback}
              textareaRef={inputRef}
            />

            <div className="dashboard-calendar-controls">
              {(["compact", "month", "detail"] as const).map((view) => (
                <Button
                  key={view}
                  className="secondary calendar-view-toggle"
                  type="button"
                  aria-pressed={calendarView === view}
                  onClick={() => chooseView(view)}
                >
                  {view === "compact"
                    ? "Tuần"
                    : view === "month"
                      ? "Tháng"
                      : "Chi tiết giờ"}
                </Button>
              ))}
              <span className="calendar-week-label">
                {calendarView === "month"
                  ? `Tháng ${Number(month.slice(5))}/${month.slice(0, 4)}`
                  : weekLabel}
              </span>
              {(calendarView === "month" || week !== 0) && (
                <Button
                  className="secondary calendar-today-btn"
                  onClick={() => {
                    if (calendarView === "month") {
                      setMonth(todayKey.slice(0, 7))
                      setSelectedMonthDate(todayKey)
                    } else setWeek(0)
                  }}
                >
                  Hôm nay
                </Button>
              )}
              <Button
                className="icon-button"
                aria-label={
                  calendarView === "month" ? "Tháng trước" : "Tuần trước"
                }
                onClick={() => {
                  if (calendarView === "month") {
                    setMonth(addMonths(month, -1))
                    setSelectedMonthDate(null)
                  } else setWeek(week - 1)
                }}
              >
                <ChevronLeft aria-hidden="true" size={18} />
              </Button>
              <Button
                className="icon-button"
                aria-label={calendarView === "month" ? "Tháng sau" : "Tuần sau"}
                onClick={() => {
                  if (calendarView === "month") {
                    setMonth(addMonths(month, 1))
                    setSelectedMonthDate(null)
                  } else setWeek(week + 1)
                }}
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
        {displaySettingsVisible(calendarView) && (
          <CalendarDisplaySettings
            ranges={displayRanges}
            onChange={setDisplayRanges}
          />
        )}
        <p className="planner-legend" aria-label="Chú thích">
          <span className="legend-confirmed">Đã xác nhận</span>

          <span className="legend-proposed">Đề xuất</span>
          <span>
            {calendarView === "month"
              ? "Chọn ngày để xem chi tiết"
              : weekEmpty
                ? "Tuần này chưa có việc."
                : "Chọn giờ để nhập yêu cầu"}
          </span>
        </p>
        {calendarView === "compact" ? (
          <CompactWeekCalendar
            weekDays={weekDays}
            todayKey={todayKey}
            events={calendarEvents}
            windows={windows ?? []}
            availability={
              apiEnabled ? [] : (proposal?.next.availability ?? availability)
            }
            changeOf={changeOf}
            proposedWindowIds={
              new Set(proposal?.windowChanges.map((change) => change.window.id))
            }
          />
        ) : calendarView === "month" ? (
          <MonthCalendar
            month={month}
            todayKey={todayKey}
            selectedDate={selectedMonthDate}
            onSelect={setSelectedMonthDate}
            events={calendarEvents}
            windows={windows ?? []}
            availability={
              apiEnabled ? [] : (proposal?.next.availability ?? availability)
            }
            changeOf={changeOf}
          />
        ) : (
          <WeekCalendar
            calendarRef={calendarRef}
            weekDays={weekDays}
            week={week}
            todayIndex={todayIndex}
            ranges={displayRanges}
            events={calendarEvents}
            windows={windows ?? []}
            availability={
              apiEnabled ? [] : (proposal?.next.availability ?? availability)
            }
            proposedWindowIds={
              new Set(proposal?.windowChanges.map((change) => change.window.id))
            }
            prefill={prefill}
            changeOf={changeOf}
            nowHour={nowHour}
            nowMinutes={nowMinutes}
          />
        )}
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
