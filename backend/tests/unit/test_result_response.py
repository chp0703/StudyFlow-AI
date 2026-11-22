from __future__ import annotations

import asyncio
import json
import unittest
from types import SimpleNamespace

from backend.app.api.v1.http import LEARNING_STATUS, ApiError, result_response
from backend.app.learning.materials import LearningMaterialOperations

RID = "11111111-1111-4111-8111-111111111111"


def error(code: str) -> dict:
    return {"schema_version": "1.1", "request_id": RID, "outcome": "ERROR", "data": None,
            "error": {"code": code, "message": "x", "field": None, "details": {}, "retryable": False}, "warnings": []}


class ResultResponseTest(unittest.TestCase):
    def test_error_status_tables(self):
        cases = [
            ("INVALID_PARAMETER", {}, 422), ("NO_SUCH_CODE", {}, 500), ("SERVICE_UNAVAILABLE", {}, 503),
            ("INVALID_PARAMETER", {"statuses": LEARNING_STATUS}, 400),
            ("MISSING_REQUIRED_FIELD", {"statuses": LEARNING_STATUS}, 400),
        ]
        for code, kwargs, status in cases:
            with self.subTest(code=code, status=status):
                response = result_response(error(code), RID, **kwargs)
                self.assertEqual(response.status_code, status)
        self.assertEqual(result_response(error("SERVICE_UNAVAILABLE"), RID).headers["retry-after"], "1")

    def test_replay_header(self):
        ok = {"outcome": "READ", "data": {}}
        self.assertNotIn("idempotency-replayed", result_response(ok, RID).headers)
        self.assertEqual(result_response(ok, RID, write=True).headers["idempotency-replayed"], "true")
        committed = {"outcome": "COMMITTED", "data": {}}
        self.assertEqual(result_response(committed, RID, write=True).headers["idempotency-replayed"], "false")
        self.assertEqual(result_response(committed, RID, write=True, replayed=True).headers["idempotency-replayed"], "true")

    def test_request_id_in_body_and_header(self):
        response = result_response({"outcome": "READ", "data": {}, "request_id": "other"}, RID)
        self.assertEqual(json.loads(response.body)["request_id"], RID)
        self.assertEqual(response.headers["x-request-id"], RID)

    def test_schema_mismatch_raises(self):
        with self.assertRaises(ApiError) as caught:
            result_response({"outcome": "READ", "data": {}}, RID, schema="DailyMaterialListResult")
        self.assertEqual(caught.exception.code, "INTERNAL_ERROR")

    def test_learning_material_list_invalid_parameter_is_400(self):
        ops = LearningMaterialOperations(lambda *a, **k: error("INVALID_PARAMETER"))
        response = asyncio.run(ops.list(SimpleNamespace(request_id=RID), 10, None))
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
