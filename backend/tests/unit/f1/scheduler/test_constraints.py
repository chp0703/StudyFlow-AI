from __future__ import annotations

import unittest

from backend.app.f1.scheduler.constraints import validate_generated_result
from backend.app.f1.scheduler.intervals import overlaps
from backend.app.f1.scheduler.models import EngineBlock, GenerationScope, Interval, SchedulingPolicy, SelectionMode

from .helpers import context, dt, task


class ConstraintTests(unittest.TestCase):
    def test_half_open_touching_intervals_do_not_overlap(self) -> None:
        self.assertFalse(overlaps(Interval(dt(4, 8), dt(4, 9)), Interval(dt(4, 9), dt(4, 10))))

    def test_generated_block_after_deadline_is_rejected(self) -> None:
        item = task(301, remaining=60, deadline=dt(4, 9))
        ctx = context((item,), available=(Interval(dt(4, 8), dt(4, 12)),))
        issues = validate_generated_result(ctx, (EngineBlock(item.task_id, dt(4, 9), dt(4, 10)),))
        self.assertIn("GENERATED_AFTER_DEADLINE", {issue.code for issue in issues})

    def test_generated_overlap_and_break_violation_are_rejected(self) -> None:
        item = task(302, remaining=180)
        ctx = context(
            (item,),
            policy=SchedulingPolicy(25, 90, True, 240, 10),
        )
        issues = validate_generated_result(ctx, (
            EngineBlock(item.task_id, dt(4, 8), dt(4, 9)),
            EngineBlock(item.task_id, dt(4, 8, 50), dt(4, 9, 50)),
        ))
        self.assertIn("STUDY_BLOCK_OVERLAP", {issue.code for issue in issues})

    def test_invalid_policy_is_reported_as_context_conflict(self) -> None:
        item = task(303, remaining=60)
        from backend.app.f1.scheduler.engine import generate_schedule
        result = generate_schedule(context(
            (item,), policy=SchedulingPolicy(90, 25, True, 240, 10)
        ))
        self.assertIn("INVALID_POLICY", {issue.code for issue in result.conflicts})
        self.assertFalse(result.generated_blocks)

    def test_scope_task_ids_must_match_resolved_selection(self) -> None:
        item = task(304, remaining=60)
        ctx = context((item,))
        from dataclasses import replace
        from backend.app.f1.scheduler.engine import generate_schedule
        broken = replace(ctx, generation_scope=GenerationScope(
            ctx.generation_scope.start_at,
            ctx.generation_scope.end_at,
            SelectionMode.SELECTED_TASKS,
            (),
        ))
        result = generate_schedule(broken)
        self.assertIn("INVALID_GENERATION_SCOPE", {issue.code for issue in result.conflicts})

    def test_numeric_priority_color_start_at_and_vietnam_timezone_validation(self) -> None:
        from dataclasses import replace
        from backend.app.f1.scheduler.constraints import validate_context

        base = task(305, remaining=60, start_at=dt(4, 9), deadline=dt(4, 12), color="#596CF0", description="Note")
        self.assertEqual((), validate_context(context((base,))))

        for bad_priority in ("HIGH", 0.2, True, False):
            with self.subTest(priority=bad_priority):
                issues = validate_context(context((replace(base, priority=bad_priority),)))
                self.assertIn("INVALID_TASK", {issue.code for issue in issues})

        for bad_color in ("red", "#12345", "#GGGGGG", ""):
            with self.subTest(color=bad_color):
                issues = validate_context(context((replace(base, color=bad_color),)))
                self.assertIn("INVALID_TASK", {issue.code for issue in issues})

        late_start = replace(base, start_at=dt(4, 13))
        self.assertIn("INVALID_TASK", {issue.code for issue in validate_context(context((late_start,)))})

        non_vn_ctx = replace(context((base,)), timezone="UTC")
        self.assertIn("INVALID_TIMEZONE", {issue.code for issue in validate_context(non_vn_ctx)})

        non_vn_task = replace(base, deadline_timezone="America/New_York")
        self.assertIn("INVALID_TIMEZONE", {issue.code for issue in validate_context(context((non_vn_task,)))})

        early_block = EngineBlock(base.task_id, dt(4, 8), dt(4, 9))
        self.assertIn("GENERATED_BEFORE_AVAILABLE", {issue.code for issue in validate_generated_result(context((base,)), (early_block,))})


if __name__ == "__main__":
    unittest.main()

