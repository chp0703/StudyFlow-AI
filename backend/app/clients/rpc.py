"""Client gọi các hàm database app_api.* qua PostgREST RPC, có ký chứng thực từ backend."""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx

from ..core.config import Settings
from ..core.contract import canonical

CONTRACT_VERSION = "1.0.1"
SCHEMA_VERSION = "1.1"
# Thao tác chỉ đọc không mang chứng thực; database cũng phân loại chúng là thao tác đọc.
READ_OPERATIONS = frozenset({
    "search_tasks", "get_study_plan", "list_time_windows", "get_scheduling_context", "lookup_operation_result",
    "get_workflow_context", "get_workflow_continuation", "get_ingestion_source",
})


class RpcUnavailable(Exception):
    """Không kết nối được database hoặc nhận phản hồi không đúng contract."""

    def __init__(self, retryable: bool, unauthenticated: bool = False):
        super().__init__("rpc unavailable")
        self.retryable = retryable
        self.unauthenticated = unauthenticated


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def child_key(origin_key: str, step: str) -> str:
    """Khóa xác định cho bước nội bộ, giúp các lần gửi lại cùng yêu cầu HTTP dùng lại cùng khóa."""
    return hashlib.sha256(f"{origin_key}|{step}".encode()).hexdigest()[:48]


class RpcClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None, clock):
        self._settings = settings
        self._clock = clock
        self._http = httpx.Client(transport=transport, timeout=settings.rpc_timeout_seconds)

    def _attest(self, envelope: dict, user_id: str) -> dict:
        now = self._clock()
        payload = canonical({
            "v": 1, "key_id": self._settings.rpc_signing_key_id, "user_id": user_id, "rpc": envelope["operation"],
            "request_id": envelope["request_id"],
            "request_digest": hashlib.sha256(canonical({k: v for k, v in envelope.items() if k != "attestation"})).hexdigest(),
            "issued_at": iso(now), "expires_at": iso(now + timedelta(seconds=60)),
        })
        encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
        signature = hmac.new(self._settings.signing_secret, encoded.encode("ascii"), hashlib.sha256).hexdigest()
        return {"key_id": self._settings.rpc_signing_key_id, "payload": encoded, "signature": signature}

    def call(self, operation: str, arguments: dict, *, token: str, user_id: str, request_id: str,
             conversation_id: str | None = None, idempotency_key: str | None = None,
             approval_action: dict | None = None, action_reference: dict | None = None,
             message_id: str | None = None) -> dict:
        """Gọi một RPC bằng JWT của chính người gọi. Trả kết quả theo contract, bao gồm ErrorResult."""
        envelope = {
            "contract_version": CONTRACT_VERSION, "schema_version": SCHEMA_VERSION, "request_id": request_id,
            "operation": operation, "arguments": arguments, "attestation": None,
            "execution_context": {
                "conversation_id": conversation_id, "idempotency_key": idempotency_key,
                "approval_action": approval_action, "action_reference": action_reference,
                "trusted_context": {
                    "request_id": request_id, "message_id": message_id or str(uuid4()),
                    "principal": {"user_id": user_id}, "timezone": self._settings.default_timezone,
                    "locale": self._settings.default_locale, "received_at": iso(self._clock()),
                },
            },
        }
        if operation not in READ_OPERATIONS:
            envelope["attestation"] = self._attest(envelope, user_id)
        try:
            response = self._http.post(
                f"{self._settings.supabase_url.rstrip('/')}/rest/v1/rpc/{operation}", json={"p_request": envelope},
                headers={"Authorization": f"Bearer {token}", "apikey": self._settings.supabase_publishable_key,
                         "Content-Profile": "app_api", "Content-Type": "application/json"})
        except httpx.HTTPError:
            raise RpcUnavailable(retryable=True) from None
        if response.status_code in (401, 403):
            raise RpcUnavailable(retryable=False, unauthenticated=True)
        if response.status_code != 200:
            raise RpcUnavailable(retryable=response.status_code >= 500)
        try:
            result = response.json()
        except ValueError:
            raise RpcUnavailable(retryable=False) from None
        if not isinstance(result, dict) or "outcome" not in result:
            raise RpcUnavailable(retryable=False)
        return result
