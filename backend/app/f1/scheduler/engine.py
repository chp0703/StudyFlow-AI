from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

from .constraints import validate_context, validate_generated_result
from .intervals import (
    add_minutes,
    ceil_to_minute,
    clip,
    duration_minutes,
    max_instant,
    merge_intervals,
    min_instant,
    pad,
    split_by_local_day,
    subtract_intervals,
    to_utc,
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


def _aware(value: object) -> bool:
    return (
        isinstance(value, datetime)
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def _ceil_to_minute(value: datetime) -> datetime:
    return ceil_to_minute(value)


def _effective_now(context: SchedulingContext) -> datetime:
    return _ceil_to_minute(context.now)


def _minutes(start, end) -> int:
    return int((to_utc(end) - to_utc(start)).total_seconds() // 60)


def _task_map(context: SchedulingContext) -> dict[object, AcademicTask]:
    return {task.task_id: task for task in context.tasks}


def _retained_future_minutes(context: SchedulingContext) -> dict[object, int]:
    result: dict[object, int] = defaultdict(int)
    if not _aware(context.now):
        return result
    for block in context.retained_blocks:
        if (
            _aware(block.start_at)
            and _aware(block.end_at)
            and to_utc(block.end_at) > to_utc(block.start_at)
            and to_utc(block.start_at) >= to_utc(context.now)
        ):
            result[block.task_id] += _minutes(block.start_at, block.end_at)
    return result


def _daily_usage(context: SchedulingContext, generated: list[EngineBlock]) -> dict[object, int]:
    tz = ZoneInfo(context.timezone)
    usage: dict[object, int] = defaultdict(int)
    for block in context.retained_blocks:
        if to_utc(block.end_at) > to_utc(context.now):
            usage[to_utc(block.start_at).astimezone(tz).date()] += _minutes(block.start_at, block.end_at)
    for block in generated:
        usage[to_utc(block.start_at).astimezone(tz).date()] += _minutes(block.start_at, block.end_at)
    return usage


def _free_intervals(context: SchedulingContext, generated: list[EngineBlock]) -> list[Interval]:
    scope_start = max_instant(context.generation_scope.start_at, _effective_now(context))
    if to_utc(scope_start) >= to_utc(context.generation_scope.end_at):
        return []
    scope = Interval(scope_start, context.generation_scope.end_at)
    available: list[Interval] = []
    for value in context.available_intervals:
        clipped = clip(value, scope)
        if clipped is not None:
            available.append(clipped)
    busy = list(context.busy_intervals)
    occupied = [
        Interval(block.start_at, block.end_at)
        for block in context.retained_blocks
        if to_utc(block.end_at) > to_utc(context.now)
    ]
    occupied.extend(Interval(block.start_at, block.end_at) for block in generated)
    protected = [pad(value, context.policy.break_minutes) for value in occupied]
    return subtract_intervals(merge_intervals(available), [*busy, *protected])


def _task_windows(
    context: SchedulingContext,
    task: AcademicTask,
    generated: list[EngineBlock],
) -> list[Interval]:
    lower = max_instant(_effective_now(context), context.generation_scope.start_at)
    if task.available_from_at is not None:
        lower = max_instant(lower, task.available_from_at)
    upper = min_instant(context.generation_scope.end_at, task.deadline_at)
    if to_utc(lower) >= to_utc(upper):
        return []
    boundary = Interval(lower, upper)
    windows: list[Interval] = []
    for value in _free_intervals(context, generated):
        clipped = clip(value, boundary)
        if clipped is not None:
            windows.extend(split_by_local_day(clipped, context.timezone))
    return sorted(windows, key=lambda value: (to_utc(value.start_at), to_utc(value.end_at)))


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
        start_at = _ceil_to_minute(window.start_at)
        if to_utc(start_at) >= to_utc(window.end_at):
            continue
        aligned_window = Interval(start_at, window.end_at)
        slot_minutes = duration_minutes(aligned_window)
        local_day = to_utc(start_at).astimezone(tz).date()
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
            start_at=start_at,
            end_at=add_minutes(start_at, candidate_minutes),
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
    lower = max_instant(_effective_now(context), context.generation_scope.start_at)
    if to_utc(task.deadline_at) <= to_utc(context.now):
        return ("DEADLINE_PASSED",)
    if to_utc(context.generation_scope.end_at) <= to_utc(lower):
        return ("OUTSIDE_HORIZON",)
    if to_utc(task.deadline_at) <= to_utc(lower):
        return ("OUTSIDE_HORIZON",)
    if task.available_from_at is not None and to_utc(task.available_from_at) >= to_utc(min_instant(task.deadline_at, context.generation_scope.end_at)):
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
    if all(usage[to_utc(value.start_at).astimezone(tz).date()] >= context.policy.max_daily_minutes for value in windows):
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
    try:
        tasks = _task_map(context)
        retained = _retained_future_minutes(context)
        summaries: list[TaskSchedulingSummary] = []
        for task_id in context.selected_task_ids:
            task = tasks.get(task_id)
            if task is None:
                continue
            remaining = (
                task.remaining_minutes
                if type(task.remaining_minutes) is int and task.remaining_minutes >= 0
                else 0
            )
            unallocated = max(0, remaining - retained[task_id])
            summaries.append(
                TaskSchedulingSummary(
                    task_id=task_id,
                    remaining_minutes=remaining,
                    retained_future_minutes=retained[task_id],
                    newly_scheduled_minutes=0,
                    unallocated_minutes=unallocated,
                    reason_codes=("INVALID_CONTEXT",) if unallocated else (),
                )
            )
        return summaries
    except Exception:
        return []


def generate_schedule(context: SchedulingContext) -> SchedulingResult:
    """Tạo kết quả đề xuất xác định, không lưu dữ liệu hay tự đọc thời gian hiện tại."""
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
        key=lambda task: (to_utc(task.deadline_at), _PRIORITY_ORDER.get(task.priority, 99), str(task.task_id)),
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
    generated.sort(key=lambda item: (to_utc(item.start_at), to_utc(item.end_at), str(item.task_id)))
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
