"""Local Supabase integration tests for F2 B5 quiz attempts, response saving, and grading."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from backend.app.core import contract
from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.nlu.extractor import ScriptedExtractor


def _supabase_env() -> dict[str, str] | None:
    url = os.environ.get("STUDYFLOW_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    anon = os.environ.get("STUDYFLOW_SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    db_url = os.environ.get("STUDYFLOW_LOCAL_DB_URL") or "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    if url and anon:
        return {"API_URL": url, "ANON_KEY": anon, "DB_URL": db_url}
    try:
        proc = subprocess.run(
            ["supabase", "status", "-o", "env"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    parsed: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            parsed[k.strip()] = v.strip().strip('"')
    if "API_URL" not in parsed or "ANON_KEY" not in parsed:
        return None
    parsed.setdefault("DB_URL", db_url)
    return parsed


class LocalSupabaseAttemptIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = _supabase_env()
        if not cls.env:
            raise unittest.SkipTest("Local Supabase stack is not running; skipping local DB integration test.")
        cls.now = datetime.now(timezone.utc)
        cls.private_key = ec.generate_private_key(ec.SECP256R1())
        public_jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(cls.private_key.public_key()))
        public_jwk.update(kid="local-b5-key", use="sig", alg="ES256")
        cls.jwks = {"keys": [public_jwk]}

    def _psql(self, sql: str) -> None:
        subprocess.run(
            ["psql", self.env["DB_URL"], "-v", "ON_ERROR_STOP=1", "-c", sql],
            check=True,
            capture_output=True,
            text=True,
        )

    def _token(self, user_id: str) -> str:
        exp = int((self.now + timedelta(minutes=30)).timestamp())
        return jwt.encode(
            {
                "sub": user_id,
                "aud": "authenticated",
                "role": "authenticated",
                "iss": f"{self.env['API_URL'].rstrip('/')}/auth/v1",
                "exp": exp,
            },
            self.private_key,
            algorithm="ES256",
            headers={"kid": "local-b5-key"},
        )

    def test_end_to_end_attempt_grading_and_immutability(self):
        user_a = str(uuid4())
        user_b = str(uuid4())
        conv_a = str(uuid4())
        key_id = f"b5-int-key-{uuid4().hex[:8]}"
        secret_bytes = b"0123456789abcdef0123456789abcdef"

        self._psql(
            f"""
            insert into auth.users(id) values ('{user_a}'), ('{user_b}');
            insert into app_private.rpc_attestation_keys(key_id, key_material, not_before, not_after)
            values ('{key_id}', decode('{secret_bytes.hex()}', 'hex'),
                    clock_timestamp() - interval '1 hour', clock_timestamp() + interval '1 hour');
            """
        )

        class StubGenerator:
            def generate(self, **kwargs):
                return [
                    {
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
                        "evidence": [
                            {
                                "chunk_id": kwargs["chunks"][0]["chunk_id"],
                                "page": 1,
                                "excerpt": "TCP truyền dữ liệu tin cậy hướng kết nối.",
                            }
                        ],
                    },
                    {
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
                        "evidence": [
                            {
                                "chunk_id": kwargs["chunks"][0]["chunk_id"],
                                "page": 1,
                                "excerpt": "UDP truyền datagram không kết nối.",
                            }
                        ],
                    },
                ]

        settings = Settings(
            supabase_url=self.env["API_URL"],
            supabase_publishable_key=self.env["ANON_KEY"],
            supabase_jwt_audience="authenticated",
            supabase_jwt_algorithm="ES256",
            deepseek_api_key="test-key",
            deepseek_base_url="https://deepseek.example.test/v1",
            deepseek_model="deepseek-chat",
            rpc_signing_key_id=key_id,
            rpc_signing_secret_base64=base64.b64encode(secret_bytes).decode(),
        )
        app = create_app(
            settings,
            jwks_transport=httpx.MockTransport(lambda req: httpx.Response(200, json=self.jwks)),
            clock=lambda: self.now,
            extractor=ScriptedExtractor({}),
            question_generator=StubGenerator(),
        )

        with TestClient(app) as client:
            headers_a = lambda k: {"Authorization": f"Bearer {self._token(user_a)}", "Idempotency-Key": k}
            headers_b = lambda k: {"Authorization": f"Bearer {self._token(user_b)}", "Idempotency-Key": k}

            # 1. Upload material
            text_b64 = base64.b64encode(
                "TCP truyền dữ liệu tin cậy hướng kết nối. UDP truyền datagram không kết nối.".encode("utf-8")
            ).decode()
            up = client.post(
                "/v1/assessment/materials",
                headers=headers_a("b5-int-mat-upload-01"),
                json={
                    "schema_version": "1.1",
                    "conversation_id": conv_a,
                    "filename": "mang.md",
                    "mime_type": "text/markdown",
                    "content_base64": text_b64,
                    "topics": ["Mạng máy tính"],
                },
            )
            self.assertEqual(up.status_code, 200)
            material_id = up.json()["data"]["material"]["material_id"]

            # 2. Generate drafts
            dr = client.post(
                "/v1/assessment/drafts",
                headers=headers_a("b5-int-drafts-gen-01"),
                json={
                    "schema_version": "1.1",
                    "conversation_id": conv_a,
                    "material_id": material_id,
                    "topic": "Mạng máy tính",
                    "question_type": "MCQ",
                    "count": 2,
                },
            )
            self.assertEqual(dr.status_code, 200)
            action_ref = dr.json()["action_reference"]
            q_ids = [q["question_id"] for q in dr.json()["result"]["data"]["question_drafts"]["items"]]

            # Reject attempt while still DRAFT -> 409
            early = client.post(
                "/v1/assessment/attempts",
                headers=headers_a("b5-int-early-attempt-01"),
                json={
                    "schema_version": "1.1",
                    "material_id": material_id,
                    "question_ids": q_ids,
                    "origin": "MANUAL",
                    "session_outcome_id": None,
                },
            )
            self.assertEqual(early.status_code, 409)

            # 3. Approve drafts via /v1/decisions
            dec = client.post(
                "/v1/decisions",
                headers=headers_a("b5-int-approve-drafts-01"),
                json={
                    "schema_version": "1.1",
                    "conversation_id": conv_a,
                    "action_reference": action_ref,
                    "decision": "APPROVE",
                },
            )
            self.assertEqual(dec.status_code, 200)

            # 4. Create attempt, save 1 correct response, leave 1 omitted, submit
            att = client.post(
                "/v1/assessment/attempts",
                headers=headers_a("b5-int-create-attempt-01"),
                json={
                    "schema_version": "1.1",
                    "material_id": material_id,
                    "question_ids": q_ids,
                    "origin": "MANUAL",
                    "session_outcome_id": None,
                },
            )
            self.assertEqual(att.status_code, 200)
            attempt_id = att.json()["data"]["attempt_id"]

            save = client.put(
                f"/v1/assessment/attempts/{attempt_id}/responses/{q_ids[0]}",
                headers=headers_a("b5-int-save-resp-0001"),
                json={"schema_version": "1.1", "selected_option_id": "B"},
            )
            self.assertEqual(save.status_code, 200)

            # Cross-user submit fails with 404
            cross = client.post(
                f"/v1/assessment/attempts/{attempt_id}/submit",
                headers=headers_b("b5-int-cross-submit-01"),
                json={"schema_version": "1.1"},
            )
            self.assertEqual(cross.status_code, 404)

            sub = client.post(
                f"/v1/assessment/attempts/{attempt_id}/submit",
                headers=headers_a("b5-int-submit-00001"),
                json={"schema_version": "1.1"},
            )
            self.assertEqual(sub.status_code, 200)
            sub_data = sub.json()["data"]
            self.assertTrue(contract.is_valid("QuizAttemptSubmissionData", sub_data))
            self.assertEqual(sub_data["attempt"]["status"], "SUBMITTED")
            self.assertEqual(sub_data["attempt"]["valid_response_count"], 1)
            self.assertEqual(sub_data["attempt"]["correct_count"], 1)
            self.assertEqual(sub_data["attempt"]["incorrect_count"], 0)
            self.assertEqual(sub_data["attempt"]["omitted_count"], 1)
            self.assertEqual(sub_data["attempt"]["score_percent"], 100)


if __name__ == "__main__":
    unittest.main()
