import { useState, useRef, useEffect, type FormEvent } from "react"
import {
  FileText,
  Upload,
  Trash2,
  Send,
  Sparkles,
  Check,
  X,
  ArrowRight,
  RotateCcw,
  BookOpen,
  HelpCircle,
  FolderOpen,
} from "lucide-react"
import Button from "../components/ui/Button"
import Card from "../components/ui/Card"
import type { StudyFile } from "../types/task"

// Question structure for Quiz
type QuizQuestion = {
  id: number
  course: string
  question: string
  hint?: string
  options: string[]
  correctIndex: number
  explanation: string
}

const quizQuestions: QuizQuestion[] = [
  {
    id: 1,
    course: "Giải tích",
    question:
      "Nếu hàm số f(x, y) = x²y + 3xy², đạo hàm riêng ∂f/∂x bằng bao nhiêu?",
    hint: "Giữ y không đổi khi lấy đạo hàm theo biến x.",
    options: ["2xy + 3y²", "x² + 6xy", "2xy + 6xy", "2x + 6y"],
    correctIndex: 0,
    explanation:
      "Khi lấy đạo hàm riêng theo biến x, coi y là hằng số: d/dx(x²y) = 2xy và d/dx(3xy²) = 3y². Do đó ∂f/∂x = 2xy + 3y².",
  },
  {
    id: 2,
    course: "Mạng máy tính",
    question:
      "Trong mô hình OSI 7 tầng, tầng nào chịu trách nhiệm định tuyến (routing) gói tin giữa các mạng?",
    hint: "Tầng này hoạt động dựa trên địa chỉ IP logic.",
    options: [
      "Tầng Mạng (Network Layer - Tầng 3)",
      "Tầng Liên kết dữ liệu (Data Link - Tầng 2)",
      "Tầng Giao vận (Transport - Tầng 4)",
      "Tầng Phiên (Session - Tầng 5)",
    ],
    correctIndex: 0,
    explanation:
      "Tầng Mạng (Layer 3) chịu trách nhiệm đánh địa chỉ logic (IP) và tìm đường đi (định tuyến) tối ưu cho gói tin qua các mạng khác nhau.",
  },
  {
    id: 3,
    course: "Kỹ thuật phần mềm",
    question:
      "Nguyên lý nào trong SOLID quy định một lớp chỉ nên có một lý do duy nhất để thay đổi?",
    hint: "Tập trung vào tính đơn nhiệm của từng module/class.",
    options: [
      "Single Responsibility Principle (SRP)",
      "Open/Closed Principle (OCP)",
      "Liskov Substitution Principle (LSP)",
      "Dependency Inversion Principle (DIP)",
    ],
    correctIndex: 0,
    explanation:
      "Single Responsibility Principle (SRP) khẳng định mỗi lớp chỉ nên đảm nhận một trách nhiệm duy nhất để giảm độ phụ thuộc và dễ bảo trì.",
  },
  {
    id: 4,
    course: "Cơ sở dữ liệu",
    question:
      "Mệnh đề SQL nào được sử dụng để loại bỏ các hàng trùng lặp trong tập kết quả truy vấn?",
    hint: "Đặt ngay sau từ khóa SELECT.",
    options: [
      "SELECT DISTINCT",
      "SELECT UNIQUE",
      "GROUP BY ALL",
      "FILTER DUPLICATES",
    ],
    correctIndex: 0,
    explanation:
      "Từ khóa DISTINCT trong câu lệnh 'SELECT DISTINCT' dùng để loại bỏ các bản ghi trùng lặp và chỉ trả về các giá trị phân biệt.",
  },
  {
    id: 5,
    course: "Cấu trúc dữ liệu & Giải thuật",
    question:
      "Độ phức tạp thời gian trung bình (average-case) của thuật toán sắp xếp nhanh (QuickSort) là gì?",
    hint: "Dựa trên chiến lược chia để trị (Divide and Conquer).",
    options: ["O(n log n)", "O(n²)", "O(n)", "O(log n)"],
    correctIndex: 0,
    explanation:
      "Thuật toán QuickSort trong trường hợp trung bình chia đôi mảng qua mỗi bước phân hoạch, đạt độ phức tạp O(n log n). Trường hợp xấu nhất mới là O(n²).",
  },
]

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

