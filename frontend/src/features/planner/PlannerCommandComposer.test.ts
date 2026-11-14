import test from "node:test"
import assert from "node:assert/strict"
import { createElement, createRef } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { createServer } from "vite"

test("composer renders compact and expanded truthful states", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { default: Composer } = await server.ssrLoadModule(
      "/src/features/planner/PlannerCommandComposer.tsx",
    )
    const base = {
      setInput: () => {},
      send: () => {},
      busy: false,
      feedback: null,
      textareaRef: createRef<HTMLTextAreaElement>(),
    }
    const compact = renderToStaticMarkup(
      createElement(Composer, { ...base, input: "", apiMode: false }),
    )
    assert.match(compact, /rows="1"/)
    assert.match(compact, /aria-expanded="false"/)
    assert.match(compact, /disabled=""/)
    assert.doesNotMatch(compact, /Bản demo dùng/)

    const expanded = renderToStaticMarkup(
      createElement(Composer, {
        ...base,
        input: "lập kế hoạch",
        apiMode: false,
        feedback: { kind: "clarification", text: "Cho mình biết ngày." },
      }),
    )
    assert.match(expanded, /rows="3"/)
    assert.match(
      expanded,
      /Bản demo dùng bộ phân tích lệnh cục bộ, chưa kết nối AI/,
    )
    assert.match(expanded, /tạo công việc Báo cáo hạn 20\/11 3 giờ/)
    assert.match(expanded, /role="alert"/)
    assert.match(expanded, /Cho mình biết ngày/)

    const api = renderToStaticMarkup(
      createElement(Composer, {
        ...base,
        input: "Tạo công việc",
        apiMode: true,
        busy: true,
      }),
    )
    assert.match(api, /Gửi qua máy chủ StudyFlow/)
    assert.doesNotMatch(api, /DeepSeek|kết nối AI/)
    assert.match(api, /Đang gửi yêu cầu/)
  } finally {
    await server.close()
  }
})

test("composer keyboard behavior protects newlines, IME and duplicate sends", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { composerKeyAction } = await server.ssrLoadModule(
      "/src/features/planner/composerKeyboard.ts",
    )
    const action = (overrides: Record<string, unknown> = {}) =>
      composerKeyAction({
        key: "Enter",
        shiftKey: false,
        isComposing: false,
        busy: false,
        hasText: true,
        ...overrides,
      })
    assert.equal(action(), "submit")
    assert.equal(action({ shiftKey: true }), "none")
    assert.equal(action({ isComposing: true }), "none")
    assert.equal(action({ busy: true }), "none")
    assert.equal(action({ hasText: false }), "none")
    assert.equal(action({ key: "Tab" }), "none")
    assert.equal(action({ key: "Escape", hasText: false }), "collapse")
  } finally {
    await server.close()
  }
})

test("API draft only clears after accepted or completed responses", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { shouldClearPlannerDraft } = await server.ssrLoadModule(
      "/src/features/planner/usePlanner.ts",
    )
    assert.equal(shouldClearPlannerDraft("AWAITING_APPROVAL"), true)
    assert.equal(shouldClearPlannerDraft("SUCCEEDED"), true)
    assert.equal(shouldClearPlannerDraft("NEEDS_CLARIFICATION"), false)
    assert.equal(shouldClearPlannerDraft("ERROR"), false)
  } finally {
    await server.close()
  }
})
