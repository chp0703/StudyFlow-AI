import unittest
from datetime import datetime, timezone

from backend.app.orchestrator.chat import ChatProcessor


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
        window = {"kind": "AVAILABILITY", "recurrence": "NONE", "start_at": "2026-11-19T09:00:00+07:00",
                  "end_at": "2026-11-19T11:00:00+07:00"}
        operation, arguments = self.operation("SET_AVAILABILITY", window)
        self.assertEqual(operation, "set_availability")
        self.assertEqual(arguments["window"]["timezone"], "Asia/Ho_Chi_Minh")
        self.assertIsNone(arguments["window"]["weekday"])


if __name__ == "__main__":
    unittest.main()
