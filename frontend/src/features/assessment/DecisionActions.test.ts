import assert from "node:assert/strict"
import test from "node:test"
import { createElement } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { createServer } from "vite"

test("decision recovery UI keeps only the original uncertain decision retryable", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { default: DecisionActions } = await server.ssrLoadModule(
      "/src/features/assessment/DecisionActions.tsx",
    )
    const html = renderToStaticMarkup(
      createElement(DecisionActions, {
        count: 5,
        state: "uncertain",
        pendingDecision: "APPROVE",
        busy: false,
        referencePresent: true,
        onDecision: () => {},
        onReconcile: () => {},
      }),
    )
    assert.match(html, /Bản nháp vẫn được giữ lại/)
    assert.match(html, /Thử lại xác minh/)
    assert.match(html, /disabled=""[^>]*>Từ chối/)
  } finally {
    await server.close()
  }
})

test("definite decision failure blocks both choices and offers reconciliation", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { default: DecisionActions } = await server.ssrLoadModule(
      "/src/features/assessment/DecisionActions.tsx",
    )
    const html = renderToStaticMarkup(
      createElement(DecisionActions, {
        count: 5,
        state: "blocked",
        pendingDecision: "APPROVE",
        busy: false,
        referencePresent: true,
        onDecision: () => {},
        onReconcile: () => {},
      }),
    )
    assert.equal((html.match(/disabled=""/g) ?? []).length, 2)
    assert.match(html, /Kiểm tra trạng thái/)
  } finally {
    await server.close()
  }
})
