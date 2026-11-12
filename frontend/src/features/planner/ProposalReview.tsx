import { Check, Sparkles, X } from "lucide-react"
import Button from "../../components/ui/Button"
import type { Proposal } from "../../types/planner"
import { describeChanges } from "./proposal"

type Props = {
  proposal: Proposal | null
  stale: boolean
  busy: boolean
  reply: string
  approve: () => void
  reject: () => void
}

export default function ProposalReview({
  proposal,
  stale,
  busy,
  reply,
  approve,
  reject,
}: Props) {
  const changes = new Map(
    proposal?.changes.map((change) => [change.task.id, change.kind]),
  )
  const entries = proposal?.server
    ? [
        ...proposal.next.tasks.map((task) => ({
          task,
          kind: changes.get(task.id) ?? "unchanged",
        })),
        ...proposal.changes
          .filter((change) => change.kind === "removed")
          .map((change) => ({ task: change.task, kind: "removed" })),
      ]
    : (proposal?.changes.map((change) => ({
        task: change.task,
        kind: change.kind,
      })) ?? [])
  const kindLabel: Record<string, string> = {
    added: "Thêm",
    scheduled: "Thêm",
    moved: "Dời",
    removed: "Xóa",
    unchanged: "Giữ nguyên",
  }

  return (
    <div className="planner-status" role="status" aria-live="polite">
      {proposal ? (
        <div className={`proposal-bar ${stale ? "is-stale" : ""}`}>
          <Sparkles aria-hidden="true" size={16} />
          <span className="proposal-text">
            <strong>
              {proposal.server ? (
                proposal.server.title
              ) : (
                <>
                  Đề xuất:{" "}
                  {describeChanges(proposal.changes, proposal.windowChanges) ||
                    "không đổi"}
                </>
              )}
            </strong>
            {proposal.server && proposal.server.details.length > 0 && (
              <span>
                {proposal.server.details
                  .map((d) => `${d.label}: ${d.value}`)
                  .join(" · ")}
              </span>
            )}
            <span>
              {stale
                ? "Lịch đã thay đổi từ lúc tạo đề xuất (STALE). Hãy từ chối và tạo lại."
                : reply || proposal.reply}
            </span>
            {proposal.server?.coverage === "PARTIAL" && (
              <span className="proposal-coverage">
                Lịch học mới chỉ xếp được một phần công việc.
              </span>
            )}
            {entries.length > 0 && (
              <details className="proposal-entries" open>
                <summary>Lịch học đề xuất ({entries.length})</summary>
                <ul>
                  {entries.map(({ task, kind }) => (
                    <li
                      key={`${kind}-${task.id}`}
                      className={`proposal-entry is-${kind}`}
                    >
                      <span className="proposal-entry-kind">
                        {kindLabel[kind]}
                      </span>
                      <strong>{task.title}</strong>
                      <span>
                        {task.date
                          ? `${task.date.split("-").reverse().join("/")} · `
                          : ""}
                        {task.time || "Chưa có giờ"} · {task.effort} phút
                      </span>
                    </li>
                  ))}
                </ul>
              </details>
            )}
            {!!proposal.server?.unscheduled?.length && (
              <section
                className="proposal-issues"
                aria-label="Công việc chưa xếp hết"
              >
                <strong>
                  Chưa xếp hết ({proposal.server.unscheduled.length})
                </strong>
                <ul>
                  {proposal.server.unscheduled.map((item, index) => (
                    <li key={`${item.title}-${index}`}>
                      {item.title}: còn {item.minutes} phút chưa xếp
                      {item.reasons.length
                        ? ` · ${item.reasons.join(", ")}`
                        : ""}
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {proposal.issues.length > 0 && (
              <section
                className="proposal-issues"
                aria-label="Cảnh báo và công việc chưa xếp"
              >
                <strong>
                  Cảnh báo và công việc chưa xếp ({proposal.issues.length})
                </strong>
                <ul>
                  {proposal.issues.map((i) => (
                    <li key={i.taskId}>
                      {i.code}: {i.message}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </span>
          <Button
            className="secondary proposal-reject"
            onClick={reject}
            disabled={busy}
          >
            <X aria-hidden="true" size={14} /> Từ chối
          </Button>
          <Button
            className="primary proposal-approve"
            onClick={approve}
            disabled={stale || busy}
          >
            <Check aria-hidden="true" size={14} /> Duyệt
          </Button>
        </div>
      ) : (
        reply && <p className="planner-reply">{reply}</p>
      )}
    </div>
  )
}
