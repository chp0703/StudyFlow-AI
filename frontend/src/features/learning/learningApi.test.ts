import assert from "node:assert/strict"
import test from "node:test"
import type {
  DailyLearningMaterial,
  DailyLearningTurn,
} from "../../api/types.ts"
import {
  MAX_MATERIAL_BYTES,
  mapLearningTurn,
  materialStatus,
  validateMaterialFile,
} from "./learningApi.ts"

const material: DailyLearningMaterial = {
  material_id: "11111111-1111-4111-8111-111111111111",
  owner_id: "22222222-2222-4222-8222-222222222222",
  course_label: "Giải tích",
  filename: "dao-ham.pdf",
  mime_type: "application/pdf",
  sha256: "a".repeat(64),
  byte_size: 1024,
  page_count: 12,
  status: "READY",
  error_code: null,
  created_at: "2026-11-22T10:00:00Z",
}

const turn: DailyLearningTurn = {
  turn_id: "33333333-3333-4333-8333-333333333333",
  session_id: "44444444-4444-4444-8444-444444444444",
  owner_id: material.owner_id,
  ordinal: 2,
  role: "ASSISTANT",
  kind: "ASK",
  hint_level: null,
  content: "Đạo hàm đo tốc độ thay đổi.",
  citations: [
    {
      chunk_id: "55555555-5555-4555-8555-555555555555",
      material_id: material.material_id,
      page: 7,
      material_deleted: false,
    },
  ],
  supported: true,
  model: "fixture-model",
  prompt_version: "f3-v1",
}

test("contract-shaped citation fixture maps to the exact Vietnamese chip label", () => {
  const mapped = mapLearningTurn(
    turn,
    new Map([[material.material_id, material]]),
  )
  assert.equal(mapped.citations[0].label, "dao-ham.pdf · tr. 7")
})

test("deleted material fixture never guesses a document name", () => {
  const mapped = mapLearningTurn(
    {
      ...turn,
      citations: [{ ...turn.citations[0], material_deleted: true }],
    },
    new Map(),
  )
  assert.equal(mapped.citations[0].label, "Tài liệu đã xoá")
})

test("unsupported fixture remains citation-free", () => {
  const mapped = mapLearningTurn(
    { ...turn, supported: false, citations: [], content: "Không đủ căn cứ." },
    new Map([[material.material_id, material]]),
  )
  assert.equal(mapped.supported, false)
  assert.deepEqual(mapped.citations, [])
})

test("material status and upload validation match the Daily Learning contract", () => {
  assert.equal(materialStatus("READY").polling, false)
  assert.equal(materialStatus("INDEXING").polling, true)
  assert.match(
    validateMaterialFile({
      name: "a.pdf",
      size: MAX_MATERIAL_BYTES + 1,
      type: "application/pdf",
    })!,
    /5 MiB/,
  )
  assert.match(
    validateMaterialFile({
      name: "a.docx",
      size: 12,
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    })!,
    /PDF, TXT hoặc Markdown/,
  )
})
