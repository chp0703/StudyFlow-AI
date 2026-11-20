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
from psycopg.types.json import Jsonb

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

    def _client(
        self,
        *,
        fake_llm=None,
        rpc_transport: httpx.BaseTransport | None = None,
    ) -> TestClient:
        f = self.fixture
        settings = Settings(
            supabase_url=f.url,
            supabase_publishable_key=f.publishable,
            rpc_signing_key_id=f.key_id,
            rpc_signing_secret_base64=base64.b64encode(f.secret).decode(),
            deepseek_api_key="local-test-key" if fake_llm is not None else "",
            cors_origins=["http://localhost:5173"],
        )
        return TestClient(
            create_app(
                settings,
                rpc_transport=rpc_transport,
                llm_transport=httpx.MockTransport(fake_llm) if fake_llm is not None else None,
            )
        )

    def _app_with_llm(self, fake_llm) -> TestClient:
        return self._client(fake_llm=fake_llm)

    def _create_material_with_verified_questions(
        self,
        app: TestClient,
        *,
        question_count: int,
        topic: str = "Mạng máy tính",
        answer_key: str = "B",
        who: str = "a",
    ) -> tuple[str, list[str]]:
        f = self.fixture
        conv_id = str(uuid4())
        text = "TCP truyền dữ liệu tin cậy hướng kết nối. UDP truyền datagram không kết nối."
        up = f.post(
            app,
            "/v1/assessment/materials",
            {
                "schema_version": "1.1",
                "conversation_id": conv_id,
                "filename": "b5.md",
                "mime_type": "text/markdown",
                "content_base64": base64.b64encode(text.encode("utf-8")).decode(),
                "topics": [topic],
            },
            who=who,
        )
        self.assertEqual(up.status_code, 200, up.text)
        up_data = up.json()["data"]
        material_id = up_data["material"]["material_id"]
        chunk_id = up_data["chunks"][0]["chunk_id"]
        user_id = f.users[who][1]
        options = [
            {"option_id": "A", "text": "UDP"},
            {"option_id": "B", "text": "TCP"},
            {"option_id": "C", "text": "ICMP"},
            {"option_id": "D", "text": "ARP"},
        ]

        q_ids: list[str] = []
        with psycopg.connect(os.environ["F1_DB_TEST_DSN"], autocommit=True) as db:
            for idx in range(question_count):
                qid = str(uuid4())
                q_ids.append(qid)
                db.execute(
                    "insert into app_private.question_drafts("
                    "question_id, user_id, conversation_id, material_id, topic, question_type, "
                    "stem, options, answer_key, source_chunk_ids, prompt_version"
                    ") values (%s, %s, %s, %s, %s, 'MCQ', %s, %s, %s, %s, 'b5-test')",
                    (
                        qid,
                        user_id,
                        conv_id,
                        material_id,
                        topic,
                        f"Câu hỏi trắc nghiệm {idx + 1}?",
                        Jsonb(options),
                        answer_key,
                        Jsonb([chunk_id]),
                    ),
                )
                db.execute(
                    "insert into app_private.question_draft_sources("
                    "question_id, chunk_id, user_id, material_id, source_order"
                    ") values (%s, %s, %s, %s, 0)",
                    (qid, chunk_id, user_id, material_id),
                )
                db.execute(
                    "update app_private.question_drafts "
                    "set status = 'VERIFIED', version = 2, verified_at = clock_timestamp() "
                    "where question_id = %s",
                    (qid,),
                )
        return material_id, q_ids

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

            # B6 reads persisted grades, including after the backend process restarts.
            with self._app_with_llm(fake_llm) as fresh_app:
                stats = fresh_app.get(
                    "/v1/assessment/topics/stats", params={"material_id": material_id}, headers=f.auth("a")
                )
                self.assertEqual(stats.status_code, 200, stats.text)
                self.assertTrue(contract.is_valid("TopicStatsResult", stats.json()))
                item = stats.json()["data"]["items"][0]
                self.assertEqual((item["valid_response_count"], item["error_count"], item["error_rate"]), (1, 0, 0))
                self.assertEqual(item["status"], "AVAILABLE")
                foreign = fresh_app.get(
                    "/v1/assessment/topics/stats", params={"material_id": material_id}, headers=f.auth("b")
                )
                self.assertEqual(foreign.status_code, 404, foreign.text)

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

    def test_submit_retries_after_concurrent_response_save_and_grades_latest_answer(self):
        f = self.fixture
        with self._client() as setup_app:
            material_id, q_ids = self._create_material_with_verified_questions(
                setup_app,
                question_count=2,
                answer_key="B",
            )
            att = f.post(
                setup_app,
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

            initial_save = self._put(
                setup_app,
                f"/v1/assessment/attempts/{attempt_id}/responses/{q_ids[0]}",
                {"schema_version": "1.1", "selected_option_id": "A"},
                who="a",
            )
            self.assertEqual(initial_save.status_code, 200, initial_save.text)

        hook_put_results: list[tuple[int, str]] = []
        submit_rpc_calls: list[dict] = []

        def forward_rpc(request: httpx.Request) -> httpx.Response:
            if request.url.path.endswith("/submit_quiz_attempt") and not hook_put_results:
                with self._client() as other_app:
                    changed = self._put(
                        other_app,
                        f"/v1/assessment/attempts/{attempt_id}/responses/{q_ids[0]}",
                        {"schema_version": "1.1", "selected_option_id": "B"},
                        who="a",
                        key=f"it-race-save-{uuid4().hex}",
                    )
                    hook_put_results.append((changed.status_code, changed.text))
            with httpx.Client(timeout=20.0) as upstream:
                response = upstream.send(request)
            if request.url.path.endswith("/submit_quiz_attempt"):
                payload = response.json()
                submit_rpc_calls.append(
                    {
                        "status_code": response.status_code,
                        "outcome": payload.get("outcome"),
                        "error_code": (payload.get("error") or {}).get("code"),
                    }
                )
            return response

        with self._client(rpc_transport=httpx.MockTransport(forward_rpc)) as wrapped_app:
            sub = f.post(
                wrapped_app,
                f"/v1/assessment/attempts/{attempt_id}/submit",
                {"schema_version": "1.1"},
                who="a",
            )

        self.assertEqual(len(hook_put_results), 1)
        self.assertEqual(hook_put_results[0][0], 200, hook_put_results[0][1])
        self.assertEqual(len(submit_rpc_calls), 2, submit_rpc_calls)
        self.assertEqual(submit_rpc_calls[0]["outcome"], "ERROR")
        self.assertEqual(submit_rpc_calls[0]["error_code"], "STALE_ENTITY_VERSION")
        self.assertEqual(submit_rpc_calls[1]["outcome"], "COMMITTED")

        self.assertEqual(sub.status_code, 200, sub.text)
        self.assertEqual(sub.headers["Idempotency-Replayed"], "false")
        sub_data = sub.json()["data"]
        self.assertTrue(contract.is_valid("QuizAttemptSubmissionData", sub_data))
        self.assertEqual(sub_data["attempt"]["status"], "SUBMITTED")
        self.assertEqual(sub_data["attempt"]["valid_response_count"], 1)
        self.assertEqual(sub_data["attempt"]["correct_count"], 1)
        self.assertEqual(sub_data["attempt"]["incorrect_count"], 0)
        self.assertEqual(sub_data["attempt"]["omitted_count"], 1)
        self.assertEqual(sub_data["attempt"]["score_percent"], 100)

        by_qid = {item["question_id"]: item for item in sub_data["responses"]}
        self.assertEqual(by_qid[q_ids[0]]["selected_option_id"], "B")
        self.assertEqual(by_qid[q_ids[0]]["validity"], "VALID")
        self.assertIs(by_qid[q_ids[0]]["is_correct"], True)
        self.assertEqual(by_qid[q_ids[1]]["validity"], "OMITTED")
        self.assertIsNone(by_qid[q_ids[1]]["is_correct"])

        with self._client() as verify_app:
            late_save = self._put(
                verify_app,
                f"/v1/assessment/attempts/{attempt_id}/responses/{q_ids[1]}",
                {"schema_version": "1.1", "selected_option_id": "B"},
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

    def test_submit_thirty_two_valid_answers_one_correct_rounds_half_up_and_replays(self):
        f = self.fixture
        submit_key = f"it-submit32-{uuid4().hex}"
        with self._client() as app:
            material_id, q_ids = self._create_material_with_verified_questions(
                app,
                question_count=32,
                answer_key="B",
            )
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

            for idx, qid in enumerate(q_ids):
                saved = self._put(
                    app,
                    f"/v1/assessment/attempts/{attempt_id}/responses/{qid}",
                    {"schema_version": "1.1", "selected_option_id": "B" if idx == 0 else "A"},
                    who="a",
                )
                self.assertEqual(saved.status_code, 200, saved.text)

            sub = f.post(
                app,
                f"/v1/assessment/attempts/{attempt_id}/submit",
                {"schema_version": "1.1"},
                who="a",
                key=submit_key,
            )
            self.assertEqual(sub.status_code, 200, sub.text)
            self.assertEqual(sub.headers["Idempotency-Replayed"], "false")
            sub_data = sub.json()["data"]
            self.assertTrue(contract.is_valid("QuizAttemptSubmissionData", sub_data))
            self.assertEqual(sub_data["attempt"]["status"], "SUBMITTED")
            self.assertEqual(sub_data["attempt"]["total_questions"], 32)
            self.assertEqual(sub_data["attempt"]["valid_response_count"], 32)
            self.assertEqual(sub_data["attempt"]["correct_count"], 1)
            self.assertEqual(sub_data["attempt"]["incorrect_count"], 31)
            self.assertEqual(sub_data["attempt"]["omitted_count"], 0)
            self.assertEqual(sub_data["attempt"]["score_percent"], 3.13)

        with self._client() as fresh_app:
            replay = f.post(
                fresh_app,
                f"/v1/assessment/attempts/{attempt_id}/submit",
                {"schema_version": "1.1"},
                who="a",
                key=submit_key,
            )
            self.assertEqual(replay.status_code, 200, replay.text)
            self.assertEqual(replay.headers["Idempotency-Replayed"], "true")
            replay_data = replay.json()["data"]
            self.assertEqual(replay_data, sub_data)
            self.assertEqual(replay_data["attempt"]["score_percent"], 3.13)

        with psycopg.connect(os.environ["F1_DB_TEST_DSN"]) as db:
            row = db.execute(
                "select status, total_questions, valid_response_count, correct_count, "
                "incorrect_count, omitted_count, score_percent "
                "from app_private.quiz_attempts where attempt_id = %s",
                (attempt_id,),
            ).fetchone()
            self.assertEqual(row[0], "SUBMITTED")
            self.assertEqual((row[1], row[2], row[3], row[4], row[5]), (32, 32, 1, 31, 0))
            self.assertEqual(float(row[6]), 3.13)


if __name__ == "__main__":
    unittest.main()
