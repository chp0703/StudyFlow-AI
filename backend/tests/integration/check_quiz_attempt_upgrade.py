"""Verify local F2 quiz attempts and recommendations across migration 202611200004 -> head."""

from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
import time
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
import psycopg

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.clients.rpc import RpcClient, child_key  # noqa: E402
from backend.app.core import contract  # noqa: E402
from backend.app.core.config import Settings  # noqa: E402
from backend.tests.integration import test_http_local_supabase as local  # noqa: E402
from backend.tests.integration.test_recommendations_local_supabase import RevisionLocalTests  # noqa: E402
from supabase.tests_concurrency.harness import local_dsn  # noqa: E402


def _validate_local_env() -> str:
    """Enforce loopback-only Supabase URL and PostgreSQL DSN before any I/O."""
    missing = [name for name in local.REQUIRED if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required local Supabase environment variables: {', '.join(missing)}")
    parsed = urlparse(os.environ["F1_LOCAL_SUPABASE_URL"].rstrip("/"))
    if parsed.scheme not in ("http", "https") or parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError("Refusing to run against a non-loopback or invalid F1_LOCAL_SUPABASE_URL")
    return local_dsn()


def _is_pgrst202(resp: httpx.Response) -> bool:
    try:
        return resp.status_code == 404 and resp.json().get("code") == "PGRST202"
    except (ValueError, AttributeError):
        return False


@contextmanager
def _rpc_client(settings: Settings, transport: httpx.BaseTransport | None = None):
    client = RpcClient(settings, transport, lambda: datetime.now(timezone.utc))
    try:
        yield client
    finally:
        client._http.close()


def _wait_for_context(settings: Settings, *, token: str, user_id: str, attempt_id: str) -> dict:
    """Read quiz attempt context via RpcClient, retrying only PostgREST PGRST202."""

    def forward(request: httpx.Request) -> httpx.Response:
        request.read()
        with httpx.Client(timeout=settings.rpc_timeout_seconds) as upstream:
            for attempt in range(24):
                resp = upstream.send(request)
                if not (request.url.path.endswith("/rpc/get_quiz_attempt_context") and _is_pgrst202(resp) and attempt < 23):
                    return resp
                time.sleep(0.25)
        return resp

    with _rpc_client(settings, httpx.MockTransport(forward)) as rpc:
        return rpc.call("get_quiz_attempt_context", {"attempt_id": attempt_id}, token=token, user_id=user_id, request_id=str(uuid4()))


class QuizAttemptUpgradeCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _validate_local_env()
        RevisionLocalTests.setUpClass()
        cls.rev = RevisionLocalTests("fixture")
        cls.f = cls.rev.f
        cls.settings = Settings(
            supabase_url=cls.f.url,
            supabase_publishable_key=cls.f.publishable,
            rpc_signing_key_id=cls.f.key_id,
            rpc_signing_secret_base64=base64.b64encode(cls.f.secret).decode(),
        )

    def ok(self, resp, replayed: bool | None = None, schema: str | None = None, outcome: str | None = None) -> dict:
        if not isinstance(resp, dict):
            self.assertEqual(resp.status_code, 200, resp.text)
            if replayed is not None:
                self.assertEqual(resp.headers.get("Idempotency-Replayed"), "true" if replayed else "false")
            resp = resp.json()
        if outcome is not None:
            self.assertEqual(resp.get("outcome"), outcome, resp)
        if schema is not None:
            self.assertTrue(contract.is_valid(schema, resp), f"{schema}: {resp}")
        return resp

    def test_quiz_attempt_upgrade(self) -> None:
        token, user_id = self.f.users["a"]
        with self.rev.client() as pre_app:
            body, qids, legacy_chunks = self.rev.fixture(pre_app)
            self.assertEqual(len(qids), 1)
            qid = qids[0]
            create_body = {"schema_version": "1.1", "material_id": body["material_id"], "question_ids": qids, "origin": "MANUAL", "session_outcome_id": None}
            created = self.ok(self.f.post(pre_app, "/v1/assessment/attempts", create_body, key=f"it-upgrade-create-{uuid4().hex}"), False, "QuizAttemptResult")
            attempt_id = created["data"]["attempt_id"]
            self.assertEqual(created["data"]["status"], "IN_PROGRESS")

        legacy_key = f"it-upgrade-legacy-save-{uuid4().hex}"
        legacy_args = {"attempt_id": attempt_id, "question_id": qid, "selected_option_id": "B", "validity": "VALID"}
        with _rpc_client(self.settings) as rpc:
            legacy = self.ok(
                rpc.call("save_quiz_response", legacy_args, token=token, user_id=user_id, request_id=str(uuid4()), idempotency_key=child_key(legacy_key, "save-quiz-response")),
                schema="QuizResponseResult", outcome="COMMITTED",
            )["data"]
        resp_id = legacy["response_id"]
        self.assertEqual((legacy["attempt_id"], legacy["question_id"], legacy["selected_option_id"], legacy["validity"], legacy["is_correct"], legacy["graded_at"]), (attempt_id, qid, "B", "VALID", None, None))

        # The pre-upgrade schema predates the current HTTP quiz submission RPC.
        # Seed one graded attempt with the DB guards active, then create B7 over HTTP.
        with psycopg.connect(local_dsn(), autocommit=True) as db:
            wrong_attempt = self.rev.seed_submitted_incorrect_attempt(db, user_id, body["material_id"], qids)
        recommendation_path = "/v1/assessment/recommendations"
        recommendation_body = {**body, "suggested_minutes": 20, "priority": 0.1}
        recommendation_key = f"it-upgrade-recommendation-{uuid4().hex}"
        with self.rev.client() as pre_app:
            recommendation = self.ok(
                self.f.post(pre_app, recommendation_path, recommendation_body, key=recommendation_key),
                False, "OrchestratorReply",
            )
        rec = recommendation["result"]["data"]["revision_recommendation"]
        self.assertEqual(rec["evidence"]["attempt_ids"], [wrong_attempt])
        self.assertEqual(rec["evidence"]["error_count"], 1)
        expected_snapshot = (20, 0.1, rec["evidence"])
        self.assertEqual(self.rev.stored_choices_and_evidence(rec["recommendation_id"]), expected_snapshot)

        proc = subprocess.run([shutil.which("supabase") or "supabase", "migration", "up", "--local", "--yes"], cwd=ROOT, check=False, timeout=180)
        self.assertEqual(proc.returncode, 0, f"supabase migration up --local --yes failed ({proc.returncode})")

        ctx = self.ok(_wait_for_context(self.settings, token=token, user_id=user_id, attempt_id=attempt_id), schema="QuizAttemptContextResult", outcome="READ")["data"]
        self.assertEqual((ctx["attempt"]["attempt_id"], ctx["attempt"]["status"], ctx["response_version"]), (attempt_id, "IN_PROGRESS", 0))
        self.assertEqual(len(ctx["responses"]), 1, ctx["responses"])
        persisted = ctx["responses"][0]
        self.assertEqual((persisted["response_id"], persisted["selected_option_id"], persisted["validity"], persisted["is_correct"], persisted["graded_at"]), (resp_id, "B", "VALID", None, None))

        save_url = f"/v1/assessment/attempts/{attempt_id}/responses/{qid}"
        put_save = lambda app, opt, key, replayed: self.ok(app.put(save_url, json={"schema_version": "1.1", "selected_option_id": opt}, headers=self.f.auth("a", **{"Idempotency-Key": key})), replayed, "QuizResponseResult", "COMMITTED")

        self.assertEqual(self.rev.stored_choices_and_evidence(rec["recommendation_id"]), expected_snapshot)
        with self.rev.client() as post_app:
            replayed_recommendation = self.ok(
                self.f.post(post_app, recommendation_path, recommendation_body, key=recommendation_key),
                True, "OrchestratorReply",
            )
            self.assertEqual(replayed_recommendation["action_reference"], recommendation["action_reference"])
            self.assertEqual(replayed_recommendation["result"]["data"], recommendation["result"]["data"])

            restored = self.ok(post_app.get(f"/v1/assessment/materials/{body['material_id']}",
                                           headers=self.f.auth("a"),
                                           params={"conversation_id": body["conversation_id"]}),
                               schema="AssessmentMaterialDetailResult", outcome="READ")
            self.assertEqual(restored["data"]["chunks"], legacy_chunks)
            self.assertEqual(put_save(post_app, "B", legacy_key, True)["data"], legacy)
            new_save = put_save(post_app, "A", f"it-upgrade-new-save-{uuid4().hex}", False)["data"]
            self.assertEqual((new_save["response_id"], new_save["selected_option_id"], new_save["validity"], new_save["is_correct"]), (resp_id, "A", "VALID", None))

            submit_key = f"it-upgrade-submit-{uuid4().hex}"
            submitted = self.ok(self.f.post(post_app, f"/v1/assessment/attempts/{attempt_id}/submit", {"schema_version": "1.1"}, key=submit_key), False, "QuizAttemptSubmissionResult")
            att, resps = submitted["data"]["attempt"], submitted["data"]["responses"]
            self.assertEqual((att["status"], att["valid_response_count"], att["correct_count"], att["incorrect_count"], att["omitted_count"], att["score_percent"]), ("SUBMITTED", 1, 1, 0, 0, 100))
            self.assertEqual(len(resps), 1)
            self.assertEqual((resps[0]["response_id"], resps[0]["selected_option_id"], resps[0]["validity"], resps[0]["is_correct"]), (resp_id, "A", "VALID", True))
            self.assertIsNotNone(resps[0]["graded_at"])

        with self.rev.client() as fresh_app:
            replay = self.ok(self.f.post(fresh_app, f"/v1/assessment/attempts/{attempt_id}/submit", {"schema_version": "1.1"}, key=submit_key), True, "QuizAttemptSubmissionResult", "COMMITTED")
            self.assertEqual(replay["data"], submitted["data"])
            self.assertNotEqual(replay["request_id"], submitted["request_id"])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(QuizAttemptUpgradeCheck)
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
