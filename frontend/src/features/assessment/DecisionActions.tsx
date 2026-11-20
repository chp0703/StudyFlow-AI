import Button from "../../components/ui/Button"
import { uncertainDecisionMessage } from "./assessmentWorkflow"

export default function DecisionActions({
  count,
  state,
  pendingDecision,
  busy,
  referencePresent,
  onDecision,
  onReconcile,
}: {
  count: number
  state: "idle" | "uncertain" | "blocked"
  pendingDecision: "APPROVE" | "REJECT" | null
  busy: boolean
  referencePresent: boolean
  onDecision: (decision: "APPROVE" | "REJECT") => void
  onReconcile: () => void
}) {
  return (
    <div className="assessment-decision-bar">
      <div>
        <strong>Áp dụng cho cả {count} câu nháp</strong>
        <small>Quyết định này cần xác nhận rõ ràng.</small>
        {state === "uncertain" && (
          <p className="assessment-decision-warning" role="status">
            {uncertainDecisionMessage}
          </p>
        )}
      </div>
      <Button
        className="secondary assessment-reject"
        onClick={() => onDecision("REJECT")}
        disabled={
          busy ||
          !referencePresent ||
          state === "blocked" ||
          (pendingDecision === "APPROVE" && state === "uncertain")
        }
      >
        {pendingDecision === "REJECT" && state === "uncertain"
          ? "Thử lại từ chối"
          : "Từ chối"}
      </Button>
      <Button
        className="primary"
        onClick={() => onDecision("APPROVE")}
        disabled={
          busy ||
          !referencePresent ||
          state === "blocked" ||
          (pendingDecision === "REJECT" && state === "uncertain")
        }
      >
        {pendingDecision === "APPROVE" && state === "uncertain"
          ? "Thử lại xác minh"
          : "Xác minh câu hỏi"}
      </Button>
      {state === "blocked" && (
        <Button className="secondary" onClick={onReconcile} disabled={busy}>
          Kiểm tra trạng thái
        </Button>
      )}
    </div>
  )
}
