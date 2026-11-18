"""HTTP/auth/RPC acceptance tests for F2 B5 quiz attempts, responses, and grading."""

from __future__ import annotations

import base64
import copy
import json
import threading
import unittest
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid5

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from backend.app.clients.rpc import iso
from backend.app.core import contract
from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.nlu.extractor import ScriptedExtractor

USER_A = "00000000-0000-4000-8000-000000000001"
USER_B = "00000000-0000-4000-8000-000000000002"
CONV_A = "a1b2c3d4-0000-4000-8000-000000000003"
MAT_A = "e5f6a7b8-0000-4000-8000-000000000201"
MAT_B = "00000000-0000-4000-8000-000000000203"
Q_VERIFIED_1 = "00000000-0000-4000-8000-000000000301"
Q_VERIFIED_2 = "00000000-0000-4000-8000-000000000302"
Q_VERIFIED_3 = "00000000-0000-4000-8000-000000000303"
Q_VERIFIED_4 = "00000000-0000-4000-8000-000000000304"
Q_DRAFT_1 = "00000000-0000-4000-8000-000000000305"
Q_REJECTED_1 = "00000000-0000-4000-8000-000000000306"
Q_USER_B = "00000000-0000-4000-8000-000000000307"
SESSION_OUTCOME_1 = "00000000-0000-4000-8000-000000000777"


def _make_question(
    qid: str,
    *,
    user_id: str = USER_A,
    material_id: str = MAT_A,
    question_type: str = "MCQ",
    answer_key: str = "B",
    status: str = "VERIFIED",
) -> dict:
    options = (
        [
            {"option_id": "A", "text": "UDP"},
            {"option_id": "B", "text": "TCP"},
            {"option_id": "C", "text": "ICMP"},
            {"option_id": "D", "text": "ARP"},
        ]
        if question_type == "MCQ"
        else [
            {"option_id": "TRUE", "text": "Đúng"},
            {"option_id": "FALSE", "text": "Sai"},
        ]
    )
    return {
        "assessment_version": "1.0.0",
        "question_id": qid,
        "user_id": user_id,
        "conversation_id": CONV_A,
        "material_id": material_id,
        "version": 1,
        "topic": "Mạng máy tính",
        "question_type": question_type,
        "stem": f"Câu hỏi kiểm tra {qid[-4:]}?",
        "options": options,
        "answer_key": answer_key,
        "explanation": "Giải thích chuẩn từ tài liệu.",
        "source_chunk_ids": ["00000000-0000-4000-8000-000000000211"],
        "status": status,
        "model": "deepseek-chat",
        "prompt_version": "f2-question-v1",
        "verified_at": "2026-11-18T07:05:00.000000Z" if status == "VERIFIED" else None,
        "created_at": "2026-11-18T07:00:00.000000Z",
        "updated_at": "2026-11-18T07:05:00.000000Z",
    }


class AttemptHttpAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.now = datetime(2026, 11, 18, 9, 0, tzinfo=timezone.utc)
        cls.private_key = ec.generate_private_key(ec.SECP256R1())
        public_jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(cls.private_key.public_key()))
        public_jwk.update(kid="f2-b5-key", use="sig", alg="ES256")
        cls.jwks = {"keys": [public_jwk]}

    def setUp(self):
        self.lock = threading.Lock()
        self.rpc_calls: list[tuple[str, dict]] = []
        self.idempotency: dict[tuple[str, str, str], dict] = {}
        self.attempts: dict[str, dict] = {}
        self.responses: dict[tuple[str, str], dict] = {}
        self.response_versions: dict[str, int] = {}
        self.before_context_snapshot: Callable[[], None] | None = None
        self.materials = {
            MAT_A: {"material_id": MAT_A, "user_id": USER_A, "status": "READY"},
            MAT_B: {"material_id": MAT_B, "user_id": USER_B, "status": "READY"},
        }
        self.questions = {
            Q_VERIFIED_1: _make_question(Q_VERIFIED_1, answer_key="B", status="VERIFIED"),
            Q_VERIFIED_2: _make_question(Q_VERIFIED_2, answer_key="D", status="VERIFIED"),
            Q_VERIFIED_3: _make_question(
                Q_VERIFIED_3,
                question_type="TRUE_FALSE",
                answer_key="TRUE",
                status="VERIFIED",
            ),
            Q_VERIFIED_4: _make_question(Q_VERIFIED_4, answer_key="A", status="VERIFIED"),
            Q_DRAFT_1: _make_question(Q_DRAFT_1, answer_key="B", status="DRAFT"),
            Q_REJECTED_1: _make_question(Q_REJECTED_1, answer_key="B", status="REJECTED"),
            Q_USER_B: _make_question(
                Q_USER_B,
                user_id=USER_B,
                material_id=MAT_B,
                answer_key="A",
                status="VERIFIED",
            ),
        }
        self.settings = Settings(
            supabase_url="https://supabase.example.test",
            supabase_publishable_key="anon-key",
            supabase_jwt_audience="authenticated",
            supabase_jwt_algorithm="ES256",
            deepseek_api_key="deepseek-test-key",
            deepseek_base_url="https://deepseek.example.test/v1",
            deepseek_model="deepseek-chat",
            rpc_signing_key_id="f2-b5-sign",
            rpc_signing_secret_base64=base64.b64encode(b"secret-material-for-f2-b5-32byte").decode(),
        )
        self.client_ctx = self._new_client()
        self.client = self.client_ctx.__enter__()

    def tearDown(self):
        self.client_ctx.__exit__(None, None, None)

    def _new_client(self):
        app = create_app(
            self.settings,
            rpc_transport=httpx.MockTransport(self._rpc_handler),
            jwks_transport=httpx.MockTransport(lambda req: httpx.Response(200, json=self.jwks)),
            clock=lambda: self.now,
            extractor=ScriptedExtractor({}),
        )
        return TestClient(app)

    def _token(self, user_id: str = USER_A) -> str:
        payload = {
            "sub": user_id,
            "aud": "authenticated",
            "iss": f"{self.settings.supabase_url}/auth/v1",
            "role": "authenticated",
            "exp": int((self.now + timedelta(hours=1)).timestamp()),
        }
        return jwt.encode(payload, self.private_key, algorithm="ES256", headers={"kid": "f2-b5-key"})

    def _headers(self, key: str, user_id: str = USER_A) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token(user_id)}",
            "Idempotency-Key": key,
        }

    def _rpc_ok(self, req_id: str, outcome: str, data: dict) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "schema_version": "1.1",
                "request_id": req_id,
                "outcome": outcome,
                "data": data,
                "error": None,
                "warnings": [],
            },
        )

    def _rpc_err(self, req_id: str, code: str, message: str) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "schema_version": "1.1",
                "request_id": req_id,
                "outcome": "ERROR",
                "data": None,
                "error": {
                    "code": code,
                    "message": message,
                    "field": None,
                    "details": {},
                    "retryable": False,
                },
                "warnings": [],
            },
        )

    def _rpc_handler(self, request: httpx.Request) -> httpx.Response:
        op = request.url.path.rsplit("/", 1)[-1]
        env = json.loads(request.content.decode("utf-8"))["p_request"]
        req_id = env["request_id"]
        uid = env["execution_context"]["trusted_context"]["principal"]["user_id"]
        idem_key = env["execution_context"]["idempotency_key"]
        args = env["arguments"]

        hook = self.before_context_snapshot if op == "get_quiz_attempt_context" else None
        if hook is not None:
            hook()

        with self.lock:
            self.rpc_calls.append((op, copy.deepcopy(env)))

            if op == "lookup_operation_result":
                existing = self.idempotency.get((uid, args["operation"], args["idempotency_key"]))
                if existing is not None and existing["fp"] != args["request_fingerprint"]:
                    return self._rpc_err(req_id, "IDEMPOTENCY_CONFLICT", "Conflicting idempotency key.")
                stored = None if existing is None else self._rpc_ok(req_id, "COMMITTED", copy.deepcopy(existing["data"])).json()
                return self._rpc_ok(req_id, "READ", {"result": stored})

            if op == "get_quiz_attempt_context":
                attempt = self.attempts.get(args["attempt_id"])
                if attempt is None or attempt["user_id"] != uid:
                    return self._rpc_err(req_id, "ENTITY_NOT_FOUND", "Attempt not found.")
                questions = [copy.deepcopy(self.questions[qid]) for qid in attempt["question_ids"]]
                responses = [
                    copy.deepcopy(self.responses[(attempt["attempt_id"], qid)])
                    for qid in attempt["question_ids"]
                    if (attempt["attempt_id"], qid) in self.responses
                ]
                return self._rpc_ok(req_id, "READ", {
                    "attempt": copy.deepcopy(attempt),
                    "questions": questions,
                    "responses": responses,
                    "response_version": self.response_versions.get(attempt["attempt_id"], 0),
                })

            if op == "list_questions":
                items = [
                    copy.deepcopy(q)
                    for q in self.questions.values()
                    if q["user_id"] == uid
                    and (args["material_id"] is None or q["material_id"] == args["material_id"])
                    and (args["status"] is None or q["status"] == args["status"])
                ]
                return self._rpc_ok(req_id, "READ", {"items": items, "next_cursor": None})

            if op == "create_quiz_attempt":
                fp = contract.sha256_hex(args)
                existing = self.idempotency.get((uid, op, idem_key))
                if existing is not None:
                    if existing["fp"] != fp:
                        return self._rpc_err(req_id, "IDEMPOTENCY_CONFLICT", "Conflicting idempotency key.")
                    return self._rpc_ok(req_id, "READ", copy.deepcopy(existing["data"]))

                mat = self.materials.get(args["material_id"])
                if mat is None or mat["user_id"] != uid or mat["status"] != "READY":
                    return self._rpc_err(req_id, "ENTITY_NOT_FOUND", "Material not found.")

                for qid in args["question_ids"]:
                    q = self.questions.get(qid)
                    if q is None or q["user_id"] != uid or q["material_id"] != args["material_id"]:
                        return self._rpc_err(req_id, "ENTITY_NOT_FOUND", "Question not found.")
                    if q["status"] != "VERIFIED":
                        return self._rpc_err(req_id, "STALE_ENTITY_VERSION", "Question is not VERIFIED.")

                stamp = iso(self.now)
                attempt = {
                    "assessment_version": "1.0.0",
                    "attempt_id": args["attempt_id"],
                    "user_id": uid,
                    "material_id": args["material_id"],
                    "origin": args["origin"],
                    "session_outcome_id": args["session_outcome_id"],
                    "status": "IN_PROGRESS",
                    "question_ids": list(args["question_ids"]),
                    "total_questions": len(args["question_ids"]),
                    "valid_response_count": 0,
                    "correct_count": 0,
                    "incorrect_count": 0,
                    "omitted_count": len(args["question_ids"]),
                    "score_percent": None,
                    "started_at": stamp,
                    "submitted_at": None,
                    "created_at": stamp,
                    "updated_at": stamp,
                }
                self.attempts[attempt["attempt_id"]] = copy.deepcopy(attempt)
                self.response_versions[attempt["attempt_id"]] = 0
                self.idempotency[(uid, op, idem_key)] = {"fp": fp, "data": copy.deepcopy(attempt)}
                return self._rpc_ok(req_id, "COMMITTED", attempt)

            if op == "save_quiz_response":
                fp_args = {k: v for k, v in args.items() if k != "include_replay_status"}
                fp = contract.sha256_hex({
                    "schema_version": "1.1", "user_id": uid, "operation": op,
                    "arguments": fp_args, "decision_binding": None,
                })
                existing = self.idempotency.get((uid, op, idem_key))
                if existing is not None:
                    if existing["fp"] != fp:
                        return self._rpc_err(req_id, "IDEMPOTENCY_CONFLICT", "Conflicting idempotency key.")
                    outcome = "READ" if args.get("include_replay_status") else "COMMITTED"
                    return self._rpc_ok(req_id, outcome, copy.deepcopy(existing["data"]))

                attempt = self.attempts.get(args["attempt_id"])
                if attempt is None or attempt["user_id"] != uid:
                    return self._rpc_err(req_id, "ENTITY_NOT_FOUND", "Attempt not found.")
                if attempt["status"] == "SUBMITTED":
                    return self._rpc_err(req_id, "STALE_ENTITY_VERSION", "Attempt already submitted.")
                if args["question_id"] not in attempt["question_ids"]:
                    return self._rpc_err(req_id, "ENTITY_NOT_FOUND", "Question not in attempt.")

                stamp = iso(self.now)
                prev = self.responses.get((args["attempt_id"], args["question_id"]))
                resp = {
                    "response_id": (
                        prev["response_id"]
                        if prev is not None
                        else str(uuid5(UUID(args["attempt_id"]), f"quiz-response:{args['question_id']}"))
                    ),
                    "attempt_id": args["attempt_id"],
                    "question_id": args["question_id"],
                    "user_id": uid,
                    "selected_option_id": args["selected_option_id"],
                    "validity": args["validity"],
                    "is_correct": None,
                    "graded_at": None,
                    "created_at": prev["created_at"] if prev is not None else stamp,
                    "updated_at": stamp,
                }
                self.responses[(args["attempt_id"], args["question_id"])] = copy.deepcopy(resp)
                self.response_versions[args["attempt_id"]] = self.response_versions.get(args["attempt_id"], 0) + 1
                self.idempotency[(uid, op, idem_key)] = {"fp": fp, "data": copy.deepcopy(resp)}
                return self._rpc_ok(req_id, "COMMITTED", resp)

            if op == "submit_quiz_attempt":
                fp = contract.sha256_hex({
                    "schema_version": "1.1", "user_id": uid, "operation": op,
                    "arguments": {"attempt_id": args["attempt_id"]}, "decision_binding": None,
                })
                existing = self.idempotency.get((uid, op, idem_key))
                if existing is not None:
                    if existing["fp"] != fp:
                        return self._rpc_err(req_id, "IDEMPOTENCY_CONFLICT", "Conflicting idempotency key.")
                    outcome = "READ" if args.get("include_replay_status") else "COMMITTED"
                    return self._rpc_ok(req_id, outcome, copy.deepcopy(existing["data"]))

                attempt = self.attempts.get(args["attempt_id"])
                if attempt is None or attempt["user_id"] != uid:
                    return self._rpc_err(req_id, "ENTITY_NOT_FOUND", "Attempt not found.")
                if attempt["status"] == "SUBMITTED":
                    return self._rpc_err(req_id, "STALE_ENTITY_VERSION", "Attempt already submitted.")

                updated_attempt = {
                    **attempt,
                    "status": "SUBMITTED",
                    "valid_response_count": args["valid_response_count"],
                    "correct_count": args["correct_count"],
                    "incorrect_count": args["incorrect_count"],
                    "omitted_count": args["omitted_count"],
                    "score_percent": args["score_percent"],
                    "submitted_at": args["submitted_at"],
                    "updated_at": args["submitted_at"],
                }
                self.attempts[attempt["attempt_id"]] = copy.deepcopy(updated_attempt)
                for item in args["graded_responses"]:
                    self.responses[(attempt["attempt_id"], item["question_id"])] = copy.deepcopy(item)
                payload = {"attempt": updated_attempt, "responses": copy.deepcopy(args["graded_responses"])}
                self.idempotency[(uid, op, idem_key)] = {"fp": fp, "data": copy.deepcopy(payload)}
                return self._rpc_ok(req_id, "COMMITTED", payload)

        raise AssertionError(f"Unexpected RPC operation: {op}")

    def test_full_attempt_lifecycle_manual_and_session_handoff(self):
        # 1. Create MANUAL attempt
        create_body = {
            "schema_version": "1.1",
            "material_id": MAT_A,
            "question_ids": [Q_VERIFIED_1, Q_VERIFIED_2, Q_VERIFIED_3, Q_VERIFIED_4],
            "origin": "MANUAL",
            "session_outcome_id": None,
        }
        r1 = self.client.post("/v1/assessment/attempts", headers=self._headers("attempt-create-0001"), json=create_body)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.headers.get("Idempotency-Replayed"), "false")
        body1 = r1.json()
        self.assertTrue(contract.is_valid("QuizAttemptResult", body1))
        attempt_id = body1["data"]["attempt_id"]
        self.assertEqual(body1["data"]["status"], "IN_PROGRESS")
        self.assertEqual(body1["data"]["origin"], "MANUAL")
        self.assertIsNone(body1["data"]["session_outcome_id"])

        # Replay create with same key -> 200 READ & Idempotency-Replayed: true
        r1_replay = self.client.post(
            "/v1/assessment/attempts",
            headers=self._headers("attempt-create-0001"),
            json=create_body,
        )
        self.assertEqual(r1_replay.status_code, 200)
        self.assertEqual(r1_replay.headers.get("Idempotency-Replayed"), "true")
        self.assertEqual(r1_replay.json()["data"]["attempt_id"], attempt_id)

        # 2. Create SESSION_HANDOFF attempt
        handoff_body = {
            "schema_version": "1.1",
            "material_id": MAT_A,
            "question_ids": [Q_VERIFIED_1],
            "origin": "SESSION_HANDOFF",
            "session_outcome_id": SESSION_OUTCOME_1,
        }
        r_handoff = self.client.post(
            "/v1/assessment/attempts",
            headers=self._headers("attempt-create-handoff-1"),
            json=handoff_body,
        )
        self.assertEqual(r_handoff.status_code, 200)
        self.assertEqual(r_handoff.json()["data"]["origin"], "SESSION_HANDOFF")
        self.assertEqual(r_handoff.json()["data"]["session_outcome_id"], SESSION_OUTCOME_1)

        # 3. Save responses (1 correct MCQ, 1 wrong MCQ, 1 invalid TRUE_FALSE, 1 omitted)
        s1 = self.client.put(
            f"/v1/assessment/attempts/{attempt_id}/responses/{Q_VERIFIED_1}",
            headers=self._headers("resp-save-0000001"),
            json={"schema_version": "1.1", "selected_option_id": "B"},
        )
        self.assertEqual(s1.status_code, 200)
        self.assertEqual(s1.headers.get("Idempotency-Replayed"), "false")
        self.assertEqual(s1.json()["data"]["validity"], "VALID")
        self.assertIsNone(s1.json()["data"]["is_correct"])

        # Replay save response
        s1_replay = self.client.put(
            f"/v1/assessment/attempts/{attempt_id}/responses/{Q_VERIFIED_1}",
            headers=self._headers("resp-save-0000001"),
            json={"schema_version": "1.1", "selected_option_id": "B"},
        )
        self.assertEqual(s1_replay.status_code, 200, s1_replay.text)
        self.assertEqual(s1_replay.headers.get("Idempotency-Replayed"), "true")

        # Save wrong option on Q_VERIFIED_2
        s2 = self.client.put(
            f"/v1/assessment/attempts/{attempt_id}/responses/{Q_VERIFIED_2}",
            headers=self._headers("resp-save-0000002"),
            json={"schema_version": "1.1", "selected_option_id": "A"},
        )
        self.assertEqual(s2.status_code, 200)
        self.assertEqual(s2.json()["data"]["validity"], "VALID")

        # Save out-of-range option on Q_VERIFIED_3 (TRUE_FALSE)
        s3 = self.client.put(
            f"/v1/assessment/attempts/{attempt_id}/responses/{Q_VERIFIED_3}",
            headers=self._headers("resp-save-0000003"),
            json={"schema_version": "1.1", "selected_option_id": "OUT_OF_RANGE"},
        )
        self.assertEqual(s3.status_code, 200)
        self.assertEqual(s3.json()["data"]["validity"], "INVALID")
        self.assertIsNone(s3.json()["data"]["is_correct"])

        # 4. Submit and grade attempt
        with self._new_client() as restarted:
            sub = restarted.post(
                f"/v1/assessment/attempts/{attempt_id}/submit",
                headers=self._headers("attempt-submit-0001"),
                json={"schema_version": "1.1"},
            )
        self.assertEqual(sub.status_code, 200)
        self.assertEqual(sub.headers.get("Idempotency-Replayed"), "false")
        sub_body = sub.json()
        self.assertTrue(contract.is_valid("QuizAttemptSubmissionResult", sub_body))

        graded_attempt = sub_body["data"]["attempt"]
        self.assertEqual(graded_attempt["status"], "SUBMITTED")
        self.assertEqual(graded_attempt["total_questions"], 4)
        self.assertEqual(graded_attempt["valid_response_count"], 2)
        self.assertEqual(graded_attempt["correct_count"], 1)
        self.assertEqual(graded_attempt["incorrect_count"], 1)
        self.assertEqual(graded_attempt["omitted_count"], 2)
        self.assertEqual(graded_attempt["score_percent"], 50)

        # Replay submit with same key -> 200 OK & Idempotency-Replayed: true
        sub_replay = self.client.post(
            f"/v1/assessment/attempts/{attempt_id}/submit",
            headers=self._headers("attempt-submit-0001"),
            json={"schema_version": "1.1"},
        )
        self.assertEqual(sub_replay.status_code, 200)
        self.assertEqual(sub_replay.headers.get("Idempotency-Replayed"), "true")

        # Second submit with new key -> 409 STALE_ENTITY_VERSION
        sub_again = self.client.post(
            f"/v1/assessment/attempts/{attempt_id}/submit",
            headers=self._headers("attempt-submit-0002"),
            json={"schema_version": "1.1"},
        )
        self.assertEqual(sub_again.status_code, 409)
        self.assertEqual(sub_again.json()["error"]["code"], "STALE_ENTITY_VERSION")

        # Saving response after submit -> 409 STALE_ENTITY_VERSION
        late_save = self.client.put(
            f"/v1/assessment/attempts/{attempt_id}/responses/{Q_VERIFIED_4}",
            headers=self._headers("resp-save-late-0001"),
            json={"schema_version": "1.1", "selected_option_id": "A"},
        )
        self.assertEqual(late_save.status_code, 409)
        self.assertEqual(late_save.json()["error"]["code"], "STALE_ENTITY_VERSION")

    def test_rejects_draft_or_rejected_questions_and_cross_user_access(self):
        # Attempt with DRAFT question -> 409
        for qid in (Q_DRAFT_1, Q_REJECTED_1):
            r = self.client.post(
                "/v1/assessment/attempts",
                headers=self._headers(f"attempt-unverified-{qid[-4:]}"),
                json={
                    "schema_version": "1.1",
                    "material_id": MAT_A,
                    "question_ids": [Q_VERIFIED_1, qid],
                    "origin": "MANUAL",
                    "session_outcome_id": None,
                },
            )
            self.assertEqual(r.status_code, 409)
            self.assertEqual(r.json()["error"]["code"], "STALE_ENTITY_VERSION")

        # Invalid origin/session_outcome_id combinations -> 422
        bad_manual = self.client.post(
            "/v1/assessment/attempts",
            headers=self._headers("attempt-bad-manual-01"),
            json={
                "schema_version": "1.1",
                "material_id": MAT_A,
                "question_ids": [Q_VERIFIED_1],
                "origin": "MANUAL",
                "session_outcome_id": SESSION_OUTCOME_1,
            },
        )
        self.assertEqual(bad_manual.status_code, 422)

        bad_handoff = self.client.post(
            "/v1/assessment/attempts",
            headers=self._headers("attempt-bad-handoff-1"),
            json={
                "schema_version": "1.1",
                "material_id": MAT_A,
                "question_ids": [Q_VERIFIED_1],
                "origin": "SESSION_HANDOFF",
                "session_outcome_id": None,
            },
        )
        self.assertEqual(bad_handoff.status_code, 422)

        # Create valid attempt as USER_A, then USER_B tries to save response and submit -> 404
        ok_create = self.client.post(
            "/v1/assessment/attempts",
            headers=self._headers("attempt-owner-a-0001", USER_A),
            json={
                "schema_version": "1.1",
                "material_id": MAT_A,
                "question_ids": [Q_VERIFIED_1],
                "origin": "MANUAL",
                "session_outcome_id": None,
            },
        )
        self.assertEqual(ok_create.status_code, 200)
        attempt_id = ok_create.json()["data"]["attempt_id"]

        cross_put = self.client.put(
            f"/v1/assessment/attempts/{attempt_id}/responses/{Q_VERIFIED_1}",
            headers=self._headers("cross-user-put-0001", USER_B),
            json={"schema_version": "1.1", "selected_option_id": "B"},
        )
        self.assertEqual(cross_put.status_code, 404)
        self.assertEqual(cross_put.json()["error"]["code"], "ENTITY_NOT_FOUND")

        cross_submit = self.client.post(
            f"/v1/assessment/attempts/{attempt_id}/submit",
            headers=self._headers("cross-user-sub-0001", USER_B),
            json={"schema_version": "1.1"},
        )
        self.assertEqual(cross_submit.status_code, 404)
        self.assertEqual(cross_submit.json()["error"]["code"], "ENTITY_NOT_FOUND")

    def test_save_replay_owns_idempotency_and_response_version(self):
        created = self.client.post(
            "/v1/assessment/attempts",
            headers=self._headers("attempt-save-ver-0001"),
            json={
                "schema_version": "1.1",
                "material_id": MAT_A,
                "question_ids": [Q_VERIFIED_1],
                "origin": "MANUAL",
                "session_outcome_id": None,
            },
        )
        self.assertEqual(created.status_code, 200)
        attempt_id = created.json()["data"]["attempt_id"]
        self.assertEqual(self.response_versions[attempt_id], 0)

        self.rpc_calls.clear()
        save1 = self.client.put(
            f"/v1/assessment/attempts/{attempt_id}/responses/{Q_VERIFIED_1}",
            headers=self._headers("resp-ver-save-000001"),
            json={"schema_version": "1.1", "selected_option_id": "B"},
        )
        self.assertEqual(save1.status_code, 200)
        self.assertEqual(save1.headers.get("Idempotency-Replayed"), "false")
        self.assertTrue(contract.is_valid("QuizResponseResult", save1.json()))
        self.assertEqual(self.response_versions[attempt_id], 1)

        save1_replay = self.client.put(
            f"/v1/assessment/attempts/{attempt_id}/responses/{Q_VERIFIED_1}",
            headers=self._headers("resp-ver-save-000001"),
            json={"schema_version": "1.1", "selected_option_id": "B"},
        )
        self.assertEqual(save1_replay.status_code, 200)
        self.assertEqual(save1_replay.headers.get("Idempotency-Replayed"), "true")
        self.assertTrue(contract.is_valid("QuizResponseResult", save1_replay.json()))
        self.assertEqual(save1_replay.json()["outcome"], "COMMITTED")
        self.assertEqual(self.response_versions[attempt_id], 1)

        save2 = self.client.put(
            f"/v1/assessment/attempts/{attempt_id}/responses/{Q_VERIFIED_1}",
            headers=self._headers("resp-ver-save-000002"),
            json={"schema_version": "1.1", "selected_option_id": "A"},
        )
        self.assertEqual(save2.status_code, 200)
        self.assertEqual(save2.headers.get("Idempotency-Replayed"), "false")
        self.assertEqual(self.response_versions[attempt_id], 2)

        self.assertEqual([op for op, _ in self.rpc_calls if op == "lookup_operation_result"], [])
        save_envs = [env for op, env in self.rpc_calls if op == "save_quiz_response"]
        self.assertEqual(len(save_envs), 3)
        self.assertTrue(all(env["arguments"].get("include_replay_status") is True for env in save_envs))

    def test_submit_same_key_race_replays_when_second_commits_before_first_snapshot(self):
        created = self.client.post(
            "/v1/assessment/attempts",
            headers=self._headers("attempt-submit-race-c1"),
            json={
                "schema_version": "1.1",
                "material_id": MAT_A,
                "question_ids": [Q_VERIFIED_1, Q_VERIFIED_2],
                "origin": "MANUAL",
                "session_outcome_id": None,
            },
        )
        self.assertEqual(created.status_code, 200)
        attempt_id = created.json()["data"]["attempt_id"]

        saved = self.client.put(
            f"/v1/assessment/attempts/{attempt_id}/responses/{Q_VERIFIED_1}",
            headers=self._headers("resp-submit-race-0001"),
            json={"schema_version": "1.1", "selected_option_id": "B"},
        )
        self.assertEqual(saved.status_code, 200)

        race_key = "attempt-submit-race-k1"
        self.rpc_calls.clear()
        first_at_snapshot = threading.Event()
        second_committed = threading.Event()
        hook_lock = threading.Lock()
        hook_armed = True

        def pause_first_snapshot():
            nonlocal hook_armed
            with hook_lock:
                if not hook_armed:
                    return
                hook_armed = False
            first_at_snapshot.set()
            if not second_committed.wait(timeout=5):
                raise AssertionError("Timed out waiting for second submit commit.")

        first_result: dict[str, object] = {}

        def run_first():
            try:
                first_result["response"] = self.client.post(
                    f"/v1/assessment/attempts/{attempt_id}/submit",
                    headers=self._headers(race_key),
                    json={"schema_version": "1.1"},
                )
            except BaseException as exc:  # pragma: no cover - surfaced below
                first_result["error"] = exc
            finally:
                first_at_snapshot.set()

        self.before_context_snapshot = pause_first_snapshot
        t1 = threading.Thread(target=run_first, daemon=True)
        t1.start()
        try:
            self.assertTrue(first_at_snapshot.wait(timeout=5))
            self.assertIsNone(first_result.get("error"))
            with self._new_client() as second_client:
                try:
                    r2 = second_client.post(
                        f"/v1/assessment/attempts/{attempt_id}/submit",
                        headers=self._headers(race_key),
                        json={"schema_version": "1.1"},
                    )
                finally:
                    second_committed.set()
            t1.join(timeout=5)
            self.assertFalse(t1.is_alive())
        finally:
            second_committed.set()
            self.before_context_snapshot = None

        self.assertIsNone(first_result.get("error"))
        r1 = first_result["response"]
        self.assertIsNotNone(r1)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)

        replayed_headers = [r1.headers.get("Idempotency-Replayed"), r2.headers.get("Idempotency-Replayed")]
        self.assertEqual(replayed_headers, ["true", "false"])

        body1 = r1.json()
        body2 = r2.json()
        self.assertTrue(contract.is_valid("QuizAttemptSubmissionResult", body1))
        self.assertTrue(contract.is_valid("QuizAttemptSubmissionResult", body2))
        self.assertEqual(body1["outcome"], "COMMITTED")
        self.assertEqual(body2["outcome"], "COMMITTED")
        self.assertEqual(body1["data"], body2["data"])

        submit_envs = [env for op, env in self.rpc_calls if op == "submit_quiz_attempt"]
        self.assertEqual(len(submit_envs), 1)
        self.assertTrue(submit_envs[0]["arguments"].get("include_replay_status"))
        lookup_calls = [op for op, _ in self.rpc_calls if op == "lookup_operation_result"]
        self.assertEqual(len(lookup_calls), 3)


if __name__ == "__main__":
    unittest.main()
