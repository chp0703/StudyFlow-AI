import unittest
from datetime import datetime, timezone

from backend.app.f1.planning.generate import default_availability, generate
from backend.tests.acceptance_sol.test_schedule_confirmation import COMMAND, FRESH_BLOCK, OWNER, TASK, availability, snapshot

NOW = datetime(2026, 11, 5, 7, tzinfo=timezone.utc)


def entries(snap):
    outcome = generate(snap, COMMAND, now=NOW, block_id_factory=lambda: FRESH_BLOCK)
    return outcome.proposal["payload"]["schedule_confirmation"]["entries"]


def without_windows(snap):
    return {**snap, "time_windows": []}


class DefaultAvailabilityTests(unittest.TestCase):
    def test_a_user_with_no_free_time_windows_still_gets_a_plan(self):
        self.assertEqual(len(entries(without_windows(snapshot()))), 1)

    def test_declared_availability_windows_are_ignored(self):
        # A legacy 1-hour window must not shrink the day: the implicit 06:00-22:00 applies.
        snap = snapshot(remaining=90, windows=[availability("2026-11-05T12:00:00Z", "2026-11-05T12:30:00Z")])
        self.assertEqual(sum(e["duration_minutes"] for e in entries(snap)), 90)

    def test_busy_time_is_still_avoided(self):
        # The task prefers 12:00Z, which is busy; start_at is the earliest start, so the block moves past the busy hour.
        busy = {**availability("2026-11-05T12:00:00Z", "2026-11-05T13:00:00Z"), "kind": "BUSY",
                "window_id": "00000000-0000-4000-8000-000000000041"}
        outcome = generate({**snapshot(), "time_windows": [busy]}, COMMAND, now=NOW, block_id_factory=lambda: FRESH_BLOCK)
        placed = outcome.proposal["payload"]["schedule_confirmation"]["entries"] if outcome.proposal else []
        self.assertTrue(placed)
        for entry in placed:
            self.assertFalse(entry["start_at"] < "2026-11-05T13:00:00" and entry["end_at"] > "2026-11-05T12:00:00", entry)

    def test_a_locked_block_outside_the_default_day_does_not_block_planning(self):
        # 22:00-22:30 local (15:00Z) was planned when users could declare any availability.
        legacy = {"block_id": "00000000-0000-4000-8000-000000000050", "user_id": OWNER, "task_id": TASK,
                  "start_at": "2026-11-05T15:00:00Z", "end_at": "2026-11-05T15:30:00Z", "is_locked": True}
        outcome = generate(snapshot(blocks=[legacy]), COMMAND, now=NOW, block_id_factory=lambda: FRESH_BLOCK)
        self.assertNotIn("RETAINED_OUTSIDE_AVAILABILITY", [c.code for c in outcome.conflicts])

    def test_every_weekday_gets_one_window_in_the_users_timezone(self):
        windows = default_availability({"user_id": "00000000-0000-4000-8000-000000000001", "timezone": "Asia/Ho_Chi_Minh"})
        self.assertEqual(sorted(w["weekday"] for w in windows), [1, 2, 3, 4, 5, 6, 7])
        self.assertEqual({(w["start_time"], w["end_time"], w["timezone"]) for w in windows},
                         {("06:00", "22:00", "Asia/Ho_Chi_Minh")})


if __name__ == "__main__":
    unittest.main()
