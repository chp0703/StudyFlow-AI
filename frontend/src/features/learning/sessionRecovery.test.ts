import assert from "node:assert/strict"
import test from "node:test"
import {
  clearLearningSessionId,
  learningSessionKey,
  loadLearningSessionId,
  saveLearningSessionId,
} from "./sessionRecovery.ts"

function memoryStorage() {
  const values = new Map<string, string>()
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  }
}

test("session recovery is user-scoped and stores only the session id", () => {
  const storage = memoryStorage()
  saveLearningSessionId(storage, "user-a", "session-1")
  assert.equal(loadLearningSessionId(storage, "user-a"), "session-1")
  assert.equal(loadLearningSessionId(storage, "user-b"), null)
  assert.equal(
    learningSessionKey("user-a"),
    "studyflow_learning_session_user-a",
  )
  clearLearningSessionId(storage, "user-a")
  assert.equal(loadLearningSessionId(storage, "user-a"), null)
})
