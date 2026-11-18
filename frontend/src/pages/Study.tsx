import { useState, useRef, useEffect, type FormEvent } from "react"

import gsap from "gsap"

import { useGSAP } from "@gsap/react"

import {
  FileText,
  Upload,
  Trash2,
  Send,
  Sparkles,
  X,
  FolderOpen,
} from "lucide-react"

import Button from "../components/ui/Button"

import Card from "../components/ui/Card"

import type { StudyFile } from "../types/task"
import DemoQuiz from "../features/assessment/DemoQuiz"
import AssessmentWorkspace from "../features/assessment/AssessmentWorkspace"
import { apiEnabled } from "../api/config"

type StudyChatMessage = {
  id: string

  sender: "user" | "ai"

  text: string

  time: string
}

const defaultFiles: StudyFile[] = [
  {
    name: "Giai-tich-2-Chuong-4-Dao-ham.pdf",

    course: "Giải tích",

    status: "2.4 MB · 14 trang · Đã lập chỉ mục",
  },

  {
    name: "Mang-may-tinh-OSI-Model.docx",

    course: "Mạng máy tính",

    status: "1.2 MB · 8 trang · Đã lập chỉ mục",
  },

  {
    name: "Ky-thuat-phan-mem-SOLID.pdf",

    course: "Kỹ thuật phần mềm",

    status: "850 KB · 5 trang · Đã lập chỉ mục",
  },
]

