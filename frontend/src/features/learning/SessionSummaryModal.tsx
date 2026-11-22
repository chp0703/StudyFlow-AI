import type { DailyLearningSummaryData } from "../../api/types"
import Button from "../../components/ui/Button"
import Modal from "../../components/ui/Modal"

export default function SessionSummaryModal({
  summary,
  busy,
  error,
  close,
  decide,
}: {
  summary: DailyLearningSummaryData
  busy: boolean
  error: string
  close: () => void
  decide: (decision: "APPROVE" | "REJECT") => void
}) {
  return (
    <Modal title="Xem lại kết quả phiên học" close={close}>
      <div className="learning-summary-modal">
        <span className="learning-draft-badge">Bản nháp – chưa lưu</span>
        <section>
          <h3>Nội dung tóm tắt</h3>
          <p>{summary.draft.summary}</p>
        </section>
        <dl>
          <div>
            <dt>Chủ đề đã học</dt>
            <dd>
              {summary.draft.topics.length
                ? summary.draft.topics.join(", ")
                : "Chưa xác định"}
            </dd>
          </div>
          <div>
            <dt>Thời lượng</dt>
            <dd>{summary.draft.duration_minutes} phút</dd>
          </div>
        </dl>
        <p className="learning-summary-note">
          Kết quả phiên là bản ghi hoạt động, không phải đánh giá mức độ thành
          thạo.
        </p>
        {error && (
          <p className="learning-modal-error" role="alert">
            {error}
          </p>
        )}
        <div className="learning-modal-actions">
          <Button
            className="secondary"
            disabled={busy}
            onClick={() => decide("REJECT")}
          >
            {busy ? "Đang xử lý…" : "Tiếp tục học"}
          </Button>
          <Button
            className="primary"
            disabled={busy}
            onClick={() => decide("APPROVE")}
          >
            {busy ? "Đang lưu…" : "Lưu kết quả"}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
