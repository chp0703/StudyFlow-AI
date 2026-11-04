import { useState, type Dispatch, type SetStateAction } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import Button from "../components/ui/Button"
import Card from "../components/ui/Card"
import Modal from "../components/ui/Modal"
import type { Task } from "../types/task"
import { today, toIsoDate } from "../utils/date"

const emptyForm = {
  title: "",
  course: "",
  priority: "Trung bình",
  effort: 30,
  deadline: toIsoDate(today),
}
const todayIndex = (today.getDay() + 6) % 7

export default function Planner({
  tasks,
  setTasks,
  query,
  notify,
}: {
  tasks: Task[]
  setTasks: Dispatch<SetStateAction<Task[]>>
  query: string
  notify: (message: string) => void
}) {
  const [form, setForm] = useState(emptyForm)
  const [editing, setEditing] = useState<Task | null>(null)
  const [open, setOpen] = useState(false)
  const [week, setWeek] = useState(0)
  const [period, setPeriod] = useState("Week")
  const [selectedDay, setSelectedDay] = useState(todayIndex)

  const monday = new Date(today)
  monday.setDate(monday.getDate() - todayIndex + week * 7)
  const weekDays = Array.from(
    { length: 7 },
    (_, i) =>
      new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + i),
  )
  const filteredTasks = tasks.filter((task) =>
    `${task.title} ${task.course}`
      .toLocaleLowerCase("vi")
      .includes(query.trim().toLocaleLowerCase("vi")),
  )

  const openForm = (task: Task | null) => {
    setEditing(task)
    setForm(
      task
        ? {
            title: task.title,
            course: task.course,
            priority: task.priority,
            effort: task.effort,
            deadline: task.deadline,
          }
        : emptyForm,
    )
    setOpen(true)
  }
  const patch = (value: Partial<typeof emptyForm>) =>
    setForm((f) => ({ ...f, ...value }))

  return (
    <>
      <div className="page-toolbar">
        <div />
        <div>
          <Button className="primary" onClick={() => openForm(null)}>
            Thêm công việc
          </Button>
        </div>
      </div>
      <Card
        className="planner-task-card"
        title="Công việc"
        action={
          <span className="count-label">{filteredTasks.length} CÔNG VIỆC</span>
        }
      >
        {filteredTasks.length ? (
          <div className="planner-task-list">
            {filteredTasks.map((task) => (
              <div className="planner-task-row" key={task.id}>
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
                <div className="planner-task-info">
                  <strong className={task.done ? "is-done" : ""}>
                    {task.title}
                  </strong>
                  <span>
                    {task.course} · {task.time}
                  </span>
                </div>
                <span
                  className={`priority-badge ${
                    task.priority === "Cao" ? "is-high" : ""
                  }`}
                >
                  {task.priority}
                </span>
                <time dateTime={task.deadline}>
                  Hạn{" "}
                  {new Date(`${task.deadline}T12:00:00`).toLocaleDateString(
                    "vi-VN",
                    { day: "numeric", month: "numeric", year: "numeric" },
                  )}
                </time>
                <Button className="secondary" onClick={() => openForm(task)}>
                  Chỉnh sửa
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-inline">
            <p>
              {query.trim()
                ? "Không có công việc phù hợp với từ khóa."
                : "Chưa có công việc nào."}
            </p>
            <Button className="primary" onClick={() => openForm(null)}>
              Thêm công việc
            </Button>
          </div>
        )}
      </Card>
      <Card
        className="dashboard-calendar"
        title="Lịch"
        action={
          <div className="dashboard-calendar-controls">
            <span>
              {monday.toLocaleDateString("vi-VN", {
                month: "long",
                year: "numeric",
              })}
            </span>
            <Button
              className="secondary"
              onClick={() => {
                setWeek(0)
                setSelectedDay(todayIndex)
              }}
            >
              Hôm nay
            </Button>
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
            <select
              aria-label="Chế độ xem lịch"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
            >
              <option value="Week">Tuần</option>
              <option value="Hôm nay">Ngày</option>
            </select>
          </div>
        }
      >
        <div
          className="dashboard-calendar-scroll"
          role="region"
          aria-label="Lịch trong tuần, cuộn ngang để xem tất cả các ngày"
          tabIndex={0}
        >
          <div
            className={`dashboard-schedule ${
              period === "Hôm nay" ? "day-view" : ""
            }`}
          >
            <div className="schedule-header">
              <span className="schedule-timezone">Giờ địa phương</span>
              {weekDays.map((d, i) =>
                period === "Hôm nay" && i !== selectedDay ? null : (
                  <Button
                    key={i}
                    className={`schedule-day ${
                      week === 0 && i === todayIndex ? "is-today" : ""
                    }`}
                    onClick={() => {
                      setSelectedDay(i)
                      setPeriod("Hôm nay")
                    }}
                  >
                    <span>{["T2", "T3", "T4", "T5", "T6", "T7", "CN"][i]}</span>
                    <strong>{d.getDate()}</strong>
                  </Button>
                ),
              )}
            </div>
            {Array.from({ length: 10 }, (_, i) => i + 8).map((hour) => (
              <div className="schedule-row" key={hour}>
                <span className="schedule-hour">
                  {String(hour).padStart(2, "0")}:00
                </span>
                {weekDays.map((_, day) =>
                  period === "Hôm nay" && day !== selectedDay ? null : (
                    <div
                      className={`schedule-cell ${
                        week === 0 && day === todayIndex ? "today-column" : ""
                      }`}
                      key={day}
                    />
                  ),
                )}
              </div>
            ))}
          </div>
        </div>
      </Card>
      {open && (
        <Modal
          title={editing ? "Chỉnh sửa công việc" : "Thêm công việc"}
          close={() => setOpen(false)}
        >
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const title = form.title.trim()
              if (!title) return
              const task: Task = {
                id: editing?.id ?? Date.now(),
                title,
                course: form.course.trim() || "Chưa phân loại",
                time: editing?.time ?? "Chưa xếp lịch",
                done: editing?.done ?? false,
                effort: form.effort,
                priority: form.priority,
                deadline: form.deadline,
              }
              setTasks((items) =>
                editing
                  ? items.map((x) => (x.id === editing.id ? task : x))
                  : [...items, task],
              )
              setOpen(false)
              notify(editing ? "Đã lưu công việc." : "Đã thêm công việc.")
            }}
          >
            <label>
              Tên công việc
              <input
                required
                value={form.title}
                onChange={(e) => patch({ title: e.target.value })}
                placeholder="Bạn muốn làm gì?"
              />
            </label>
            <div className="form-grid">
              <label>
                Môn học
                <input
                  value={form.course}
                  onChange={(e) => patch({ course: e.target.value })}
                  placeholder="Ví dụ: Giải tích"
                />
              </label>
              <label>
                Mức ưu tiên
                <select
                  value={form.priority}
                  onChange={(e) => patch({ priority: e.target.value })}
                >
                  {["Thấp", "Trung bình", "Cao"].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
              <label>
                Thời lượng dự kiến (phút)
                <input
                  type="number"
                  min="15"
                  max="480"
                  required
                  value={form.effort}
                  onChange={(e) => patch({ effort: +e.target.value })}
                />
              </label>
            </div>
            <label>
              Hạn chót · ngày địa phương
              <input
                type="date"
                required
                min={toIsoDate(today)}
                value={form.deadline}
                onChange={(e) => patch({ deadline: e.target.value })}
              />
            </label>
            <div className="modal-actions">
              {editing && (
                <Button
                  className="danger-text"
                  onClick={() => {
                    setTasks((items) => items.filter((t) => t.id !== editing.id))
                    setOpen(false)
                  }}
                >
                  Xóa công việc
                </Button>
              )}
              <Button className="secondary" onClick={() => setOpen(false)}>
                Hủy
              </Button>
              <Button className="primary" type="submit">
                {editing ? "Lưu thay đổi" : "Thêm công việc"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  )
}
