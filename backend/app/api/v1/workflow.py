"""Adapter HTTP cho kết quả điều phối action và receipt."""

from __future__ import annotations

from ...orchestrator.actions import ActionProcessor as WorkflowActions
from ...orchestrator.receipts import ReceiptProcessor
from ...orchestrator.workflow_shared import Terminal
from .http import STATUS, error_body, respond


def terminal_reply(error: Terminal, request_id: str) -> tuple[int, dict]:
    return STATUS.get(error.error["code"], 500), error_body(error.error, request_id, post=True)


class ActionProcessor:
    def __init__(self, api):
        self.actions = WorkflowActions(api.rpc, api.clock, api.extractor, api.settings.default_timezone)
        self.receipts = ReceiptProcessor(api.rpc, self.actions.dispatch, terminal_reply)

    def run(self, ctx, http_operation: str, key: str, fingerprint: str, body: dict, path: dict):
        result = self.receipts.run(ctx, http_operation, key, fingerprint, body, path)
        return respond(result.body, result.http_status, ctx.request_id, post=True, replayed=result.replayed)
