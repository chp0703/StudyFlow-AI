"""Phụ thuộc tối thiểu và lỗi dùng chung của workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Protocol

Clock = Callable[[], datetime]


class WorkflowError(Exception):
    def __init__(self, code: str, message: str, *, field: str | None = None,
                 retryable: bool = False, retry_after: int | None = None):
        super().__init__(code)
        self.code, self.message, self.field = code, message, field
        self.retryable, self.retry_after = retryable, retry_after

    def error(self) -> dict:
        return {"code": self.code, "message": self.message, "field": self.field,
                "details": {}, "retryable": self.retryable}


class ChatActions(Protocol):
    def step(self, ctx, operation: str, arguments: dict, **kwargs) -> dict: ...

    def workflow_context(self, ctx, conversation: str, action_id: str | None,
                         key: str, tolerate_absent: bool) -> dict: ...

    def build_action(self, ctx, **kwargs) -> dict: ...

    def awaiting_reply(self, ctx, presentation: dict, target: tuple) -> dict: ...

    def normalize_slots(self, raw: dict) -> dict: ...

    def questions(self, slots: dict) -> list[dict]: ...
