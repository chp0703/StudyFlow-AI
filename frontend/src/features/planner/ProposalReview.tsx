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
            {proposal.issues.length > 0 && (
              <details className="proposal-issues">
                <summary>Chưa xếp được ({proposal.issues.length})</summary>
                <ul>
                  {proposal.issues.map((i) => (
                    <li key={i.taskId}>
                      {i.code}: {i.message}
                    </li>
                  ))}
                </ul>
              </details>
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
