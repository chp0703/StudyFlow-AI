import { useEffect, useRef, useState } from "react"
import {
  ArrowRight,
  BookOpen,
  Check,
  CheckCheck,
  FileText,
  Pause,
  Play,
  Upload,
  X,
} from "lucide-react"
import Button from "../components/ui/Button"
import Card from "../components/ui/Card"
import Modal from "../components/ui/Modal"
import type { StudyFile } from "../types/task"

export default function Study({
  notify,
}: {
  notify: (message: string) => void
}) {
  const [files, setFiles] = useState<StudyFile[]>([])
  const [running, setRunning] = useState(false)
  const [seconds, setSeconds] = useState(0)
  const [notes, setNotes] = useState("")
  const [saved, setSaved] = useState(false)
  const [modal, setModal] = useState<"" | "reflection" | "manual">("")
  const uploadRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!running) return
    const id = setInterval(() => setSeconds((v) => v + 1), 1000)
    return () => clearInterval(id)
  }, [running])

  return (
    <>
      <input
        className="hidden"
        ref={uploadRef}
        type="file"
        accept=".pdf,.txt,.doc,.docx,.png,.jpg,.jpeg"
        multiple
        onChange={(e) => {
          setFiles((items) => [
            ...items,
            ...Array.from(e.target.files || []).map((file) => ({
              name: file.name,
              course: "Chưa phân loại",
              status: "Chỉ lưu tên tệp trong phiên · chưa đọc nội dung",
            })),
          ])
          e.target.value = ""
        }}
      />
      <Card
        className="study-tools"
        title="Tài liệu"
        action={
          <>
            <Button className="secondary" onClick={() => setModal("manual")}>
              Thêm ghi chú
            </Button>
            <Button className="primary" onClick={() => uploadRef.current?.click()}>
              <Upload aria-hidden="true" size={16} />
              Thêm tài liệu
            </Button>
          </>
        }
      >
        {files.length ? (
          <div className="materials-list">
            {files.map((f, i) => (
              <div key={i} className="material-row">
                <span className="course-icon">
                  <FileText aria-hidden="true" size={22} />
                </span>
                <div>
                  <strong>{f.name}</strong>
                  <p>{f.status}</p>
                </div>
                <Button
                  className="icon-button"
                  aria-label={`Xóa ${f.name}`}
                  onClick={() => setFiles(files.filter((x) => x !== f))}
                >
                  <X aria-hidden="true" size={16} />
                </Button>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-inline">
            <p>Chưa có tài liệu hoặc ghi chú nào.</p>
          </div>
        )}
      </Card>
      <div className="study-session-bar">
        <span className="course-icon">
          <BookOpen aria-hidden="true" size={21} />
        </span>
        <div>
          <strong>Buổi học</strong>
        </div>
        <span
          className="timer"
          role="timer"
          aria-label="Thời gian đã trôi qua của buổi học"
        >
          {String(Math.floor(seconds / 60)).padStart(2, "0")}:
          {String(seconds % 60).padStart(2, "0")}
        </span>
        <Button className="secondary" onClick={() => setRunning(!running)}>
          {running ? (
            <Pause aria-hidden="true" size={15} />
          ) : (
            <Play aria-hidden="true" size={15} />
          )}{" "}
          {running ? "Tạm dừng" : seconds ? "Tiếp tục" : "Bắt đầu"}
        </Button>
        <Button
          className="primary"
          onClick={() => {
            setRunning(false)
            setModal("reflection")
          }}
        >
          Kết thúc buổi học <ArrowRight aria-hidden="true" size={15} />
        </Button>
      </div>
      {saved && (
        <div className="info-banner">
          <Check aria-hidden="true" size={18} />
          <div>
            <strong>Đã xác nhận kết quả buổi học</strong>
            <p>Thời gian học không chứng minh mức độ thành thạo.</p>
          </div>
        </div>
      )}
      <Card title="Ghi chú buổi học">
        <textarea
          className="session-notes"
          aria-label="Ghi chú buổi học"
          placeholder="Ghi lại câu hỏi, điều bạn hiểu được hoặc nội dung cần xem lại..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </Card>
      {modal === "reflection" && (
        <Modal title="Thời gian nhìn lại" close={() => setModal("")}>
          <div className="reflection-summary">
            <CheckCheck aria-hidden="true" size={18} />
            <div>
              <strong>{Math.floor(seconds / 60)} phút hoạt động</strong>
            </div>
          </div>
          <label>
            Phản hồi của bạn
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Bạn đã học nội dung gì? Bạn muốn xem lại điều gì?"
            />
          </label>
          <Button
            className="primary"
            onClick={() => {
              setSaved(true)
              setModal("")
              notify("Đã xác nhận kết quả buổi học.")
            }}
          >
            Xác nhận kết quả buổi học
          </Button>
        </Modal>
      )}
      {modal === "manual" && (
        <Modal title="Thêm ghi chú thủ công" close={() => setModal("")}>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const data = new FormData(e.currentTarget)
              setFiles((items) => [
                ...items,
                {
                  name: String(data.get("title")),
                  course: "Chưa phân loại",
                  status: "Ghi chú thủ công · chưa xác minh",
                },
              ])
              setModal("")
              notify("Đã thêm ghi chú.")
            }}
          >
            <label>
              Tên ghi chú
              <input name="title" required />
            </label>
            <label>
              Nội dung ghi chú
              <textarea
                required
                name="note"
                placeholder="Dán đoạn nội dung bạn được phép sử dụng..."
              />
            </label>
            <Button className="primary" type="submit">
              Thêm ghi chú
            </Button>
          </form>
        </Modal>
      )}
    </>
  )
}