export default function Study() {
  // === Thẻ 2: Trạng thái tài liệu ===

  // Phản hồi tải lên/xóa hiển thị trong thẻ tài liệu thay vì thông báo nổi toàn trang.

  const [docNotice, setDocNotice] = useState("")

  const noticeRef = useRef<HTMLDivElement>(null)

  const noticeTimer = useRef<number>(0)

  const showDocNotice = (message: string) => {
    window.clearTimeout(noticeTimer.current)

    setDocNotice(message)

    noticeTimer.current = window.setTimeout(() => closeDocNotice(), 3500)
  }

  const closeDocNotice = () => {
    window.clearTimeout(noticeTimer.current)

    if (!noticeRef.current) return setDocNotice("")

    gsap.to(noticeRef.current, {
      y: 16,

      opacity: 0,

      duration: 0.25,

      ease: "power2.in",

      onComplete: () => setDocNotice(""),
    })
  }

  useEffect(() => () => window.clearTimeout(noticeTimer.current), [])

  useGSAP(
    () => {
      if (docNotice)
        gsap.fromTo(
          noticeRef.current,

          { y: 24, opacity: 0 },

          { y: 0, opacity: 1, duration: 0.4, ease: "back.out(1.6)" },
        )
    },

    { dependencies: [docNotice] },
  )

  const [files, setFiles] = useState<StudyFile[]>(defaultFiles)

  const uploadRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const uploaded = Array.from(e.target.files || [])

    if (!uploaded.length) return

    const newFiles: StudyFile[] = uploaded.map((f) => {
      const sizeStr =
        f.size > 1024 * 1024
          ? `${(f.size / (1024 * 1024)).toFixed(1)} MB`
          : `${Math.round(f.size / 1024)} KB`

      return {
        name: f.name,

        course: "Tài liệu mới",

        status: `${sizeStr} · Đã nạp thành công`,
      }
    })

    setFiles((prev) => [...prev, ...newFiles])

    showDocNotice(`Đã tải lên ${uploaded.length} tài liệu mới.`)

    e.target.value = ""
  }

  const handleDeleteFile = (fileName: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== fileName))

    showDocNotice(`Đã xóa tài liệu: ${fileName}`)
  }

  // === Thẻ 3: Trạng thái hỏi đáp AI ===

  const [chatMessages, setChatMessages] = useState<StudyChatMessage[]>([])

  const [chatInput, setChatInput] = useState("")

  const chatBottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatMessages])

  const sendQuestion = (queryText: string) => {
    const text = queryText.trim()

    if (!text) return

    const userMsg: StudyChatMessage = {
      id: crypto.randomUUID(),

      sender: "user",

      text,

      time: new Date().toLocaleTimeString("vi-VN", {
        hour: "2-digit",

        minute: "2-digit",
      }),
    }

    let aiReplyText = ""

    const qLower = text.toLowerCase()

    if (qLower.includes("đạo hàm") || qLower.includes("giải tích")) {
      aiReplyText =
        "Đạo hàm riêng của hàm nhiều biến f(x, y) theo biến x là đạo hàm thông thường khi coi biến y là hằng số. Ký hiệu là ∂f/∂x. Ví dụ: với f(x,y) = x²y + 3xy², ta có ∂f/∂x = 2xy + 3y²."
    } else if (qLower.includes("osi") || qLower.includes("mạng")) {
      aiReplyText =
        "Mô hình OSI gồm 7 tầng từ dưới lên: 1. Vật lý (Physical), 2. Liên kết dữ liệu (Data Link), 3. Mạng (Network), 4. Giao vận (Transport), 5. Phiên (Session), 6. Trình diễn (Presentation), 7. Ứng dụng (Application). Tầng Mạng chịu trách nhiệm định tuyến gói tin."
    } else if (qLower.includes("tcp") || qLower.includes("udp")) {
      aiReplyText =
        "TCP là giao thức hướng kết nối (connection-oriented), đảm bảo truyền dữ liệu tin cậy, không mất gói tin nhưng tốc độ chậm hơn. UDP không hướng kết nối (connectionless), truyền nhanh, chấp nhận mất gói nhẹ, phù hợp phát video/game trực tuyến."
    } else if (qLower.includes("solid")) {
      aiReplyText =
        "SOLID gồm 5 nguyên lý hướng đối tượng: Single Responsibility (Đơn nhiệm), Open/Closed (Mở rộng/Đóng sửa đổi), Liskov Substitution (Thay thế Liskov), Interface Segregation (Phân tách giao diện), và Dependency Inversion (Đảo ngược phụ thuộc)."
    } else {
      const activeDoc = files[0]?.name || "Tài liệu của bạn"

      aiReplyText = `Dựa trên tài liệu "${activeDoc}": Câu hỏi "${text}" liên quan đến các khái niệm cốt lõi của bài học. Hãy kết hợp tự luyện tập trắc nghiệm ở cột bên trái để nắm vững kiến thức!`
    }

    const aiMsg: StudyChatMessage = {
      id: crypto.randomUUID(),

      sender: "ai",

      text: aiReplyText,

      time: new Date().toLocaleTimeString("vi-VN", {
        hour: "2-digit",

        minute: "2-digit",
      }),
    }

    setChatMessages((prev) => [...prev, userMsg, aiMsg])

    setChatInput("")
  }

  const handleChatSubmit = (e: FormEvent) => {
    e.preventDefault()

    sendQuestion(chatInput)
  }

  if (apiEnabled)
    return (
      <div className="study-container study-assessment-container">
        <AssessmentWorkspace />
      </div>
    )

  return (
    <div className="study-container">
      {/* Ô chọn tệp ẩn để tải tài liệu lên */}
      <input
        ref={uploadRef}
        type="file"
        className="hidden"
        accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
        multiple
        onChange={handleFileUpload}
      />

      <DemoQuiz />
      {/* ========================================================
          CỘT PHẢI:
          - TRÊN: TÀI LIỆU (tổng hợp tệp và một nút tải tài liệu lên)
          - DƯỚI: HỎI ĐÁP (khung chat hỏi đáp trực tiếp với AI)
         ======================================================== */}
      <div className="study-right-col">
        {/* Thẻ 2: Tài liệu (phía trên bên phải) */}
        <Card
          className="study-card study-materials-card"
          title="Tài liệu"
          action={
            <Button
              className="primary upload-action-btn"
              onClick={() => uploadRef.current?.click()}
            >
              <Upload size={14} aria-hidden="true" />
              <span>Thêm tài liệu</span>
            </Button>
          }
        >
          {docNotice && (
            <div className="doc-notice" ref={noticeRef}>
              <span role="status">{docNotice}</span>
              <button
                type="button"
                className="doc-notice-close"
                aria-label="Đóng thông báo"
                onClick={closeDocNotice}
              >
                <X size={14} aria-hidden="true" />
              </button>
            </div>
          )}
          {files.length ? (
            <div className="materials-scroll-list">
              {files.map((file, idx) => (
                <div key={idx} className="material-item-row">
                  <span className="material-file-icon" aria-hidden="true">
                    <FileText size={20} />
                  </span>
                  <div className="material-file-details">
                    <strong title={file.name}>{file.name}</strong>
                    <div className="material-meta">
                      <span className="material-course-pill">
                        {file.course}
                      </span>
                      <span className="material-status-desc">
                        {file.status}
                      </span>
                    </div>
                  </div>
                  <Button
                    className="icon-button delete-file-btn"
                    aria-label={`Xóa tệp ${file.name}`}
                    onClick={() => handleDeleteFile(file.name)}
                  >
                    <Trash2 size={16} aria-hidden="true" />
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="materials-empty-state">
              <FolderOpen size={36} className="text-muted" aria-hidden="true" />
              <p>Chưa có tài liệu nào được tải lên.</p>
              <Button
                className="secondary"
                onClick={() => uploadRef.current?.click()}
              >
                <Upload size={14} aria-hidden="true" /> Chọn tệp từ máy
              </Button>
            </div>
          )}
        </Card>

        {/* Thẻ 3: Hỏi đáp (phía dưới bên phải) */}
        <Card className="study-card study-qa-card" title="Hỏi đáp AI">
          <div className="qa-chat-container">
            {/* Lịch sử tin nhắn */}
            <div
              className="qa-transcript"
              role="log"
              aria-label="Nội dung hỏi đáp với AI"
            >
              {chatMessages.length === 0 ? (
                <div className="qa-empty-state">
                  <p>
                    Nhập câu hỏi bên dưới để hỏi đáp trực tiếp cùng AI về tài
                    liệu.
                  </p>
                </div>
              ) : (
                chatMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`qa-message-row ${
                      msg.sender === "user" ? "is-user" : "is-ai"
                    }`}
                  >
                    {msg.sender === "ai" && (
                      <div className="qa-avatar" aria-hidden="true">
                        <Sparkles size={14} />
                      </div>
                    )}
                    <div className="qa-bubble">
                      <p>{msg.text}</p>
                    </div>
                  </div>
                ))
              )}
              <div ref={chatBottomRef} />
            </div>

            {/* Biểu mẫu nhập tin nhắn */}
            <form className="qa-composer-form" onSubmit={handleChatSubmit}>
              <input
                type="text"
                className="qa-composer-input"
                placeholder="Hỏi đáp về các tài liệu đã tải lên..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                aria-label="Đặt câu hỏi về tài liệu"
              />
              <Button
                className="primary qa-send-btn"
                type="submit"
                aria-label="Gửi câu hỏi"
                disabled={!chatInput.trim()}
              >
                <Send size={15} aria-hidden="true" />
              </Button>
            </form>
          </div>
        </Card>
      </div>
    </div>
  )
}
