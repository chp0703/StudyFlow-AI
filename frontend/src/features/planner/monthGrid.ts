import { addCivilDays, civilWeekday } from "../../utils/date.ts"

export const addMonths = (month: string, amount: number) => {
  const [year, number] = month.split("-").map(Number)
  return new Date(Date.UTC(year, number - 1 + amount, 1))
    .toISOString()
    .slice(0, 7)
}

export const monthDates = (month: string) => {
  const first = `${month}-01`
  const next = addMonths(month, 1)
  const last = addCivilDays(`${next}-01`, -1)
  const start = addCivilDays(first, -civilWeekday(first))
  const count =
    Math.ceil(
      (Math.round(
        (Date.parse(`${last}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) /
          86400000,
      ) +
        1) /
        7,
    ) * 7
  return Array.from({ length: count }, (_, index) => addCivilDays(start, index))
}
