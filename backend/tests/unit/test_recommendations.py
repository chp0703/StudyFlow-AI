from __future__ import annotations

import unittest
from uuid import UUID, uuid5

from fastapi import FastAPI

from backend.app.api.v1.routes import Api
from backend.app.assessment.recommendations import RevisionRecommendationOperations
from backend.app.core import contract
from backend.app.orchestrator.actions import ActionProcessor


USER = "00000000-0000-4000-8000-000000000001"
CONVERSATION = "00000000-0000-4000-8000-000000000003"
MATERIAL = "00000000-0000-4000-8000-000000000201"
RECOMMENDATION = "00000000-0000-4000-8000-000000000251"
ACTION = "00000000-0000-4000-8000-000000000261"
STAMP = "2026-11-20T08:00:00Z"


class Ctx:
    user_id = USER
    request_id = "request-1"


def recommendation(status: str = "PROPOSED") -> dict:
    return {
        "assessment_version": "1.0.0", "recommendation_id": RECOMMENDATION, "user_id": USER,
        "conversation_id": CONVERSATION, "material_id": MATERIAL, "topic": "Xác suất",
        "priority": 1, "suggested_minutes": 60,
        "reason_summary": "Tỷ lệ sai là 2/3 câu trả lời hợp lệ.",
        "evidence": {
            "attempt_ids": ["00000000-0000-4000-8000-000000000231"],
            "chunk_ids": ["00000000-0000-4000-8000-000000000211"],
            "valid_response_count": 3, "error_count": 2, "error_rate": 2 / 3,
        },
        "confidence_limit": {"level": "LOW", "limitations": ["Dữ liệu hiện có gồm 3 câu trả lời hợp lệ."]},
        "pending_action_id": ACTION, "candidate_id": None, "status": status,
        "created_at": STAMP, "updated_at": STAMP,
    }


def pending() -> dict:
    return {
        "action_id": ACTION, "user_id": USER, "conversation_id": CONVERSATION, "version": 1,
        "intent": "REVIEW_REVISION_RECOMMENDATION", "state": "AWAITING_APPROVAL",
        "requires_review": False, "candidate_id": None, "proposal_id": None,
        "draft_arguments": {"recommendation_id": RECOMMENDATION}, "missing_fields": [],
        "ambiguities": [], "depends_on_action_id": None, "created_at": STAMP, "updated_at": STAMP,
    }


class RecommendationTests(unittest.TestCase):
    def test_recommendation_route_is_registered(self):
        api = object.__new__(Api)
        app = FastAPI()
        api.register(app)
        self.assertIn(
            ("/v1/assessment/recommendations", "POST"),
            {(route.path, method) for route in app.routes for method in getattr(route, "methods", set())},
        )

    def test_create_returns_evidence_and_exact_pending_action_reference(self):
        calls = []
        key = "recommendation-key-0001"
        expected_recommendation = str(uuid5(UUID(USER), "revision-recommendation:" + key))
        expected_action = str(uuid5(UUID(USER), "revision-recommendation-action:" + key))
        stored = recommendation()
        stored.update(recommendation_id=expected_recommendation, pending_action_id=expected_action)
        stored_pending = pending()
        stored_pending.update(action_id=expected_action, draft_arguments={"recommendation_id": expected_recommendation})
        presentation = {
            "kind": "ACTION_PRESENTATION", "pending_action": stored_pending, "candidate": None,
            "proposal": None, "normalized_command": None, "effective_policy": None,
            "schedule_confirmation": None,
        }

        def rpc(ctx, operation, arguments, **kwargs):
            calls.append((operation, arguments, kwargs))
            if operation == "create_revision_recommendation":
                return {"schema_version": "1.1", "request_id": "db", "outcome": "PROPOSED",
                        "data": stored, "error": None, "warnings": []}
            return {"outcome": "READ", "data": {
                "selected_action": {"last_presentation": {"presentation": presentation}}
            }}

        status, body = RevisionRecommendationOperations(rpc).create(
            Ctx(), {"message_id": "00000000-0000-4000-8000-000000000099"}, key,
            {"conversation_id": CONVERSATION, "material_id": MATERIAL, "topic": "Xác suất",
             "suggested_minutes": 60, "priority": 1},
        )
        self.assertEqual(status, 200)
        self.assertTrue(contract.is_valid("OrchestratorReply", body))
        self.assertEqual(body["state"], "AWAITING_APPROVAL")
        self.assertEqual(body["action_reference"]["target_type"], "PENDING_ACTION")
        self.assertEqual(body["result"]["data"]["recommendation"]["evidence"]["error_count"], 2)
        self.assertEqual([call[0] for call in calls], ["create_revision_recommendation", "get_workflow_context"])

    def test_decision_preserves_reference_and_uses_dedicated_rpc(self):
        calls = []

        def rpc(ctx, operation, arguments, **kwargs):
            calls.append((operation, arguments, kwargs))
            return {"schema_version": "1.1", "request_id": "db", "outcome": "COMMITTED",
                    "data": recommendation("ACCEPTED"), "error": None, "warnings": []}

        processor = object.__new__(ActionProcessor)
        processor.rpc = rpc
        ref = {"action_id": ACTION, "action_version": 1, "target_type": "PENDING_ACTION",
               "target_id": ACTION, "target_version": 1}
        status, body = processor._decide_revision_recommendation(
            Ctx(), {"message_id": "00000000-0000-4000-8000-000000000099"}, "decision-key-00001",
            CONVERSATION, ref, pending(), "APPROVE",
        )
        self.assertEqual(status, 200)
        self.assertTrue(contract.is_valid("OrchestratorReply", body))
        operation, arguments, kwargs = calls[0]
        self.assertEqual(operation, "decide_revision_recommendation")
        self.assertEqual(arguments["recommendation_id"], RECOMMENDATION)
        self.assertEqual(kwargs["action_reference"], ref)
        self.assertEqual(kwargs["approval_action"]["decision"], "APPROVE")


if __name__ == "__main__":
    unittest.main()
