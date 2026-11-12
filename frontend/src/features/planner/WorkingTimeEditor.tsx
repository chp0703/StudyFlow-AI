import { useState, type FormEvent } from "react"
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
  "Thứ 2",
  "Thứ 3",
  "Thứ 4",
  "Thứ 5",
  "Thứ 6",
  "Thứ 7",
  "Chủ nhật",
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

  const begin = (weekday: number, source?: ApiTimeWindow) => {
    setEditing({ weekday, source })
    setStart(source?.start_time ?? "08:00")
    setEnd(
      source?.end_time === "24:00" ? "23:59" : (source?.end_time ?? "09:00"),
    )
    setEnd24(source?.end_time === "24:00")
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
      <summary>Thời gian làm việc / Thời gian học</summary>
      <p>
        Chọn các khoảng học lặp lại hằng tuần. Giờ bận được xử lý riêng và được
        ưu tiên khi xếp lịch. Mỗi thay đổi cần được duyệt trước khi lưu.
      </p>
      <div className="working-time-days">
        {weekdays.map((label, index) => {
          const weekday = index + 1
          const intervals = weekly.filter((item) => item.weekday === weekday)
          return (
            <section
              key={weekday}
              className="working-time-day"
              aria-label={label}
            >
              <h3>{label}</h3>
              {intervals.length ? (
                <ul>
                  {intervals.map((item) => (
                    <li key={item.window_id}>
                      <span>
                        {item.start_time}–{item.end_time}
                      </span>
                      <Button
                        type="button"
                        className="secondary"
                        disabled={busy || pending}
                        onClick={() => begin(weekday, item)}
                      >
                        Sửa
                      </Button>
                      <Button
                        type="button"
                        className="secondary"
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
                        Xóa
                      </Button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p>Chưa có thời gian học.</p>
              )}
              <Button
                type="button"
                className="secondary"
                disabled={busy || pending}
                onClick={() => begin(weekday)}
              >
                Thêm khoảng
              </Button>
            </section>
          )
        })}
      </div>
      {editing && (
        <form
          className="working-time-form"
          onSubmit={(event) => void submit(event)}
        >
          <strong>
            {editing.source ? "Sửa" : "Thêm"} thời gian học ·{" "}
            {weekdays[editing.weekday - 1]}
          </strong>
          <label>
            Bắt đầu
            <input
              type="time"
              value={start}
              onChange={(event) => setStart(event.target.value)}
              required
            />
          </label>
          <label>
            Kết thúc
            <input
              type="time"
              value={end}
              onChange={(event) => setEnd(event.target.value)}
              disabled={end24}
              required
            />
          </label>
          <label className="working-time-midnight">
            <input
              type="checkbox"
              checked={end24}
              onChange={(event) => setEnd24(event.target.checked)}
            />{" "}
            Đến 24:00
          </label>
          {error && <p role="alert">{error}</p>}
          <Button type="submit" className="primary" disabled={busy || pending}>
            Xem đề xuất
          </Button>
          <Button
            type="button"
            className="secondary"
            onClick={() => setEditing(null)}
          >
            Hủy
          </Button>
        </form>
      )}
    </details>
  )
}
