import test from "node:test"
import assert from "node:assert/strict"
import { createElement } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import { createServer } from "vite"

test("ordinary composer feedback is not duplicated in proposal review", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { default: ProposalReview } = await server.ssrLoadModule(
      "/src/features/planner/ProposalReview.tsx",
    )
    const html = renderToStaticMarkup(
      createElement(ProposalReview, {
        proposal: null,
        stale: false,
        busy: false,
        reply: "Lệnh chưa hợp lệ",
        approve: () => {},
        reject: () => {},
      }),
    )

    assert.doesNotMatch(html, /Lệnh chưa hợp lệ/)
  } finally {
    await server.close()
  }
})

test("an unresolved TimeWindow warning disables approval but keeps rejection", async () => {
  const server = await createServer({
    server: { middlewareMode: true, hmr: false },
    appType: "custom",
  })
  try {
    const { default: ProposalReview } = await server.ssrLoadModule(
      "/src/features/planner/ProposalReview.tsx",
    )
    const html = renderToStaticMarkup(
      createElement(ProposalReview, {
        proposal: {
          id: "a",
          createdAt: 0,
          baseRevision: 1,
          next: { tasks: [], availability: [] },
          changes: [],
          windowChanges: [],
          issues: [],
          reply: "Xem lại",
          server: {
            reference: {
              action_id: "a",
              action_version: 1,
              target_type: "PENDING_ACTION",
              target_id: "a",
              target_version: 1,
            },
            title: "Sửa thời gian học",
            details: [],
            taskIds: [],
            approvalError: "Không thể xác minh đầy đủ khung giờ bị ảnh hưởng.",
          },
        },
        stale: false,
        busy: false,
        reply: "",
        approve: () => {},
        reject: () => {},
      }),
    )
    assert.match(html, /role="alert"/)
    assert.match(html, /proposal-reject[^>]*>.*Từ chối/s)
    assert.doesNotMatch(html, /proposal-reject[^>]*disabled/s)
    assert.match(html, /proposal-approve[^>]*disabled/s)
  } finally {
    await server.close()
  }
})
