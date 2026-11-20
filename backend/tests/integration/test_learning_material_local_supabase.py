"""M1 FastAPI -> PostgREST -> shared Postgres library, using a deterministic embedder."""

import base64
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.ingestion.document import IndexTimeoutError
from backend.app.learning.indexing import index_document
from backend.app.main import create_app
from backend.tests.integration import test_http_local_supabase as local
from backend.tests.unit.test_learning_indexing import FakeEmbeddingModel


def fake_index(content, mime, **kwargs):
    return index_document(content, mime, model=FakeEmbeddingModel(), **kwargs)


class LearningMaterialLocalSupabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = local.LocalSupabaseHttp()
        cls.fixture.setUpClass()

    def client(self, indexer=fake_index):
        f = self.fixture
        settings = Settings(supabase_url=f.url, supabase_publishable_key=f.publishable, rpc_signing_key_id=f.key_id,
                            rpc_signing_secret_base64=base64.b64encode(f.secret).decode())
        return TestClient(create_app(settings, learning_indexer=indexer))

    @staticmethod
    def body(content=None, filename="lesson.txt", mime="text/plain"):
        if content is None:
            content = (f"Ôn tập tài liệu {uuid4()}. " * 25).encode("utf-8")
        return {"schema_version": "1.1", "filename": filename, "mime_type": mime, "course_label": "Tin",
                "content_base64": base64.b64encode(content).decode()}

    def test_upload_poll_list_delete_and_replay_through_restart(self):
        f, body, key = self.fixture, self.body(), uuid4().hex
        with self.client() as app:
            first = f.post(app, "/v1/materials", body, key=key)
            self.assertEqual(first.status_code, 200, first.text)
            material = first.json()["data"]
            self.assertEqual(material["status"], "READY")
            self.assertEqual(material["page_count"], 1)
        material_id = material["material_id"]
        path = f"/v1/materials/{material_id}"
        delete_headers = f.auth("a", **{"Idempotency-Key": uuid4().hex})
        with self.client() as app:
            again = f.post(app, "/v1/materials", body, key=key)
            self.assertEqual(again.json()["data"], material)
            self.assertEqual(again.headers["Idempotency-Replayed"], "true")
            mismatch = f.post(app, "/v1/materials", {**body, "course_label": "Khác"}, key=key)
            self.assertEqual(mismatch.status_code, 409)
            dedup = f.post(app, "/v1/materials", body)
            self.assertEqual(dedup.json()["data"]["material_id"], material_id)
            self.assertEqual(app.get(path, headers=f.auth("a")).json()["data"], material)
            self.assertEqual(app.get(path, headers=f.auth("b")).status_code, 404)
            self.assertEqual(app.get("/v1/materials", headers=f.auth("b")).json()["data"]["materials"], [])
            second = f.post(app, "/v1/materials", self.body())
            self.assertEqual(second.status_code, 200, second.text)
            page = app.get("/v1/materials", headers=f.auth("a"), params={"limit": 1})
            self.assertEqual(page.status_code, 200, page.text)
            cursor = page.json()["data"]["next_cursor"]
            self.assertIsNotNone(cursor)
            next_page = app.get("/v1/materials", headers=f.auth("a"), params={"limit": 1, "cursor": cursor})
            self.assertEqual(next_page.json()["data"]["materials"][0]["material_id"], material_id)
            self.assertEqual(app.delete(path, headers=f.auth("b", **{"Idempotency-Key": uuid4().hex})).status_code, 404)
            with psycopg.connect(os.environ["F1_DB_TEST_DSN"]) as db:
                conv = db.execute("select conversation_id from app_private.materials where material_id=%s", (material_id,)).fetchone()[0]
            assessment = app.get(f"/v1/assessment/materials/{material_id}", headers=f.auth("a"),
                                 params={"conversation_id": str(conv)})
            self.assertEqual(assessment.status_code, 200, assessment.text)
            self.assertEqual(len(assessment.json()["data"]["chunks"]), 1)
            deleted = app.delete(path, headers=delete_headers)
            self.assertEqual(deleted.status_code, 200, deleted.text)
        with self.client() as app:
            replay = app.delete(path, headers=delete_headers)
            self.assertEqual(replay.status_code, 200, replay.text)
            self.assertEqual(replay.headers["Idempotency-Replayed"], "true")
            self.assertEqual(app.get(path, headers=f.auth("a")).status_code, 404)
        with psycopg.connect(os.environ["F1_DB_TEST_DSN"]) as db:
            self.assertEqual(db.execute("select count(*) from app_private.material_chunks where material_id=%s",
                                        (material_id,)).fetchone()[0], 0)

    def test_reupload_legacy_material_preserves_assessment_and_blocks_delete_with_evidence(self):
        f, body, conv = self.fixture, self.body(), str(uuid4())
        legacy = {k: v for k, v in body.items() if k != "course_label"}
        legacy.update(conversation_id=conv, topics=["Tin"])
        with self.client() as app:
            before = f.post(app, "/v1/assessment/materials", legacy)
            self.assertEqual(before.status_code, 200, before.text)
            data = before.json()["data"]
            material_id = data["material"]["material_id"]
            chunk_id = data["chunks"][0]["chunk_id"]
            with psycopg.connect(os.environ["F1_DB_TEST_DSN"]) as db:
                question = db.execute("""insert into app_private.question_drafts(user_id, conversation_id, material_id,
                    question_id, topic, question_type, stem, options, answer_key, source_chunk_ids, status, prompt_version)
                    values (%s,%s,%s,%s,'Tin','TRUE_FALSE','Đúng hay sai?',
                    '[{"option_id":"TRUE","text":"Đúng"},{"option_id":"FALSE","text":"Sai"}]',
                    'TRUE',jsonb_build_array(%s::uuid),'DRAFT','test') returning question_id""",
                    (f.users["a"][1], conv, material_id, uuid4(), chunk_id)).fetchone()[0]
                db.execute("""insert into app_private.question_draft_sources(user_id,material_id,question_id,chunk_id,source_order)
                    values (%s,%s,%s,%s,0)""", (f.users["a"][1], material_id, question, chunk_id))
            uploaded = f.post(app, "/v1/materials", body)
            self.assertEqual(uploaded.status_code, 200, uploaded.text)
            self.assertEqual(uploaded.json()["data"]["material_id"], material_id)
            self.assertEqual(uploaded.json()["data"]["status"], "READY")
            blocked = app.delete(f"/v1/materials/{material_id}", headers=f.auth("a", **{"Idempotency-Key": uuid4().hex}))
            self.assertEqual(blocked.status_code, 409, blocked.text)
            self.assertEqual(blocked.json()["error"]["details"]["reason"], "MATERIAL_IN_USE")
            after = app.get(f"/v1/assessment/materials/{material_id}", headers=f.auth("a"), params={"conversation_id": conv})
            self.assertEqual(after.json()["data"], data)

    def test_bad_inputs_and_retry_after_worker_timeout(self):
        f = self.fixture
        body = self.body()
        def timed_out(*args, **kwargs):
            raise IndexTimeoutError()
        key = uuid4().hex
        with self.client(timed_out) as app:
            self.assertEqual(app.post("/v1/materials", json=body).status_code, 401)
            self.assertEqual(f.post(app, "/v1/materials", {**body, "content_base64": "!!!!"}).status_code, 400)
            self.assertEqual(f.post(app, "/v1/materials", self.body(b"bad", "lesson.pdf", "application/pdf")).status_code, 400)
            self.assertEqual(f.post(app, "/v1/materials", {**body, "mime_type": "image/png"}).status_code, 415)
            failed = f.post(app, "/v1/materials", body, key=key)
            self.assertEqual(failed.status_code, 200, failed.text)
            first = failed.json()["data"]
            self.assertEqual((first["status"], first["error_code"]), ("FAILED", "INDEX_TIMEOUT"))
        with self.client() as app:
            replay = f.post(app, "/v1/materials", body, key=key)
            self.assertEqual(replay.json()["data"], first)
            succeeded = f.post(app, "/v1/materials", body)
            self.assertEqual(succeeded.status_code, 200, succeeded.text)
            self.assertEqual((succeeded.json()["data"]["material_id"], succeeded.json()["data"]["status"]),
                             (first["material_id"], "READY"))
            full = b"A" * (5 * 1024 * 1024)
            self.assertEqual(f.post(app, "/v1/materials", self.body(full + b"A")).status_code, 413)

    def test_concurrent_uploads_share_one_claim(self):
        f = self.fixture
        entered, release = threading.Event(), threading.Event()
        write_count = []
        body, key = self.body(), uuid4().hex

        def blocked_index(content, mime, **kwargs):
            write_count.append(mime)
            entered.set()
            if not release.wait(timeout=15):
                raise AssertionError("test did not release index")
            return fake_index(content, mime, **kwargs)

        with self.client(blocked_index) as app, ThreadPoolExecutor(max_workers=1) as workers:
            pending = workers.submit(f.post, app, "/v1/materials", body, key=key)
            try:
                self.assertTrue(entered.wait(timeout=10), pending.result(timeout=1).text if pending.done() else "")
                inflight = f.post(app, "/v1/materials", body, key=key)
                self.assertEqual(inflight.status_code, 409, inflight.text)
                dedup = f.post(app, "/v1/materials", body)
                self.assertEqual(dedup.status_code, 200, dedup.text)
                snapshot = dedup.json()["data"]
                self.assertEqual(snapshot["status"], "INDEXING")
            finally:
                release.set()
            completed = pending.result(timeout=20)
            self.assertEqual(completed.status_code, 200, completed.text)
            self.assertEqual(completed.json()["data"]["material_id"], snapshot["material_id"])
            self.assertEqual(write_count, ["text/plain"])
