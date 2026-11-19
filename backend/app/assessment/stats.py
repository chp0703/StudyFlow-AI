"""Owner-scoped topic statistics from durable, submitted quiz responses."""

from __future__ import annotations

from math import isclose

from ..core import contract
from ..orchestrator.workflow_ports import WorkflowError


class TopicStatsOperations:
    def __init__(self, rpc):
        self.rpc = rpc

    def get(self, ctx, arguments: dict) -> dict:
        if not contract.is_valid("GetTopicStatsArguments", arguments):
            raise WorkflowError("INVALID_PARAMETER", "Tham số thống kê chủ đề không đúng contract.")
        result = self.rpc(ctx, "get_topic_stats", arguments)
        if not contract.is_valid("TopicStatsResult", result):
            raise WorkflowError("INTERNAL_ERROR", "Phản hồi thống kê chủ đề không đúng contract.")
        if result["outcome"] == "ERROR":
            return result
        data = result["data"]
        seen = set()
        valid = data["material_id"] == arguments["material_id"]
        for item in data["items"]:
            key = (item["material_id"], item["topic"])
            count, errors = item["valid_response_count"], item["error_count"]
            valid = valid and key not in seen and (
                arguments["material_id"] is None or item["material_id"] == arguments["material_id"]
            )
            seen.add(key)
            if count == 0:
                valid = valid and (
                    item["status"] == "INSUFFICIENT_DATA" and errors == 0
                    and item["error_rate"] is None and item["last_attempt_at"] is None
                )
            else:
                valid = valid and item["status"] == "AVAILABLE" and errors <= count and (
                    item["error_rate"] is not None and isclose(item["error_rate"], errors / count, abs_tol=1e-12)
                ) and item["last_attempt_at"] is not None
        if not valid:
            raise WorkflowError("INTERNAL_ERROR", "Thống kê chủ đề không nhất quán với dữ liệu hợp lệ.")
        return result
