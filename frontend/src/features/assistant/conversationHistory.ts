import type {
  ChatMessage,
  ChatAttachment,
  ActionProposal,
} from "../../types/assistant.ts"

export const HISTORY_SCHEMA_VERSION = 1

export type Draft = {
  title: string

  course: string

  deadline: string

  duration: string

  availability: string

  block: string

  target: string
}

export const emptyDraft = (): Draft => ({
  title: "",

  course: "",

  deadline: "",

  duration: "",

  availability: "",

  block: "",

  target: "",
})

export type WorkflowStatus = "idle" | "awaiting_clarification" | "awaiting_approval" | "review_required" | "cancelled" | "demo_acknowledged"

export type Conversation = {
  schemaVersion: 1

  id: string

  title: string

  manuallyRenamed: boolean

  createdAt: string

  updatedAt: string

  messages: ChatMessage[]

  draftInput: string

  workflow: {
    status: WorkflowStatus

    draft: Draft

    formError: string
  }
}

export function titleFromMessage(text: string): string {
  const compact = text.trim().replace(/\s+/gu, " ")

  return compact.length > 60 ? `${compact.slice(0, 57).trimEnd()}…` : compact
}

export function createConversation(
  text: string,

  now = new Date().toISOString(),
): Conversation {
  return {
    schemaVersion: 1,

    id: crypto.randomUUID(),

    title: titleFromMessage(text),

    manuallyRenamed: false,

    createdAt: now,

    updatedAt: now,

    messages: [],

    draftInput: "",

    workflow: { status: "idle", draft: emptyDraft(), formError: "" },
  }
}

export function appendMessages(
  conversation: Conversation,

  messages: ChatMessage[],

  now = new Date().toISOString(),
): Conversation {
  const last = messages.at(-1)

  return {
    ...conversation,

    updatedAt: now,

    messages: [...conversation.messages, ...messages],

    draftInput: "",

    workflow: {
      status:
        last?.category === "CLARIFICATION"
          ? "awaiting_clarification"
          : last?.category === "PROPOSAL"
            ? "awaiting_approval"
            : "idle",

      draft: emptyDraft(),

      formError: "",
    },
  }
}

