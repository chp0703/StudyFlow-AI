import test, { after, before } from "node:test"

import assert from "node:assert/strict"

import { createElement, createRef } from "react"

import { renderToStaticMarkup } from "react-dom/server"

import { createServer, type ViteDevServer } from "vite"

let server: ViteDevServer

before(async () => {
  server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
})

after(async () => {
  await server.close()
})

test("composer renders a compact truthful state before focus", async () => {
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

    assert.match(compact, /maxLength="8000"/)

    assert.match(compact, /aria-expanded="false"/)

    assert.match(compact, /disabled=""/)

    assert.doesNotMatch(compact, /Bản demo dùng/)

    const draft = renderToStaticMarkup(
      createElement(Composer, {
        ...base,

        input: "lập kế hoạch",

        apiMode: false,

        feedback: { kind: "clarification", text: "Cho mình biết ngày." },
      }),
    )

    assert.match(draft, /rows="1"/)

    assert.match(draft, /aria-expanded="false"/)

    assert.doesNotMatch(draft, /Bản demo dùng/)

    const api = renderToStaticMarkup(
      createElement(Composer, {
        ...base,

        input: "Tạo công việc",

        apiMode: true,

        busy: true,
      }),
    )

    assert.doesNotMatch(api, /DeepSeek|kết nối AI/)

    assert.match(api, /Đang gửi yêu cầu/)
})

test("composer textarea grows to content and caps at its CSS maximum", async () => {
    const { resizePlannerComposer } = await server.ssrLoadModule(
      "/src/features/planner/composerTextarea.ts",
    )

    const textarea = { style: {}, scrollHeight: 80 }

    resizePlannerComposer(textarea as unknown as HTMLTextAreaElement)

    assert.deepEqual(textarea.style, { height: "80px", overflowY: "hidden" })

    textarea.scrollHeight = 140

    resizePlannerComposer(textarea as unknown as HTMLTextAreaElement)

    assert.deepEqual(textarea.style, { height: "112px", overflowY: "auto" })
})

test("composer keyboard behavior protects newlines, IME and duplicate sends", async () => {
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
})

test("API draft only clears after accepted or completed responses", async () => {
    const { shouldClearPlannerDraft } = await server.ssrLoadModule(
      "/src/features/planner/usePlanner.ts",
    )

    assert.equal(shouldClearPlannerDraft("AWAITING_APPROVAL"), true)

    assert.equal(shouldClearPlannerDraft("SUCCEEDED"), true)

    assert.equal(shouldClearPlannerDraft("NEEDS_CLARIFICATION"), false)

    assert.equal(shouldClearPlannerDraft("ERROR"), false)
})

test("PlannerClarificationPopup prefills from server slots after F5 without forcing deadline_at", async () => {
    const { default: Popup } = await server.ssrLoadModule(
      "/src/features/planner/PlannerClarificationPopup.tsx",
    )
    const html = renderToStaticMarkup(
      createElement(Popup, {
        clarification: {
          source: "api",
          originalPrompt: "",
          message: "Cần thêm thông tin.",
          questions: [
            {
              field: "estimated_minutes",
              message: "Bạn dự kiến cần bao nhiêu phút?",
              choices: [],
            },
          ],
          slots: {
            title: "Học Toán",
            start_at: "2026-11-28T13:00:00.000000Z",
          },
        },
        busy: false,
        onDismiss: () => {},
        onSubmit: () => {},
      }),
    )
    assert.match(html, /value="Học Toán"/)
    assert.match(html, /value="2026-11-28"/)
    assert.match(html, /value="20:00"/)
    assert.doesNotMatch(html, /Đã điền sẵn từ yêu cầu/)
    assert.doesNotMatch(html, /Giờ hạn hoàn thành/)
})
