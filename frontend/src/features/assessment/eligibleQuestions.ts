import type { QuestionDraft } from "../../api/types.ts"

// The server also enforces this boundary when an attempt is created.
export function eligibleQuestions(
  questions: QuestionDraft[],
  materialId: string,
) {
  return questions.filter(
    (question) =>
      question.material_id === materialId &&
      question.status === "VERIFIED" &&
      (question.question_type === "MCQ" ||
        question.question_type === "TRUE_FALSE"),
  )
}
