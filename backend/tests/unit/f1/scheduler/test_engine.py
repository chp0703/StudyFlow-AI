from __future__ import annotations

import unittest

from backend.app.f1.scheduler.engine import ALGORITHM_VERSION, generate_schedule
from backend.app.f1.scheduler.evaluation import evaluate_context
from backend.app.f1.scheduler.models import Coverage, Interval, Priority, SchedulingPolicy

from .helpers import block, context, dt, task


class SchedulingEngineTests(unittest.TestCase):
    def test_single_task_is_split_with_required_break(self) -> None:
        item = task(10, remaining=120, deadline=dt(4, 18))
        result = generate_schedule(context((item,)))

        self.assertEqual(Coverage.FULL, result.coverage)
        self.assertEqual(ALGORITHM_VERSION, result.algorithm_version)
        self.assertEqual(2, len(result.generated_blocks))
        self.assertEqual((dt(4, 8), dt(4, 9, 30)), (result.generated_blocks[0].start_at, result.generated_blocks[0].end_at))
        self.assertEqual(dt(4, 9, 40), result.generated_blocks[1].start_at)
        self.assertEqual(0, result.task_summaries[0].unallocated_minutes)
        self.assertFalse(result.conflicts)

    def test_earlier_deadline_wins_even_when_other_task_has_high_priority(self) -> None:
        early = task(20, remaining=60, deadline=dt(4, 10), priority=Priority.LOW)
        high = task(21, remaining=60, deadline=dt(4, 12), priority=Priority.HIGH)
        ctx = context(
            (high, early),
            available=(Interval(dt(4, 8), dt(4, 9)),),
            policy=SchedulingPolicy(25, 60, True, 240, 10),
        )
        result = generate_schedule(ctx)

        self.assertEqual(early.task_id, result.generated_blocks[0].task_id)
        by_id = {summary.task_id: summary for summary in result.task_summaries}
        self.assertEqual(0, by_id[early.task_id].unallocated_minutes)
        self.assertEqual(60, by_id[high.task_id].unallocated_minutes)

    def test_priority_breaks_equal_deadline_tie(self) -> None:
        low = task(30, remaining=60, deadline=dt(4, 12), priority=Priority.LOW)
        high = task(31, remaining=60, deadline=dt(4, 12), priority=Priority.HIGH)
        result = generate_schedule(context(
            (low, high),
            available=(Interval(dt(4, 8), dt(4, 9)),),
            policy=SchedulingPolicy(25, 60, True, 240, 10),
        ))
        self.assertEqual(high.task_id, result.generated_blocks[0].task_id)

    def test_busy_interval_is_subtracted_from_availability(self) -> None:
        item = task(40, remaining=120, deadline=dt(4, 14))
        result = generate_schedule(context(
            (item,),
            available=(Interval(dt(4, 8), dt(4, 12)),),
            busy=(Interval(dt(4, 9), dt(4, 10)),),
            policy=SchedulingPolicy(25, 60, True, 240, 10),
        ))
        self.assertEqual([(dt(4, 8), dt(4, 9)), (dt(4, 10), dt(4, 11))], [(b.start_at, b.end_at) for b in result.generated_blocks])

    def test_overlapping_availability_is_not_double_counted(self) -> None:
        item = task(50, remaining=180, deadline=dt(4, 13))
        result = generate_schedule(context(
            (item,),
            available=(Interval(dt(4, 8), dt(4, 11)), Interval(dt(4, 9), dt(4, 12))),
            policy=SchedulingPolicy(25, 90, True, 240, 10),
        ))
        total = sum(int((b.end_at - b.start_at).total_seconds() // 60) for b in result.generated_blocks)
        self.assertEqual(180, total)
        self.assertEqual(Coverage.FULL, result.coverage)

    def test_partial_result_reports_all_unallocated_minutes(self) -> None:
        item = task(60, remaining=120, deadline=dt(4, 18))
        result = generate_schedule(context((item,), available=(Interval(dt(4, 8), dt(4, 9)),)))
        self.assertEqual(Coverage.PARTIAL, result.coverage)
        self.assertEqual(60, result.task_summaries[0].newly_scheduled_minutes)
        self.assertEqual(60, result.task_summaries[0].unallocated_minutes)
        self.assertIn("INSUFFICIENT_CAPACITY", result.task_summaries[0].reason_codes)

    def test_no_availability_returns_none_not_fake_success(self) -> None:
        item = task(70, remaining=60)
        result = generate_schedule(context((item,), available=()))
        self.assertEqual(Coverage.NONE, result.coverage)
        self.assertFalse(result.generated_blocks)
        self.assertEqual(("NO_AVAILABILITY",), result.task_summaries[0].reason_codes)

    def test_short_final_block_respects_policy(self) -> None:
        item = task(80, remaining=100, deadline=dt(4, 14))
        allowed = generate_schedule(context(
            (item,), available=(Interval(dt(4, 8), dt(4, 12)),),
            policy=SchedulingPolicy(25, 90, True, 240, 10),
        ))
        denied = generate_schedule(context(
            (item,), available=(Interval(dt(4, 8), dt(4, 12)),),
            policy=SchedulingPolicy(25, 90, False, 240, 10),
        ))
        self.assertEqual([90, 10], [int((b.end_at - b.start_at).total_seconds() // 60) for b in allowed.generated_blocks])
        self.assertEqual(10, denied.task_summaries[0].unallocated_minutes)
        self.assertEqual(("BLOCK_TOO_SHORT",), denied.task_summaries[0].reason_codes)

    def test_daily_limit_counts_retained_and_new_blocks(self) -> None:
        item = task(90, remaining=240, deadline=dt(4, 20))
        kept = block(900, item.task_id, dt(4, 8), dt(4, 9))
        result = generate_schedule(context(
            (item,), now=dt(4, 7), available=(Interval(dt(4, 8), dt(4, 18)),), retained=(kept,),
            policy=SchedulingPolicy(25, 90, True, 120, 10),
        ))
        summary = result.task_summaries[0]
        self.assertEqual(60, summary.retained_future_minutes)
        self.assertEqual(60, summary.newly_scheduled_minutes)
        self.assertEqual(120, summary.unallocated_minutes)
        self.assertEqual(dt(4, 9, 10), result.generated_blocks[0].start_at)

    def test_retained_minutes_are_not_scheduled_twice(self) -> None:
        item = task(100, remaining=180, deadline=dt(4, 18))
        kept = block(1000, item.task_id, dt(4, 8), dt(4, 9))
        result = generate_schedule(context(
            (item,), available=(Interval(dt(4, 8), dt(4, 16)),), retained=(kept,)
        ))
        summary = result.task_summaries[0]
        self.assertEqual((60, 120, 0), (summary.retained_future_minutes, summary.newly_scheduled_minutes, summary.unallocated_minutes))

    def test_retained_minutes_over_remaining_is_hard_conflict(self) -> None:
        item = task(110, remaining=30, deadline=dt(4, 18))
        kept = block(1100, item.task_id, dt(4, 8), dt(4, 9))
        result = generate_schedule(context((item,), retained=(kept,)))
        self.assertIn("RETAINED_EXCEEDS_REMAINING", {issue.code for issue in result.conflicts})
        self.assertFalse(result.generated_blocks)

    def test_past_deadline_is_reported(self) -> None:
        item = task(120, remaining=30, deadline=dt(4, 6))
        result = generate_schedule(context((item,), now=dt(4, 7)))
        self.assertEqual(("DEADLINE_PASSED",), result.task_summaries[0].reason_codes)

    def test_same_input_is_deterministic(self) -> None:
        item = task(130, remaining=180)
        ctx = context((item,))
        first, metrics = evaluate_context(ctx, repetitions=5)
        self.assertTrue(metrics.deterministic)
        self.assertEqual(first, generate_schedule(ctx))
        self.assertEqual(0, metrics.hard_constraint_violations)

    def test_exact_start_at_is_preserved_in_generated_blocks(self) -> None:
        item = task(140, remaining=60, start_at=dt(4, 9, 30), deadline=dt(4, 10, 30), priority=Priority.HIGH)
        result = generate_schedule(context((item,), available=(Interval(dt(4, 8), dt(4, 12)),)))
        self.assertEqual(Coverage.FULL, result.coverage)
        self.assertEqual(1, len(result.generated_blocks))
        self.assertEqual((dt(4, 9, 30), dt(4, 10, 30)), (result.generated_blocks[0].start_at, result.generated_blocks[0].end_at))


if __name__ == "__main__":
    unittest.main()

