import assert from "node:assert/strict"
import test from "node:test"
import { readFileSync } from "node:fs"
import { summarize } from "./mappers.ts"
import type { ActionPresentation } from "./types.ts"

test("B7 summary exposes observed errors, user choices and confidence/source limits", () => {
  const rec = JSON.parse(
    readFileSync(
      new URL(
        "../../../contracts/examples/valid/RevisionRecommendation.json",
        import.meta.url,
      ),
      "utf8",
    ),
  )
  const chunk = JSON.parse(
    readFileSync(
      new URL(
        "../../../contracts/examples/valid/MaterialChunk.json",
        import.meta.url,
      ),
      "utf8",
    ),
  )
  const p = {
    kind: "ACTION_PRESENTATION",
    pending_action: { intent: "ACCEPT_REVISION_RECOMMENDATION" },
    candidate: null,
    proposal: null,
    normalized_command: null,
    effective_policy: null,
    revision_recommendation: rec,
    revision_source_chunks: [chunk],
  } as unknown as ActionPresentation
  const before = structuredClone(p)
  const result = summarize(p)
  assert.match(result.title, /Gợi ý ôn tập/)
  const text = result.details.map((d) => `${d.label}: ${d.value}`).join("\n")
  assert.match(text, /3\/4/)
  assert.match(text, /LOW/)
  assert.ok(text.includes(rec.evidence.attempt_ids[0]))
  assert.ok(text.includes(chunk.chunk_id))
  assert.ok(text.includes(chunk.text))
  assert.ok(
    text.includes(`Thời lượng do bạn chọn: ${rec.suggested_minutes} phút`),
  )
  assert.ok(text.includes(`Ưu tiên do bạn chọn: ${rec.priority}`))
  assert.deepEqual(p, before)
})
