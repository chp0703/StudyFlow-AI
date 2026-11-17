"""Two-user F2 B5 HTTP -> signed RPC -> local PostgreSQL integration tests."""

from __future__ import annotations

import base64
import json
import os
import unittest
from uuid import uuid4

import httpx
import psycopg
from fastapi.testclient import TestClient

from backend.app.core import contract
from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.tests.integration import test_http_local_supabase as local


class AttemptsLocalSupabaseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        missing = [name for name in local.REQUIRED if not os.environ.get(name)]
        if missing:
            raise unittest.SkipTest(f"Local Supabase environment not configured ({', '.join(missing)})")
        cls.fixture = local.LocalSupabaseHttp()
        cls.fixture.setUpClass()

    def _app_with_llm(self, fake_llm) -> TestClient:
        f = self.fixture
        settings = Settings(
            supabase_url=f.url,
            supabase_publishable_key=f.publishable,
            rpc_signing_key_id=f.key_id,
            rpc_signing_secret_base64=base64.b64encode(f.secret).decode(),
            deepseek_api_key="local-test-key",
            cors_origins=["http://localhost:5173"],
        )
        return TestClient(create_app(settings, llm_transport=httpx.MockTransport(fake_llm)))

    def _put(self, client: TestClient, path: str, body: dict, who: str = "a", key: str | None = None):
        return client.put(
            path,
            json=body,
            headers=self.fixture.auth(who, **{"Idempotency-Key": key or f"it-{uuid4().hex}"}),
        )

    def test_end_to_end_attempt_grading_and_immutability(self):
        f = self.fixture
        conv_a = str(uuid4())
        chunk_holder: dict[str, str] = {}

        def fake_llm(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": json.dumps(
                                    {
                                        "questions": [
                                            {
                                                "topic": "Mạng máy tính",
                                                "question_type": "MCQ",
                                                "stem": "Giao thức nào hướng kết nối?",
                                                "options": [
                                                    {"option_id": "A", "text": "UDP"},
                                                    {"option_id": "B", "text": "TCP"},
                                                    {"option_id": "C", "text": "ICMP"},
                                                    {"option_id": "D", "text": "ARP"},
                                                ],
                                                "answer_key": "B",
                                                "explanation": "TCP hướng kết nối.",
                                                "source_chunk_ids": [chunk_holder["chunk_id"]],
                                            },
                                            {
                                                "topic": "Mạng máy tính",
                                                "question_type": "MCQ",
                                                "stem": "Giao thức nào không kết nối?",
                                                "options": [
                                                    {"option_id": "A", "text": "UDP"},
                                                    {"option_id": "B", "text": "TCP"},
                                                    {"option_id": "C", "text": "HTTP"},
                                                    {"option_id": "D", "text": "TLS"},
                                                ],
                                                "answer_key": "A",
                                                "explanation": "UDP không kết nối.",
                                                "source_chunk_ids": [chunk_holder["chunk_id"]],
                                            },
                                        ]
                                    }
                                )
                            },
                        }
                    ]
                },
            )

        with self._app_with_llm(fake_llm) as app:
            # 1. Upload material
            text = "TCP truyền dữ liệu tin cậy hướng kết nối. UDP truyền datagram không kết nối."
            up = f.post(
                app,
                "/v1/assessment/materials",
                {
                    "schema_version": "1.1",
                    "conversation_id": conv_a,
                    "filename": "mang.md",
                    "mime_type": "text/markdown",
                    "content_base64": base64.b64encode(text.encode("utf-8")).decode(),
                    "topics": ["Mạng máy tính"],
                },
                who="a",
            )
            self.assertEqual(up.status_code, 200, up.text)
            material_id = up.json()["data"]["material"]["material_id"]
            chunk_holder["chunk_id"] = up.json()["data"]["chunks"][0]["chunk_id"]

            # 2. Generate 2 question drafts
            dr = f.post(
                app,
                "/v1/assessment/drafts",
                {
                    "schema_version": "1.1",
                    "conversation_id": conv_a,
                    "material_id": material_id,
                    "topic": "Mạng máy tính",
                    "question_type": "MCQ",
                    "count": 2,
                },
                who="a",
            )
            self.assertEqual(dr.status_code, 200, dr.text)
            action_ref = dr.json()["action_reference"]
            q_ids = [q["question_id"] for q in dr.json()["result"]["data"]["question_drafts"]["items"]]

            # Creating attempt while questions are still DRAFT fails with 409
            early = f.post(
                app,
                "/v1/assessment/attempts",
                {
                    "schema_version": "1.1",
                    "material_id": material_id,
                    "question_ids": q_ids,
                    "origin": "MANUAL",
                    "session_outcome_id": None,
                },
                who="a",
            )
            self.assertEqual(early.status_code, 409, early.text)
            self.assertEqual(early.json()["error"]["code"], "STALE_ENTITY_VERSION")

            # 3. Approve drafts via /v1/decisions
            dec = f.post(
                app,
                "/v1/decisions",
                {
                    "schema_version": "1.1",
                    "conversation_id": conv_a,
                    "action_reference": action_ref,
                    "decision": "APPROVE",
                },
                who="a",
            )
            self.assertEqual(dec.status_code, 200, dec.text)

            # 4. Create MANUAL attempt, save 1 correct response, leave 1 omitted, submit
            att = f.post(
                app,
                "/v1/assessment/attempts",
                {
                    "schema_version": "1.1",
                    "material_id": material_id,
                    "question_ids": q_ids,
                    "origin": "MANUAL",
                    "session_outcome_id": None,
                },
                who="a",
            )
            self.assertEqual(att.status_code, 200, att.text)
            attempt_id = att.json()["data"]["attempt_id"]

            save = self._put(
                app,
                f"/v1/assessment/attempts/{attempt_id}/responses/{q_ids[0]}",
                {"schema_version": "1.1", "selected_option_id": "B"},
                who="a",
            )
            self.assertEqual(save.status_code, 200, save.text)

            # Cross-user save & submit fail with 404
            cross_save = self._put(
                app,
                f"/v1/assessment/attempts/{attempt_id}/responses/{q_ids[0]}",
                {"schema_version": "1.1", "selected_option_id": "A"},
                who="b",
            )
            self.assertEqual(cross_save.status_code, 404, cross_save.text)

            cross_sub = f.post(
                app,
                f"/v1/assessment/attempts/{attempt_id}/submit",
                {"schema_version": "1.1"},
                who="b",
            )
            self.assertEqual(cross_sub.status_code, 404, cross_sub.text)

            sub = f.post(
                app,
                f"/v1/assessment/attempts/{attempt_id}/submit",
                {"schema_version": "1.1"},
                who="a",
            )
            self.assertEqual(sub.status_code, 200, sub.text)
            sub_data = sub.json()["data"]
            self.assertTrue(contract.is_valid("QuizAttemptSubmissionData", sub_data))
            self.assertEqual(sub_data["attempt"]["status"], "SUBMITTED")
            self.assertEqual(sub_data["attempt"]["valid_response_count"], 1)
            self.assertEqual(sub_data["attempt"]["correct_count"], 1)
            self.assertEqual(sub_data["attempt"]["incorrect_count"], 0)
            self.assertEqual(sub_data["attempt"]["omitted_count"], 1)
            self.assertEqual(sub_data["attempt"]["score_percent"], 100)

            # Saving response after submit fails with 409
            late_save = self._put(
                app,
                f"/v1/assessment/attempts/{attempt_id}/responses/{q_ids[1]}",
                {"schema_version": "1.1", "selected_option_id": "A"},
                who="a",
            )
            self.assertEqual(late_save.status_code, 409, late_save.text)

        with psycopg.connect(os.environ["F1_DB_TEST_DSN"]) as db:
            row = db.execute(
                "select status, valid_response_count, correct_count, incorrect_count, omitted_count, score_percent "
                "from app_private.quiz_attempts where attempt_id = %s",
                (attempt_id,),
            ).fetchone()
            self.assertEqual(row[0], "SUBMITTED")
            self.assertEqual((row[1], row[2], row[3], row[4]), (1, 1, 0, 1))
            self.assertEqual(float(row[5]), 100.0)


if __name__ == "__main__":
    unittest.main()
