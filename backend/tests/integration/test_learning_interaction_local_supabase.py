"""F3 M2 + M3 integration tests against local Supabase (FastAPI -> PostgREST -> pgvector + FTS + FORCE RLS)."""

from __future__ import annotations

import base64
import json
import math
import unittest
from uuid import uuid4

import httpx
from fastapi.testclient import TestClient

from backend.app.core import contract
from backend.app.core.config import Settings
from backend.app.learning.answer import UNSUPPORTED_ANSWER
from backend.app.learning.embedding import embed_query
from backend.app.learning.indexing import index_document
from backend.app.main import create_app
from backend.tests.integration import test_http_local_supabase as local
from backend.tests.unit.test_learning_indexing import FakeTokenizer


class TopicVectorModel:
    """Deterministic CPU embedder mapping topic keywords to orthogonal 384-d unit vectors."""

    def __init__(self):
        self.tokenizer = FakeTokenizer()

    def encode(self, sentences: list[str], normalize_embeddings: bool = True, **kwargs) -> list[list[float]]:
        out: list[list[float]] = []
        for sentence in sentences:
            text = sentence.lower()
            vec = [0.0] * 384
            if "chẵn" in text or "lẻ" in text:
                vec[0] = 1.0
            elif "nguyên tố" in text:
                vec[1] = 1.0
            else:
                vec[200] = 1.0
            norm = math.sqrt(sum(x * x for x in vec))
            out.append([x / norm for x in vec])
        return out


_TOPIC_MODEL = TopicVectorModel()


def topic_index(content: bytes, mime: str, **kwargs):
    return index_document(content, mime, model=_TOPIC_MODEL, **kwargs)


def topic_embed_query(query: str) -> list[float]:
    return embed_query(query, model=_TOPIC_MODEL)


class LearningInteractionLocalSupabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = local.LocalSupabaseHttp()
        cls.fixture.setUpClass()

    def setUp(self):
        self.llm_calls: list[dict] = []
        self.llm_replies: list[str] = []
        self.expected_mat_id: str | None = None
        self.forbidden_mat_id: str | None = None

    def _llm_handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.llm_calls.append(body)
        if not self.llm_replies:
            raise AssertionError("DeepSeek called unexpectedly")
        user_msg = body["messages"][1]["content"]
        if self.expected_mat_id is not None:
            self.assertIn(self.expected_mat_id, user_msg)
        if self.forbidden_mat_id is not None:
            self.assertNotIn(self.forbidden_mat_id, user_msg)
        marker = 'chunk_id="'
        start = user_msg.index(marker) + len(marker)
        cid = user_msg[start : start + 36]
        text_out = self.llm_replies.pop(0)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps({"answer": text_out, "citation_ids": [cid], "supported": True}, ensure_ascii=False)}}]},
        )

    def client(self, *, api_key: str = "sk-local-test") -> TestClient:
        f = self.fixture
        settings = Settings(
            supabase_url=f.url,
            supabase_publishable_key=f.publishable,
            rpc_signing_key_id=f.key_id,
            rpc_signing_secret_base64=base64.b64encode(f.secret).decode(),
            deepseek_api_key=api_key,
            deepseek_model="deepseek-chat",
        )
        return TestClient(
            create_app(
                settings,
                llm_transport=httpx.MockTransport(self._llm_handler),
                learning_indexer=topic_index,
                learning_embedder=topic_embed_query,
            )
        )

    @staticmethod
    def material_body(text: str, filename: str = "lesson.txt") -> dict:
        return {
            "schema_version": "1.1",
            "filename": filename,
            "mime_type": "text/plain",
            "course_label": "Toán",
            "content_base64": base64.b64encode(text.encode("utf-8")).decode(),
        }

    def test_upload_session_grounded_qa_unsupported_hints_isolation_and_delete(self):
        f = self.fixture
        doc1 = f"Tổng hai số chẵn luôn là số chẵn vì 2a + 2b = 2(a + b). Mã tài liệu {uuid4()}."
        doc2 = f"Tổng hai số chẵn ở tài liệu thứ hai không được chọn trong phiên. Mã {uuid4()}."

        with self.client() as app:
            m1 = f.post(app, "/v1/materials", self.material_body(doc1, "so_chan.txt"))
            self.assertEqual(m1.status_code, 200, m1.text)
            mat1_id = m1.json()["data"]["material_id"]
            self.assertEqual(m1.json()["data"]["status"], "READY")

            m2 = f.post(app, "/v1/materials", self.material_body(doc2, "khac.txt"))
            self.assertEqual(m2.status_code, 200, m2.text)
            mat2_id = m2.json()["data"]["material_id"]

            # User B cannot start session with User A's material
            foreign_sess = f.post(
                app,
                "/v1/learning/sessions",
                {"schema_version": "1.1", "goal": "Đọc trộm", "material_ids": [mat1_id], "planner_block_id": None},
                who="b",
            )
            self.assertEqual(foreign_sess.status_code, 404, foreign_sess.text)

            # User A creates session selecting ONLY mat1_id
            sess_key = f"it-f3-sess-{uuid4().hex}"
            sess_body = {"schema_version": "1.1", "goal": "Ôn tính chẵn lẻ", "material_ids": [mat1_id], "planner_block_id": None}
            created = f.post(app, "/v1/learning/sessions", sess_body, key=sess_key)
            self.assertEqual(created.status_code, 200, created.text)
            self.assertTrue(contract.is_valid("DailyLearningSessionCreateResult", created.json()))
            sid = created.json()["data"]["session_id"]

            # Empty session HINT without text -> 400
            no_q_hint = f.post(app, f"/v1/learning/sessions/{sid}/turns", {"schema_version": "1.1", "kind": "HINT"})
            self.assertEqual(no_q_hint.status_code, 400, no_q_hint.text)

            self.expected_mat_id = mat1_id
            self.forbidden_mat_id = mat2_id

        with self.client() as app:
            # Replay session creation through restart
            replayed_sess = f.post(app, "/v1/learning/sessions", sess_body, key=sess_key)
            self.assertEqual(replayed_sess.status_code, 200)
            self.assertEqual(replayed_sess.headers["Idempotency-Replayed"], "true")
            self.assertEqual(replayed_sess.json()["data"]["session_id"], sid)

            # Grounded ASK
            self.llm_replies.append("Tổng hai số chẵn luôn là số chẵn.")
            ask_key = f"it-f3-ask-{uuid4().hex}"
            ask_body = {"schema_version": "1.1", "kind": "ASK", "text": "Tổng hai số chẵn là gì?"}
            asked = f.post(app, f"/v1/learning/sessions/{sid}/turns", ask_body, key=ask_key)
            self.assertEqual(asked.status_code, 200, asked.text)
            self.assertTrue(contract.is_valid("DailyLearningTurnResult", asked.json()))
            a_turn = asked.json()["data"]["assistant_turn"]
            self.assertTrue(a_turn["supported"])
            self.assertEqual(a_turn["citations"][0]["material_id"], mat1_id)
            self.assertEqual(a_turn["citations"][0]["page"], 1)
            self.assertFalse(a_turn["citations"][0]["material_deleted"])
            self.assertEqual(len(self.llm_calls), 1)

            # Out-of-material ASK -> below tau -> supported=false WITHOUT calling model
            ood = f.post(
                app,
                f"/v1/learning/sessions/{sid}/turns",
                {"schema_version": "1.1", "kind": "ASK", "text": "Thủ đô của Pháp là gì?"},
            )
            self.assertEqual(ood.status_code, 200, ood.text)
            self.assertFalse(ood.json()["data"]["assistant_turn"]["supported"])
            self.assertEqual(ood.json()["data"]["assistant_turn"]["citations"], [])
            self.assertEqual(ood.json()["data"]["assistant_turn"]["content"], UNSUPPORTED_ANSWER)
            self.assertEqual(len(self.llm_calls), 1)

            # Progressive hints 1 -> 2 -> 3 for explicit grounded question
            self.llm_replies.extend([
                "Hãy biểu diễn mỗi số chẵn dưới dạng bội của 2.",
                "Xem lại biểu thức ở trang 1 để nhóm nhân tử chung.",
                "Bước 1: đặt 2a và 2b; Bước 2: cộng thành 2(a + b) chia hết cho 2.",
            ])
            h1 = f.post(app, f"/v1/learning/sessions/{sid}/turns", {"schema_version": "1.1", "kind": "HINT", "text": "Tổng hai số chẵn là gì?"})
            self.assertEqual(h1.status_code, 200, h1.text)
            self.assertEqual(h1.json()["data"]["assistant_turn"]["hint_level"], 1)
            h2 = f.post(app, f"/v1/learning/sessions/{sid}/turns", {"schema_version": "1.1", "kind": "HINT"})
            self.assertEqual(h2.status_code, 200, h2.text)
            self.assertEqual(h2.json()["data"]["assistant_turn"]["hint_level"], 2)
            h3 = f.post(app, f"/v1/learning/sessions/{sid}/turns", {"schema_version": "1.1", "kind": "HINT"})
            self.assertEqual(h3.status_code, 200, h3.text)
            self.assertEqual(h3.json()["data"]["assistant_turn"]["hint_level"], 3)

            # User B cannot read or write turns on User A's session
            self.assertEqual(app.get(f"/v1/learning/sessions/{sid}", headers=f.auth("b")).status_code, 404)
            self.assertEqual(f.post(app, f"/v1/learning/sessions/{sid}/turns", ask_body, who="b").status_code, 404)

            # Delete mat1_id -> GET session keeps citations with material_deleted=true
            deleted = app.delete(f"/v1/materials/{mat1_id}", headers=f.auth("a", **{"Idempotency-Key": f"it-f3-del-{uuid4().hex}"}))
            self.assertEqual(deleted.status_code, 200, deleted.text)
            history = app.get(f"/v1/learning/sessions/{sid}", headers=f.auth("a"))
            self.assertEqual(history.status_code, 200, history.text)
            self.assertTrue(contract.is_valid("DailyLearningSessionReadResult", history.json()))
            self.assertTrue(history.json()["data"]["turns"][1]["citations"][0]["material_deleted"])

        # Replay ASK turn through fresh app restart -> no extra LLM call
        calls_before = len(self.llm_calls)
        with self.client() as restarted:
            replayed_turn = f.post(restarted, f"/v1/learning/sessions/{sid}/turns", ask_body, key=ask_key)
            self.assertEqual(replayed_turn.status_code, 200, replayed_turn.text)
            self.assertEqual(replayed_turn.headers["Idempotency-Replayed"], "true")
            self.assertEqual(len(self.llm_calls), calls_before)
            conflict = f.post(restarted, f"/v1/learning/sessions/{sid}/turns", {"schema_version": "1.1", "kind": "ASK", "text": "Khác"}, key=ask_key)
            self.assertEqual(conflict.status_code, 409)


if __name__ == "__main__":
    unittest.main()