export default function Study({
  notify,
}: {
  notify: (message: string) => void
}) {
  // === Card 1: Quiz State ===
  const [quizIndex, setQuizIndex] = useState(0)
  const [selectedOption, setSelectedOption] = useState<number | null>(null)
  const [isAnswerChecked, setIsAnswerChecked] = useState(false)
  const [score, setScore] = useState(0)
  const [quizCompleted, setQuizCompleted] = useState(false)

  const currentQ = quizQuestions[quizIndex]

  const handleSelectOption = (index: number) => {
    if (isAnswerChecked) return
    setSelectedOption(index)
  }

  const handleCheckAnswer = () => {
    if (selectedOption === null || isAnswerChecked) return
    setIsAnswerChecked(true)
    if (selectedOption === currentQ.correctIndex) {
      setScore((s) => s + 1)
    }
  }

  const handleNextQuestion = () => {
    if (quizIndex < quizQuestions.length - 1) {
      setQuizIndex((i) => i + 1)
      setSelectedOption(null)
      setIsAnswerChecked(false)
    } else {
      setQuizCompleted(true)
    }
  }

  const handleRestartQuiz = () => {
    setQuizIndex(0)
    setSelectedOption(null)
    setIsAnswerChecked(false)
    setScore(0)
    setQuizCompleted(false)
  }

  // === Card 2: Documents (Tài liệu) State ===
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
    notify(`Đã tải lên ${uploaded.length} tài liệu mới.`)
    e.target.value = ""
  }

  const handleDeleteFile = (fileName: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== fileName))
    notify(`Đã xóa tài liệu: ${fileName}`)
  }

  // === Card 3: AI Q&A (Hỏi đáp) State ===
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

  return (
    <div className="study-container">
      {/* Hidden file input for document uploading */}
      <input
        ref={uploadRef}
        type="file"
        className="hidden"
        accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
        multiple
        onChange={handleFileUpload}
      />

      {/* ========================================================
          CỘT TRÁI: QUIZ (Mỗi lần hiển thị 1 câu với 4 đáp án)
         ======================================================== */}
      <div className="study-left-col">
        <Card
          className="study-card study-quiz-card"
          title="Luyện tập trắc nghiệm"
          action={
            <div className="quiz-header-badge">
              <span className="quiz-counter">
                Câu {quizIndex + 1}/{quizQuestions.length}
              </span>
              <span className="quiz-score">Đúng: {score}</span>
            </div>
          }
        >
          {!quizCompleted ? (
            <div className="quiz-body">
              {/* Subject Tag */}
              <div className="quiz-meta">
                <span className="quiz-subject-tag">
                  <BookOpen size={13} aria-hidden="true" />
                  {currentQ.course}
                </span>
                {currentQ.hint && (
                  <span className="quiz-hint-text">
                    <HelpCircle size={13} aria-hidden="true" />
                    {currentQ.hint}
                  </span>
                )}
              </div>

              {/* Question Title */}
              <h3 className="quiz-question-title">{currentQ.question}</h3>

              {/* 4 Answer Options */}
              <div
                className="quiz-options-group"
                role="radiogroup"
                aria-label="Các lựa chọn"
              >
                {currentQ.options.map((optionText, idx) => {
                  const isSelected = selectedOption === idx
                  const isCorrect = idx === currentQ.correctIndex

                  let optionClass = "quiz-option-btn"
                  if (isSelected) optionClass += " is-selected"

                  if (isAnswerChecked) {
                    if (isCorrect) {
                      optionClass += " is-correct"
                    } else if (isSelected && !isCorrect) {
                      optionClass += " is-wrong"
                    }
                  }

                  const optionLetter = ["A", "B", "C", "D"][idx]

                  return (
                    <button
                      key={idx}
                      type="button"
                      className={optionClass}
                      onClick={() => handleSelectOption(idx)}
                      disabled={isAnswerChecked}
                      aria-pressed={isSelected}
                    >
                      <span className="option-letter">{optionLetter}</span>
                      <span className="option-label">{optionText}</span>
                      {isAnswerChecked && isCorrect && (
                        <Check
                          size={18}
                          className="option-feedback-icon correct"
                          aria-hidden="true"
                        />
                      )}
                      {isAnswerChecked && isSelected && !isCorrect && (
                        <X
                          size={18}
                          className="option-feedback-icon wrong"
                          aria-hidden="true"
                        />
                      )}
                    </button>
                  )
                })}
              </div>

              {/* Explanation section if answered */}
              {isAnswerChecked && (
                <div
                  className={`quiz-explanation-box ${
                    selectedOption === currentQ.correctIndex
                      ? "success"
                      : "warning"
                  }`}
                >
                  <div className="explanation-header">
                    <strong>
                      {selectedOption === currentQ.correctIndex
                        ? "Chính xác!"
                        : `Chưa đúng! Đáp án đúng là ${["A", "B", "C", "D"][currentQ.correctIndex]}`}
                    </strong>
                  </div>
                  <p>{currentQ.explanation}</p>
                </div>
              )}

              {/* Bottom Action Button */}
              <div className="quiz-bottom-actions">
                {!isAnswerChecked ? (
                  <Button
                    className="primary quiz-submit-btn"
                    onClick={handleCheckAnswer}
                    disabled={selectedOption === null}
                  >
                    Kiểm tra đáp án
                  </Button>
                ) : (
                  <Button
                    className="primary quiz-submit-btn"
                    onClick={handleNextQuestion}
                  >
                    {quizIndex < quizQuestions.length - 1 ? (
                      <>
                        Câu tiếp theo{" "}
                        <ArrowRight size={16} aria-hidden="true" />
                      </>
                    ) : (
                      <>
                        Xem kết quả <ArrowRight size={16} aria-hidden="true" />
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
          ) : (
            /* Quiz Completed Results Screen */
            <div className="quiz-results-screen">
              <div className="results-icon-wrap">
                <Sparkles size={32} className="text-primary" />
              </div>
              <h3>Hoàn thành bài luyện tập!</h3>
              <p className="results-score-text">
                Bạn đã trả lời đúng <strong>{score}</strong> /{" "}
                {quizQuestions.length} câu (
                {Math.round((score / quizQuestions.length) * 100)}%).
              </p>
              <p className="results-subtext">
                Kiến thức được tổng hợp từ các tài liệu học tập của bạn. Hãy
                luyện tập thường xuyên để ghi nhớ sâu hơn!
              </p>
              <Button
                className="primary restart-btn"
                onClick={handleRestartQuiz}
              >
                <RotateCcw size={16} aria-hidden="true" /> Làm lại bài kiểm tra
              </Button>
            </div>
          )}
        </Card>
      </div>

      {/* ========================================================
          CỘT PHẢI:
          - TRÊN: TÀI LIỆU (Tổng hợp tệp + 1 nút cho phép up tài liệu)
          - DƯỚI: HỎI ĐÁP (Khung chat hỏi đáp trực tiếp với AI)
         ======================================================== */}
      <div className="study-right-col">
        {/* Card 2: Tài liệu (Phải trên) */}
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

        {/* Card 3: Hỏi đáp (Phải dưới) */}
        <Card className="study-card study-qa-card" title="Hỏi đáp AI">
          <div className="qa-chat-container">
            {/* Transcript messages */}
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

            {/* Chat Input Form */}
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
