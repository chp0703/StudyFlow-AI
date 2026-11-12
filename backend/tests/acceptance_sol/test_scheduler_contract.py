"""Test hồi quy hành vi theo Planner schema mục 6/7 và contract mục 4.2.

Các test dùng giao diện planner/validator công khai và kết quả kỳ vọng cụ thể.
Chủ động không import hàm hỗ trợ test của nhóm triển khai.
"""

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID

from backend.app.f1.scheduler.constraints import validate_generated_result
from backend.app.f1.scheduler.engine import generate_schedule
from backend.app.f1.scheduler.models import (
    AcademicTask, Coverage, EngineBlock, GenerationScope, Interval,
    SchedulingContext, SchedulingPolicy, SelectionMode, StudyBlock,
)
from backend.app.f1.scheduler.replanning import materialize_snapshot
from backend.app.f1.scheduler.service import PlanningService


OWNER = UUID(int=1)
TASK = UUID(int=2)
OTHER_TASK = UUID(int=3)
BLOCK_A = UUID(int=10)
BLOCK_B = UUID(int=11)
FRESH_BLOCK = UUID(int=12)


def instant(hour, minute=0, second=0, *, day=5):
    return datetime(2026, 11, day, hour, minute, second, tzinfo=timezone.utc)


def task(task_id=TASK, minutes=60):
    return AcademicTask(
        task_id=task_id, user_id=OWNER, title="Contract fixture",
        deadline_at=instant(23), estimated_minutes=minutes,
        remaining_minutes=minutes,
    )


def context(minutes=60):
    return SchedulingContext(
        now=instant(7), timezone="UTC",
        generation_scope=GenerationScope(
            instant(8), instant(18), SelectionMode.ALL_ELIGIBLE,
        ),
        selected_task_ids=(TASK,), tasks=(task(minutes=minutes),),
        available_intervals=(Interval(instant(8), instant(18)),),
    )


