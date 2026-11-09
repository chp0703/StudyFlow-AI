import { useEffect, useState } from "react"

import { CalendarDays, ChevronRight, Clock3, ListTodo } from "lucide-react"

import Button from "./ui/Button"

import Card from "./ui/Card"

import type { Task } from "../types/task"

import { daysUntil } from "../utils/date"

// Thời điểm người dùng mở ứng dụng web; đồng hồ bắt đầu đếm từ đây.

const sessionStart = Date.now()

const formatElapsed = (ms: number) => {
  const s = Math.floor(ms / 1000)

  return [Math.floor(s / 3600), Math.floor(s / 60) % 60, s % 60]

    .map((n) => String(n).padStart(2, "0"))

    .join(":")
}

export default function HomeSummary({
  tasks,

  go,
}: {
  tasks: Task[]

  go: (page: string) => void
}) {
  const [now, setNow] = useState(Date.now())

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)

    return () => clearInterval(id)
  }, [])

  const todayTasks = tasks.filter((task) => daysUntil(task.deadline) === 0)

  const deadlines = tasks.filter((task) => {
    const days = daysUntil(task.deadline)

    return !task.done && days > 0 && days <= 5
  })

  const cards = [
    {
      title: "Công việc hôm nay",

      value: `${todayTasks.filter((t) => t.done).length} / ${todayTasks.length}`,

      color: "summary-blue",

      icon: ListTodo,

      page: "Planner",
    },

    {
      title: "Deadline 5 ngày tới",

      value: String(deadlines.length),

      color: "summary-rose",

      icon: CalendarDays,

      page: "Planner",
    },

    {
      title: "Thời gian học",

      value: formatElapsed(now - sessionStart),

      color: "summary-purple",

      icon: Clock3,
    },
  ]

  const summary = (card: typeof cards[number]) => (
    <div className="summary-main">
      <span className="summary-icon">
        <card.icon aria-hidden="true" size={20} />
      </span>
      <div>
        <p>{card.title}</p>
        <strong>{card.value}</strong>
      </div>
    </div>
  )

  return (
    <div className="home-stats" role="group" aria-label="Tổng quan việc học">
      {cards.map((card) => (
        <Card key={card.title} className={`summary-card ${card.color}`}>
          {card.page ? (
            <Button
              className="summary-link"
              onClick={() => go(card.page)}
              aria-label={`${card.title}: ${card.value}`}
            >
              {summary(card)}
              <ChevronRight aria-hidden="true" size={17} />
            </Button>
          ) : (
            summary(card)
          )}
        </Card>
      ))}
    </div>
  )
}
