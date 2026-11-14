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
