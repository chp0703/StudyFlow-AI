import test from "node:test"
import assert from "node:assert/strict"
import { getAssistantReply } from "./assistantService.ts"

test("demo attachments remain display-only and never claim extraction", () => {
  const file = {
    id: "1",
    name: "notes.pdf",
    size: "10 KB",
    type: "file" as const,
  }
  for (const input of ["", "tạo task từ tệp", "lập kế hoạch", "tóm tắt tệp"]) {
    const reply = getAssistantReply(input, [file])
    assert.match(reply.text, /Chưa tải lên hoặc đọc nội dung/)
    assert.doesNotMatch(reply.text, /đã nạp|trích xuất thành công/i)
  }
})
