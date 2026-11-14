import test from "node:test"

import assert from "node:assert/strict"

import { ApiError, createApiClient, errorText } from "./client.ts"

import { createEndpoints } from "./endpoints.ts"

type Call = {
  url: string

  init: RequestInit
}

function setup(responses: (Response | Error)[], token: string | null = "tok") {
  const calls: Call[] = []

  const unauth: number[] = []

  const client = createApiClient({
    baseUrl: "http://api.test",

    getToken: async () => token,

    onUnauthenticated: () => unauth.push(1),

    retryDelayMs: 0,

    fetchImpl: (async (url: string, init: RequestInit) => {
      calls.push({ url, init })

      const next = responses.shift()!

      if (next instanceof Error) throw next

      return next
    }) as unknown as typeof fetch,
  })

  return { client, calls, unauth }
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status,

    headers: { "Content-Type": "application/json" },
  })

const errBody = (code: string, retryable = false) => ({
  error: { code, message: "m", field: null, retryable },
})

test("GET sends the bearer token, repeats status_filter and skips empty query values", async () => {
  const { client, calls } = setup([
    json({ data: { items: [], next_cursor: null } }),
  ])

  await client.request("GET", "/v1/tasks", {
    query: {
      status_filter: ["TODO", "IN_PROGRESS"],

      cursor: undefined,

      page_size: 100,
    },
  })

  assert.equal(
    calls[0].url,

    "http://api.test/v1/tasks?status_filter=TODO&status_filter=IN_PROGRESS&page_size=100",
  )

  const headers = calls[0].init.headers as Record<string, string>

  assert.equal(headers.Authorization, "Bearer tok")

  assert.equal(headers["Idempotency-Key"], undefined)
})

test("POST sends a JSON body and an idempotency key", async () => {
  const { client, calls } = setup([json({ state: "SUCCEEDED" })])

  await client.request("POST", "/v1/messages", {
    body: { a: 1 },

    idempotencyKey: "k-1234567890123456",
  })

  const headers = calls[0].init.headers as Record<string, string>

  assert.equal(headers["Idempotency-Key"], "k-1234567890123456")

  assert.equal(headers["Content-Type"], "application/json")

  assert.equal(calls[0].init.body, '{"a":1}')
})

test("a transient failure is retried once with the same idempotency key", async () => {
  const { client, calls } = setup([
    json(errBody("SERVICE_UNAVAILABLE", true), 503),

    json({ state: "SUCCEEDED" }),
  ])

  assert.deepEqual(
    await client.request("POST", "/v1/decisions", { body: {} }),

    { state: "SUCCEEDED" },
  )

  assert.equal(calls.length, 2)

  const keys = calls.map(
    (c) => (c.init.headers as Record<string, string>)["Idempotency-Key"],
  )

  assert.equal(keys[0], keys[1])

  assert.ok(keys[0].length >= 16)
})

test("a network failure is retryable and then reported as unavailable", async () => {
  const { client, calls } = setup([new Error("down"), new Error("down")])

  await assert.rejects(
    client.request("GET", "/v1/tasks"),

    (e: ApiError) => e.code === "SERVICE_UNAVAILABLE" && e.status === 0,
  )

  assert.equal(calls.length, 2)
})

test("a domain error is not retried and keeps its code", async () => {
  const { client, calls } = setup([json(errBody("STALE_PROPOSAL"), 409)])

  await assert.rejects(
    client.request("POST", "/v1/decisions", { body: {} }),

    (e: ApiError) => e.code === "STALE_PROPOSAL" && e.status === 409,
  )

  assert.equal(calls.length, 1)

  assert.match(
    errorText(new ApiError(409, errBody("STALE_PROPOSAL").error)),

    /Lịch đã thay đổi/,
  )
})

test("401 notifies the app and a missing token never reaches the network", async () => {
  const first = setup([json(errBody("UNAUTHENTICATED"), 401)])

  await assert.rejects(first.client.request("GET", "/v1/tasks"))

  assert.equal(first.unauth.length, 1)

  const second = setup([], null)

  await assert.rejects(
    second.client.request("GET", "/v1/tasks"),

    (e: ApiError) => e.code === "UNAUTHENTICATED",
  )

  assert.equal(second.calls.length, 0)

  assert.equal(second.unauth.length, 1)
})

