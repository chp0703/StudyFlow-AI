"""Claim, phát lại, hoàn tất và giải phóng receipt lưu bền vững."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable

from ..clients.rpc import child_key
from .workflow_ports import RpcCall, WorkflowError
from .workflow_shared import Terminal


@dataclass(frozen=True)
class ReceiptResult:
    body: dict
    http_status: int
    replayed: bool = False


class ReceiptProcessor:
    def __init__(self, rpc: RpcCall, dispatch: Callable[..., tuple[int, dict]],
                 terminal_reply: Callable[[Terminal, str], tuple[int, dict]]):
        self.rpc, self.dispatch, self.terminal_reply = rpc, dispatch, terminal_reply

    def run(self, ctx, http_operation: str, key: str, fingerprint: str, body: dict, path: dict):
        conversation = body["conversation_id"]
        claim = self.rpc(ctx, "claim_api_receipt", {
            "http_operation": http_operation, "idempotency_key": key, "request_fingerprint": fingerprint,
            "conversation_id": conversation}, conversation_id=conversation, idempotency_key=child_key(key, "claim"))
        if claim.get("outcome") == "ERROR":
            error = claim["error"]
            raise WorkflowError(error["code"], error["message"], retryable=bool(error.get("retryable")), retry_after=2 if error["code"] == "SERVICE_UNAVAILABLE" else None)
        receipt = claim["data"]
        if receipt["state"] == "COMPLETED":
            return self.replay(ctx, receipt)
        binding = {"http_operation": http_operation, "idempotency_key": key,
                   "request_fingerprint": receipt["request_fingerprint"], "expected_lease_version": receipt["lease_version"]}
        try:
            status, answer = self.dispatch(ctx, receipt, http_operation, key, body, path)
        except Terminal as exc:
            status, answer = self.terminal_reply(exc, ctx.request_id)
        except Exception:
            self._release(ctx, binding, key, conversation)  # lỗi tạm thời hoặc ngoài dự kiến: cho phép lần gửi lại nhận lại lease
            raise
        done = self.rpc(ctx, "complete_api_receipt", {**binding, "http_status": status, "response": answer},
                            conversation_id=conversation, idempotency_key=child_key(key, "complete"))
        if done.get("outcome") == "ERROR":
            # Đã mất lease; thao tác nghiệp vụ hỗ trợ phát lại an toàn nên client chỉ cần thử lại.
            raise WorkflowError("SERVICE_UNAVAILABLE", "The request is being completed; retry shortly.", retryable=True, retry_after=2)
        return ReceiptResult(answer, status)

    def _release(self, ctx, binding: dict, key: str, conversation: str) -> None:
        try:
            self.rpc(ctx, "release_api_receipt", binding, conversation_id=conversation,
                         idempotency_key=child_key(key, "release"))
        except WorkflowError:
            pass  # lease tự hết hạn sau 120 giây

    @staticmethod
    def replay(ctx, receipt: dict):
        """Phản hồi đã lưu là nguồn duy nhất; không trích xuất hay thực thi lại."""
        stored = copy.deepcopy(receipt["response"])
        stored["request_id"] = ctx.request_id
        if stored.get("result") is not None:
            stored["result"]["request_id"] = ctx.request_id
        return ReceiptResult(stored, receipt["http_status"], replayed=True)
