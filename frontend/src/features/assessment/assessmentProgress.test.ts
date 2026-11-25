import assert from "node:assert/strict"
import test from "node:test"
import { assessmentStageState } from "./assessmentProgress.ts"

test("assessment stages unlock only from persisted backend state", () => {
  const empty = assessmentStageState({
    materialReady: false,
    verifiedCount: 0,
    hasAttempt: false,
    hasResult: false,
    statsLoaded: false,
  })
  assert.deepEqual(empty, {
    materials: { available: true, completed: false },
    questions: { available: false, completed: false },
    practice: { available: false, completed: false },
    results: { available: false, completed: false },
  })

  const verified = assessmentStageState({
    materialReady: true,
    verifiedCount: 2,
    hasAttempt: false,
    hasResult: false,
    statsLoaded: true,
  })
  assert.equal(verified.materials.completed, true)
  assert.equal(verified.questions.completed, true)
  assert.equal(verified.practice.available, true)
  assert.equal(verified.practice.completed, false)
  assert.equal(verified.results.completed, true)
})
