export type KeyValueStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">

export const learningSessionKey = (userId: string) =>
  `studyflow_learning_session_${userId}`

export function loadLearningSessionId(
  storage: KeyValueStorage,
  userId: string,
) {
  const value = storage.getItem(learningSessionKey(userId))
  return value?.trim() || null
}

export function saveLearningSessionId(
  storage: KeyValueStorage,
  userId: string,
  sessionId: string,
) {
  storage.setItem(learningSessionKey(userId), sessionId)
}

export function clearLearningSessionId(
  storage: KeyValueStorage,
  userId: string,
) {
  storage.removeItem(learningSessionKey(userId))
}
