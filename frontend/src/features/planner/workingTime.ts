import type { ApiTimeWindow } from "../../api/types"

const minutes = (value: string) => {
  const [hour, minute] = value.split(":").map(Number)
  return hour * 60 + minute
}

export function intervalError(
  start: string,
  end: string,
  others: Pick<ApiTimeWindow, "start_time" | "end_time">[],
) {
  if (
    !/^([01]\d|2[0-3]):[0-5]\d$/.test(start) ||
    (!/^([01]\d|2[0-3]):[0-5]\d$/.test(end) && end !== "24:00")
  )
    return "Hãy nhập giờ bắt đầu và kết thúc hợp lệ."
  if (minutes(start) >= minutes(end))
    return "Giờ kết thúc phải sau giờ bắt đầu."
  if (
    others.some(
      (item) =>
        item.start_time &&
        item.end_time &&
        minutes(start) < minutes(item.end_time) &&
        minutes(end) > minutes(item.start_time),
    )
  )
    return "Khoảng này trùng với thời gian học đã có."
  return ""
}
