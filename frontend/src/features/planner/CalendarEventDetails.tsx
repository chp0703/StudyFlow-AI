import Modal from "../../components/ui/Modal"
import type { TaskChange } from "../../types/planner"
import type { Task } from "../../types/task"
import { formatShortDate } from "../../utils/date"
import { presentTaskDescription } from "./taskPresentation"
import { BookOpen } from "lucide-react"
import Button from "../../components/ui/Button"

export default function CalendarEventDetails({
  event,
  change,
  close,
  onStartLearning,
}: {
  event: Task
  change?: TaskChange["kind"]
  close: () => void
  onStartLearning?: (blockId: string, goal: string) => void
}) {
  const proposed = Boolean(change)
  const description = presentTaskDescription(event.description)
  return (
    <Modal title="Chi tiết buổi học" close={close}>
      <div className="calendar-event-detail">
        <strong>{event.title}</strong>
        <dl>
          <div>
            <dt>Ngày</dt>
            <dd>{formatShortDate(event.date ?? event.deadline)}</dd>
          </div>
          <div>
            <dt>Thời gian</dt>
            <dd>{event.time}</dd>
          </div>
          <div>
            <dt>Thời lượng</dt>
            <dd>{event.effort} phút</dd>
          </div>
          <div>
            <dt>Trạng thái</dt>
            <dd>{proposed ? "Đề xuất, chưa xác nhận" : "Đã xác nhận"}</dd>
          </div>
          <div>
            <dt>Ưu tiên</dt>
            <dd>{event.priority}</dd>
          </div>
        </dl>
        {description && <p>{description.summary}</p>}
        <p className="calendar-event-contract-note">
          Dời hoặc bỏ riêng buổi học chưa được backend hỗ trợ. Công việc gốc vẫn
          được giữ nguyên.
        </p>
        {!proposed && onStartLearning && (
          <Button
            className="primary calendar-event-learn-button"
            onClick={() => onStartLearning(event.id, event.title)}
          >
            <BookOpen size={16} aria-hidden="true" />
            Học ngay
          </Button>
        )}
      </div>
    </Modal>
  )
}
