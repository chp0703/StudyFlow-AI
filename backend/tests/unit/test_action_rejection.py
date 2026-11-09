"""Regression coverage for stale plan rejection after extracting the orchestrator."""

from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from backend.app.orchestrator.actions import ActionProcessor
from backend.app.orchestrator.workflow_shared import Terminal


class PlanRejectionTest(unittest.TestCase):
    def setUp(self):
        self.ctx = SimpleNamespace(request_id="request", user_id="user")
        self.reference = {"action_id": "action", "action_version": 1, "target_type": "PLAN_PROPOSAL",
                          "target_id": "proposal", "target_version": 1}
        self.calls = []
        self.reject_result = {"outcome": "REJECTED", "data": {"proposal_id": "proposal"}}
        self.processor = ActionProcessor(self.rpc, lambda: None, None, "Asia/Ho_Chi_Minh")
        self.processor.chat.resume = Mock(return_value=None)

    def rpc(self, ctx, operation, arguments, **kwargs):
        self.calls.append((operation, arguments, kwargs))
        if operation == "get_workflow_context":
            return {"outcome": "READ", "data": {"selected_action": {
                "pending_action": {"state": "AWAITING_APPROVAL", "version": 1, "requires_review": False},
                "last_presentation": {"presentation": {"normalized_command": {"operation": "approve_study_plan"}}},
            }}}
        if operation == "reject_study_plan":
            return self.reject_result
        if operation == "cancel_pending_action":
            return {"outcome": "CANCELLED", "data": {"action_id": "action", "state": "CANCELLED"}}
        self.fail(f"Unexpected operation: {operation}")

    def decide(self):
        return self.processor.decide(self.ctx, {"message_id": "message"}, "client-key", {
            "conversation_id": "conversation", "action_reference": self.reference, "decision": "REJECT"})

    def test_stale_proposal_rejection_releases_action_and_resumes_conversation(self):
        self.reject_result = {"outcome": "ERROR", "error": {"code": "STALE_PROPOSAL", "message": "Stale"}}
        status, answer = self.decide()
        self.assertEqual(200, status)
        self.assertEqual("SUCCEEDED", answer["state"])
        self.assertEqual("CANCELLED", answer["result"]["data"]["pending_action"]["state"])
        self.assertEqual(["get_workflow_context", "reject_study_plan", "cancel_pending_action"],
                         [operation for operation, _, _ in self.calls])
        _, arguments, kwargs = self.calls[-1]
        self.assertEqual({"action_reference": self.reference, "candidate_id": None}, arguments)
        self.assertEqual("conversation", kwargs["conversation_id"])
        self.assertEqual("message", kwargs["message_id"])
        self.assertNotEqual(self.calls[1][2]["idempotency_key"], kwargs["idempotency_key"])
        self.assertIs(True, self.processor.chat.resume.call_args.args[7])

    def test_valid_rejection_keeps_domain_result_without_cancelling_again(self):
        status, answer = self.decide()
        self.assertEqual(200, status)
        self.assertEqual("REJECTED", answer["result"]["outcome"])
        self.assertEqual(["get_workflow_context", "reject_study_plan"], [op for op, _, _ in self.calls])
        self.processor.chat.resume.assert_called_once()

    def test_other_domain_errors_do_not_cancel_the_action(self):
        self.reject_result = {"outcome": "ERROR", "error": {"code": "STALE_ENTITY_VERSION", "message": "Changed"}}
        with self.assertRaises(Terminal) as caught:
            self.decide()
        self.assertEqual("STALE_ENTITY_VERSION", caught.exception.error["code"])
        self.assertEqual(["get_workflow_context", "reject_study_plan"], [op for op, _, _ in self.calls])
        self.processor.chat.resume.assert_not_called()