test("listTasks follows cursors until the last page", async () => {
  const { client, calls } = setup([
    json({ data: { items: [{ task_id: "a" }], next_cursor: "c1" } }),

    json({ data: { items: [{ task_id: "b" }], next_cursor: null } }),
  ])

  const items = await createEndpoints(client).listTasks()

  assert.deepEqual(
    items.map((t) => t.task_id),

    ["a", "b"],
  )

  assert.match(calls[1].url, /cursor=c1/)
})

test("decide sends the action reference untouched", async () => {
  const { client, calls } = setup([json({ state: "SUCCEEDED" })])

  const reference = {
    action_id: "a",

    action_version: 1,

    target_type: "TASK_CANDIDATE" as const,

    target_id: "t",

    target_version: 2,
  }

  await createEndpoints(client).decide(
    "conv",

    reference,

    "APPROVE",

    "key-0123456789abcdef",
  )

  const body = JSON.parse(calls[0].init.body as string)

  assert.deepEqual(body, {
    schema_version: "1.1",

    conversation_id: "conv",

    action_reference: reference,

    decision: "APPROVE",
  })
})

test("weekly window archive prepares an action without approving it", async () => {
  const { client, calls } = setup([json({ state: "AWAITING_APPROVAL" })])
  await createEndpoints(client).prepareAvailability(
    "conv",
    {
      change_type: "ARCHIVE",
      window_id: "window-id",
      expected_window_version: 3,
      window: null,
    },
    "key-0123456789abcdef",
  )
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, "http://api.test/v1/actions")
  assert.deepEqual(JSON.parse(calls[0].init.body as string), {
    schema_version: "1.1",
    conversation_id: "conv",
    operation: "set_availability",
    arguments: {
      change_type: "ARCHIVE",
      window_id: "window-id",
      expected_window_version: 3,
      window: null,
    },
  })
})

test("weekly ADD and UPDATE send exact schema 1.1 arguments and version", async () => {
  const { client, calls } = setup([
    json({ state: "AWAITING_APPROVAL" }),
    json({ state: "AWAITING_APPROVAL" }),
  ])
  const window = {
    kind: "AVAILABILITY" as const,
    label: null,
    recurrence: "WEEKLY" as const,
    timezone: "Asia/Ho_Chi_Minh",
    start_at: null,
    end_at: null,
    weekday: 1,
    start_time: "08:15",
    end_time: "11:30",
    valid_from: "2026-11-16",
    valid_until: null,
  }
  const endpoints = createEndpoints(client)
  await endpoints.prepareAvailability(
    "conv",
    {
      change_type: "ADD",
      window_id: null,
      expected_window_version: null,
      window,
    },
    "add-key",
  )
  await endpoints.prepareAvailability(
    "conv",
    {
      change_type: "UPDATE",
      window_id: "server-window",
      expected_window_version: 4,
      window: { ...window, end_time: "17:45" },
    },
    "update-key",
  )
  assert.equal(calls.length, 2)
  const add = JSON.parse(calls[0].init.body as string)
  const update = JSON.parse(calls[1].init.body as string)
  assert.equal(add.schema_version, "1.1")
  assert.equal(add.operation, "set_availability")
  assert.deepEqual(add.arguments, {
    change_type: "ADD",
    window_id: null,
    expected_window_version: null,
    window,
  })
  assert.equal(update.arguments.window_id, "server-window")
  assert.equal(update.arguments.expected_window_version, 4)
  assert.equal(update.arguments.window.end_time, "17:45")
})

test("availability POST retries a network failure with the same idempotency key", async () => {
  const { client, calls } = setup([
    new Error("timeout"),
    json({ state: "AWAITING_APPROVAL" }),
  ])
  await createEndpoints(client).prepareAvailability(
    "conv",
    {
      change_type: "ARCHIVE",
      window_id: "server-window",
      expected_window_version: 4,
      window: null,
    },
    "same-key",
  )
  assert.equal(calls.length, 2)
  assert.equal(
    (calls[0].init.headers as Record<string, string>)["Idempotency-Key"],
    "same-key",
  )
  assert.equal(
    (calls[1].init.headers as Record<string, string>)["Idempotency-Key"],
    "same-key",
  )
  assert.equal(calls[0].init.body, calls[1].init.body)
})
