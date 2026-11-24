import assert from "node:assert/strict"
import test from "node:test"

import { createEndpoints } from "./endpoints.ts"
import type { ApiClient, RequestOptions } from "./client.ts"

type Call = { method: string; path: string; options: RequestOptions }

function fixture() {
  const calls: Call[] = []
  const pages: Record<string, unknown> = {
    first: { materials: [{ material_id: "m-1" }], next_cursor: "c2" },
    c2: { materials: [{ material_id: "m-2" }], next_cursor: null },
  }
  const client: ApiClient = {
    async request<T>(method: string, path: string, options: RequestOptions = {}) {
      calls.push({ method, path, options })
      if (method === "GET") return { data: pages[String(options.query?.cursor ?? "first")] } as T
      return { data: { ok: true } } as T
    },
  }
  return { calls, endpoints: createEndpoints(client) }
}

test("learning material endpoints send the upload body, walk every page and delete by id", async () => {
  const { calls, endpoints } = fixture()

  await endpoints.uploadMaterial("so_hoc.pdf", "application/pdf", "aGk=", "idem-1")
  const all = await endpoints.listMaterials()
  await endpoints.deleteMaterial("m/1", "idem-2")

  assert.equal(calls[0].path, "/v1/materials")
  assert.deepEqual(calls[0].options.body, {
    schema_version: "1.1",
    filename: "so_hoc.pdf",
    mime_type: "application/pdf",
    content_base64: "aGk=",
  })
  assert.equal(calls[0].options.idempotencyKey, "idem-1")
  assert.deepEqual(
    all.map((m) => m.material_id),
    ["m-1", "m-2"],
  )
  assert.equal(calls[3].method, "DELETE")
  assert.equal(calls[3].path, "/v1/materials/m%2F1")
})
