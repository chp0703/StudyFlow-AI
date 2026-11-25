import assert from "node:assert/strict"
import test from "node:test"
import { readFile } from "node:fs/promises"

test("task panel owns a bounded independently scrolling list", async () => {
  const css = await readFile(
    new URL("../../styles/planner.css", import.meta.url),
    "utf8",
  )
  assert.match(
    css,
    /\.task-panel-wrap \.task-panel\s*\{[^}]*max-height:\s*100%[^}]*min-height:\s*0[^}]*overflow:\s*hidden/s,
  )
  assert.match(
    css,
    /\.task-panel-body\s*\{[^}]*min-height:\s*0[^}]*overflow:\s*hidden/s,
  )
  assert.match(
    css,
    /\.task-panel-list\s*\{[^}]*flex:\s*1[^}]*min-height:\s*0[^}]*overflow-y:\s*auto/s,
  )
  assert.match(
    css,
    /@container \(max-width: 1050px\)[\s\S]*\.task-panel-wrap\s*\{[^}]*height:\s*420px/s,
  )
})
