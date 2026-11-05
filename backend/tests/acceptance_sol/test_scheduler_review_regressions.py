"""Independent follow-up regressions from the read-only WP1 review.

These cases were added after the initial 29 acceptance methods passed, before
the implementation owner received this round's fixes. Earlier assertions remain
unchanged.
"""

import unittest
from dataclasses import replace

from backend.app.f1.scheduler.constraints import validate_context, validate_generated_result
from backend.app.f1.scheduler.engine import generate_schedule
from backend.app.f1.scheduler.models import EngineBlock, Interval
from backend.app.f1.scheduler.normalization import normalize_time_windows
from backend.tests.acceptance_sol.test_normalization_contract import once, utc, weekly
from backend.tests.acceptance_sol.test_scheduler_contract import context, instant, task


class SchedulerReviewRegressionAcceptance(unittest.TestCase):
    def test_archived_window_is_excluded_before_dst_expansion_and_kind_check(self):
        archived = weekly(
            timezone="America/New_York", weekday=7,
            start_time="01:30", end_time="02:30",
            valid_from="2026-11-01", valid_until="2026-11-02",
            archived_at="2026-10-30T12:00:00Z",
        )
        busy = once(
            "2026-11-01T15:00:00Z", "2026-11-01T16:00:00Z",
            kind="BUSY", timezone="America/New_York",
            window_id="00000000-0000-0000-0000-000000000065",
        )
        for label, windows, expected in (
            ("archived only", [archived], ()),
            ("archived availability plus active busy", [busy, archived], (
                Interval(utc("2026-11-01T15:00:00Z"), utc("2026-11-01T16:00:00Z")),
            )),
        ):
            with self.subTest(case=label):
                result = normalize_time_windows(
                    windows,
                    start_at=utc("2026-11-01T00:00:00Z"),
                    end_at=utc("2026-11-02T00:00:00Z"),
                )
                self.assertEqual(result, expected)

    def test_invalid_task_priority_and_status_fail_closed_before_engine_use(self):
        for field, value in (("priority", "URGENT"), ("status", "INVALID_STATUS")):
            malformed = replace(context(), tasks=(replace(task(), **{field: value}),))
            with self.subTest(field=field, entrypoint="validate_context"):
                self.assertTrue(validate_context(malformed), "Invalid task enum was accepted")
            with self.subTest(field=field, entrypoint="generate_schedule"):
                result = generate_schedule(malformed)
                self.assertTrue(result.conflicts, "Engine must report the malformed task enum")
                self.assertEqual(result.generated_blocks, ())

    def test_unhashable_generated_task_id_returns_issue_instead_of_crashing(self):
        malformed = EngineBlock(task_id=[], start_at=instant(8), end_at=instant(9))
        issues = validate_generated_result(context(), (malformed,))
        self.assertTrue(issues, "Malformed generated task ID must be rejected before lookup")


if __name__ == "__main__":
    unittest.main()
