import test from "node:test"
import assert from "node:assert/strict"
import { intervalError } from "./workingTime.ts"

test("weekly working intervals allow separated periods and reject overlap", () => {
  const morning = [{ start_time: "08:00", end_time: "11:00" }]
  assert.equal(intervalError("14:00", "17:30", morning), "")
  assert.equal(intervalError("20:00", "24:00", morning), "")
  assert.match(intervalError("10:30", "12:00", morning), /trùng/)
  assert.match(intervalError("18:00", "17:00", []), /sau/)
})
