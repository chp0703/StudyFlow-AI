"""Adapter HTTP cho vòng đời receipt và điều phối action."""

from __future__ import annotations

import copy

from ...clients.rpc import child_key
from ...orchestrator.actions import ActionProcessor as WorkflowActions
from ...orchestrator.workflow_shared import Terminal
from .http import STATUS, ApiError, error_body, respond


class ActionProcessor:
    def __init__(self, api):
        self.api = api
        self.actions = WorkflowActions(api.rpc, api.clock, api.extractor, api.settings.default_timezone)

    def run(self, ctx, http_operation: str, key: str, fingerprint: str, body: dict, path: dict):
        conversation = body["conversation_id"]
        claim = self.api.rpc(ctx, "claim_api_receipt", {
            "http_operation": http_operation, "idempotency_key": key, "request_fingerprint": fingerprint,
            "conversation_id": conversation}, conversation_id=conversation, idempotency_key=child_key(key, "claim"))
        if claim.get("outcome") == "ERROR":
            error = claim["error"]
            raise ApiError(error["code"], error["message"], status=STATUS.get(error["code"], 500),
                           retryable=bool(error.get("retryable")), retry_after=2 if error["code"] == "SERVICE_UNAVAILABLE" else None)
        receipt = claim["data"]
        if receipt["state"] == "COMPLETED":
            return self.replay(ctx, receipt)
        binding = {"http_operation": http_operation, "idempotency_key": key,
                   "request_fingerprint": receipt["request_fingerprint"], "expected_lease_version": receipt["lease_version"]}
        try:
            status, answer = self.actions.dispatch(ctx, receipt, http_operation, key, body, path)
        except Terminal as exc:
            status, answer = STATUS.get(exc.error["code"], 500), error_body(exc.error, ctx.request_id, post=True)
        except Exception:
            self._release(ctx, binding, key, conversation)  # lỗi tạm thời hoặc ngoài dự kiến: cho phép lần gửi lại nhận lại lease
            raise
        done = self.api.rpc(ctx, "complete_api_receipt", {**binding, "http_status": status, "response": answer},
                            conversation_id=conversation, idempotency_key=child_key(key, "complete"))
        if done.get("outcome") == "ERROR":
            # Đã mất lease; thao tác nghiệp vụ hỗ trợ phát lại an toàn nên client chỉ cần thử lại.
            raise ApiError("SERVICE_UNAVAILABLE", "The request is being completed; retry shortly.", retryable=True, retry_after=2)
        return respond(answer, status, ctx.request_id, post=True)

    def _release(self, ctx, binding: dict, key: str, conversation: str) -> None:
        try:
            self.api.rpc(ctx, "release_api_receipt", binding, conversation_id=conversation,
                         idempotency_key=child_key(key, "release"))
        except ApiError:
            pass  # lease tự hết hạn sau 120 giây

    @staticmethod
    def replay(ctx, receipt: dict):
        """Phản hồi đã lưu là nguồn duy nhất; không trích xuất hay thực thi lại."""
        stored = copy.deepcopy(receipt["response"])
        stored["request_id"] = ctx.request_id
        if stored.get("result") is not None:
            stored["result"]["request_id"] = ctx.request_id
        return respond(stored, receipt["http_status"], ctx.request_id, post=True, replayed=True)
