import { useState, type FormEvent } from "react"
import { CalendarClock, ChevronDown, Clock3, Pencil, Plus, Trash2 } from "lucide-react"
import type { ApiTimeWindow } from "../../api/types"
import { vietnamDate } from "../../utils/date"
import Button from "../../components/ui/Button"
import { intervalError } from "./workingTime"

type Arguments = {
  change_type: "ADD" | "UPDATE" | "ARCHIVE"
  window_id: string | null
  expected_window_version: number | null
  window: Omit<ApiTimeWindow, "window_id" | "version" | "archived_at"> | null
}

const weekdays = [
  { name: "Thứ 2", short: "T2" },
  { name: "Thứ 3", short: "T3" },
  { name: "Thứ 4", short: "T4" },
  { name: "Thứ 5", short: "T5" },
  { name: "Thứ 6", short: "T6" },
  { name: "Thứ 7", short: "T7" },
  { name: "Chủ nhật", short: "CN" },
]

export default function WorkingTimeEditor({
  windows,
  busy,
  pending,
  prepare,
}: {
  windows: ApiTimeWindow[]
  busy: boolean
  pending: boolean
  prepare: (args: Arguments) => Promise<boolean>
}) {
  const [weekday, setWeekday] = useState(1)
  const [editing, setEditing] = useState<{
    weekday: number
    source?: ApiTimeWindow
  } | null>(null)
  const [start, setStart] = useState("08:00")
  const [end, setEnd] = useState("09:00")
  const [end24, setEnd24] = useState(false)
  const [error, setError] = useState("")

  const weekly = windows.filter(
    (item) =>
      item.kind === "AVAILABILITY" &&
      item.recurrence === "WEEKLY" &&
      !item.archived_at,
  )
  const dayCount = new Set(weekly.map((item) => item.weekday)).size
  const dayWindows = weekly
    .filter((item) => item.weekday === weekday)
    .sort((a, b) => (a.start_time ?? "").localeCompare(b.start_time ?? ""))
  const currentDay = weekdays[weekday - 1]

  const begin = (day: number, source?: ApiTimeWindow) => {
    setWeekday(day)
    setEditing({ weekday: day, source })
    setStart(source?.start_time ?? "08:00")
    setEnd(
      source?.end_time === "24:00" ? "23:59" : (source?.end_time ?? "09:00"),
    )
    setEnd24(source?.end_time === "24:00")
    setError("")
  }

  const selectDay = (day: number) => {
    setWeekday(day)
    setEditing(null)
    setError("")
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!editing) return

    const others = weekly.filter(
      (item) =>
        item.weekday === editing.weekday &&
        item.window_id !== editing.source?.window_id,
    )
    const chosenEnd = end24 ? "24:00" : end
    const problem = intervalError(start, chosenEnd, others)
    if (problem) return setError(problem)

    const source = editing.source
    const accepted = await prepare({
      change_type: source ? "UPDATE" : "ADD",
      window_id: source?.window_id ?? null,
      expected_window_version: source?.version ?? null,
      window: {
        kind: "AVAILABILITY",
        label: source?.label ?? null,
        recurrence: "WEEKLY",
        timezone: "Asia/Ho_Chi_Minh",
        start_at: null,
        end_at: null,
        weekday: editing.weekday,
        start_time: start,
        end_time: chosenEnd,
        valid_from: source?.valid_from ?? vietnamDate(),
        valid_until: source?.valid_until ?? null,
      },
    })
    if (accepted) setEditing(null)
  }

  return (
    <details className="working-time-editor">
      <summary className="working-time-summary">
        <span className="working-time-summary-icon" aria-hidden="true">
          <CalendarClock size={19} />
        </span>
        <span className="working-time-summary-copy">
          <strong>Khung giờ học hằng tuần</strong>
          <small>
            {weekly.length
              ? dayCount + " ngày đã thiết lập · " + weekly.length + " khoảng"
              : "Chưa có giờ học — chọn ngày để thiết lập"}
          </small>
        </span>
        <span className="working-time-summary-action" aria-hidden="true">
          Chỉnh sửa <ChevronDown size={16} />
        </span>
      </summary>

      <div className="working-time-body">
        <p className="working-time-intro">
          Chọn một ngày để thêm hoặc sửa khoảng học. Giờ bận được ưu tiên khi
          trùng thời gian.
        </p>

        <div
          className="working-time-tabs"
          role="group"
          aria-label="Chọn ngày trong tuần"
        >
          {weekdays.map((day, index) => {
            const selectedDay = index + 1
            const count = weekly.filter(
              (item) => item.weekday === selectedDay,
            ).length
            return (
              <button
                key={day.short}
                type="button"
                className={
                  "working-time-tab" +
                  (weekday === selectedDay ? " is-active" : "")
                }
                aria-pressed={weekday === selectedDay}
                aria-label={
                  day.name + (count ? ", " + count + " khoảng học" : ", chưa có giờ học")
                }
                onClick={() => selectDay(selectedDay)}
              >
                <strong>{day.short}</strong>
                <small>{count ? count + " khoảng" : "Chưa có"}</small>
              </button>
            )
          })}
        </div>

        <section
          className="working-time-day-panel"
          aria-label={"Thời gian học " + currentDay.name}
        >
          <div className="working-time-day-heading">
            <div>
              <h3>{currentDay.name}</h3>
              <p>
                {dayWindows.length
                  ? dayWindows.length + " khoảng học đã thiết lập"
                  : "Chưa có khung giờ cho ngày này"}
              </p>
            </div>
            {!editing && (
              <Button
                className="secondary working-time-add"
                disabled={busy || pending}
                onClick={() => begin(weekday)}
              >
                <Plus size={16} aria-hidden="true" /> Thêm khoảng
              </Button>
            )}
          </div>

          {dayWindows.length ? (
            <ul className="working-time-slots">
              {dayWindows.map((item) => (
                <li key={item.window_id}>
                  <span className="working-time-slot-icon" aria-hidden="true">
                    <Clock3 size={17} />
                  </span>
                  <span className="working-time-slot-clock">
                    {item.start_time} <span aria-hidden="true">–</span>{" "}
                    {item.end_time}
                  </span>
                  <span className="working-time-slot-actions">
                    <Button
                      className="secondary working-time-icon-button"
                      aria-label={
                        "Sửa giờ học " + currentDay.name + " " +
                        item.start_time + "–" + item.end_time
                      }
                      title="Sửa khoảng học"
                      disabled={busy || pending}
                      onClick={() => begin(weekday, item)}
                    >
                      <Pencil size={16} aria-hidden="true" />
                    </Button>
                    <Button
                      className="secondary working-time-icon-button is-delete"
                      aria-label={
                        "Xóa giờ học " + currentDay.name + " " +
                        item.start_time + "–" + item.end_time
                      }
                      title="Xóa khoảng học (cần duyệt)"
                      disabled={busy || pending}
                      onClick={() =>
                        void prepare({
                          change_type: "ARCHIVE",
                          window_id: item.window_id,
                          expected_window_version: item.version,
                          window: null,
                        })
                      }
                    >
                      <Trash2 size={16} aria-hidden="true" />
                    </Button>
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="working-time-empty">
              Ngày này chưa có thời gian học. Chọn “Thêm khoảng” để bắt đầu.
            </p>
          )}

          {editing && editing.weekday === weekday && (
            <form
              className="working-time-form"
              onSubmit={(event) => void submit(event)}
            >
              <strong>
                {editing.source ? "Sửa khoảng học" : "Thêm khoảng học"} ·{" "}
                {currentDay.name}
              </strong>
              <label>
                Bắt đầu
                <input
                  type="time"
                  step={60}
                  value={start}
                  onChange={(event) => {
                    setStart(event.target.value)
                    setError("")
                  }}
                  aria-describedby={error ? "working-time-error" : undefined}
                  required
                />
              </label>
              <label>
                Kết thúc
                <input
                  type="time"
                  step={60}
                  value={end}
                  onChange={(event) => {
                    setEnd(event.target.value)
                    setError("")
                  }}
                  aria-describedby={error ? "working-time-error" : undefined}
                  disabled={end24}
                  required
                />
              </label>
              <label className="working-time-midnight">
                <input
                  type="checkbox"
                  checked={end24}
                  onChange={(event) => setEnd24(event.target.checked)}
                />
                Đến 24:00
              </label>
              {error && (
                <p role="alert" id="working-time-error">
                  {error}
                </p>
              )}
              <div className="working-time-form-actions">
                <Button type="submit" className="primary" disabled={busy || pending}>
                  Xem đề xuất
                </Button>
                <Button
                  className="secondary"
                  onClick={() => setEditing(null)}
                >
                  Hủy
                </Button>
              </div>
            </form>
          )}

          <p className="working-time-footnote">
            {pending
              ? "Đang có thay đổi chờ duyệt. Duyệt hoặc Từ chối trước khi chỉnh tiếp."
              : "Mọi thay đổi đều được xem trước và chỉ lưu sau khi bạn Duyệt."}
          </p>
        </section>
      </div>
    </details>
  )
}
