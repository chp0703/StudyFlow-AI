from types import SimpleNamespace
import unittest

from backend.app.api.v1.workflow import terminal_reply
from backend.app.orchestrator.receipts import ReceiptProcessor
from backend.app.orchestrator.workflow_ports import WorkflowError
from backend.app.orchestrator.workflow_shared import Terminal


class ReceiptRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.ctx = SimpleNamespace(request_id="current-request")
        self.calls = []
        self.receipt = {"state": "IN_PROGRESS", "request_fingerprint": "fingerprint", "lease_version": 3}

    def rpc(self, ctx, operation, arguments, **kwargs):
        self.calls.append((operation, arguments, kwargs))
        return {"outcome": "READ", "data": self.receipt}

    def run_processor(self, dispatch):
        processor = ReceiptProcessor(self.rpc, dispatch, terminal_reply)
        return processor.run(self.ctx, "send_message", "client-key", "fingerprint", {"conversation_id": "conversation"}, {})

    def test_completed_receipt_replays_without_dispatch_and_preserves_stored_response(self):
        stored = {"request_id": "old", "result": {"request_id": "old"}}
        self.receipt = {"state": "COMPLETED", "response": stored, "http_status": 200}

        def dispatch(*args):
            self.fail("A completed receipt must not execute its workflow again")

        result = self.run_processor(dispatch)
        self.assertTrue(result.replayed)
        self.assertEqual("current-request", result.body["request_id"])
        self.assertEqual("current-request", result.body["result"]["request_id"])
        self.assertEqual("old", stored["request_id"])
        self.assertEqual("old", stored["result"]["request_id"])
        self.assertEqual(["claim_api_receipt"], [op for op, _, _ in self.calls])

    def test_transient_failure_releases_lease_without_completing(self):
        failure = WorkflowError("SERVICE_UNAVAILABLE", "Thử lại", retryable=True)

        def dispatch(*args):
            raise failure

        with self.assertRaises(WorkflowError) as caught:
            self.run_processor(dispatch)
        self.assertIs(failure, caught.exception)
        self.assertEqual(["claim_api_receipt", "release_api_receipt"], [op for op, _, _ in self.calls])
        self.assertEqual(3, self.calls[-1][1]["expected_lease_version"])

    def test_terminal_error_completes_receipt_with_catalog_response(self):
        def dispatch(*args):
            raise Terminal("ACTION_REVIEW_REQUIRED", "Xem lại")

        result = self.run_processor(dispatch)
        self.assertEqual(409, result.http_status)
        self.assertEqual("ACTION_REVIEW_REQUIRED", result.body["error"]["code"])
        self.assertEqual(["claim_api_receipt", "complete_api_receipt"], [op for op, _, _ in self.calls])
        self.assertEqual(result.body, self.calls[-1][1]["response"])
        self.assertEqual(409, self.calls[-1][1]["http_status"])
