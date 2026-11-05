#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import sys
from uuid import UUID
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.f1.scheduler.evaluation import evaluate_context
from backend.app.f1.scheduler.models import (
    AcademicTask,
    GenerationScope,
    Interval,
    Priority,
    SchedulingContext,
    SchedulingPolicy,
    SelectionMode,
    StudyBlock,
)


TZ = ZoneInfo("Asia/Ho_Chi_Minh")
USER = UUID(int=1)


def dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 11, 4, hour, minute, tzinfo=TZ)


def task(value: int, remaining: int, deadline_hour: int, priority: Priority = Priority.NORMAL) -> AcademicTask:
    return AcademicTask(
        task_id=UUID(int=value), user_id=USER, title=f"Fixture {value}",
        deadline_at=dt(deadline_hour), estimated_minutes=remaining,
        remaining_minutes=remaining, priority=priority,
    )


def context(
    tasks: tuple[AcademicTask, ...],
    availability: tuple[Interval, ...],
    *,
    busy: tuple[Interval, ...] = (),
    retained: tuple[StudyBlock, ...] = (),
    policy: SchedulingPolicy = SchedulingPolicy(),
) -> SchedulingContext:
    selected = tuple(item.task_id for item in tasks)
    return SchedulingContext(
        now=dt(7), timezone="Asia/Ho_Chi_Minh",
        generation_scope=GenerationScope(dt(8), dt(23), SelectionMode.SELECTED_TASKS, selected),
        selected_task_ids=selected, tasks=tasks,
        available_intervals=availability, busy_intervals=busy,
        retained_blocks=retained, policy=policy,
    )


def cases() -> dict[str, SchedulingContext]:
    full = task(10, 120, 18)
    busy = task(20, 120, 18)
    partial = task(30, 180, 18)
    retained_task = task(40, 180, 18)
    early = task(50, 60, 10, Priority.LOW)
    high = task(51, 60, 12, Priority.HIGH)
    retained_block = StudyBlock(UUID(int=400), USER, retained_task.task_id, dt(8), dt(9))
    return {
        "single_full": context((full,), (Interval(dt(8), dt(12)),)),
        "busy_split": context(
            (busy,), (Interval(dt(8), dt(12)),),
            busy=(Interval(dt(9), dt(10)),),
            policy=SchedulingPolicy(25, 60, True, 240, 10),
        ),
        "partial_capacity": context((partial,), (Interval(dt(8), dt(9)),)),
        "retained_work": context(
            (retained_task,), (Interval(dt(8), dt(14)),), retained=(retained_block,)
        ),
        "deadline_before_priority": context(
            (high, early), (Interval(dt(8), dt(9)),),
            policy=SchedulingPolicy(25, 60, True, 240, 10),
        ),
    }


def main() -> None:
    report: dict[str, object] = {
        "schema_version": "1.1",
        "algorithm_version": "greedy-edf-1.1.0",
        "repetitions_per_case": 100,
        "cases": {},
    }
    for name, fixture in cases().items():
        result, metrics = evaluate_context(fixture, repetitions=100)
        report["cases"][name] = {
            "coverage": result.coverage.value,
            "hard_constraint_violations": metrics.hard_constraint_violations,
            "scheduled_ratio": round(metrics.scheduled_ratio, 4),
            "fully_covered_tasks": metrics.fully_covered_tasks,
            "unallocated_minutes": metrics.unallocated_minutes,
            "generated_block_count": metrics.generated_block_count,
            "mean_latency_ms": round(metrics.mean_latency_ms, 4),
            "deterministic": metrics.deterministic,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

