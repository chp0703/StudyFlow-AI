import type {
  Proposal,
  TaskChange,
  TimeWindow,
  WindowChange,
} from "../../types/planner.ts"

import type { Task } from "../../types/task.ts"

export function diffTasks(base: Task[], next: Task[]): TaskChange[] {
  const before = new Map(base.map((t) => [t.id, t]))

  const after = new Set(next.map((t) => t.id))

  const changes: TaskChange[] = []

  for (const task of next) {
    const old = before.get(task.id)

    if (!old) changes.push({ kind: "added", task })
    else if (old.date !== task.date || old.hour !== task.hour)
      changes.push({
        kind: old.date ? "moved" : "scheduled",

        task,

        from: { date: old.date, hour: old.hour },
      })
  }

  for (const task of base)
    if (!after.has(task.id)) changes.push({ kind: "removed", task })

  return changes
}

export function diffWindows(
  base: TimeWindow[],

  next: TimeWindow[],
): WindowChange[] {
  const before = new Map(base.map((w) => [w.id, w]))

  const after = new Set(next.map((w) => w.id))

  return [
    ...next

      .filter((w) => before.get(w.id)?.kind !== w.kind)

      .map((window) => ({ kind: "added" as const, window })),

    ...base

      .filter((w) => !after.has(w.id))

      .map((window) => ({ kind: "removed" as const, window })),
  ]
}

export const isStale = (proposal: Proposal, revision: number) =>
  proposal.baseRevision !== revision

export const hasPendingWeeklyChange = (proposal: Proposal) =>
  proposal.next.weeklyWindows !== undefined

export const demoNoOpResult = (proposal: Proposal | null, response: string) =>
  proposal && hasPendingWeeklyChange(proposal)
    ? { proposal, reply: proposal.reply, notice: response }
    : { proposal: null, reply: response, notice: null }

export function describeChanges(
  changes: TaskChange[],

  windowChanges: WindowChange[] = [],
) {
  const count = (kind: TaskChange["kind"]) =>
    changes.filter((c) => c.kind === kind).length

  return [
    ["Thêm", count("added")],

    ["Xếp", count("scheduled")],

    ["Dời", count("moved")],

    ["Xóa", count("removed")],

    ["Thêm khung giờ", windowChanges.filter((c) => c.kind === "added").length],

    ["Bỏ khung giờ", windowChanges.filter((c) => c.kind === "removed").length],
  ]

    .filter(([, n]) => n)

    .map(([label, n]) => `${label} ${n}`)

    .join(" · ")
}
