import { useState, useRef, useEffect, type FormEvent } from "react"

import gsap from "gsap"

import { useGSAP } from "@gsap/react"

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

// Cấu trúc câu hỏi trắc nghiệm

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

export default function Study() {
  // === Thẻ 1: Trạng thái trắc nghiệm ===

  const [quizIndex, setQuizIndex] = useState(0)

  const [selectedOption, setSelectedOption] = useState<number | null>(null)

  const [isAnswerChecked, setIsAnswerChecked] = useState(false)

  const [showExplanationPopup, setShowExplanationPopup] = useState(false)

  const [score, setScore] = useState(0)

  const [failedIndices, setFailedIndices] = useState<Set<number>>(new Set())

  const [quizCompleted, setQuizCompleted] = useState(false)

  const currentQ = quizQuestions[quizIndex]

  const handleSelectOption = (index: number) => {
    if (isAnswerChecked) return

    setSelectedOption(index)
  }

  const handleCheckAnswer = () => {
    if (selectedOption === null || isAnswerChecked) return

    setIsAnswerChecked(true)

    setShowExplanationPopup(true)

    const isCorrect = selectedOption === currentQ.correctIndex

    const isRetry = failedIndices.has(quizIndex)

    if (isCorrect) {
      if (!isRetry) {
        setScore((s) => s + 1)
      }
    } else {
      setFailedIndices((prev) => new Set(prev).add(quizIndex))
    }
  }

  const quizRef = useRef<HTMLDivElement>(null)

  const popupRef = useRef<HTMLDivElement>(null)

  const prevQuizIndex = useRef(0)

  // Hộp giải thích phóng ra từ tâm thẻ; khi đóng chạy ngược hiệu ứng rồi mới gỡ khỏi giao diện.

  const popupOpen = isAnswerChecked && showExplanationPopup

  useGSAP(
    () => {
      if (!popupOpen) return

      gsap.from(popupRef.current, {
        opacity: 0,

        duration: 0.2,

        clearProps: "opacity",
      })

      gsap.from(".quiz-popup-card", {
        scale: 0.9,

        y: 24,

        opacity: 0,

        duration: 0.4,

        ease: "back.out(1.6)",

        clearProps: "transform,opacity",
      })
    },

    { scope: quizRef, dependencies: [popupOpen] },
  )

  const closePopup = (after?: () => void) => {
    if (!popupRef.current) {
      setShowExplanationPopup(false)

      after?.()

      return
    }

    gsap.to(".quiz-popup-card", {
      scale: 0.94,

      y: 12,

      opacity: 0,

      duration: 0.2,

      ease: "power2.in",
    })

    gsap.to(popupRef.current, {
      opacity: 0,

      duration: 0.2,

      onComplete: () => {
        setShowExplanationPopup(false)

        after?.()
      },
    })
  }

  // Câu tiếp theo trượt vào: tiêu đề trước, rồi lần lượt từng đáp án.

  useGSAP(
    () => {
      const changed = prevQuizIndex.current !== quizIndex

      prevQuizIndex.current = quizIndex

      if (!changed) return

      const tl = gsap.timeline({
        defaults: { ease: "power2.out", clearProps: "transform,opacity" },
      })

      tl.from(".quiz-meta, .quiz-question-title", {
        x: 28,

        opacity: 0,

        duration: 0.35,

        stagger: 0.06,
      })

        .from(
          ".quiz-option-btn",

          { y: 18, opacity: 0, duration: 0.35, stagger: 0.07 },

          "-=0.2",
        )

        .from(".quiz-bottom-actions", { opacity: 0, duration: 0.3 }, "-=0.2")
    },

    { scope: quizRef, dependencies: [quizIndex] },
  )

  // Màn hình kết quả hiện nhẹ nhàng sau câu cuối.

  useGSAP(
    () => {
      if (quizCompleted)
        gsap.from(".quiz-results-screen", {
          scale: 0.96,

          y: 16,

          opacity: 0,

          duration: 0.5,

          ease: "power3.out",

          clearProps: "transform,opacity",
        })
    },

    { scope: quizRef, dependencies: [quizCompleted] },
  )

  const handleNextQuestion = () => {
    setShowExplanationPopup(false)

    if (quizIndex < quizQuestions.length - 1) {
      setQuizIndex((i) => i + 1)

      setSelectedOption(null)

      setIsAnswerChecked(false)
    } else {
      setQuizCompleted(true)
    }
  }

  const handleRetryQuestion = () => {
    if (showExplanationPopup) {
      closePopup(() => {
        setSelectedOption(null)

        setIsAnswerChecked(false)
      })
    } else {
      setSelectedOption(null)

      setIsAnswerChecked(false)
    }
  }

  const handleRestartQuiz = () => {
    setFailedIndices(new Set())

    setQuizIndex(0)

    setSelectedOption(null)

    setIsAnswerChecked(false)

    setShowExplanationPopup(false)

    setScore(0)

    setQuizCompleted(false)
  }

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

      {/* ========================================================
          CỘT TRÁI: TRẮC NGHIỆM (mỗi lần hiển thị một câu với bốn đáp án)
         ======================================================== */}
      <div className="study-left-col" ref={quizRef}>
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
          {/* Hộp giải thích đúng/sai hiện ngay trong thẻ */}
          {isAnswerChecked && showExplanationPopup && (
            <div
              ref={popupRef}
              className="quiz-popup-backdrop"
              onClick={() => closePopup()}
              role="dialog"
              aria-modal="true"
              aria-label="Kết quả câu trả lời"
            >
              <div
                className={`quiz-popup-card ${
                  selectedOption === currentQ.correctIndex
                    ? "is-correct"
                    : "is-wrong"
                }`}
                onClick={(e) => e.stopPropagation()}
              >
                <div className="quiz-popup-header">
                  <div className="quiz-popup-status">
                    <span className="quiz-popup-status-icon">
                      {selectedOption === currentQ.correctIndex ? (
                        <Check size={18} aria-hidden="true" />
                      ) : (
                        <X size={18} aria-hidden="true" />
                      )}
                    </span>
                    <strong>
                      {selectedOption === currentQ.correctIndex
                        ? "Chính xác!"
                        : `Chưa đúng! Đáp án đúng là ${["A", "B", "C", "D"][currentQ.correctIndex]}`}
                    </strong>
                  </div>
                  <button
                    type="button"
                    className="quiz-popup-close-btn"
                    onClick={() => closePopup()}
                    aria-label="Đóng"
                  >
                    <X size={16} aria-hidden="true" />
                  </button>
                </div>
                <div className="quiz-popup-body">
                  <p>{currentQ.explanation}</p>
                </div>
                <div className="quiz-popup-footer">
                  {selectedOption !== currentQ.correctIndex && (
                    <Button
                      className="secondary quiz-popup-retry-btn"
                      onClick={handleRetryQuestion}
                    >
                      <RotateCcw size={15} aria-hidden="true" />
                      Làm lại câu này
                    </Button>
                  )}
                  <Button
                    className="primary quiz-popup-next-btn"
                    onClick={() => closePopup(handleNextQuestion)}
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
                </div>
              </div>
            </div>
          )}

          {!quizCompleted ? (
            <div className="quiz-body">
              {/* Nhãn môn học */}
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

              {/* Tiêu đề câu hỏi */}
              <h3 className="quiz-question-title">{currentQ.question}</h3>

              {/* Bốn lựa chọn trả lời */}
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

              {/* Nút thao tác phía dưới */}
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
                  <div className="quiz-action-group">
                    {selectedOption !== currentQ.correctIndex && (
                      <Button
                        className="secondary quiz-retry-btn"
                        onClick={handleRetryQuestion}
                      >
                        <RotateCcw size={15} aria-hidden="true" />
                        Làm lại
                      </Button>
                    )}
                    <Button
                      className="secondary quiz-review-btn"
                      onClick={() => setShowExplanationPopup(true)}
                    >
                      Xem giải thích
                    </Button>
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
                          Xem kết quả{" "}
                          <ArrowRight size={16} aria-hidden="true" />
                        </>
                      )}
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Màn hình kết quả sau khi hoàn thành trắc nghiệm */

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
