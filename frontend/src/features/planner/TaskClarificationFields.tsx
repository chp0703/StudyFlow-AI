import { Check } from "lucide-react"
import {
  TASK_COLOR_OPTIONS,
  TASK_PRIORITY_OPTIONS,
  type ClarificationDraftValues,
} from "./clarification"

function MissingBadge({ show }: { show: boolean }) {
  if (!show) return null
  return <span className="planner-clarification-badge">Cần bổ sung</span>
}

export default function TaskClarificationFields({
  idPrefix,
  values,
  setField,
  missingFields,
  useDeadlineDatetime = false,
  busy = false,
}: {
  idPrefix: string
  values: ClarificationDraftValues
  setField: (key: string, value: string) => void
  missingFields: Set<string>
  useDeadlineDatetime?: boolean
  busy?: boolean
}) {
  return (
    <div className="planner-clarification-fields">
      <label
        htmlFor={`${idPrefix}-title`}
        className="planner-clarification-field"
      >
        <span className="planner-clarification-label-row">
          <span className="planner-clarification-label">Tên công việc *</span>
          <MissingBadge show={missingFields.has("title")} />
        </span>
        <input
          id={`${idPrefix}-title`}
          type="text"
          placeholder="Ví dụ: Làm báo cáo môn học"
          value={values.title ?? ""}
          disabled={busy}
          onChange={(e) => setField("title", e.target.value)}
        />
      </label>

      <div className="planner-clarification-field">
        <span className="planner-clarification-label-row">
          <span className="planner-clarification-label">Thời gian bắt đầu</span>
          <MissingBadge show={missingFields.has("start_at")} />
        </span>
        <div className="planner-clarification-datetime">
          <input
            id={`${idPrefix}-start-date`}
            type="date"
            aria-label="Thời gian bắt đầu - Ngày"
            value={values["start_at.date"] ?? ""}
            disabled={busy}
            onChange={(e) => setField("start_at.date", e.target.value)}
          />
          <input
            id={`${idPrefix}-start-time`}
            type="time"
            aria-label="Thời gian bắt đầu - Giờ"
            value={values["start_at.time"] ?? ""}
            disabled={busy}
            onChange={(e) => setField("start_at.time", e.target.value)}
          />
        </div>
      </div>

      {useDeadlineDatetime ? (
        <div className="planner-clarification-field">
          <span className="planner-clarification-label-row">
            <span className="planner-clarification-label">Hạn hoàn thành</span>
            <MissingBadge show={missingFields.has("deadline_at")} />
          </span>
          <div className="planner-clarification-datetime">
            <input
              id={`${idPrefix}-deadline-at-date`}
              type="date"
              aria-label="Hạn hoàn thành - Ngày"
              value={values["deadline_at.date"] ?? ""}
              disabled={busy}
              onChange={(e) => setField("deadline_at.date", e.target.value)}
            />
            <input
              id={`${idPrefix}-deadline-at-time`}
              type="time"
              aria-label="Hạn hoàn thành - Giờ"
              value={values["deadline_at.time"] ?? ""}
              disabled={busy}
              onChange={(e) => setField("deadline_at.time", e.target.value)}
            />
          </div>
        </div>
      ) : (
        <label
          htmlFor={`${idPrefix}-deadline-date`}
          className="planner-clarification-field"
        >
          <span className="planner-clarification-label-row">
            <span className="planner-clarification-label">Hạn hoàn thành</span>
            <MissingBadge show={missingFields.has("deadline_date")} />
          </span>
          <input
            id={`${idPrefix}-deadline-date`}
            type="date"
            value={values.deadline_date ?? ""}
            disabled={busy}
            onChange={(e) => setField("deadline_date", e.target.value)}
          />
        </label>
      )}

      <div className="planner-clarification-row">
        <label
          htmlFor={`${idPrefix}-duration`}
          className="planner-clarification-field"
        >
          <span className="planner-clarification-label-row">
            <span className="planner-clarification-label">
              Thời lượng (phút)
            </span>
            <MissingBadge show={missingFields.has("estimated_minutes")} />
          </span>
          <input
            id={`${idPrefix}-duration`}
            type="number"
            min={5}
            step={5}
            placeholder="60"
            value={values.estimated_minutes ?? ""}
            disabled={busy}
            onChange={(e) => setField("estimated_minutes", e.target.value)}
          />
        </label>

        <label
          htmlFor={`${idPrefix}-priority`}
          className="planner-clarification-field"
        >
          <span className="planner-clarification-label">Mức ưu tiên</span>
          <select
            id={`${idPrefix}-priority`}
            value={values.priority ?? "MEDIUM"}
            disabled={busy}
            onChange={(e) => setField("priority", e.target.value)}
          >
            {TASK_PRIORITY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="planner-clarification-field">
        <span className="planner-clarification-label">Màu sắc</span>
        <div
          className="planner-clarification-colors"
          role="radiogroup"
          aria-label="Màu sắc công việc"
        >
          {TASK_COLOR_OPTIONS.map((swatch) => {
            const selected = values.color === swatch.value
            return (
              <button
                key={swatch.value}
                type="button"
                role="radio"
                aria-checked={selected}
                aria-label={swatch.label}
                title={swatch.label}
                className={`planner-clarification-color${
                  selected ? " is-selected" : ""
                }`}
                style={{ backgroundColor: swatch.value }}
                disabled={busy}
                onClick={() => setField("color", swatch.value)}
              >
                {selected && <Check size={14} aria-hidden="true" />}
              </button>
            )
          })}
        </div>
      </div>

      <label
        htmlFor={`${idPrefix}-description`}
        className="planner-clarification-field"
      >
        <span className="planner-clarification-label">Mô tả</span>
        <textarea
          id={`${idPrefix}-description`}
          rows={2}
          placeholder="Ghi chú hoặc chi tiết công việc (không bắt buộc)"
          value={values.description ?? ""}
          disabled={busy}
          onChange={(e) => setField("description", e.target.value)}
        />
      </label>
    </div>
  )
}
