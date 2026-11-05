from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .intervals import contains, duration_minutes, is_single_local_day, merge_intervals, overlaps
from .models import (
    AcademicTask,
    EngineBlock,
    Interval,
    Issue,
    SchedulingContext,
    SelectionMode,
    StudyBlock,
    TaskStatus,
)


def _aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _minute_aligned(value: datetime) -> bool:
    return value.second == 0 and value.microsecond == 0


def _issue(code: str, message: str, field: str | None = None, **details: object) -> Issue:
    return Issue(code=code, message=message, field=field, details=details)


def _task_map(context: SchedulingContext) -> dict[object, AcademicTask]:
    return {task.task_id: task for task in context.tasks}


def validate_policy(context: SchedulingContext) -> list[Issue]:
    policy = context.policy
    issues: list[Issue] = []
    if policy.min_block_minutes <= 0:
        issues.append(_issue("INVALID_POLICY", "min_block_minutes must be positive", "policy.min_block_minutes"))
    if policy.max_block_minutes < policy.min_block_minutes:
        issues.append(_issue("INVALID_POLICY", "max_block_minutes must be >= min_block_minutes", "policy.max_block_minutes"))
    if policy.max_daily_minutes <= 0:
        issues.append(_issue("INVALID_POLICY", "max_daily_minutes must be positive", "policy.max_daily_minutes"))
    if policy.break_minutes < 0:
        issues.append(_issue("INVALID_POLICY", "break_minutes must be non-negative", "policy.break_minutes"))
    if type(policy.allow_short_final_block) is not bool:
        issues.append(_issue("INVALID_POLICY", "allow_short_final_block must be boolean", "policy.allow_short_final_block"))
    return issues


