"""Unit tests requiring explicit start_at when creating or clarifying a task."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from backend.app.nlu.extractor import ScriptedExtractor
from backend.app.orchestrator.actions import ActionProcessor


class InMemoryWorkflowRpc:
    def __init__(self):
        self.calls = []
        self.queue = None
        self.active = None
        self.candidate = None
        self.candidate_version = 0
        self.action_version = 0

    def __call__(self, ctx, operation, arguments, **kwargs):
        self.calls.append(operation)
        if operation == "record_source_message":
            return {"outcome": "COMMITTED", "data": arguments["message"]}
        if operation == "get_workflow_continuation":
            msg_id = arguments.get("source_message_id")
            if self.queue is None or (msg_id is not None and self.queue["source_message_id"] != msg_id):
                return {"outcome": "READ", "data": {"continuation": None}}
            return {"outcome": "READ", "data": {"continuation": self.queue}}
        if operation == "initialize_workflow_continuation":
            self.queue = {
                "continuation_id": "cont-1",
                "conversation_id": kwargs["conversation_id"],
                "source_message_id": arguments["source_message_id"],
                "origin_idempotency_key": kwargs["idempotency_key"],
                "version": 1,
                "cursor": 0,
                "extraction": arguments["extraction"],
                "depends_on": arguments["depends_on"],
                "completed_steps": [],
                "awaiting_reference": None,
                "status": "ACTIVE",
            }
            return {"outcome": "COMMITTED", "data": self.queue}
        if operation == "checkpoint_workflow_continuation":
            step = arguments["outcome"]
            if step is not None:
                self.queue["completed_steps"].append(step)
            if arguments["transition"] == "ADVANCE":
                self.queue["cursor"] += 1
            self.queue["awaiting_reference"] = arguments["action_reference"]
            self.queue["version"] += 1
            return {"outcome": "COMMITTED", "data": self.queue}
        if operation == "get_workflow_context":
            return {"outcome": "READ", "data": {"active_action": self.active, "selected_action": self.active}}
        if operation == "create_task_candidate":
            self.candidate_version += 1
            self.candidate = {
                "candidate_id": "cand-1",
                "version": self.candidate_version,
                "slots": arguments["slots"],
                "field_sources": {},
            }
            return {"outcome": "DRAFTED", "data": self.candidate}
        if operation == "update_candidate_draft":
            self.candidate_version += 1
            self.candidate = {
                **self.candidate,
                "version": self.candidate_version,
                "slots": arguments["slots"],
                "field_sources": arguments["field_sources"],
            }
            return {"outcome": "DRAFTED", "data": self.candidate}
        if operation == "prepare_pending_action":
            self.action_version += 1
            presentation = dict(arguments["presentation"])
            pending = {**presentation["pending_action"], "version": self.action_version}
            presentation["pending_action"] = pending
            presentation["candidate"] = self.candidate
            self.active = {
                "pending_action": pending,
                "candidate": self.candidate,
                "proposal": None,
                "last_presentation": {"presentation": presentation},
            }
            return {"outcome": "DRAFTED", "data": presentation}
        raise AssertionError(f"Unexpected RPC call: {operation}")


class TaskStartAtRequirementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ctx = SimpleNamespace(request_id="req-1", user_id="user-1", message_id="msg-0")
        self.clock = lambda: datetime(2026, 11, 5, 1, 0, tzinfo=timezone.utc)

    def test_form_with_deadline_only_asks_for_start_at_without_writing(self) -> None:
        rpc = InMemoryWorkflowRpc()
        processor = ActionProcessor(rpc, self.clock, None, "Asia/Ho_Chi_Minh")
        status, reply = processor.prepare(
            self.ctx,
            {"message_id": "msg-1", "created_at": "2026-11-05T01:00:00Z", "action_id": "act-1"},
            "idem-prepare-key-1",
            {
                "conversation_id": "conv-1",
                "operation": "create_task_candidate",
                "arguments": {
                    "slots": {
                        "title": "Ôn xác suất",
                        "start_at": None,
                        "deadline_precision": "DATE",
                        "deadline_date": "2026-11-06",
                        "deadline_timezone": "Asia/Ho_Chi_Minh",
                        "estimated_minutes": 60,
                    }
                },
            },
        )
        self.assertEqual(200, status)
        self.assertEqual("NEEDS_CLARIFICATION", reply["state"])
        self.assertEqual(["start_at"], [q["field"] for q in reply["questions"]])
        self.assertEqual([], rpc.calls)

    def test_normalize_slots_does_not_copy_available_from_at_into_start_at(self) -> None:
        slots = ActionProcessor.normalize_slots({
            "title": "Ôn giải tích",
            "available_from_at": "2026-11-06T09:00:00+07:00",
            "deadline_precision": "DATE",
            "deadline_date": "2026-11-06",
            "estimated_minutes": 60,
        })
        self.assertNotIn("start_at", slots)
        self.assertEqual(["start_at"], [q["field"] for q in ActionProcessor.questions(slots)])

    def test_chat_deadline_only_clarification_keeps_asking_start_at_until_supplied(self) -> None:
        rpc = InMemoryWorkflowRpc()
        script = {
            "thêm bài OOP": {
                "intents": [{"intent": "CREATE_TASK", "slots": {"title": "Bài OOP"}, "raw_expressions": {}, "ambiguities": []}],
            },
            "hạn 5/3, 60 phút": {
                "intents": [{
                    "intent": "CREATE_TASK",
                    "slots": {
                        "deadline_precision": "DATE",
                        "deadline_date": "2027-03-05",
                        "deadline_timezone": "Asia/Ho_Chi_Minh",
                        "estimated_minutes": 60,
                    },
                    "raw_expressions": {},
                    "ambiguities": [],
                }],
            },
            "lúc 9 giờ sáng 5/3": {
                "intents": [{
                    "intent": "CREATE_TASK",
                    "slots": {"start_at": "2027-03-05T09:00:00+07:00"},
                    "raw_expressions": {},
                    "ambiguities": [],
                }],
            },
        }
        processor = ActionProcessor(rpc, self.clock, ScriptedExtractor(script), "Asia/Ho_Chi_Minh")

        def receipt(msg_id, stamp):
            return {
                "message_id": msg_id,
                "created_at": stamp,
                "request_fingerprint": f"fp-{msg_id}",
                "lease_version": 1,
            }

        _, ask1 = processor.chat.handle_message(
            self.ctx,
            receipt("00000000-0000-4000-8000-000000000101", "2026-11-05T01:00:00Z"),
            "chat-key-1",
            {"conversation_id": "conv-chat", "text": "thêm bài OOP"},
        )
        self.assertEqual("NEEDS_CLARIFICATION", ask1["state"])
        self.assertEqual({"start_at", "estimated_minutes"}, {q["field"] for q in ask1["questions"]})

        _, ask2 = processor.chat.handle_message(
            self.ctx,
            receipt("00000000-0000-4000-8000-000000000102", "2026-11-05T01:01:00Z"),
            "chat-key-2",
            {"conversation_id": "conv-chat", "text": "hạn 5/3, 60 phút"},
        )
        self.assertEqual("NEEDS_CLARIFICATION", ask2["state"])
        self.assertEqual(["start_at"], [q["field"] for q in ask2["questions"]])

        _, ready = processor.chat.handle_message(
            self.ctx,
            receipt("00000000-0000-4000-8000-000000000103", "2026-11-05T01:02:00Z"),
            "chat-key-3",
            {"conversation_id": "conv-chat", "text": "lúc 9 giờ sáng 5/3"},
        )
        self.assertEqual("AWAITING_APPROVAL", ready["state"])
        slots = ready["result"]["data"]["candidate"]["slots"]
        self.assertEqual("2027-03-05T09:00:00+07:00", slots["start_at"])
        self.assertEqual("2027-03-05", slots["deadline_date"])
        self.assertEqual(60, slots["estimated_minutes"])


if __name__ == "__main__":
    unittest.main()
