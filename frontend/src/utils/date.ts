export const today = new Date()
today.setHours(12, 0, 0, 0)

export const toIsoDate = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`

export const daysUntil = (iso: string) =>
  Math.round((new Date(`${iso}T12:00:00`).getTime() - today.getTime()) / 86400000)

export const formatShortDate = (iso: string) =>
  new Date(`${iso}T12:00:00`).toLocaleDateString("vi-VN", {
    day: "numeric",
    month: "long",
  })
