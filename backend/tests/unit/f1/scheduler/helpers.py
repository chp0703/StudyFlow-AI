from __future__ import annotations

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from backend.app.f1.scheduler.models import (
    AcademicTask,
    GenerationScope,
    Interval,
    Priority,
    SchedulingContext,
    SchedulingPolicy,
    SelectionMode,
    StudyBlock,
    TaskStatus,
)


TZ = ZoneInfo("Asia/Ho_Chi_Minh")
USER_ID = UUID("00000000-0000-0000-0000-000000000001")


def dt(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, day, hour, minute, tzinfo=TZ)


def uid(value: int) -> UUID:
    return UUID(int=value)


def task(
    value: int,
    *,
    deadline: datetime | None = None,
    remaining: int = 120,
    priority: Priority = Priority.NORMAL,
    status: TaskStatus = TaskStatus.TODO,
    available_from: datetime | None = None,
) -> AcademicTask:
    return AcademicTask(
        task_id=uid(value),
        user_id=USER_ID,
        title=f"Task {value}",
        deadline_at=deadline or dt(5, 23, 0),
        estimated_minutes=max(remaining, 1),
        remaining_minutes=remaining,
        priority=priority,
        status=status,
        available_from_at=available_from,
    )


def block(value: int, task_id: UUID, start: datetime, end: datetime, locked: bool = False) -> StudyBlock:
    return StudyBlock(uid(value), USER_ID, task_id, start, end, locked)


def context(
    tasks: tuple[AcademicTask, ...],
    *,
    selected: tuple[UUID, ...] | None = None,
    now: datetime | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    available: tuple[Interval, ...] | None = None,
    busy: tuple[Interval, ...] = (),
    retained: tuple[StudyBlock, ...] = (),
    replaceable: tuple[StudyBlock, ...] = (),
    policy: SchedulingPolicy | None = None,
) -> SchedulingContext:
    now = now or dt(4, 7)
    start = start or dt(4, 8)
    end = end or dt(5, 23)
    selected = selected if selected is not None else tuple(item.task_id for item in tasks)
    available = available if available is not None else (Interval(dt(4, 8), dt(4, 18)),)
    return SchedulingContext(
        now=now,
        timezone="Asia/Ho_Chi_Minh",
        generation_scope=GenerationScope(start, end, SelectionMode.SELECTED_TASKS, selected),
        selected_task_ids=selected,
        tasks=tasks,
        available_intervals=available,
        busy_intervals=busy,
        retained_blocks=retained,
        replaceable_blocks=replaceable,
        policy=policy or SchedulingPolicy(),
    )

