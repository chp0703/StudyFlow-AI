import assert from "node:assert/strict"
import test from "node:test"
import { eligibleQuestions } from "./eligibleQuestions.ts"
import type { QuestionDraft } from "../../api/types.ts"

const question = {
  material_id: "material-1",
  status: "VERIFIED",
  question_type: "MCQ",
} as QuestionDraft

test("only verified questions from the selected material are eligible", () => {
  assert.deepEqual(
    eligibleQuestions(
      [
        question,
        { ...question, status: "DRAFT" },
        { ...question, status: "REJECTED" },
        { ...question, material_id: "material-2" },
      ],
      "material-1",
    ),
    [question],
  )
})
