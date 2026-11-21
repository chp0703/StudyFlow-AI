"""F3 M4 integration: summary -> /v1/decisions -> SessionOutcome against local Supabase."""

from __future__ import annotations

import base64
import json
import unittest
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from backend.app.core import contract
from backend.app.core.config import Settings
from backend.app.learning.summary import SUMMARY_SYSTEM_PROMPT
from backend.app.main import create_app
from backend.tests.integration import test_http_local_supabase as local
from backend.tests.integration.test_learning_interaction_local_supabase import topic_embed_query, topic_index


class LearningOutcomeLocalSupabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = local.LocalSupabaseHttp()
        cls.fixture.setUpClass()

    def setUp(self):
        self.summary_calls = 0

    def _llm(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        system, user = body["messages"][0]["content"], body["messages"][1]["content"]
        if system == SUMMARY_SYSTEM_PROMPT:
            self.summary_calls += 1
            output = {"summary": f"Bản tóm tắt {self.summary_calls}: đã hỏi về tổng hai số chẵn.",
                      "topics": ["Tính chẵn lẻ", "tính chẵn lẻ"]}
        else:
            marker = 'chunk_id="'
            start = user.index(marker) + len(marker)
            output = {"answer": "Tổng hai số chẵn là số chẵn.", "citation_ids": [user[start:start + 36]], "supported": True}
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(output, ensure_ascii=False)}}]})

    def client(self) -> TestClient:
        f = self.fixture
        settings = Settings(
            supabase_url=f.url, supabase_publishable_key=f.publishable, rpc_signing_key_id=f.key_id,
            rpc_signing_secret_base64=base64.b64encode(f.secret).decode(),
            deepseek_api_key="sk-local-test", deepseek_model="deepseek-chat",
        )
        return TestClient(create_app(settings, llm_transport=httpx.MockTransport(self._llm),
                                     learning_indexer=topic_index, learning_embedder=topic_embed_query))

    def decide(self, app, session, ref, decision, who="a", key=None):
        body = {"schema_version": "1.1", "conversation_id": session["conversation_id"], "action_reference": ref,
                "decision": decision}
        return self.fixture.post(app, "/v1/decisions", body, who=who, key=key)

    def test_summary_reject_resummarize_approve_and_replay(self):
        f = self.fixture
        text = f"Tổng hai số chẵn luôn là số chẵn vì 2a + 2b = 2(a + b). Mã {uuid4()}."
        with self.client() as app:
            material = f.post(app, "/v1/materials", {
                "schema_version": "1.1", "filename": "so_chan.txt", "mime_type": "text/plain", "course_label": "Toán",
                "content_base64": base64.b64encode(text.encode("utf-8")).decode()})
            self.assertEqual(material.status_code, 200, material.text)
            created = f.post(app, "/v1/learning/sessions", {"schema_version": "1.1", "goal": "Ôn tính chẵn lẻ",
                             "material_ids": [material.json()["data"]["material_id"]], "planner_block_id": None})
            self.assertEqual(created.status_code, 200, created.text)
            sid = created.json()["data"]["session_id"]

            empty = f.post(app, f"/v1/learning/sessions/{sid}/summary", {"schema_version": "1.1"})
            self.assertEqual(empty.status_code, 409, empty.text)
            self.assertEqual(self.summary_calls, 0)

            asked = f.post(app, f"/v1/learning/sessions/{sid}/turns",
                           {"schema_version": "1.1", "kind": "ASK", "text": "Tổng hai số chẵn là gì?"})
            self.assertEqual(asked.status_code, 200, asked.text)

            # Draft, then a turn is blocked while the summary waits for review.
            key = f"it-f3-sum-{uuid4().hex}"
            drafted = f.post(app, f"/v1/learning/sessions/{sid}/summary", {"schema_version": "1.1"}, key=key)
            self.assertEqual(drafted.status_code, 200, drafted.text)
            self.assertTrue(contract.is_valid("DailyLearningSummaryResult", drafted.json()))
            data = drafted.json()["data"]
            self.assertEqual(data["session"]["status"], "SUMMARY_PENDING")
            self.assertEqual(data["draft"]["topics"], ["Tính chẵn lẻ"])
            blocked = f.post(app, f"/v1/learning/sessions/{sid}/turns",
                             {"schema_version": "1.1", "kind": "ASK", "text": "Thêm câu hỏi"})
            self.assertEqual(blocked.status_code, 409, blocked.text)

            replay = f.post(app, f"/v1/learning/sessions/{sid}/summary", {"schema_version": "1.1"}, key=key)
            self.assertEqual(replay.headers["Idempotency-Replayed"], "true")
            self.assertEqual(replay.json()["data"]["action_reference"], data["action_reference"])
            self.assertEqual(self.summary_calls, 1)

            # Another user cannot decide; a modified reference is refused.
            foreign = self.decide(app, data["session"], data["action_reference"], "APPROVE", who="b")
            self.assertGreaterEqual(foreign.status_code, 400, foreign.text)
            tampered = dict(data["action_reference"], action_version=data["action_reference"]["action_version"] + 1,
                            target_version=data["action_reference"]["target_version"] + 1)
            self.assertEqual(self.decide(app, data["session"], tampered, "APPROVE").status_code, 409)

            rejected = self.decide(app, data["session"], data["action_reference"], "REJECT")
            self.assertEqual(rejected.status_code, 200, rejected.text)
            self.assertTrue(contract.is_valid("DailyLearningOutcomeDecisionResult", rejected.json()))
            self.assertEqual(rejected.json()["result"]["data"]["session"]["status"], "ACTIVE")
            self.assertIsNone(rejected.json()["result"]["data"]["session_outcome"])

            again = f.post(app, f"/v1/learning/sessions/{sid}/summary", {"schema_version": "1.1"})
            self.assertEqual(again.status_code, 200, again.text)
            second = again.json()["data"]
            self.assertNotEqual(second["action_reference"]["action_id"], data["action_reference"]["action_id"])

            decision_key = f"it-f3-dec-{uuid4().hex}"
            approved = self.decide(app, second["session"], second["action_reference"], "APPROVE", key=decision_key)
            self.assertEqual(approved.status_code, 200, approved.text)
            self.assertTrue(contract.is_valid("DailyLearningOutcomeDecisionResult", approved.json()))
            result = approved.json()["result"]["data"]
            self.assertEqual(result["session"]["status"], "CLOSED")
            self.assertEqual(result["session_outcome"]["summary"], second["draft"]["summary"])

        with self.client() as restarted:
            replayed = self.decide(restarted, second["session"], second["action_reference"], "APPROVE", key=decision_key)
            self.assertEqual(replayed.status_code, 200, replayed.text)
            self.assertEqual(replayed.json()["result"]["data"]["session_outcome"]["outcome_id"],
                             result["session_outcome"]["outcome_id"])
            reused = self.decide(restarted, second["session"], second["action_reference"], "APPROVE")
            self.assertEqual(reused.status_code, 409, reused.text)
            closed = restarted.get(f"/v1/learning/sessions/{sid}", headers=self.fixture.auth("a"))
            self.assertEqual(closed.json()["data"]["session"]["status"], "CLOSED")


if __name__ == "__main__":
    unittest.main()
