import type { Proposal, TaskChange } from "../../types/planner.ts"
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
        kind: "moved",
        task,
        from: { date: old.date, hour: old.hour },
      })
  }
  for (const task of base)
    if (!after.has(task.id)) changes.push({ kind: "removed", task })

  return changes
}

export const isStale = (proposal: Proposal, revision: number) =>
  proposal.baseRevision !== revision

export function describeChanges(changes: TaskChange[]) {
  const count = (kind: TaskChange["kind"]) =>
    changes.filter((c) => c.kind === kind).length
  return [
    ["Thêm", count("added")],
    ["Dời", count("moved")],
    ["Xóa", count("removed")],
  ]
    .filter(([, n]) => n)
    .map(([label, n]) => `${label} ${n}`)
    .join(" · ")
}
