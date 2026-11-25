import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const demoSource = readFileSync(
  new URL("./DemoLearningWorkspace.tsx", import.meta.url),
  "utf8",
)
const sessionSource = readFileSync(
  new URL("./LearningSession.tsx", import.meta.url),
  "utf8",
)
const styles = readFileSync(
  new URL("../../styles/study.css", import.meta.url),
  "utf8",
)

test("demo workspace explains backend limits without fabricating an AI turn", () => {
  assert.match(demoSource, /Chế độ demo · Chưa kết nối AI và tài liệu thật/)
  assert.match(demoSource, /Cần kết nối API và có tài liệu READY/)
  assert.doesNotMatch(demoSource, /setMessages|citations|Trợ lý học tập.*text:/)
})

test("API session requires a goal and READY material before starting", () => {
  assert.match(sessionSource, /!goal\.trim\(\)/)
  assert.match(sessionSource, /!selectedMaterials\.length/)
  assert.match(sessionSource, /role="log"/)
  assert.match(sessionSource, /nativeEvent\.isComposing/)
})

test("responsive learning workspace switches panels without horizontal layout", () => {
  assert.match(styles, /\.learning-mobile-switcher \{[\s\S]*?display: none;/)
  assert.match(
    styles,
    /@media \(max-width: 960px\)[\s\S]*?\.daily-learning-workspace \{[\s\S]*?display: block;/,
  )
  assert.match(
    styles,
    /\.daily-learning-workspace \.is-mobile-hidden \{[\s\S]*?display: none;/,
  )
})
