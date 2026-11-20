import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const workspaceSource = readFileSync(
  new URL("./AssessmentWorkspace.tsx", import.meta.url),
  "utf8",
)
const studyStyles = readFileSync(
  new URL("../../styles/study.css", import.meta.url),
  "utf8",
)

test("assessment workspace keeps one compact heading and four stages", () => {
  assert.doesNotMatch(workspaceSource, /assessment-hero/)
  assert.doesNotMatch(
    workspaceSource,
    /Học từ tài liệu, kiểm tra bằng dữ liệu thật/,
  )
  for (const label of ["Tài liệu", "Câu hỏi", "Luyện tập", "Kết quả"]) {
    assert.match(workspaceSource, new RegExp(`label: "${label}"`))
  }
})

test("assessment layout uses natural page scrolling and compact controls", () => {
  assert.match(
    studyStyles,
    /\.main-content:has\(\.study-assessment-container\)[\s\S]*?overflow: visible;/,
  )
  assert.match(studyStyles, /\.assessment-step \{[^}]*min-height: 48px;/)
  assert.match(studyStyles, /\.assessment-dropzone \{[^}]*min-height: 124px;/)
  assert.match(
    studyStyles,
    /\.assessment-workspace \{[^}]*box-sizing: border-box;/,
  )
  assert.doesNotMatch(
    studyStyles,
    /\.study-assessment-container \{[^}]*overflow: auto;/,
  )
})

test("quiz does not render the next button on the final question", () => {
  assert.match(
    workspaceSource,
    /quizIndex < attempt\.question_ids\.length - 1 && \([\s\S]*?Câu tiếp theo[\s\S]*?\)/,
  )
  assert.doesNotMatch(
    workspaceSource,
    /disabled=\{quizIndex === attempt\.question_ids\.length - 1\}/,
  )
})
