import assert from "node:assert/strict"
import test from "node:test"

import { createEndpoints } from "./endpoints.ts"
import type { ApiClient, RequestOptions } from "./client.ts"

function fixture() {
  const calls: Array<{ method: string; path: string; options: RequestOptions }> = []
  const client: ApiClient = {
    async request<T>(method: string, path: string, options: RequestOptions = {}) {
      calls.push({ method, path, options })
      return { data: { source_id: "source" } } as T
    },
  }
  return { calls, endpoints: createEndpoints(client) }
}

test("source endpoints preserve conversation and retry keys", async () => {
  const { calls, endpoints } = fixture()
  await endpoints.uploadSource("conversation", "task.txt", "text/plain", "aGk=", "upload-key")
  await endpoints.extractSource("conversation", "source/id", "extract-key")
  assert.deepEqual(calls[0].options.body, { schema_version: "1.1", conversation_id: "conversation", filename: "task.txt", mime_type: "text/plain", content_base64: "aGk=" })
  assert.equal(calls[0].options.idempotencyKey, "upload-key")
  assert.equal(calls[1].path, "/v1/sources/source%2Fid/extract")
  assert.equal(calls[1].options.idempotencyKey, "extract-key")
})

test("old messages omit source IDs; source messages reference IDs without approval", async () => {
  const { calls, endpoints } = fixture()
  await endpoints.sendMessage("conversation", "hello", "message-key")
  await endpoints.sendMessage("conversation", "import this", "source-message-key", ["source"])
  assert.deepEqual(calls[0].options.body, { schema_version: "1.1", conversation_id: "conversation", text: "hello" })
  assert.deepEqual(calls[1].options.body, { schema_version: "1.1", conversation_id: "conversation", text: "import this", source_ids: ["source"] })
})
