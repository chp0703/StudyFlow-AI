"""Kiểm tra ứng dụng FastAPI thật qua giao diện truyền transport đã chốt.

Chỉ thay các phụ thuộc HTTP bên ngoài. Xác thực, đọc yêu cầu, kiểm tra schema,
tạo context và chuyển đổi RPC đều chạy bằng code thật.
Bộ giả lập phản hồi RPC không chứng minh RLS PostgreSQL hay bảo mật wrapper.
"""

import base64
import copy
import hashlib
import hmac
import importlib
import json
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts"
SCHEMA = json.loads((CONTRACTS / "schemas/f1.schema.json").read_text(encoding="utf-8"))
USER_A = "00000000-0000-4000-8000-000000000001"
USER_B = "00000000-0000-4000-8000-000000000002"
CONVERSATION = "00000000-0000-4000-8000-000000000003"
SUPABASE_URL = "https://supabase.example.test"
ALLOWED_ORIGIN = "https://studyflow.example.test"
IDEMPOTENCY_KEY = "sol-api-contract-0001"
TEST_SIGNING_SECRET = b"test-only-signing-material-32bytes!"


def validate_schema(value, name):
    """Chỉ phân giải các định nghĩa cục bộ đã duyệt, có kiểm tra UUID và date-time."""
    selected = {"$ref": f"#/$defs/{name}", "$defs": SCHEMA["$defs"]}
    Draft202012Validator(selected, format_checker=FormatChecker()).validate(value)


def fixture(name):
    return json.loads((CONTRACTS / "examples/valid" / name).read_text(encoding="utf-8"))


class HttpContractAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.create_app = staticmethod(importlib.import_module("backend.app.main").create_app)
            cls.Settings = importlib.import_module("backend.app.core.config").Settings
        except (ImportError, AttributeError) as exc:
            raise AssertionError(
                "Runtime boundary missing: implement backend.app.main.create_app(settings=None, "
                "*, rpc_transport=None, llm_transport=None, jwks_transport=None, clock=None) "
                "and backend.app.core.config.Settings. Acceptance tests must fail until it exists."
            ) from exc
        cls.now = datetime.now(timezone.utc).replace(microsecond=0)
        cls.private_key = ec.generate_private_key(ec.SECP256R1())
        cls.other_key = ec.generate_private_key(ec.SECP256R1())
        public_jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(cls.private_key.public_key()))
        public_jwk.update(kid="sol-ephemeral-key", use="sig", alg="ES256")
        cls.jwks = {"keys": [public_jwk]}

    def setUp(self):
        self.rpc_calls = []
        self.jwks_calls = []
        self.llm_calls = []
        self.rpc_override = None
        self.capture_lock = threading.Lock()
        settings = self.Settings(
            supabase_url=SUPABASE_URL,
            supabase_publishable_key="test-publishable-key",
            supabase_jwt_audience="authenticated",
            supabase_jwt_algorithm="ES256",
            deepseek_api_key="test-deepseek-key",
            deepseek_base_url="https://deepseek.example.test/v1",
            deepseek_model="test-model",
            rpc_signing_key_id="sol-test-only",
            rpc_signing_secret_base64=base64.b64encode(TEST_SIGNING_SECRET).decode(),
            cors_origins=[ALLOWED_ORIGIN],
        )
        self.settings = settings
        self.client_context = self.new_client()
        self.client = self.client_context.__enter__()

    def new_client(self):
        """Tạo ứng dụng khác, chỉ giữ trạng thái của các phụ thuộc giả bên ngoài."""
        app = self.create_app(
            self.settings,
            rpc_transport=httpx.MockTransport(self.rpc_response),
            llm_transport=httpx.MockTransport(self.llm_response),
            jwks_transport=httpx.MockTransport(self.jwks_response),
            clock=lambda: self.now,
        )
        return TestClient(app, raise_server_exceptions=True)

    def tearDown(self):
        self.client_context.__exit__(None, None, None)

    def token(self, user=USER_A, *, signing_key=None, kid="sol-ephemeral-key", **claims):
        payload = {
            "sub": user,
            "iss": f"{SUPABASE_URL}/auth/v1",
            "aud": "authenticated",
            "iat": int((self.now - timedelta(seconds=30)).timestamp()),
            "exp": int((self.now + timedelta(minutes=10)).timestamp()),
            "role": "authenticated",
        }
        payload.update(claims)
        return jwt.encode(payload, signing_key or self.private_key, algorithm="ES256", headers={"kid": kid})

    def headers(self, token=None, **extra):
        return {"Authorization": f"Bearer {token or self.token()}", **extra}

    def post_headers(self, **extra):
        return self.headers(**{"Idempotency-Key": IDEMPOTENCY_KEY, **extra})

    def message(self, **extra):
        return {"schema_version": "1.1", "conversation_id": CONVERSATION, "text": "Lên lịch giúp mình", **extra}

    def jwks_response(self, request):
        with self.capture_lock:
            self.jwks_calls.append(request)
        self.assertEqual(str(request.url), f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
        self.assertEqual(request.method, "GET")
        return httpx.Response(200, json=self.jwks)

    def llm_response(self, request):
        self.llm_calls.append(request)
        raise AssertionError("Rejected requests and GET reads must not call the LLM")

    def rpc_response(self, request):
        body = json.loads(request.content)
        with self.capture_lock:
            self.rpc_calls.append((request, body))
        self.assertEqual(request.method, "POST")
        self.assertEqual(set(body), {"p_request"})
        envelope = body["p_request"]
        if self.rpc_override is not None:
            return self.rpc_override(request, envelope)
        self.assertEqual(request.headers["Content-Profile"], "app_api")
        self.assertEqual(request.headers["apikey"], "test-publishable-key")
        self.assertEqual(request.headers["Content-Type"].split(";")[0], "application/json")
        bearer = request.headers["Authorization"]
        self.assertTrue(bearer.startswith("Bearer "))
        token = bearer.removeprefix("Bearer ")
        claims = jwt.decode(token, self.private_key.public_key(), algorithms=["ES256"],
                            audience="authenticated", issuer=f"{SUPABASE_URL}/auth/v1")
        user = claims["sub"]
        self.assertEqual(envelope["execution_context"]["trusted_context"]["principal"], {"user_id": user})
        operations = [entry["p_request"]["operation"] for _, entry in self.rpc_calls
                      if entry["p_request"]["request_id"] == envelope["request_id"]]
        if envelope["operation"] == "ensure_user_context":
            self.assertEqual(operations, ["ensure_user_context"], "At most one signed context bootstrap may precede this read")
            self.assert_signed_mutation(request, envelope, "ensure_user_context", token, user=user)
            self.assertEqual(envelope["arguments"], {})
            self.assertIsNone(envelope["execution_context"]["idempotency_key"])
            self.assertIsNone(envelope["execution_context"]["approval_action"])
            profile = fixture("User.json")
            profile["user_id"] = user
            result = {"schema_version": "1.1", "request_id": envelope["request_id"],
                      "outcome": "COMMITTED", "data": profile, "error": None, "warnings": []}
            validate_schema(result, "ensure_user_contextInternalResult")
            return httpx.Response(200, json=result)
        self.assertEqual(envelope["operation"], "search_tasks")
        self.assertIn(operations, (["search_tasks"], ["ensure_user_context", "search_tasks"]))
        result = fixture("search_tasks-result.json")
        result["request_id"] = envelope["request_id"]
        # Gán lại chủ sở hữu fixture cho mỗi phản hồi database mô phỏng.
        # Test kiểm tra riêng việc adapter lấy principal này từ JWT.
        for task in result["data"]["items"]:
            task["user_id"] = user
        validate_schema(result, "search_tasksResult")
        return httpx.Response(200, json=result)

    def assert_request_id(self, response):
        body = response.json()
        request_id = response.headers.get("X-Request-ID")
        self.assertIsInstance(request_id, str)
        self.assertTrue(request_id.strip())
        self.assertEqual(request_id, body["request_id"])
        return body

    def assert_error(self, response, status, code, *, post=False):
        if isinstance(status, tuple):
            self.assertIn(response.status_code, status, response.text)
        else:
            self.assertEqual(response.status_code, status, response.text)
        body = self.assert_request_id(response)
        validate_schema(body, "OrchestratorReply" if post else "ErrorResult")
        self.assertEqual(body["state" if post else "outcome"], "ERROR")
        self.assertEqual(body["error"]["code"], code)
        self.assertFalse(body["error"]["retryable"])
        self.assertEqual(self.rpc_calls, [], "Request must be rejected before any persistence RPC")
        self.assertEqual(self.llm_calls, [])
        return body

    def assert_task_rpc(self, index, token, user, expected_arguments):
        request, body = self.task_rpc_calls()[index]
        self.assertEqual(str(request.url), f"{SUPABASE_URL}/rest/v1/rpc/search_tasks")
        self.assertEqual(request.headers["Authorization"], f"Bearer {token}")
        self.assertEqual(request.headers["Content-Profile"], "app_api")
        self.assertEqual(request.headers["apikey"], "test-publishable-key")
        self.assertEqual(request.headers["Content-Type"].split(";")[0], "application/json")
        envelope = body["p_request"]
        validate_schema(envelope, "RpcRequest")
        self.assertEqual(envelope["arguments"], expected_arguments)
        context = envelope["execution_context"]
        self.assertEqual(context["trusted_context"]["principal"], {"user_id": user})
        self.assertEqual(context["trusted_context"]["request_id"], envelope["request_id"])
        UUID(context["trusted_context"]["message_id"])
        self.assertIsNone(context["conversation_id"])
        self.assertIsNone(context["idempotency_key"])
        self.assertIsNone(context["approval_action"])
        self.assertIsNone(context["action_reference"])
        self.assertIsNone(envelope["attestation"])
        exchange = [(req, item["p_request"]) for req, item in self.rpc_calls
                    if item["p_request"]["request_id"] == envelope["request_id"]]
        self.assertIn([item["operation"] for _, item in exchange],
                      (["search_tasks"], ["ensure_user_context", "search_tasks"]))
        for outbound, item in exchange:
            self.assertEqual(outbound.headers["Authorization"], f"Bearer {token}")
            self.assertEqual(item["execution_context"]["trusted_context"]["principal"], {"user_id": user})
            if item["operation"] == "ensure_user_context":
                self.assert_signed_mutation(outbound, item, "ensure_user_context", token, user=user)
        return envelope

    def task_rpc_calls(self):
        return [(request, body) for request, body in self.rpc_calls
                if body["p_request"]["operation"] == "search_tasks"]

    def test_missing_jwt_get_uses_error_result(self):
        spoof = "client-chosen-unauthenticated-trace"
        response = self.client.get("/v1/tasks", headers={"X-Request-ID": spoof})
        body = self.assert_error(response, 401, "UNAUTHENTICATED")
        self.assertNotEqual(body["request_id"], spoof)

    def test_missing_jwt_post_uses_orchestrator_reply(self):
        response = self.client.post("/v1/messages", json=self.message(), headers={"Idempotency-Key": IDEMPOTENCY_KEY})
        self.assert_error(response, 401, "UNAUTHENTICATED", post=True)

    def test_invalid_jwt_is_rejected(self):
        self.assert_error(self.client.get("/v1/tasks", headers=self.headers("not-a-jwt")), 401, "UNAUTHENTICATED")

    def test_expired_jwt_is_rejected(self):
        token = self.token(exp=int((self.now - timedelta(minutes=5)).timestamp()))
        self.assert_error(self.client.get("/v1/tasks", headers=self.headers(token)), 401, "UNAUTHENTICATED")

    def test_wrong_signature_is_rejected(self):
        token = self.token(signing_key=self.other_key)
        self.assert_error(self.client.get("/v1/tasks", headers=self.headers(token)), 401, "UNAUTHENTICATED")

    def test_wrong_issuer_audience_and_subject_are_rejected(self):
        for claims in ({"iss": "https://attacker.example/auth/v1"}, {"aud": "other"}, {"sub": ""}, {"sub": "not-a-uuid"}):
            with self.subTest(claims=claims):
                self.assert_error(self.client.get("/v1/tasks", headers=self.headers(self.token(**claims))), 401, "UNAUTHENTICATED")

    def test_wrong_algorithm_is_rejected(self):
        payload = jwt.decode(self.token(), options={"verify_signature": False})
        token = jwt.encode(payload, "test-only-HS256-key-32-characters-long", algorithm="HS256", headers={"kid": "sol-ephemeral-key"})
        self.assert_error(self.client.get("/v1/tasks", headers=self.headers(token)), 401, "UNAUTHENTICATED")

    def test_unknown_signing_key_is_rejected(self):
        self.assert_error(self.client.get("/v1/tasks", headers=self.headers(self.token(kid="unknown-key"))), 401, "UNAUTHENTICATED")

    def test_unknown_json_field_is_rejected(self):
        response = self.client.post("/v1/messages", json=self.message(unapproved_field="value"), headers=self.post_headers())
        self.assert_error(response, 422, "INVALID_PARAMETER", post=True)

    def test_client_cannot_supply_trusted_context(self):
        for field, value in (("user_id", USER_B), ("principal", {"user_id": USER_B}), ("requires_review", False), ("attestation", {})):
            with self.subTest(field=field):
                response = self.client.post("/v1/messages", json=self.message(**{field: value}), headers=self.post_headers())
                self.assert_error(response, 422, "INVALID_PARAMETER", post=True)

    def test_malformed_json_is_catalog_error(self):
        response = self.client.post("/v1/messages", content=b'{"schema_version":', headers=self.post_headers(**{"Content-Type": "application/json"}))
        self.assert_error(response, 400, "INVALID_PARAMETER", post=True)

    def test_unsupported_schema_version_is_catalog_error(self):
        response = self.client.post("/v1/messages", json=self.message(schema_version="0.0"), headers=self.post_headers())
        self.assert_error(response, 400, "INVALID_PARAMETER", post=True)

    def test_body_size_is_measured_in_utf8_bytes(self):
        # Văn bản 8.000 ký tự hợp lệ nhưng vượt 64 KiB khi tính cả khoảng trắng JSON.
        # Bộ đọc phải kiểm soát giới hạn transport trước khi kiểm tra nghiệp vụ.
        payload = json.dumps(self.message(text="ắ" * 8000), ensure_ascii=False).encode("utf-8")
        payload += b" " * (65537 - len(payload))
        self.assertEqual(len(payload), 65537)
        response = self.client.post("/v1/messages", content=payload, headers=self.post_headers(**{"Content-Type": "application/json"}))
        self.assert_error(response, 413, "PAYLOAD_TOO_LARGE", post=True)

    def test_message_text_limit_is_separate_from_body_limit(self):
        response = self.client.post("/v1/messages", json=self.message(text="a" * 8001), headers=self.post_headers())
        self.assert_error(response, 422, "INVALID_PARAMETER", post=True)

    def test_missing_and_invalid_idempotency_keys_are_rejected(self):
        for key in (None, "short", "a" * 129, "invalid key has spaces", "invalid/key/0001"):
            with self.subTest(key=key):
                headers = self.headers()
                if key is not None:
                    headers["Idempotency-Key"] = key
                response = self.client.post("/v1/messages", json=self.message(), headers=headers)
                self.assert_error(response, 400, "INVALID_PARAMETER", post=True)

    def test_raw_approval_operations_are_not_public_actions(self):
        for operation in ("confirm_task", "approve_study_plan", "reject_study_plan"):
            with self.subTest(operation=operation):
                command = {"schema_version": "1.1", "conversation_id": CONVERSATION, "operation": operation, "arguments": {}}
                response = self.client.post("/v1/actions", json=command, headers=self.post_headers())
                self.assert_error(response, 422, "UNSUPPORTED_OPERATION", post=True)

    def test_unknown_action_operation_is_rejected(self):
        command = {"schema_version": "1.1", "conversation_id": CONVERSATION, "operation": "delete_everything", "arguments": {}}
        self.assert_error(self.client.post("/v1/actions", json=command, headers=self.post_headers()), 422, "UNSUPPORTED_OPERATION", post=True)

    def test_task_get_materializes_contract_defaults(self):
        token = self.token()
        response = self.client.get("/v1/tasks", headers=self.headers(token))
        self.assertEqual(response.status_code, 200, response.text)
        validate_schema(self.assert_request_id(response), "search_tasksResult")
        self.assertEqual(len(self.task_rpc_calls()), 1)
        envelope = self.assert_task_rpc(0, token, USER_A, {"query": None, "status_filter": [], "page_size": 50, "cursor": None})
        self.assertEqual(envelope["request_id"], response.json()["request_id"])

    def test_task_get_passes_repeated_statuses_and_opaque_cursor(self):
        token = self.token()
        cursor = "opaque.cursor:V1_-do-not-decode"
        response = self.client.get("/v1/tasks", params=[("query", "OOP tiếng Việt"), ("status_filter", "TODO"), ("status_filter", "IN_PROGRESS"), ("page_size", "100"), ("cursor", cursor)], headers=self.headers(token))
        self.assertEqual(response.status_code, 200, response.text)
        validate_schema(self.assert_request_id(response), "search_tasksResult")
        self.assertEqual(len(self.task_rpc_calls()), 1)
        self.assert_task_rpc(0, token, USER_A, {"query": "OOP tiếng Việt", "status_filter": ["TODO", "IN_PROGRESS"], "page_size": 100, "cursor": cursor})

    def test_request_id_is_server_generated_and_unique(self):
        spoof = "client-chosen-trace-id"
        responses = [self.client.get("/v1/tasks", headers=self.headers(**{"X-Request-ID": spoof})) for _ in range(2)]
        ids = []
        for response in responses:
            self.assertEqual(response.status_code, 200, response.text)
            body = self.assert_request_id(response)
            self.assertNotEqual(body["request_id"], spoof)
            ids.append(body["request_id"])
        self.assertNotEqual(ids[0], ids[1])
        self.assertEqual([body["p_request"]["request_id"] for _, body in self.task_rpc_calls()], ids)

    def test_two_users_do_not_share_rpc_authorization(self):
        tokens = {USER_A: self.token(USER_A), USER_B: self.token(USER_B)}
        # Cho các yêu cầu chồng thời gian trên cùng ứng dụng/client để phát hiện header
        # Authorization dùng chung bị sửa, bên cạnh kiểm tra tái sử dụng tuần tự.
        users = [USER_A, USER_B, USER_A, USER_B]
        with ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(lambda user: self.client.get("/v1/tasks", headers=self.headers(tokens[user])), users))
        for user, response in zip(users, responses):
            self.assertEqual(response.status_code, 200, response.text)
            body = self.assert_request_id(response)
            validate_schema(body, "search_tasksResult")
            self.assertEqual({task["user_id"] for task in body["data"]["items"]}, {user})
        self.assertEqual(len(self.task_rpc_calls()), len(users))
        for index, (_, body) in enumerate(self.task_rpc_calls()):
            user = body["p_request"]["execution_context"]["trusted_context"]["principal"]["user_id"]
            self.assertIn(user, tokens)
            self.assert_task_rpc(index, tokens[user], user, {"query": None, "status_filter": [], "page_size": 50, "cursor": None})

    def test_invalid_task_query_is_catalog_error(self):
        # Contract quy định giới hạn và việc từ chối, nhưng chưa chốt lỗi ngữ nghĩa
        # của query được phân loại là HTTP 400 hay 422.
        for params in ({"page_size": "101"}, {"page_size": "0"}, {"cursor": ""}, {"cursor": "x" * 2049}, {"query": "a" * 501}, {"status_filter": "UNKNOWN"}):
            with self.subTest(params=params):
                self.assert_error(self.client.get("/v1/tasks", params=params, headers=self.headers()), (400, 422), "INVALID_PARAMETER")

    def test_unparseable_query_is_http_400(self):
        self.assert_error(self.client.get("/v1/tasks", params={"page_size": "nope"}, headers=self.headers()), 400, "INVALID_PARAMETER")

    def test_proposal_view_rejects_time_filter(self):
        params = {"view": "PROPOSAL", "proposal_id": CONVERSATION, "start_at": "2026-11-05T00:00:00Z", "end_at": "2026-11-06T00:00:00Z"}
        self.assert_error(self.client.get("/v1/plans", params=params, headers=self.headers()), 422, "INVALID_PARAMETER")

    def assert_signed_mutation(self, request, envelope, operation, token, *, user=USER_A):
        """Kiểm tra giao thức độc lập; đây không phải bộ xác minh database mô phỏng."""
        validate_schema(envelope, "RpcRequest")
        self.assertEqual(str(request.url), f"{SUPABASE_URL}/rest/v1/rpc/{operation}")
        self.assertEqual(request.headers["Authorization"], f"Bearer {token}")
        self.assertEqual(request.headers["Content-Profile"], "app_api")
        self.assertEqual(request.headers["apikey"], "test-publishable-key")
        self.assertEqual(request.headers["Content-Type"].split(";")[0], "application/json")
        self.assertEqual(envelope["operation"], operation)
        self.assertEqual(envelope["execution_context"]["trusted_context"]["principal"], {"user_id": user})
        attestation = envelope["attestation"]
        self.assertEqual(attestation["key_id"], "sol-test-only")
        encoded = attestation["payload"]
        self.assertNotIn("=", encoded, "Attestation base64url must be unpadded")
        decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        payload = json.loads(decoded)
        validate_schema(payload, "AttestationPayload")
        unsigned = {key: value for key, value in envelope.items() if key != "attestation"}
        canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        self.assertEqual(payload["request_digest"], hashlib.sha256(canonical).hexdigest())
        self.assertEqual(payload["key_id"], attestation["key_id"])
        self.assertEqual(payload["user_id"], user)
        self.assertEqual(payload["rpc"], operation)
        self.assertEqual(payload["request_id"], envelope["request_id"])
        issued = datetime.fromisoformat(payload["issued_at"].replace("Z", "+00:00"))
        expires = datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00"))
        self.assertEqual(expires - issued, timedelta(seconds=60))
        self.assertEqual(issued, self.now)
        expected_signature = hmac.new(TEST_SIGNING_SECRET, encoded.encode("ascii"), hashlib.sha256).hexdigest()
        self.assertEqual(attestation["signature"], expected_signature)

    def assert_completed_receipt_replay_after_restart(self, path, command, http_operation, stored_reply, stored_status):
        """Receipt có sẵn bên ngoài vẫn dùng được qua hai ứng dụng tạo mới hoàn toàn.

        Điều này chứng minh nhánh phát lại không trích xuất/thực thi nghiệp vụ lại;
        không chứng minh database thật đã lưu receipt hay trạng thái workflow.
        """
        token = self.token()
        fingerprints = []
        validate_schema(stored_reply, "OrchestratorReply")
        stamp = self.now.isoformat().replace("+00:00", "Z")

        def completed_receipt(request, envelope):
            self.assert_signed_mutation(request, envelope, "claim_api_receipt", token)
            args = envelope["arguments"]
            self.assertEqual(args["http_operation"], http_operation)
            self.assertEqual(args["idempotency_key"], IDEMPOTENCY_KEY)
            self.assertEqual(args["conversation_id"], CONVERSATION)
            fingerprints.append(args["request_fingerprint"])
            receipt = {
                "user_id": USER_A, "http_operation": http_operation,
                "idempotency_key": IDEMPOTENCY_KEY,
                "request_fingerprint": args["request_fingerprint"],
                "state": "COMPLETED", "lease_version": 3, "lease_until": None,
                "message_id": "00000000-0000-4000-8000-000000000003",
                "action_id": "00000000-0000-4000-8000-000000000006",
                "http_status": stored_status, "response": copy.deepcopy(stored_reply),
                "created_at": stamp, "updated_at": stamp,
            }
            validate_schema(receipt, "ApiReceipt")
            result = {"schema_version": "1.1", "request_id": envelope["request_id"],
                      "outcome": "COMMITTED", "data": receipt, "error": None, "warnings": []}
            validate_schema(result, "claim_api_receiptInternalResult")
            return httpx.Response(200, json=result)

        self.rpc_override = completed_receipt
        replies = []
        # Cả hai ứng dụng đều chưa xử lý thao tác gốc. Receipt là nguồn duy nhất
        # của phản hồi đã cấp, không phải bộ nhớ đệm trong tiến trình.
        for _ in range(2):
            with self.new_client() as restarted_client:
                response = restarted_client.post(path, json=command, headers=self.headers(token, **{"Idempotency-Key": IDEMPOTENCY_KEY}))
            self.assertEqual(response.status_code, stored_status, response.text)
            body = self.assert_request_id(response)
            validate_schema(body, "OrchestratorReply")
            self.assertEqual(response.headers.get("Idempotency-Replayed"), "true")
            expected = copy.deepcopy(stored_reply)
            expected["request_id"] = body["request_id"]
            if expected["result"] is not None:
                expected["result"]["request_id"] = body["request_id"]
            self.assertEqual(body, expected)
            replies.append(body)
        self.assertEqual(len(self.rpc_calls), 2, "Completed replay must make no additional workflow/domain RPC")
        self.assertEqual(fingerprints[0], fingerprints[1])
        self.assertNotEqual(replies[0]["request_id"], replies[1]["request_id"])
        self.assertEqual(self.llm_calls, [])

    def test_completed_preparation_receipt_replays_across_cold_apps(self):
        command = fixture("ActionRequest.json")
        command["conversation_id"] = CONVERSATION
        reply = fixture("OrchestratorReply.json")
        reply["result"]["data"]["pending_action"]["conversation_id"] = CONVERSATION
        reply["result"]["data"]["candidate"]["conversation_id"] = CONVERSATION
        self.assert_completed_receipt_replay_after_restart("/v1/actions", command, "prepare_action", reply, 200)

    def test_terminal_review_error_receipt_replays_before_stale_decision(self):
        issued = fixture("OrchestratorReply.json")
        decision = {"schema_version": "1.1", "conversation_id": CONVERSATION,
                    "decision": "APPROVE", "action_reference": issued["action_reference"]}
        error = {"code": "ACTION_REVIEW_REQUIRED", "message": "Review the current action before approval.",
                 "field": None, "details": {}, "retryable": False}
        reply = {"schema_version": "1.1", "request_id": "stored-terminal-request",
                 "state": "ERROR", "message": error["message"], "action_reference": None,
                 "questions": [], "result": None, "error": error}
        self.assert_completed_receipt_replay_after_restart("/v1/decisions", decision, "submit_decision", reply, 409)

    def test_first_preferences_get_bootstraps_through_signed_helper(self):
        token = self.token()
        profile = fixture("User.json")
        profile["user_id"] = USER_A

        def bootstrap(request, envelope):
            self.assert_signed_mutation(request, envelope, "ensure_user_context", token)
            self.assertEqual(envelope["arguments"], {})
            self.assertIsNone(envelope["execution_context"]["idempotency_key"])
            self.assertIsNone(envelope["execution_context"]["approval_action"])
            result = {"schema_version": "1.1", "request_id": envelope["request_id"],
                      "outcome": "COMMITTED", "data": profile, "error": None, "warnings": []}
            validate_schema(result, "ensure_user_contextInternalResult")
            return httpx.Response(200, json=result)

        self.rpc_override = bootstrap
        response = self.client.get("/v1/preferences", headers=self.headers(token))
        self.assertEqual(response.status_code, 200, response.text)
        body = self.assert_request_id(response)
        validate_schema(body, "PreferencesResult")
        self.assertEqual(body["data"], {"scheduling_policy": profile["scheduling_policy"],
                                       "schedule_revision": profile["schedule_revision"]})
        self.assertEqual(len(self.rpc_calls), 1)
        self.assertEqual(self.llm_calls, [])

    def test_cors_preflight_allows_documented_headers(self):
        response = self.client.options("/v1/messages", headers={"Origin": ALLOWED_ORIGIN, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,idempotency-key,content-type"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), ALLOWED_ORIGIN)
        allowed = {part.strip().lower() for part in response.headers["Access-Control-Allow-Headers"].split(",")}
        self.assertTrue({"authorization", "idempotency-key", "content-type"} <= allowed)
        self.assertEqual(self.rpc_calls, [])

    def test_cors_exposes_response_headers(self):
        response = self.client.get("/v1/tasks", headers=self.headers(**{"Origin": ALLOWED_ORIGIN}))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), ALLOWED_ORIGIN)
        exposed = {part.strip().lower() for part in response.headers.get("Access-Control-Expose-Headers", "").split(",")}
        self.assertTrue({"x-request-id", "idempotency-replayed", "retry-after"} <= exposed)

    def test_cors_does_not_allow_unlisted_origin(self):
        response = self.client.options("/v1/messages", headers={"Origin": "https://attacker.example.test", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,idempotency-key"})
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)
        self.assertEqual(self.rpc_calls, [])


if __name__ == "__main__":
    unittest.main()