export function setProposalStatus(
  conversation: Conversation,

  messageId: string,

  status: ActionProposal["status"],
): Conversation {
  return {
    ...conversation,

    updatedAt: new Date().toISOString(),

    messages: conversation.messages.map((message) =>
      message.id === messageId && message.proposal
        ? { ...message, proposal: { ...message.proposal, status } }
        : message,
    ),

    workflow: { ...conversation.workflow, status },
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function safeDraft(value: unknown): Draft {
  const source = isObject(value) ? value : {}

  const result = emptyDraft()

  const keys: Array<keyof Draft> = [
    "title",

    "course",

    "deadline",

    "duration",

    "availability",

    "block",

    "target",
  ]

  for (const key of keys)
    result[key] = typeof source[key] === "string" ? source[key] as string : ""

  return result
}

function safeMessage(value: unknown): ChatMessage | null {
  if (
    !isObject(value) ||
    typeof value.id !== "string" ||
    typeof value.text !== "string" ||
    typeof value.timestamp !== "string" ||
    !["user", "assistant"].includes(String(value.role))
  )
    return null

  const category = [
    "MESSAGE",

    "CLARIFICATION",

    "PROPOSAL",

    "UNSUPPORTED",

    "ERROR",
  ].includes(String(value.category))
    ? value.category as ChatMessage["category"]
    : "ERROR"

  const message: ChatMessage = {
    id: value.id,

    timestamp: value.timestamp,

    role: value.role as ChatMessage["role"],

    category,

    text: value.text,
  }

  if (Array.isArray(value.attachments)) {
    const attachments = value.attachments
      .filter(
        (att): att is ChatAttachment =>
          isObject(att) &&
          typeof att.id === "string" &&
          typeof att.name === "string" &&
          typeof att.size === "string" &&
          (att.type === "image" || att.type === "file"),
      )
      .map((att) => ({
        id: att.id,
        name: att.name,
        size: att.size,
        type: att.type,
        ...(typeof att.dataUrl === "string" ? { dataUrl: att.dataUrl } : {}),
      }))

    if (attachments.length > 0) message.attachments = attachments
  }

  if (["task", "plan", "view", "reschedule"].includes(String(value.scenario)))
    message.scenario = (value.scenario as ChatMessage["scenario"])

  if (typeof value.intent === "string")
    message.intent = (value.intent as ChatMessage["intent"])

  if (
    ["missing_information", "valid_demo_draft"].includes(
      String(value.validation),
    )
  )
    message.validation = (value.validation as ChatMessage["validation"])

  if (
    isObject(value.proposal) &&
    typeof value.proposal.title === "string" &&
    typeof value.proposal.caveat === "string" &&
    Array.isArray(value.proposal.details)
  ) {
    const details = value.proposal.details.filter(
      (item): item is {
        label: string

        value: string
      } =>
        isObject(item) &&
        typeof item.label === "string" &&
        typeof item.value === "string",
    )

    const status = ["cancelled", "demo_acknowledged"].includes(
      String(value.proposal.status),
    )
      ? value.proposal.status as ActionProposal["status"]
      : "review_required"

    message.proposal = {
      intent: value.proposal.intent as ActionProposal["intent"],

      title: value.proposal.title,

      caveat: value.proposal.caveat,

      details,

      status,
    }
  }

  return message
}

// Tin nhắn được khôi phục chỉ là lịch sử. Thao tác chờ duyệt luôn cần xem lại trước.

export function restoreConversation(value: unknown): Conversation | null {
  if (
    !isObject(value) ||
    value.schemaVersion !== HISTORY_SCHEMA_VERSION ||
    typeof value.id !== "string" ||
    typeof value.title !== "string" ||
    typeof value.createdAt !== "string" ||
    typeof value.updatedAt !== "string" ||
    !Array.isArray(value.messages)
  )
    return null

  const messages = value.messages

    .map(safeMessage)

    .filter((item): item is ChatMessage => item !== null)

  const savedWorkflow = isObject(value.workflow) ? value.workflow : {}

  const last = messages.at(-1)

  const status: WorkflowStatus =
    last?.proposal?.status === "review_required"
      ? "review_required"
      : last?.category === "CLARIFICATION"
        ? "awaiting_clarification"
        : ["idle", "cancelled", "demo_acknowledged"].includes(
              String(savedWorkflow.status),
            )
          ? savedWorkflow.status as WorkflowStatus
          : "idle"

  return {
    schemaVersion: 1,

    id: value.id,

    title: value.title.slice(0, 60),

    manuallyRenamed: value.manuallyRenamed === true,

    createdAt: value.createdAt,

    updatedAt: value.updatedAt,

    messages,

    draftInput: typeof value.draftInput === "string" ? value.draftInput : "",

    workflow: {
      status,

      draft: safeDraft(savedWorkflow.draft),

      formError:
        typeof savedWorkflow.formError === "string"
          ? savedWorkflow.formError
          : "",
    },
  }
}

export function historyGroup(
  updatedAt: string,

  now = new Date(),
): "Hôm nay" | "Hôm qua" | "7 ngày gần đây" | "Cũ hơn" {
  const date = new Date(updatedAt)

  if (Number.isNaN(date.getTime())) return "Cũ hơn"

  const start = new Date(
    now.getFullYear(),

    now.getMonth(),

    now.getDate(),
  ).getTime()

  const day = new Date(
    date.getFullYear(),

    date.getMonth(),

    date.getDate(),
  ).getTime()

  const elapsed = Math.round((start - day) / 86400000)

  if (elapsed <= 0) return "Hôm nay"

  if (elapsed === 1) return "Hôm qua"

  if (elapsed <= 7) return "7 ngày gần đây"

  return "Cũ hơn"
}

const DB_NAME = "studyflow-assistant-history"

export function openHistoryDatabase(
  factory: IDBFactory | undefined = globalThis.indexedDB,
): Promise<IDBDatabase> {
  if (!factory) return Promise.reject(new Error("IndexedDB unavailable"))

  return new Promise((resolve, reject) => {
    const request = factory.open(DB_NAME, HISTORY_SCHEMA_VERSION)

    request.onupgradeneeded = () => {
      const db = request.result

      if (!db.objectStoreNames.contains("conversations"))
        db.createObjectStore("conversations", { keyPath: "id" })

      if (!db.objectStoreNames.contains("meta"))
        db.createObjectStore("meta", { keyPath: "key" })
    }

    request.onsuccess = () => resolve(request.result)

    request.onerror = () =>
      reject(request.error ?? new Error("IndexedDB open failed"))

    request.onblocked = () => reject(new Error("IndexedDB upgrade blocked"))
  })
}

function asPromise<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)

    request.onerror = () =>
      reject(request.error ?? new Error("IndexedDB request failed"))
  })
}

function transactionDone(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve()

    transaction.onerror = () =>
      reject(transaction.error ?? new Error("IndexedDB transaction failed"))

    transaction.onabort = () =>
      reject(transaction.error ?? new Error("IndexedDB transaction aborted"))
  })
}

export async function loadHistory(
  db: IDBDatabase,
): Promise<{
  conversations: Conversation[]

  activeId: string | null

  skipped: number
}> {
  const transaction = db.transaction(["conversations", "meta"], "readonly")

  const records = asPromise(transaction.objectStore("conversations").getAll())

  const selected = asPromise(transaction.objectStore("meta").get("activeId"))

  const [raw, meta] = await Promise.all([records, selected])

  const conversations = raw

    .map(restoreConversation)

    .filter((item): item is Conversation => item !== null)

  return {
    conversations,

    activeId:
      isObject(meta) && typeof meta.value === "string" ? meta.value : null,

    skipped: raw.length - conversations.length,
  }
}

export async function putConversation(
  db: IDBDatabase,

  conversation: Conversation,
): Promise<void> {
  const tx = db.transaction("conversations", "readwrite")

  tx.objectStore("conversations").put(conversation)

  await transactionDone(tx)
}

export async function removeConversation(
  db: IDBDatabase,

  id: string,
): Promise<void> {
  const tx = db.transaction("conversations", "readwrite")

  tx.objectStore("conversations").delete(id)

  await transactionDone(tx)
}

export async function clearConversations(db: IDBDatabase): Promise<void> {
  const tx = db.transaction(["conversations", "meta"], "readwrite")

  tx.objectStore("conversations").clear()

  tx.objectStore("meta").put({ key: "activeId", value: null })

  await transactionDone(tx)
}

export async function putActiveId(
  db: IDBDatabase,

  id: string | null,
): Promise<void> {
  const tx = db.transaction("meta", "readwrite")

  tx.objectStore("meta").put({ key: "activeId", value: id })

  await transactionDone(tx)
}
