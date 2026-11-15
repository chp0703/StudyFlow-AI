import { vietnamDate } from "../../utils/date"

export function prefillPlannerCommand(
  date: Date,
  minuteOfDay: number,
  apiMode: boolean,
  setInput: (value: string) => void,
  textarea: HTMLTextAreaElement | null,
) {
  const [year, month, day] = vietnamDate(date).split("-")
  const d = `${Number(day)}/${Number(month)}/${year}`
  const time = `${String(Math.floor(minuteOfDay / 60)).padStart(2, "0")}:${String(minuteOfDay % 60).padStart(2, "0")}`
  const text = apiMode
    ? `Thêm công việc hạn ngày ${d}, làm khoảng 60 phút`
    : `thêm  lúc ${time} ngày ${d}`
  setInput(text)
  requestAnimationFrame(() => {
    textarea?.focus()
    const cursor = apiMode ? text.length : 5
    textarea?.setSelectionRange(cursor, cursor)
  })
}
