"""Two-user F2 B3+B4 HTTP -> signed RPC -> local PostgreSQL integration tests."""

from __future__ import annotations

import base64
import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import psycopg
from fastapi.testclient import TestClient

from backend.app.core import contract
from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.tests.integration import test_http_local_supabase as local


class _FailFirstCompleteTransport(httpx.BaseTransport):
    """Forwards real PostgREST calls except fails the first complete_api_receipt HTTP response."""

    def __init__(self, inner: httpx.BaseTransport):
        self._inner = inner
        self._lock = threading.Lock()
        self.failed_once = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/rpc/complete_api_receipt"):
            with self._lock:
                if not self.failed_once:
                    self.failed_once = True
                    return httpx.Response(503, json={"message": "simulated lost complete"})
        return self._inner.handle_request(request)

    def close(self) -> None:
        self._inner.close()


class QuestionsLocalSupabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = local.LocalSupabaseHttp()
        cls.fixture.setUpClass()

    def _app_with_llm(self, fake_llm, *, rpc_transport: httpx.BaseTransport | None = None) -> TestClient:
        f = self.fixture
        settings = Settings(
            supabase_url=f.url,
            supabase_publishable_key=f.publishable,
            rpc_signing_key_id=f.key_id,
            rpc_signing_secret_base64=base64.b64encode(f.secret).decode(),
            deepseek_api_key="local-test-key",
            cors_origins=["http://localhost:5173"],
        )
        return TestClient(create_app(settings, rpc_transport=rpc_transport, llm_transport=httpx.MockTransport(fake_llm)))

    def _upload_material(self, app: TestClient, conv_id: str, who: str = "a") -> tuple[str, str]:
        text = "Kỳ vọng E(X) là tổng giá trị nhân xác suất."
        res = self.fixture.post(
            app,
            "/v1/assessment/materials",
            {
                "schema_version": "1.1",
                "conversation_id": conv_id,
                "filename": "xac_suat.md",
                "mime_type": "text/markdown",
                "topics": ["Xác suất"],
                "content_base64": base64.b64encode(text.encode()).decode(),
            },
            who=who,
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()["data"]
        return data["material"]["material_id"], data["chunks"][0]["chunk_id"]

    @staticmethod
    def _fake_llm_factory(chunk_holder: dict[str, str], calls: list[dict]):
        def fake_llm(request: httpx.Request) -> httpx.Response:
            calls.append(json.loads(request.content.decode()))
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
                                                "topic": "Xác suất",
                                                "question_type": "MCQ",
                                                "stem": "Kỳ vọng E(X) là gì?",
                                                "options": [
                                                    {"option_id": "A", "text": "Tổng có trọng số"},
                                                    {"option_id": "B", "text": "Hiệu cực trị"},
                                                ],
                                                "answer_key": "A",
                                                "explanation": "Trang 1.",
                                                "source_chunk_ids": [chunk_holder["chunk_id"]],
                                            }
                                        ]
                                    }
                                )
                            },
                        }
                    ]
                },
            )

        return fake_llm

    def test_two_user_question_generate_review_concurrent_decide_and_lost_http_recovery(self):
        f = self.fixture
        conv_a = str(uuid4())
        chunk_holder: dict[str, str] = {}
        llm_calls: list[dict] = []
        intercept_transport = _FailFirstCompleteTransport(httpx.HTTPTransport())

        with self._app_with_llm(self._fake_llm_factory(chunk_holder, llm_calls), rpc_transport=intercept_transport) as app:
            mat_a, chunk_a = self._upload_material(app, conv_a, "a")
            chunk_holder["chunk_id"] = chunk_a
            draft_body = {
                "schema_version": "1.1",
                "conversation_id": conv_a,
                "material_id": mat_a,
                "topic": "Xác suất",
                "question_type": "MCQ",
                "count": 1,
            }
            foreign = f.post(app, "/v1/assessment/drafts", draft_body, who="b")
            self.assertEqual(foreign.status_code, 404, foreign.text)

            # 1) Simulate post-commit lost HTTP (create_question_drafts commits, complete_api_receipt returns 503).
            drafts_key = f"b3-lost-{uuid4().hex}"
            first_try = f.post(app, "/v1/assessment/drafts", draft_body, who="a", key=drafts_key)
            self.assertEqual(first_try.status_code, 503, first_try.text)
            self.assertEqual(len(llm_calls), 1)

            # Expire local test receipt lease via local DSN so client retry can reclaim immediately without waiting 120s.
            with psycopg.connect(os.environ["F1_DB_TEST_DSN"]) as db:
                db.execute(
                    """update app_private.api_request_receipts
                       set lease_until = clock_timestamp() - interval '1 minute'
                       where http_operation = 'generate_question_drafts' and idempotency_key = %s""",
                    (drafts_key,),
                )
                db.commit()

            recovered = f.post(app, "/v1/assessment/drafts", draft_body, who="a", key=drafts_key)
            self.assertEqual(recovered.status_code, 200, recovered.text)
            self.assertEqual(len(llm_calls), 1, "Retry after lost HTTP must recover via lookup before calling DeepSeek")
            self.assertTrue(contract.is_valid("OrchestratorReply", recovered.json()))
            self.assertTrue(recovered.json()["result"]["data"]["question_drafts"]["source_chunks"])
            ref = recovered.json()["action_reference"]

            # 2) Review shows persisted batch + source_chunks
            rev = f.post(
                app,
                f"/v1/actions/{ref['action_id']}/review",
                {"schema_version": "1.1", "conversation_id": conv_a, "expected_action_version": ref["action_version"]},
                who="a",
            )
            self.assertEqual(rev.status_code, 200, rev.text)
            self.assertIn("Kỳ vọng E(X) là gì?", rev.text)
            self.assertIn("tổng giá trị nhân xác suất", rev.text)

            # 3) Real concurrent APPROVE vs REJECT against local Postgres
            def submit_decision(decision: str, key: str):
                return f.post(
                    app,
                    "/v1/decisions",
                    {"schema_version": "1.1", "conversation_id": conv_a, "action_reference": ref, "decision": decision},
                    who="a",
                    key=key,
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_approve = pool.submit(submit_decision, "APPROVE", f"b4-conc-approve-{uuid4().hex}")
                fut_reject = pool.submit(submit_decision, "REJECT", f"b4-conc-reject-{uuid4().hex}")
                res_approve, res_reject = fut_approve.result(), fut_reject.result()

            self.assertEqual(sorted([res_approve.status_code, res_reject.status_code]), [200, 409])
            winner_res = res_approve if res_approve.status_code == 200 else res_reject
            expected_status = "VERIFIED" if res_approve.status_code == 200 else "REJECTED"

            # 4) Owner sees matching final state; User B sees empty list
            list_a = app.get("/v1/assessment/questions", headers=f.auth("a"), params={"status": expected_status})
            self.assertEqual(list_a.status_code, 200, list_a.text)
            self.assertTrue(contract.is_valid("QuestionDraftListResult", list_a.json()))
            self.assertTrue(any(q["material_id"] == mat_a for q in list_a.json()["data"]["items"]))
            self.assertEqual(winner_res.json()["result"]["data"]["items"][0]["status"], expected_status)

            list_b = app.get("/v1/assessment/questions", headers=f.auth("b"), params={"material_id": mat_a})
            self.assertEqual(list_b.status_code, 200, list_b.text)
            self.assertEqual(list_b.json()["data"]["items"], [])

        with psycopg.connect(os.environ["F1_DB_TEST_DSN"]) as db:
            q_statuses = [
                row[0]
                for row in db.execute(
                    "select status from app_private.question_drafts where material_id = %s",
                    (mat_a,),
                ).fetchall()
            ]
            self.assertEqual(q_statuses, [expected_status])
            decision_count = db.execute(
                "select count(*) from app_private.approval_actions where target_id = %s",
                (ref["action_id"],),
            ).fetchone()[0]
            self.assertEqual(decision_count, 1)


if __name__ == "__main__":
    unittest.main()
