import type { Dispatch, SetStateAction } from "react"
import { CalendarDays, CheckCheck } from "lucide-react"
import Button from "../components/ui/Button"
import Card from "../components/ui/Card"
import type { Task } from "../types/task"
import { daysUntil, formatShortDate } from "../utils/date"

export default function Dashboard({
  tasks,
  setTasks,
  go,
}: {
  tasks: Task[]
  setTasks: Dispatch<SetStateAction<Task[]>>
  go: (page: string) => void
}) {
  const completed = tasks.filter((task) => task.done).length
  const deadlines = tasks
    .filter((task) => !task.done)
    .sort((a, b) => a.deadline.localeCompare(b.deadline))
  return (
    <>
      <div
        className="dashboard-summary"
        role="group"
        aria-label="Tổng quan việc học"
      >
        <Card className="summary-card summary-purple">
          <div className="summary-main">
            <span className="summary-icon">
              <CheckCheck aria-hidden="true" size={27} />
            </span>
            <div>
              <strong>
                {completed} <span>/ {tasks.length}</span>
              </strong>
              <p>Công việc đã hoàn thành</p>
            </div>
          </div>
          <div
            className="summary-progress"
            role="progressbar"
            aria-label="Công việc đã hoàn thành"
            aria-valuenow={completed}
            aria-valuemin={0}
            aria-valuemax={Math.max(tasks.length, 1)}
          >
            <i
              style={{
                width: `${tasks.length ? (completed / tasks.length) * 100 : 0}%`,
              }}
            />
          </div>
        </Card>
        <Card className="summary-card summary-rose">
          <div className="summary-main">
            <span className="summary-icon">
              <CalendarDays aria-hidden="true" size={27} />
            </span>
            <div>
              <strong>{deadlines.length}</strong>
              <p>Hạn chót sắp tới</p>
            </div>
          </div>
        </Card>
      </div>
      <div className="dashboard-today-grid">
        <Card
          title="Công việc"
          action={<span className="count-label">{tasks.length} CÔNG VIỆC</span>}
        >
          <div className="today-task-list">
            {tasks.length === 0 && (
              <div className="empty-inline">
                <p>Chưa có công việc nào.</p>
                <Button className="text-button" onClick={() => go("Planner")}>
                  Mở Lập kế hoạch
                </Button>
              </div>
            )}
            {tasks.map((task) => (
              <div
                className={`today-task-row ${task.done ? "complete" : ""}`}
                key={task.id}
              >
                <input
                  type="checkbox"
                  className="task-checkbox"
                  checked={task.done}
                  aria-label={`Đánh dấu ${task.title} ${
                    task.done ? "chưa hoàn thành" : "hoàn thành"
                  }`}
                  onChange={() =>
                    setTasks((items) =>
                      items.map((item) =>
                        item.id === task.id
                          ? { ...item, done: !item.done }
                          : item,
                      ),
                    )
                  }
                />
                <div className="task-info">
                  <strong>{task.title}</strong>
                  <span>{task.course}</span>
                </div>
                <span className="task-time">{task.time}</span>
              </div>
            ))}
          </div>
        </Card>
        <Card
          title="Deadline sắp tới"
          action={
            <span className="count-label">{deadlines.length} HẠN CHÓT</span>
          }
        >
          <div className="deadline-list">
            {deadlines.length === 0 && (
              <div className="empty-inline">
                <p>Không có hạn chót nào sắp tới.</p>
              </div>
            )}
            {deadlines.map((task) => (
              <div className="deadline-row" key={task.id}>
                <span
                  className={`deadline-dot ${
                    daysUntil(task.deadline) <= 4 ? "urgent" : ""
                  }`}
                />
                <span className="deadline-info">
                  <strong>{task.title}</strong>
                  <small>{task.course}</small>
                </span>
                <span className="deadline-date">
                  <strong>{formatShortDate(task.deadline)}</strong>
                  <small>Còn {daysUntil(task.deadline)} ngày</small>
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  )
}