class SchedulingContractAcceptance(unittest.TestCase):
    def test_identical_partial_replacement_keeps_partial_without_duplicate_proposal(self):
        """Coverage phản ánh nhu cầu còn lại ngay cả khi phần chênh lệch snapshot rỗng."""
        original = StudyBlock(BLOCK_A, OWNER, TASK, instant(8), instant(9))
        ctx = replace(
            context(minutes=120),
            available_intervals=(Interval(instant(8), instant(9)),),
            replaceable_blocks=(original,),
        )
        outcome = PlanningService(lambda: FRESH_BLOCK).generate_proposal_payload(
            ctx, user_id=OWNER,
        )
        self.assertFalse(outcome.scheduling_result.conflicts)
        self.assertEqual(outcome.scheduling_result.coverage, Coverage.PARTIAL)
        summary, = outcome.scheduling_result.task_summaries
        self.assertEqual(summary.unallocated_minutes, 60)
        self.assertEqual(summary.newly_scheduled_minutes, 60)
        self.assertEqual(summary.remaining_minutes, 120)
        self.assertIsNone(outcome.proposal_payload)

    def test_materialization_preserves_exact_match_before_pairing_moved_blocks(self):
        """Cùng một task: xóa block 08–09 không được lấy ID logic của block 10–11."""
        old_a = StudyBlock(BLOCK_A, OWNER, TASK, instant(8), instant(9))
        old_b = StudyBlock(BLOCK_B, OWNER, TASK, instant(10), instant(11))
        snapshot, diff = materialize_snapshot(
            retained_blocks=(), replaceable_blocks=(old_a, old_b),
            generated_blocks=(EngineBlock(TASK, instant(10), instant(11)),),
            user_id=OWNER, block_id_factory=lambda: FRESH_BLOCK,
        )
        self.assertEqual(len(snapshot), 1)
        self.assertEqual(snapshot[0].block_id, BLOCK_B)
        self.assertEqual((snapshot[0].start_at, snapshot[0].end_at),
                         (instant(10), instant(11)))
        self.assertEqual(diff.unchanged, (BLOCK_B,))
        self.assertEqual(diff.removed, (BLOCK_A,))
        self.assertEqual(diff.moved, ())
        self.assertEqual(diff.added, ())

    def test_result_validator_rejects_zero_duration_even_with_short_final_enabled(self):
        ctx = replace(context(), tasks=(task(minutes=60), task(OTHER_TASK, 60)))
        # Kết quả 0 phút không được chấp nhận là phần thời lượng cuối cùng của task.
        ctx = replace(ctx, retained_blocks=(
            StudyBlock(BLOCK_B, OWNER, TASK, instant(10), instant(11), True),
        ))
        issues = validate_generated_result(ctx, (EngineBlock(TASK, instant(8), instant(8)),))
        self.assertTrue(issues, "Generated zero-duration block was accepted")

    def test_result_validator_rejects_negative_duration(self):
        # Tránh lỗi buổi cuối quá ngắn vô tình che mất khoảng thời gian sai cấu trúc.
        ctx = replace(context(), policy=SchedulingPolicy(min_block_minutes=1))
        issues = validate_generated_result(ctx, (EngineBlock(TASK, instant(9), instant(8)),))
        self.assertTrue(issues, "Generated negative-duration block was accepted")

    def test_result_validator_rejects_subminute_start(self):
        issues = validate_generated_result(context(), (
            EngineBlock(TASK, instant(8, second=1), instant(9)),
        ))
        self.assertTrue(issues, "Generated timestamp with seconds was accepted")

    def test_result_validator_rejects_subminute_end(self):
        issues = validate_generated_result(context(), (
            EngineBlock(TASK, instant(8), instant(9, second=1)),
        ))
        self.assertTrue(issues, "Generated timestamp with seconds was accepted")

    def test_result_validator_handles_naive_datetime_as_validation_failure(self):
        # Validator công khai phải trả danh sách lỗi; TypeError là sự cố không được kiểm soát.
        issues = validate_generated_result(context(), (
            EngineBlock(TASK, instant(8).replace(tzinfo=None),
                        instant(9).replace(tzinfo=None)),
        ))
        self.assertTrue(issues, "Naive generated timestamps must fail closed")

    def test_result_validator_checks_retained_busy_conflicts_in_full_snapshot(self):
        ctx = replace(
            context(), tasks=(task(), task(OTHER_TASK)),
            retained_blocks=(StudyBlock(
                BLOCK_B, OWNER, OTHER_TASK, instant(10), instant(11), True,
            ),),
            busy_intervals=(Interval(instant(10, 30), instant(10, 45)),),
        )
        issues = validate_generated_result(ctx, (EngineBlock(TASK, instant(8), instant(9)),))
        self.assertTrue(issues, "Validator accepted a full snapshot with retained BUSY conflict")

    def test_history_over_current_daily_limit_does_not_block_future_planning(self):
        """Lịch sử 300 phút của ngày trước phải được giữ khi policy hôm nay giới hạn 240 phút."""
        historical = StudyBlock(
            BLOCK_B, OWNER, OTHER_TASK, instant(8, day=4), instant(13, day=4),
        )
        ctx = replace(
            context(), tasks=(task(), task(OTHER_TASK, 300)),
            retained_blocks=(historical,),
        )
        outcome = PlanningService(lambda: FRESH_BLOCK).generate_proposal_payload(
            ctx, user_id=OWNER,
        )
        self.assertFalse(outcome.scheduling_result.conflicts)
        self.assertEqual(outcome.scheduling_result.coverage, Coverage.FULL)
        self.assertIsNotNone(outcome.proposal_payload)
        retained = next(b for b in outcome.proposal_payload.study_blocks if b.block_id == BLOCK_B)
        self.assertEqual((retained.start_at, retained.end_at),
                         (historical.start_at, historical.end_at))
        self.assertEqual(outcome.scheduling_result.task_summaries[0].unallocated_minutes, 0)

    def test_clock_seconds_are_supported_and_new_blocks_never_start_before_actual_now(self):
        """Đồng hồ kiểm toán có thể có giây; độ chính xác theo phút áp dụng cho block nghiệp vụ."""
        actual_now = instant(8, second=30) + timedelta(microseconds=123456)
        result = generate_schedule(replace(context(), now=actual_now))
        self.assertFalse(result.conflicts)
        self.assertEqual(result.coverage, Coverage.FULL)
        self.assertTrue(result.generated_blocks)
        for block in result.generated_blocks:
            self.assertGreaterEqual(block.start_at, actual_now)
            self.assertEqual((block.start_at.second, block.start_at.microsecond), (0, 0))
            self.assertEqual((block.end_at.second, block.end_at.microsecond), (0, 0))

    def test_known_good_generation_preserves_workload_equation(self):
        result = generate_schedule(context(minutes=120))
        self.assertFalse(result.conflicts)
        self.assertEqual(result.coverage, Coverage.FULL)
        summary, = result.task_summaries
        self.assertEqual(summary.remaining_minutes, 120)
        self.assertEqual(summary.remaining_minutes,
                         summary.retained_future_minutes + summary.newly_scheduled_minutes
                         + summary.unallocated_minutes)
        self.assertEqual(summary.unallocated_minutes, 0)
        self.assertTrue(all(block.end_at > block.start_at for block in result.generated_blocks))


if __name__ == "__main__":
    unittest.main()
