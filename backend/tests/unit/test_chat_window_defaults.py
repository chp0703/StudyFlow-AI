import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from backend.app.orchestrator.chat import ChatProcessor
from backend.app.orchestrator.actions import ActionProcessor
from backend.app.orchestrator.workflow_shared import Terminal


class WindowDefaultsTests(unittest.TestCase):
    def operation(self, kind, window):
        chat = ChatProcessor(None, None, clock=lambda: datetime(2026, 11, 18, tzinfo=timezone.utc))
        return chat.operation_for(None, kind, {"change_type": "ADD", "window": window})

    def test_weekly_window_with_only_the_spoken_fields_becomes_a_valid_command(self):
        window = {"kind": "BUSY", "recurrence": "WEEKLY", "timezone": "Asia/Ho_Chi_Minh", "weekday": 5,
                  "start_time": "07:00", "end_time": "09:00", "valid_from": "2026-11-18"}
        operation, arguments = self.operation("SET_BUSY_INTERVAL", window)
        self.assertEqual(operation, "set_busy_interval")
        self.assertIsNotNone(arguments)
        self.assertEqual((arguments["window"]["label"], arguments["window"]["valid_until"]), (None, None))

    def test_one_off_window_gets_the_missing_weekly_keys_as_null(self):
        window = {"kind": "BUSY", "recurrence": "NONE", "start_at": "2026-11-19T09:00:00+07:00",
                  "end_at": "2026-11-19T11:00:00+07:00"}
        operation, arguments = self.operation("SET_BUSY_INTERVAL", window)
        self.assertEqual(operation, "set_busy_interval")
        self.assertEqual(arguments["window"]["timezone"], "Asia/Ho_Chi_Minh")
        self.assertIsNone(arguments["window"]["weekday"])

    def test_plan_scope_aligns_model_seconds_and_starts_after_now(self):
        chat = ChatProcessor(None, None, clock=lambda: datetime(2026, 11, 18, 8, 10, 29, tzinfo=timezone.utc))
        operation, arguments = chat.operation_for(None, "GENERATE_STUDY_PLAN", {
            "start_at": "2026-11-18T08:10:29Z", "end_at": "2026-11-25T08:10:29Z"})
        self.assertEqual("generate_study_plan", operation)
        self.assertEqual("2026-11-18T08:11:00.000000Z", arguments["generation_scope"]["start_at"])
        self.assertEqual("2026-11-25T08:10:00.000000Z", arguments["generation_scope"]["end_at"])

    def test_reversed_windows_never_get_approval_cards(self):
        for window in (
            {"kind": "BUSY", "recurrence": "NONE", "start_at": "2026-11-19T12:00:00+07:00", "end_at": "2026-11-19T08:00:00+07:00"},
            {"kind": "BUSY", "recurrence": "WEEKLY", "weekday": 4, "start_time": "12:00", "end_time": "08:00"},
        ):
            with self.subTest(window=window), self.assertRaises(Terminal) as caught:
                self.operation("SET_BUSY_INTERVAL", window)
            self.assertEqual("Giờ kết thúc phải sau giờ bắt đầu.", caught.exception.error["message"])

    def test_structured_actions_reject_reversed_windows_before_creating_drafts(self):
        for window in (
            {"recurrence": "NONE", "start_at": "2026-11-19T12:00:00+07:00", "end_at": "2026-11-19T08:00:00+07:00"},
            {"recurrence": "WEEKLY", "start_time": "12:00", "end_time": "08:00"},
        ):
            with self.subTest(window=window), self.assertRaises(Terminal) as caught:
                ActionProcessor.validate_window_order(window)
            self.assertEqual("Giờ kết thúc phải sau giờ bắt đầu.", caught.exception.error["message"])

    def test_compose_deduplicates_successful_steps(self):
        chat = ChatProcessor(None, None, clock=lambda: datetime(2026, 11, 18, tzinfo=timezone.utc))
        step = {"disposition": "SUCCEEDED", "operation": "set_busy_interval", "result": {"data": {}}, "error": None}
        result = chat.compose(SimpleNamespace(request_id="request"),
                              {"completed_steps": [step] * 5, "awaiting_reference": None}, "conversation")
        self.assertEqual("Đã cập nhật giờ bận.", result["message"])

    def test_normalize_slots_rotates_default_color_when_omitted(self):
        first = ActionProcessor.normalize_slots({"title": "bt toán", "start_at": "2026-11-19T09:00:00+07:00", "estimated_minutes": 60})
        second = ActionProcessor.normalize_slots({"title": "đọc lý thuyết xác suất", "start_at": "2026-11-19T14:00:00+07:00", "estimated_minutes": 60})
        self.assertRegex(first["color"], r"^#[0-9A-F]{6}$")
        self.assertRegex(second["color"], r"^#[0-9A-F]{6}$")
        self.assertNotEqual(first["color"], second["color"])

    def test_busy_query_reads_time_windows_when_plan_is_empty(self):
        class FakeProc:
            def step(self, ctx, operation, arguments, **kwargs):
                self.last_op = operation
                return {"data": {"items": [{
                    "kind": "BUSY", "label": "Học trên lớp", "recurrence": "NONE",
                    "start_at": "2026-11-19T01:00:00Z", "end_at": "2026-11-19T03:00:00Z", "archived_at": None,
                }]}}

        chat = ChatProcessor(FakeProc(), None, clock=lambda: datetime(2026, 11, 18, tzinfo=timezone.utc))
        cont = {
            "source_message_id": "msg-1",
            "extraction": {"intents": [{"intent": "GET_STUDY_PLAN", "slots": {
                "view": "CURRENT", "start_at": "2026-11-19T08:00:00+07:00", "end_at": "2026-11-19T09:00:00+07:00",
            }}]},
            "completed_steps": [{"intent_index": 0, "disposition": "SUCCEEDED", "operation": "get_study_plan",
                                 "result": {"data": {"plan": None}}, "error": None}],
            "awaiting_reference": None,
        }
        result = chat.compose(SimpleNamespace(request_id="req-1"), cont, "conv-1")
        self.assertIn("Bạn có lịch bận: Học trên lớp (08:00–10:00).", result["message"])


if __name__ == "__main__":
    unittest.main()
