import type { ActionReference } from "./types"

// The action waiting for the user's decision. Only the reference is kept (never its content): after a
// reload the screen asks the server to rebuild the presentation (POST /v1/actions/{id}/review).
export type Pending = {
  conversationId: string

  reference: ActionReference
}

const key = (userId: string) => `studyflow_pending_${userId}`

export function loadPending(userId: string): Pending | null {
  try {
    const raw = localStorage.getItem(key(userId))

    return raw ? JSON.parse(raw) as Pending : null
  } catch {
    return null
  }
}

export function savePending(userId: string, pending: Pending | null) {
  try {
    if (pending) localStorage.setItem(key(userId), JSON.stringify(pending))
    else localStorage.removeItem(key(userId))
  } catch {
    // Storage may be unavailable; the pending action is then simply not restored after a reload.
  }
}

// One server conversation for the Planner per account and browser.
export function plannerConversationId(userId: string): string {
  const name = `studyflow_planner_conversation_${userId}`

  try {
    const saved = localStorage.getItem(name)

    if (saved) return saved

    const fresh = crypto.randomUUID()

    localStorage.setItem(name, fresh)

    return fresh
  } catch {
    return crypto.randomUUID()
  }
}
