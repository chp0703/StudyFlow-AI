"""Evidence-backed B7 revision recommendations behind explicit user decisions."""

from __future__ import annotations

from uuid import UUID, uuid5

from ..clients.rpc import child_key
from ..core import contract
from ..orchestrator.workflow_ports import WorkflowError
from ..orchestrator.workflow_shared import Terminal, _ok, reply


class RevisionRecommendationOperations:
    def __init__(self, rpc):
        self.rpc = rpc

    def _call(self, ctx, operation: str, arguments: dict, **kwargs) -> dict:
        result = self.rpc(ctx, operation, arguments, **kwargs)
        if result.get("outcome") == "ERROR":
            error = result["error"]
            if error["code"] in ("SERVICE_UNAVAILABLE", "INTERNAL_ERROR", "UNAUTHENTICATED"):
                raise WorkflowError(error["code"], error["message"], retryable=True, retry_after=1)
            raise Terminal(error["code"], error["message"], error.get("field"))
        return result

    def create(self, ctx, receipt: dict, key: str, body: dict) -> tuple[int, dict]:
        conversation_id = str(UUID(body["conversation_id"]))
        material_id = str(UUID(body["material_id"]))
        recommendation_id = str(uuid5(UUID(ctx.user_id), "revision-recommendation:" + key))
        action_id = str(uuid5(UUID(ctx.user_id), "revision-recommendation-action:" + key))
        result = self._call(
            ctx,
            "create_revision_recommendation",
            {
                "recommendation_id": recommendation_id,
                "action_id": action_id,
                "conversation_id": conversation_id,
                "material_id": material_id,
                "topic": body["topic"],
                "suggested_minutes": body["suggested_minutes"],
                "priority": body["priority"],
            },
            conversation_id=conversation_id,
            idempotency_key=child_key(key, "create-recommendation"),
            message_id=receipt["message_id"],
        )
        if not contract.is_valid("RevisionRecommendationResult", result):
            raise WorkflowError("INTERNAL_ERROR", "Phản hồi gợi ý ôn tập từ database không đúng contract.")
        created = result["data"]
        if (created["recommendation_id"] != recommendation_id or created["pending_action_id"] != action_id
                or created["user_id"] != ctx.user_id or created["conversation_id"] != conversation_id
                or created["material_id"] != material_id or created["status"] != "PROPOSED"):
            raise WorkflowError("INTERNAL_ERROR", "Database trả về gợi ý ôn tập không khớp yêu cầu.")
        context = self._call(
            ctx,
            "get_workflow_context",
            {"conversation_id": conversation_id, "action_id": action_id, "message_id": None},
            conversation_id=conversation_id,
        )["data"]
        selected = context.get("selected_action")
        if selected is None or not selected.get("last_presentation"):
            raise WorkflowError("INTERNAL_ERROR", "Không thể tải đề xuất ôn tập vừa tạo.")
        live = selected.get("pending_action") or {}
        if live.get("state") != "AWAITING_APPROVAL":  # replayed key after a decision: presentation is a stale snapshot
            raise Terminal("STALE_ENTITY_VERSION", "Gợi ý ôn tập đã được xử lý.")
        presentation = selected["last_presentation"]["presentation"]
        action = presentation["pending_action"]
        reference = {
            "action_id": action["action_id"],
            "action_version": action["version"],
            "target_type": "PENDING_ACTION",
            "target_id": action["action_id"],
            "target_version": action["version"],
        }
        tool_result = _ok(ctx.request_id, "DRAFTED", {
            "recommendation": created, "presentation": presentation,
        })
        message = f'Đã tạo gợi ý ôn tập cho chủ đề "{body["topic"]}". Vui lòng xem bằng chứng và xác nhận.'
        return 200, reply(ctx.request_id, "AWAITING_APPROVAL", message, reference=reference, result=tool_result)
