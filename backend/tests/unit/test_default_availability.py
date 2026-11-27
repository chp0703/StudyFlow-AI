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

    def test_explicit_late_night_start_at_schedules_on_requested_hour(self):
        # 23:00-24:00 local (16:00Z-17:00Z) is outside 06:00-22:00 but explicitly requested.
        snap = snapshot(remaining=60, windows=[])
        snap["tasks"][0]["start_at"] = "2026-11-05T16:00:00Z"
        snap["tasks"][0]["available_from_at"] = "2026-11-05T16:00:00Z"
        snap["tasks"][0]["deadline_at"] = "2026-11-05T17:00:00Z"
        cmd = {
            "generation_scope": {
                "start_at": "2026-11-05T07:00:00Z",
                "end_at": "2026-11-06T17:00:00Z",
                "selection_mode": "ALL_ELIGIBLE",
                "task_ids": [],
            },
            "policy_overrides": {},
        }
        outcome = generate(snap, cmd, now=NOW, block_id_factory=lambda: FRESH_BLOCK)
        self.assertEqual((), outcome.conflicts)
        self.assertIsNotNone(outcome.proposal)
        placed = outcome.proposal["payload"]["schedule_confirmation"]["entries"]
        self.assertEqual(len(placed), 1)
        self.assertEqual(placed[0]["start_at"], "2026-11-05T16:00:00.000000Z")
        self.assertEqual(placed[0]["end_at"], "2026-11-05T17:00:00.000000Z")

    def test_explicit_early_morning_start_at_schedules_before_06_00(self):
        # 05:00-06:00 local on 2026-11-06 (2026-11-05T22:00:00Z-23:00:00Z)
        snap = snapshot(remaining=60, windows=[])
        snap["tasks"][0]["start_at"] = "2026-11-05T22:00:00Z"
        snap["tasks"][0]["available_from_at"] = "2026-11-05T22:00:00Z"
        snap["tasks"][0]["deadline_at"] = "2026-11-06T12:00:00Z"
        cmd = {
            "generation_scope": {
                "start_at": "2026-11-05T17:00:00Z",
                "end_at": "2026-11-06T17:00:00Z",
                "selection_mode": "ALL_ELIGIBLE",
                "task_ids": [],
            },
            "policy_overrides": {},
        }
        outcome = generate(snap, cmd, now=NOW, block_id_factory=lambda: FRESH_BLOCK)
        self.assertEqual((), outcome.conflicts)
        self.assertIsNotNone(outcome.proposal)
        placed = outcome.proposal["payload"]["schedule_confirmation"]["entries"]
        self.assertEqual(len(placed), 1)
        self.assertEqual(placed[0]["start_at"], "2026-11-05T22:00:00.000000Z")
        self.assertEqual(placed[0]["end_at"], "2026-11-05T23:00:00.000000Z")

    def test_explicit_start_at_crossing_22_00_keeps_contiguous_blocks(self):
        # 21:30 local (14:30Z) for 120m -> 21:30-23:00 (90m) + 23:10-23:40 (30m)
        snap = snapshot(remaining=120, windows=[])
        snap["tasks"][0]["estimated_minutes"] = 120
        snap["tasks"][0]["start_at"] = "2026-11-05T14:30:00Z"
        snap["tasks"][0]["available_from_at"] = "2026-11-05T14:30:00Z"
        snap["tasks"][0]["deadline_at"] = "2026-11-05T17:00:00Z"
        cmd = {
            "generation_scope": {
                "start_at": "2026-11-05T07:00:00Z",
                "end_at": "2026-11-06T17:00:00Z",
                "selection_mode": "ALL_ELIGIBLE",
                "task_ids": [],
            },
            "policy_overrides": {},
        }
        outcome = generate(snap, cmd, now=NOW)
        self.assertEqual((), outcome.conflicts)
        self.assertIsNotNone(outcome.proposal)
        placed = outcome.proposal["payload"]["schedule_confirmation"]["entries"]
        self.assertEqual(len(placed), 2)
        self.assertEqual(placed[0]["start_at"], "2026-11-05T14:30:00.000000Z")
        self.assertEqual(placed[0]["end_at"], "2026-11-05T16:00:00.000000Z")
        self.assertEqual(placed[1]["start_at"], "2026-11-05T16:10:00.000000Z")
        self.assertEqual(placed[1]["end_at"], "2026-11-05T16:40:00.000000Z")

    def test_late_night_start_at_still_avoids_busy_intervals(self):
        # 23:00-24:00 local (16:00Z-17:00Z) requested, but 23:00-24:00 local is BUSY -> no overlap.
        busy = {**availability("2026-11-05T16:00:00Z", "2026-11-05T17:00:00Z"), "kind": "BUSY",
                "window_id": "00000000-0000-4000-8000-000000000042"}
        snap = snapshot(remaining=60, windows=[busy])
        snap["tasks"][0]["start_at"] = "2026-11-05T16:00:00Z"
        snap["tasks"][0]["available_from_at"] = "2026-11-05T16:00:00Z"
        snap["tasks"][0]["deadline_at"] = "2026-11-05T17:00:00Z"
        cmd = {
            "generation_scope": {
                "start_at": "2026-11-05T07:00:00Z",
                "end_at": "2026-11-05T17:00:00Z",
                "selection_mode": "ALL_ELIGIBLE",
                "task_ids": [],
            },
            "policy_overrides": {},
        }
        outcome = generate(snap, cmd, now=NOW, block_id_factory=lambda: FRESH_BLOCK)
        self.assertEqual((), outcome.conflicts)
        self.assertIsNone(outcome.proposal)
        self.assertEqual("NONE", outcome.report["coverage"])

    def test_untimed_task_stays_inside_06_00_to_22_00_default_day(self):
        # 2026-11-06 local starts at 2026-11-05T17:00:00Z; untimed task must land at 06:00 local (23:00Z), not 00:00 local.
        snap = snapshot(remaining=60, windows=[])
        snap["tasks"][0]["start_at"] = None
        snap["tasks"][0]["available_from_at"] = None
        snap["tasks"][0]["deadline_at"] = "2026-11-06T17:00:00Z"
        cmd = {
            "generation_scope": {
                "start_at": "2026-11-05T17:00:00Z",
                "end_at": "2026-11-06T17:00:00Z",
                "selection_mode": "ALL_ELIGIBLE",
                "task_ids": [],
            },
            "policy_overrides": {},
        }
        outcome = generate(snap, cmd, now=NOW, block_id_factory=lambda: FRESH_BLOCK)
        self.assertEqual((), outcome.conflicts)
        self.assertIsNotNone(outcome.proposal)
        placed = outcome.proposal["payload"]["schedule_confirmation"]["entries"]
        self.assertEqual(len(placed), 1)
        self.assertEqual(placed[0]["start_at"], "2026-11-05T23:00:00.000000Z")
        self.assertEqual(placed[0]["end_at"], "2026-11-06T00:00:00.000000Z")


if __name__ == "__main__":
    unittest.main()
