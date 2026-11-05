from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

from .constraints import validate_context, validate_generated_result
from .intervals import (
    clip,
    duration_minutes,
    merge_intervals,
    pad,
    split_by_local_day,
    subtract_intervals,
)
from .models import (
    AcademicTask,
    Coverage,
    EngineBlock,
    Interval,
    Issue,
    Priority,
    SchedulingContext,
    SchedulingResult,
    TaskSchedulingSummary,
    TaskStatus,
)


ALGORITHM_VERSION = "greedy-edf-1.1.0"

_PRIORITY_ORDER = {
    Priority.HIGH: 0,
    Priority.NORMAL: 1,
    Priority.LOW: 2,
}


def _minutes(start, end) -> int:
    return int((end - start).total_seconds() // 60)


def _task_map(context: SchedulingContext) -> dict[object, AcademicTask]:
    return {task.task_id: task for task in context.tasks}


def _retained_future_minutes(context: SchedulingContext) -> dict[object, int]:
    result: dict[object, int] = defaultdict(int)
    for block in context.retained_blocks:
        if block.start_at >= context.now:
            result[block.task_id] += _minutes(block.start_at, block.end_at)
    return result


def _daily_usage(context: SchedulingContext, generated: list[EngineBlock]) -> dict[object, int]:
    tz = ZoneInfo(context.timezone)
    usage: dict[object, int] = defaultdict(int)
    for block in context.retained_blocks:
        usage[block.start_at.astimezone(tz).date()] += _minutes(block.start_at, block.end_at)
    for block in generated:
        usage[block.start_at.astimezone(tz).date()] += _minutes(block.start_at, block.end_at)
    return usage


def _free_intervals(context: SchedulingContext, generated: list[EngineBlock]) -> list[Interval]:
    scope = Interval(
        max(context.generation_scope.start_at, context.now),
        context.generation_scope.end_at,
    )
    available: list[Interval] = []
    for value in context.available_intervals:
        clipped = clip(value, scope)
        if clipped is not None:
            available.append(clipped)
    busy = list(context.busy_intervals)
    occupied = [Interval(block.start_at, block.end_at) for block in context.retained_blocks]
    occupied.extend(Interval(block.start_at, block.end_at) for block in generated)
    protected = [pad(value, context.policy.break_minutes) for value in occupied]
    return subtract_intervals(merge_intervals(available), [*busy, *protected])


def _task_windows(
    context: SchedulingContext,
    task: AcademicTask,
    generated: list[EngineBlock],
) -> list[Interval]:
    lower = max(context.now, context.generation_scope.start_at)
    if task.available_from_at is not None:
        lower = max(lower, task.available_from_at)
    upper = min(context.generation_scope.end_at, task.deadline_at)
    if lower >= upper:
        return []
    boundary = Interval(lower, upper)
    windows: list[Interval] = []
    for value in _free_intervals(context, generated):
        clipped = clip(value, boundary)
        if clipped is not None:
            windows.extend(split_by_local_day(clipped, context.timezone))
    return sorted(windows, key=lambda value: (value.start_at, value.end_at))


def _next_block(
    context: SchedulingContext,
    task: AcademicTask,
    remaining: int,
    generated: list[EngineBlock],
) -> EngineBlock | None:
    policy = context.policy
    tz = ZoneInfo(context.timezone)
    usage = _daily_usage(context, generated)
    for window in _task_windows(context, task, generated):
        slot_minutes = duration_minutes(window)
        local_day = window.start_at.astimezone(tz).date()
        daily_left = max(0, policy.max_daily_minutes - usage[local_day])
        candidate_minutes = min(
            remaining,
            policy.max_block_minutes,
            slot_minutes,
            daily_left,
        )
        if candidate_minutes <= 0:
            continue
        if candidate_minutes < policy.min_block_minutes:
            is_complete_final = remaining <= candidate_minutes
            if not (policy.allow_short_final_block and is_complete_final):
                continue
            candidate_minutes = remaining
        return EngineBlock(
            task_id=task.task_id,
            start_at=window.start_at,
            end_at=window.start_at + timedelta(minutes=candidate_minutes),
        )
    return None


def _reason_codes(
    context: SchedulingContext,
    task: AcademicTask,
    remaining: int,
    generated: list[EngineBlock],
) -> tuple[str, ...]:
    if remaining <= 0:
        return ()
    if task.status not in (TaskStatus.TODO, TaskStatus.IN_PROGRESS):
        return ("TASK_NOT_ELIGIBLE",)
    lower = max(context.now, context.generation_scope.start_at)
    if task.deadline_at <= context.now:
        return ("DEADLINE_PASSED",)
    if context.generation_scope.end_at <= lower:
        return ("OUTSIDE_HORIZON",)
    if task.deadline_at <= lower:
        return ("OUTSIDE_HORIZON",)
    if task.available_from_at is not None and task.available_from_at >= min(task.deadline_at, context.generation_scope.end_at):
        return ("OUTSIDE_HORIZON",)

    windows = _task_windows(context, task, generated)
    if not context.available_intervals:
        return ("NO_AVAILABILITY",)
    if not windows:
        return ("INSUFFICIENT_CAPACITY",)
    if remaining < context.policy.min_block_minutes and not context.policy.allow_short_final_block:
        return ("BLOCK_TOO_SHORT",)
    max_fragment = max((duration_minutes(value) for value in windows), default=0)
    short_can_finish = context.policy.allow_short_final_block and remaining <= max_fragment
    if max_fragment < context.policy.min_block_minutes and not short_can_finish:
        return ("BLOCK_TOO_SHORT",)
    usage = _daily_usage(context, generated)
    tz = ZoneInfo(context.timezone)
    if all(usage[value.start_at.astimezone(tz).date()] >= context.policy.max_daily_minutes for value in windows):
        return ("DAILY_LIMIT_REACHED",)
    return ("INSUFFICIENT_CAPACITY",)


def _coverage(summaries: list[TaskSchedulingSummary], has_generated: bool) -> Coverage:
    if not summaries:
        return Coverage.NO_CHANGE
    unallocated = sum(item.unallocated_minutes for item in summaries)
    covered = sum(item.retained_future_minutes + item.newly_scheduled_minutes for item in summaries)
    if unallocated == 0:
        return Coverage.FULL if has_generated else Coverage.NO_CHANGE
    return Coverage.PARTIAL if covered > 0 else Coverage.NONE


def _summaries_without_generation(
    context: SchedulingContext,
) -> list[TaskSchedulingSummary]:
    tasks = _task_map(context)
    retained = _retained_future_minutes(context)
    summaries: list[TaskSchedulingSummary] = []
    for task_id in context.selected_task_ids:
        task = tasks.get(task_id)
        if task is None:
            continue
        unallocated = max(0, task.remaining_minutes - retained[task_id])
        summaries.append(
            TaskSchedulingSummary(
                task_id=task_id,
                remaining_minutes=task.remaining_minutes,
                retained_future_minutes=retained[task_id],
                newly_scheduled_minutes=0,
                unallocated_minutes=unallocated,
                reason_codes=("INVALID_CONTEXT",) if unallocated else (),
            )
        )
    return summaries


def generate_schedule(context: SchedulingContext) -> SchedulingResult:
    """Create a deterministic proposal result without persistence or implicit time reads."""
    context_issues = validate_context(context)
    if context_issues:
        summaries = _summaries_without_generation(context)
        return SchedulingResult(
            generated_blocks=(),
            task_summaries=tuple(summaries),
            coverage=_coverage(summaries, False),
            conflicts=context_issues,
            warnings=(),
            algorithm_version=ALGORITHM_VERSION,
        )

    tasks = _task_map(context)
    retained = _retained_future_minutes(context)
    ordered_tasks = sorted(
        (tasks[task_id] for task_id in context.selected_task_ids),
        key=lambda task: (task.deadline_at, _PRIORITY_ORDER[task.priority], str(task.task_id)),
    )
    generated: list[EngineBlock] = []
    summaries_by_id: dict[object, TaskSchedulingSummary] = {}

    for task in ordered_tasks:
        needed = max(0, task.remaining_minutes - retained[task.task_id])
        newly_scheduled = 0
        if task.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS):
            while needed > 0:
                block = _next_block(context, task, needed, generated)
                if block is None:
                    break
                minutes = _minutes(block.start_at, block.end_at)
                generated.append(block)
                newly_scheduled += minutes
                needed -= minutes
        reasons = _reason_codes(context, task, needed, generated)
        summaries_by_id[task.task_id] = TaskSchedulingSummary(
            task_id=task.task_id,
            remaining_minutes=task.remaining_minutes,
            retained_future_minutes=retained[task.task_id],
            newly_scheduled_minutes=newly_scheduled,
            unallocated_minutes=needed,
            reason_codes=reasons,
        )

    summaries = [summaries_by_id[task_id] for task_id in context.selected_task_ids]
    generated.sort(key=lambda item: (item.start_at, item.end_at, str(item.task_id)))
    result_issues = validate_generated_result(context, tuple(generated))
    warnings = tuple(
        Issue(
            code="UNALLOCATED_WORK",
            message="The greedy baseline could not allocate all remaining work.",
            field=None,
            details={"task_id": str(summary.task_id), "minutes": summary.unallocated_minutes, "reason_codes": list(summary.reason_codes)},
        )
        for summary in summaries
        if summary.unallocated_minutes > 0
    )
    return SchedulingResult(
        generated_blocks=tuple(generated),
        task_summaries=tuple(summaries),
        coverage=_coverage(summaries, bool(generated)),
        conflicts=result_issues,
        warnings=warnings,
        algorithm_version=ALGORITHM_VERSION,
    )

