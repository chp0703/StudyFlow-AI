import assert from "node:assert/strict"
import test from "node:test"
import { createElement } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { createServer } from "vite"

test("quiz overview exposes current, answered and unanswered navigator states", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { default: QuizOverview } = await server.ssrLoadModule(
      "/src/features/assessment/QuizOverview.tsx",
    )
    const html = renderToStaticMarkup(
      createElement(QuizOverview, {
        questionIds: ["q1", "q2", "q3"],
        answers: { q1: "A", stale: "B" },
        currentIndex: 1,
        busy: false,
        canSubmit: true,
        showConfirmation: false,
        onNavigate: () => {},
        onRequestSubmit: () => {},
        onCancelSubmit: () => {},
        onConfirmSubmit: () => {},
      }),
    )
    assert.match(html, /1\/3 đã trả lời/)
    assert.match(html, /aria-current="true"/)
    assert.match(html, /Đi đến câu 1, đã trả lời/)
    assert.match(html, /Đi đến câu 3, chưa trả lời/)
    assert.doesNotMatch(html, /đúng|sai/i)
  } finally {
    await server.close()
  }
})

test("submission confirmation reports omissions and offers cancel or confirm", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { default: QuizOverview } = await server.ssrLoadModule(
      "/src/features/assessment/QuizOverview.tsx",
    )
    const html = renderToStaticMarkup(
      createElement(QuizOverview, {
        questionIds: ["q1", "q2", "q3"],
        answers: { q2: "C" },
        currentIndex: 2,
        busy: false,
        canSubmit: true,
        showConfirmation: true,
        onNavigate: () => {},
        onRequestSubmit: () => {},
        onCancelSubmit: () => {},
        onConfirmSubmit: () => {},
      }),
    )
    assert.match(html, /2 câu chưa trả lời sẽ được gửi dưới dạng bỏ qua/)
    assert.match(html, /Quay lại bài làm/)
    assert.match(html, /Xác nhận nộp bài/)
  } finally {
    await server.close()
  }
})