def validate_context(context: SchedulingContext) -> tuple[Issue, ...]:
    issues: list[Issue] = []
    scope = context.generation_scope
    try:
        ZoneInfo(context.timezone)
    except ZoneInfoNotFoundError:
        issues.append(_issue("INVALID_TIMEZONE", "timezone must be a valid IANA name", "timezone", value=context.timezone))
        return tuple(issues)

    timestamps = [("now", context.now), ("generation_scope.start_at", scope.start_at), ("generation_scope.end_at", scope.end_at)]
    for field_name, value in timestamps:
        if not _aware(value):
            issues.append(_issue("NAIVE_TIMESTAMP", "timestamp must include an offset", field_name))
        elif not _minute_aligned(value):
            issues.append(_issue("TIMESTAMP_NOT_MINUTE_ALIGNED", "planner timestamps must be minute-aligned", field_name))
    if all(_aware(value) for _, value in timestamps) and scope.start_at >= scope.end_at:
        issues.append(_issue("INVALID_GENERATION_SCOPE", "generation scope end must be after start", "generation_scope"))

    issues.extend(validate_policy(context))
    if len(set(context.selected_task_ids)) != len(context.selected_task_ids):
        issues.append(_issue("DUPLICATE_SELECTED_TASK", "selected_task_ids must be unique", "selected_task_ids"))
    if scope.selection_mode is SelectionMode.SELECTED_TASKS:
        if not scope.task_ids:
            issues.append(_issue("INVALID_GENERATION_SCOPE", "SELECTED_TASKS requires non-empty task_ids", "generation_scope.task_ids"))
        elif set(scope.task_ids) != set(context.selected_task_ids):
            issues.append(_issue("SELECTED_TASK_MISMATCH", "generation_scope.task_ids must match resolved selected_task_ids", "generation_scope.task_ids"))
    elif scope.task_ids:
        issues.append(_issue("INVALID_GENERATION_SCOPE", "ALL_ELIGIBLE requires empty task_ids", "generation_scope.task_ids"))

    tasks_by_id = _task_map(context)
    if len(tasks_by_id) != len(context.tasks):
        issues.append(_issue("DUPLICATE_TASK", "task IDs must be unique", "tasks"))
    for task_id in context.selected_task_ids:
        if task_id not in tasks_by_id:
            issues.append(_issue("TASK_NOT_FOUND", "selected task is missing from context", "selected_task_ids", task_id=str(task_id)))

    owners = {task.user_id for task in context.tasks}
    owners.update(block.user_id for block in context.retained_blocks)
    owners.update(block.user_id for block in context.replaceable_blocks)
    if len(owners) > 1:
        issues.append(_issue("OWNER_MISMATCH", "all tasks and blocks in one context must have the same owner"))

    for task in context.tasks:
        prefix = f"tasks.{task.task_id}"
        if not task.title.strip():
            issues.append(_issue("INVALID_TASK", "task title must not be blank", f"{prefix}.title"))
        if task.estimated_minutes <= 0:
            issues.append(_issue("INVALID_TASK", "estimated_minutes must be positive", f"{prefix}.estimated_minutes"))
        if not 0 <= task.remaining_minutes <= task.estimated_minutes:
            issues.append(_issue("INVALID_TASK", "remaining_minutes must be between zero and estimated_minutes", f"{prefix}.remaining_minutes"))
        if not _aware(task.deadline_at):
            issues.append(_issue("NAIVE_TIMESTAMP", "deadline must include an offset", f"{prefix}.deadline_at"))
        if task.available_from_at is not None:
            if not _aware(task.available_from_at):
                issues.append(_issue("NAIVE_TIMESTAMP", "available_from_at must include an offset", f"{prefix}.available_from_at"))
            elif task.available_from_at > task.deadline_at:
                issues.append(_issue("INVALID_TASK", "available_from_at must not be later than deadline", f"{prefix}.available_from_at"))
        if task.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS) and task.remaining_minutes == 0:
            issues.append(_issue("INVALID_TASK", "active task must have remaining work", f"{prefix}.remaining_minutes"))
        if task.status is TaskStatus.COMPLETED and task.remaining_minutes != 0:
            issues.append(_issue("INVALID_TASK", "completed task must have zero remaining work", f"{prefix}.remaining_minutes"))

    for name, values in (("available_intervals", context.available_intervals), ("busy_intervals", context.busy_intervals)):
        for index, interval in enumerate(values):
            field_name = f"{name}.{index}"
            if not _aware(interval.start_at) or not _aware(interval.end_at):
                issues.append(_issue("NAIVE_TIMESTAMP", "interval timestamps must include an offset", field_name))
            elif interval.start_at >= interval.end_at:
                issues.append(_issue("INVALID_INTERVAL", "interval end must be after start", field_name))

    retained_ids = {block.block_id for block in context.retained_blocks}
    replaceable_ids = {block.block_id for block in context.replaceable_blocks}
    if retained_ids & replaceable_ids:
        issues.append(_issue("BLOCK_PARTITION_OVERLAP", "a block cannot be retained and replaceable", details={"block_ids": [str(value) for value in sorted(retained_ids & replaceable_ids, key=str)]}))
    if len(retained_ids) != len(context.retained_blocks) or len(replaceable_ids) != len(context.replaceable_blocks):
        issues.append(_issue("DUPLICATE_BLOCK", "block IDs must be unique inside each partition"))

    for group_name, blocks in (("retained_blocks", context.retained_blocks), ("replaceable_blocks", context.replaceable_blocks)):
        for block in blocks:
            prefix = f"{group_name}.{block.block_id}"
            if block.task_id not in tasks_by_id:
                issues.append(_issue("TASK_NOT_FOUND", "block task is missing from context", f"{prefix}.task_id"))
            if not _aware(block.start_at) or not _aware(block.end_at):
                issues.append(_issue("NAIVE_TIMESTAMP", "block timestamps must include an offset", prefix))
                continue
            if block.start_at >= block.end_at:
                issues.append(_issue("INVALID_BLOCK", "block end must be after start", prefix))
            elif not is_single_local_day(Interval(block.start_at, block.end_at), context.timezone):
                issues.append(_issue("BLOCK_CROSSES_LOCAL_DAY", "block must stay in one local day or end at next midnight", prefix))
            if group_name == "replaceable_blocks" and block.is_locked:
                issues.append(_issue("LOCKED_BLOCK_REPLACEABLE", "locked block must be retained", prefix))
            if group_name == "replaceable_blocks" and block.task_id not in context.selected_task_ids:
                issues.append(_issue("UNSELECTED_BLOCK_REPLACEABLE", "replaceable block must belong to a selected task", prefix))
            if group_name == "replaceable_blocks" and _aware(block.start_at) and _aware(block.end_at):
                scope_interval = Interval(scope.start_at, scope.end_at)
                if block.start_at < context.now:
                    issues.append(_issue("NON_FUTURE_BLOCK_REPLACEABLE", "replaceable block must start at or after now", prefix))
                if not contains(scope_interval, Interval(block.start_at, block.end_at)):
                    issues.append(_issue("OUT_OF_SCOPE_BLOCK_REPLACEABLE", "replaceable block must lie fully inside the generation scope", prefix))

    if issues:
        return tuple(issues)
    issues.extend(validate_retained_constraints(context))
    return tuple(issues)


