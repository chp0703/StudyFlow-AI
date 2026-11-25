import assert from "node:assert/strict"
import test from "node:test"
import {
  applyServerHintLevel,
  hintButtonLabel,
  initialHintState,
  resetHintState,
} from "./hintState.ts"

test("hint state follows server levels and stops at three", () => {
  const one = applyServerHintLevel(initialHintState(), 1)
  const two = applyServerHintLevel(one, 2)
  const three = applyServerHintLevel(two, 3)
  assert.equal(hintButtonLabel(one), "Gợi ý 2/3")
  assert.equal(two.level, 2)
  assert.equal(three.exhausted, true)
  assert.equal(hintButtonLabel(three), "Đã dùng 3/3 gợi ý")
})

test("a new question resets hint UI", () => {
  assert.deepEqual(resetHintState(), initialHintState())
})

test("invalid, decreasing, or missing server levels never fabricate progress", () => {
  const current = applyServerHintLevel(initialHintState(), 2)
  for (const invalid of [null, 0, 1, 4, 1.5]) {
    const next = applyServerHintLevel(current, invalid)
    assert.equal(next.level, 2)
    assert.equal(next.valid, false)
  }
})
