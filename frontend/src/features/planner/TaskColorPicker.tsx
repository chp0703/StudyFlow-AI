import { TASK_COLOR_OPTIONS } from "./clarification"

export default function TaskColorPicker({
  color,
  onChange,
  disabled,
}: {
  color: string
  onChange: (color: string) => void
  disabled: boolean
}) {
  return (
    <label className="task-color-picker">
      <span className="planner-clarification-label">Nhãn màu</span>
      <span className="task-color-control">
        <span
          aria-hidden="true"
          className="task-color-swatch"
          style={color ? { backgroundColor: color } : undefined}
        />
        <select
          value={color}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
        >
          <option value="">Mặc định</option>
          {TASK_COLOR_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </span>
    </label>
  )
}
