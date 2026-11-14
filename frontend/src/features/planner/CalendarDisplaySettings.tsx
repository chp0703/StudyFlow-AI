import { useState } from "react"
import { Settings2 } from "lucide-react"
import type { CalendarDisplayRanges } from "./calendarDisplay"
import { displayRangeError } from "./calendarDisplay"

const days = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]

export default function CalendarDisplaySettings({
  ranges,
  onChange,
}: {
  ranges: CalendarDisplayRanges
  onChange: (ranges: CalendarDisplayRanges) => void
}) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<CalendarDisplayRanges>(ranges)
  const [errors, setErrors] = useState<string[]>(Array(7).fill(""))

  const update = (day: number, field: "start" | "end", value: string) => {
    const next = draft.map((range, index) =>
      index === day ? { ...range, [field]: value } : range,
    ) as unknown as CalendarDisplayRanges
    setDraft(next)
    setErrors((previous) =>
      previous.map((error, index) => (index === day ? "" : error)),
    )
  }

  const save = () => {
    const nextErrors = draft.map(displayRangeError)
    setErrors(nextErrors)
    if (nextErrors.some(Boolean)) return
    onChange(draft)
    setOpen(false)
  }

  return (
    <div className="calendar-display-settings">
      <button
        className="calendar-settings-toggle"
        type="button"
        aria-expanded={open}
        aria-controls="calendar-display-panel"
        onClick={() => {
          setDraft(ranges)
          setErrors(Array(7).fill(""))
          setOpen(!open)
        }}
      >
        <Settings2 size={16} aria-hidden="true" /> Tùy chỉnh giờ hiển thị
      </button>
      {open && (
        <div
          id="calendar-display-panel"
          className="calendar-display-panel"
          role="group"
          aria-label="Cài đặt hiển thị lịch"
        >
          <p>
            Chỉ thay đổi phần lịch nhìn thấy. Công việc và lịch học được giữ
            nguyên.
          </p>
          <div className="calendar-display-days">
            {days.map((day, index) => (
              <div className="calendar-display-day" key={day}>
                <strong>{day}</strong>
                <label>
                  {" "}
                  Từ{" "}
                  <input
                    type="text"
                    inputMode="numeric"
                    value={draft[index].start}
                    aria-label={`${day} từ`}
                    aria-invalid={!!errors[index]}
                    onChange={(event) =>
                      update(index, "start", event.target.value)
                    }
                  />
                </label>
                <label>
                  {" "}
                  Đến{" "}
                  <input
                    type="text"
                    inputMode="numeric"
                    value={draft[index].end}
                    aria-label={`${day} đến`}
                    aria-invalid={!!errors[index]}
                    onChange={(event) =>
                      update(index, "end", event.target.value)
                    }
                  />
                </label>
                {errors[index] && <small role="alert">{errors[index]}</small>}
              </div>
            ))}
          </div>
          <div className="calendar-display-actions">
            <button type="button" onClick={() => setOpen(false)}>
              Đóng
            </button>
            <button type="button" className="primary" onClick={save}>
              Lưu hiển thị
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
