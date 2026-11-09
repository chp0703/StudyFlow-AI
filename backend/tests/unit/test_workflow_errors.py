import json
import unittest

from backend.app.api.v1.http import ApiError, error_response
from backend.app.orchestrator.workflow_ports import WorkflowError


class WorkflowErrorBoundaryTest(unittest.TestCase):
    def test_workflow_errors_keep_public_envelopes_and_retry_headers(self):
        for post in (False, True):
            for code, expected_status, retry_after in (
                ("INVALID_PARAMETER", 422, None),
                ("ACTION_REVIEW_REQUIRED", 409, None),
                ("SERVICE_UNAVAILABLE", 503, "1"),
            ):
                with self.subTest(post=post, code=code):
                    response = error_response(WorkflowError(code, "Chi tiết", field="intent"), "request", post=post)
                    body = json.loads(response.body)
                    self.assertEqual(expected_status, response.status_code)
                    self.assertEqual("request", response.headers["x-request-id"])
                    self.assertEqual(retry_after, response.headers.get("retry-after"))
                    self.assertEqual("false" if post else None, response.headers.get("idempotency-replayed"))
                    self.assertEqual({"code": code, "message": "Chi tiết", "field": "intent",
                                      "details": {}, "retryable": False}, body["error"])
                    self.assertEqual("ERROR", body["state" if post else "outcome"])

    def test_explicit_transport_status_and_retry_after_are_preserved(self):
        error = ApiError("INVALID_PARAMETER", "Chi tiết", status=400, retry_after=7)
        response = error_response(error, "request", post=False)
        self.assertEqual(400, response.status_code)
        self.assertEqual("7", response.headers["retry-after"])
