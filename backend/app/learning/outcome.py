"""UI decision on a pending save_session_outcome action (F3 M4). Reached only through POST /v1/decisions."""

from __future__ import annotations

from uuid import uuid4

from ..clients.rpc import child_key, iso
from ..core import contract
from ..orchestrator.workflow_ports import WorkflowError
from ..orchestrator.workflow_shared import Terminal, reply

_TRANSIENT = ("SERVICE_UNAVAILABLE", "INTERNAL_ERROR", "UNAUTHENTICATED")
_DONE = {"APPROVE": "Đã lưu kết quả phiên học.", "REJECT": "Đã bỏ bản tóm tắt, phiên học tiếp tục."}


class LearningOutcomeOperations:
    def __init__(self, rpc, clock):
        self.rpc = rpc
        self.clock = clock

    def decide(self, ctx, receipt, key, body):
        ref, decision = body["action_reference"], body["decision"]
        approval = {
            "approval_action_id": str(uuid4()), "user_id": ctx.user_id, "target_type": "PENDING_ACTION",
            "target_id": ref["action_id"], "target_version": ref["action_version"], "decision": decision,
            "source": "UI", "source_message_id": None, "created_at": iso(self.clock()),
        }
        result = self.rpc(
            ctx, "decide_learning_session_outcome", {"decision": decision},
            conversation_id=body["conversation_id"], idempotency_key=child_key(key, "learning-outcome"),
            approval_action=approval, action_reference=ref, message_id=receipt["message_id"],
        )
        if result.get("outcome") == "ERROR":
            error = result["error"]
            if error["code"] in _TRANSIENT:
                raise WorkflowError(error["code"], error["message"], retryable=True, retry_after=1)
            raise Terminal(error["code"], error["message"], error.get("field"))
        if not contract.is_valid("DecideLearningSessionOutcomeResult", result):
            raise WorkflowError("INTERNAL_ERROR", "Invalid DecideLearningSessionOutcomeResult response")
        payload = reply(ctx.request_id, "SUCCEEDED", _DONE[decision], result={**result, "request_id": ctx.request_id})
        if not contract.is_valid("DailyLearningOutcomeDecisionResult", payload):
            raise WorkflowError("INTERNAL_ERROR", "Invalid DailyLearningOutcomeDecisionResult payload")
        return 200, payload