def _is_available(context: SchedulingContext, interval: Interval) -> bool:
    return any(contains(value, interval) for value in merge_intervals(context.available_intervals))


def _busy_overlap(context: SchedulingContext, interval: Interval) -> bool:
    return any(overlaps(value, interval) for value in context.busy_intervals)


def validate_retained_constraints(context: SchedulingContext) -> list[Issue]:
    """Validate future retained blocks against current hard constraints."""
    issues: list[Issue] = []
    tasks = _task_map(context)
    future_blocks = [block for block in context.retained_blocks if block.end_at > context.now]

    for block in future_blocks:
        interval = Interval(block.start_at, block.end_at)
        task = tasks[block.task_id]
        if block.start_at < context.now < block.end_at and block.task_id in context.selected_task_ids:
            issues.append(_issue("ACTIVE_BLOCK_REQUIRES_REVIEW", "an active block for a selected task cannot be reallocated", block_id=str(block.block_id), task_id=str(block.task_id)))
        if not _is_available(context, interval):
            issues.append(_issue("RETAINED_OUTSIDE_AVAILABILITY", "retained block is outside current availability", block_id=str(block.block_id)))
        if _busy_overlap(context, interval):
            issues.append(_issue("RETAINED_BUSY_CONFLICT", "retained block overlaps a busy interval", block_id=str(block.block_id)))
        if block.end_at > task.deadline_at:
            issues.append(_issue("RETAINED_AFTER_DEADLINE", "retained block ends after task deadline", block_id=str(block.block_id), task_id=str(block.task_id)))
        if task.available_from_at is not None and block.start_at < task.available_from_at:
            issues.append(_issue("RETAINED_BEFORE_AVAILABLE", "retained block starts before task is available", block_id=str(block.block_id), task_id=str(block.task_id)))

    retained_minutes: dict[object, int] = defaultdict(int)
    for block in context.retained_blocks:
        if block.start_at >= context.now:
            retained_minutes[block.task_id] += duration_minutes(Interval(block.start_at, block.end_at))
    for task_id in context.selected_task_ids:
        task = tasks[task_id]
        if retained_minutes[task_id] > task.remaining_minutes:
            issues.append(_issue("RETAINED_EXCEEDS_REMAINING", "future retained blocks exceed remaining task work", task_id=str(task_id), retained_minutes=retained_minutes[task_id], remaining_minutes=task.remaining_minutes))

    issues.extend(_validate_calendar_policy(context, (), include_generated_lengths=False))
    return issues


