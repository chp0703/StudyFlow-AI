import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { test } from "node:test"

const schema = JSON.parse(readFileSync(new URL("../schemas/f1.schema.json", import.meta.url)))
const { pattern, maxLength } = schema.$defs.DailyMaterialUploadRequest.properties.content_base64

test("the upload pattern accepts a full 5 MiB payload in JavaScript", () => {
  const encoded = Buffer.alloc(5 * 1024 * 1024).toString("base64")
  const base64 = new RegExp(pattern)
  assert.equal(encoded.length, maxLength)
  assert.equal(base64.test(encoded), true)
  assert.equal(base64.test(encoded + "\n"), false)
  assert.equal(base64.test("ab*="), false)
})
