import { useState, useRef } from "react"
import gsap from "gsap"
import { useGSAP } from "@gsap/react"
import {
  Check,
  X,
  ArrowRight,
  RotateCcw,
  BookOpen,
  HelpCircle,
  Sparkles,
} from "lucide-react"
import Button from "../../components/ui/Button"
import Card from "../../components/ui/Card"
import { quizQuestions } from "./demoQuestions"

export default function DemoQuiz() {
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

  return (
    <div className="study-left-col" ref={quizRef}>
      <Card
        className="study-card study-quiz-card"
        title="Luyện tập trắc nghiệm (Demo)"
        action={
          <div className="quiz-header-badge">
            <span className="quiz-counter">
              Câu {quizIndex + 1}/{quizQuestions.length}
            </span>
            <span className="quiz-score">Đúng: {score}</span>
          </div>
        }
      >
        <div className="demo-quiz-notice" role="note">
          <span>Bản minh họa</span>
          Nội dung mẫu, không sử dụng tài liệu hoặc kết quả từ API.
        </div>
        <div
          className="demo-quiz-progress"
          role="progressbar"
          aria-label="Tiến độ bài trắc nghiệm"
          aria-valuemin={1}
          aria-valuemax={quizQuestions.length}
          aria-valuenow={quizIndex + 1}
        >
          <span
            style={{
              width: `${((quizIndex + 1) / quizQuestions.length) * 100}%`,
            }}
          />
        </div>
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
                      Câu tiếp theo <ArrowRight size={16} aria-hidden="true" />
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
                    role="radio"
                    aria-checked={isSelected}
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
                        Xem kết quả <ArrowRight size={16} aria-hidden="true" />
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
              Đây là kết quả từ bộ câu hỏi minh họa, không phải dữ liệu tài liệu
              hoặc thống kê học tập của bạn.
            </p>
            <Button className="primary restart-btn" onClick={handleRestartQuiz}>
              <RotateCcw size={16} aria-hidden="true" /> Làm lại bài kiểm tra
            </Button>
          </div>
        )}
      </Card>
    </div>
  )
}