def _validate_calendar_policy(
    context: SchedulingContext,
    generated_blocks: tuple[EngineBlock, ...],
    *,
    include_generated_lengths: bool = True,
) -> list[Issue]:
    issues: list[Issue] = []
    tz = ZoneInfo(context.timezone)
    combined: list[tuple[datetime, datetime, str, object]] = []
    for block in context.retained_blocks:
        combined.append((block.start_at, block.end_at, "retained", block.block_id))
    for index, block in enumerate(generated_blocks):
        combined.append((block.start_at, block.end_at, "generated", index))
    combined.sort(key=lambda value: (value[0], value[1], value[2], str(value[3])))

    daily: dict[object, int] = defaultdict(int)
    for start_at, end_at, kind, identifier in combined:
        local_day = start_at.astimezone(tz).date()
        daily[local_day] += int((end_at - start_at).total_seconds() // 60)
        if daily[local_day] > context.policy.max_daily_minutes:
            issues.append(_issue("MAX_DAILY_MINUTES_EXCEEDED", "study blocks exceed max_daily_minutes", day=str(local_day), scheduled_minutes=daily[local_day], limit=context.policy.max_daily_minutes))
    for previous, current in zip(combined, combined[1:]):
        previous_end = previous[1]
        current_start = current[0]
        gap = int((current_start - previous_end).total_seconds() // 60)
        if current_start < previous_end:
            issues.append(_issue("STUDY_BLOCK_OVERLAP", "study blocks overlap", first=str(previous[3]), second=str(current[3])))
        elif gap < context.policy.break_minutes:
            issues.append(_issue("BREAK_TOO_SHORT", "study blocks do not satisfy break_minutes", first=str(previous[3]), second=str(current[3]), gap_minutes=gap, required_minutes=context.policy.break_minutes))

    if include_generated_lengths:
        by_task: dict[object, list[EngineBlock]] = defaultdict(list)
        for block in generated_blocks:
            by_task[block.task_id].append(block)
        tasks = _task_map(context)
        retained_minutes: dict[object, int] = defaultdict(int)
        for block in context.retained_blocks:
            if block.start_at >= context.now:
                retained_minutes[block.task_id] += duration_minutes(Interval(block.start_at, block.end_at))
        for task_id, blocks in by_task.items():
            ordered = sorted(blocks, key=lambda item: (item.start_at, item.end_at))
            generated_total = sum(duration_minutes(Interval(item.start_at, item.end_at)) for item in ordered)
            required = tasks[task_id].remaining_minutes - retained_minutes[task_id]
            for index, block in enumerate(ordered):
                minutes = duration_minutes(Interval(block.start_at, block.end_at))
                if minutes > context.policy.max_block_minutes:
                    issues.append(_issue("BLOCK_TOO_LONG", "generated block exceeds max_block_minutes", task_id=str(task_id), minutes=minutes))
                if minutes < context.policy.min_block_minutes:
                    allowed_final = context.policy.allow_short_final_block and index == len(ordered) - 1 and generated_total == required
                    if not allowed_final:
                        issues.append(_issue("BLOCK_TOO_SHORT", "generated block is shorter than min_block_minutes", task_id=str(task_id), minutes=minutes))
    return issues


def validate_generated_result(
    context: SchedulingContext,
    generated_blocks: tuple[EngineBlock, ...],
) -> tuple[Issue, ...]:
    issues: list[Issue] = []
    tasks = _task_map(context)
    scope = Interval(context.generation_scope.start_at, context.generation_scope.end_at)
    retained_minutes: dict[object, int] = defaultdict(int)
    generated_minutes: dict[object, int] = defaultdict(int)
    for block in context.retained_blocks:
        if block.start_at >= context.now:
            retained_minutes[block.task_id] += duration_minutes(Interval(block.start_at, block.end_at))

    for index, block in enumerate(generated_blocks):
        field = f"generated_blocks.{index}"
        interval = Interval(block.start_at, block.end_at)
        task = tasks.get(block.task_id)
        if task is None or block.task_id not in context.selected_task_ids:
            issues.append(_issue("INVALID_GENERATED_TASK", "generated block must target a selected task", field, task_id=str(block.task_id)))
            continue
        if block.start_at < context.now:
            issues.append(_issue("GENERATED_IN_PAST", "generated block starts before now", field))
        if not contains(scope, interval):
            issues.append(_issue("GENERATED_OUTSIDE_SCOPE", "generated block lies outside generation scope", field))
        if not _is_available(context, interval):
            issues.append(_issue("GENERATED_OUTSIDE_AVAILABILITY", "generated block lies outside availability", field))
        if _busy_overlap(context, interval):
            issues.append(_issue("GENERATED_BUSY_CONFLICT", "generated block overlaps a busy interval", field))
        if block.end_at > task.deadline_at:
            issues.append(_issue("GENERATED_AFTER_DEADLINE", "generated block ends after task deadline", field))
        if task.available_from_at is not None and block.start_at < task.available_from_at:
            issues.append(_issue("GENERATED_BEFORE_AVAILABLE", "generated block starts before task is available", field))
        if not is_single_local_day(interval, context.timezone):
            issues.append(_issue("BLOCK_CROSSES_LOCAL_DAY", "generated block crosses a local-day boundary", field))
        generated_minutes[block.task_id] += duration_minutes(interval)

    for task_id in context.selected_task_ids:
        task = tasks.get(task_id)
        if task is not None and retained_minutes[task_id] + generated_minutes[task_id] > task.remaining_minutes:
            issues.append(_issue("SCHEDULED_EXCEEDS_REMAINING", "retained and generated minutes exceed remaining work", task_id=str(task_id)))
    issues.extend(_validate_calendar_policy(context, generated_blocks))
    return tuple(issues)

