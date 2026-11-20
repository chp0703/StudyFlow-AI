#!/usr/bin/env python3
"""So sánh greedy scheduler với CP-SAT trên subset 5 phút được công bố."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.f1.scheduler.engine import generate_schedule  # noqa: E402
from backend.app.f1.scheduler.intervals import to_utc  # noqa: E402
from backend.app.f1.scheduler.models import (  # noqa: E402
    AcademicTask, GenerationScope, Interval, Priority, SchedulingContext, SchedulingPolicy, SelectionMode)

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
USER = UUID(int=1)
STEP_MINUTES = 5
TASK_MINUTES = 60
BREAK_MINUTES = 10


def make_context(seed: int) -> SchedulingContext:
    rng = random.Random(seed)
    day0 = datetime(2026, 11, 4, tzinfo=TZ)
    days = rng.randint(1, 3)
    count = rng.randint(5, 12)
    available = tuple(Interval(day0 + timedelta(days=day, hours=8),
                               day0 + timedelta(days=day, hours=18)) for day in range(days))
    busy = tuple(Interval(day0 + timedelta(days=day, hours=12),
                          day0 + timedelta(days=day, hours=13)) for day in range(days) if rng.random() < 0.6)
    tasks = tuple(AcademicTask(
        task_id=UUID(int=seed * 100 + index + 1), user_id=USER, title=f"Oracle task {index}",
        deadline_at=day0 + timedelta(days=rng.randrange(days), hours=rng.choice((12, 15, 18))),
        estimated_minutes=TASK_MINUTES, remaining_minutes=TASK_MINUTES,
        priority=rng.choice(tuple(Priority)),
    ) for index in range(count))
    ids = tuple(task.task_id for task in tasks)
    return SchedulingContext(
        now=day0 + timedelta(hours=7), timezone="Asia/Ho_Chi_Minh",
        generation_scope=GenerationScope(day0 + timedelta(hours=8), day0 + timedelta(days=days - 1, hours=18),
                                         SelectionMode.SELECTED_TASKS, ids),
        selected_task_ids=ids, tasks=tasks, available_intervals=available, busy_intervals=busy,
        policy=SchedulingPolicy(TASK_MINUTES, TASK_MINUTES, False, 240, BREAK_MINUTES))


def _overlaps(left: Interval, right: Interval) -> bool:
    return to_utc(left.start_at) < to_utc(right.end_at) and to_utc(right.start_at) < to_utc(left.end_at)


def optimal_solution(context: SchedulingContext, time_limit_seconds: float = 300.0) -> dict:
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    placements: list[tuple[object, int, datetime, datetime, int]] = []
    for task_index, task in enumerate(context.tasks):
        for window in context.available_intervals:
            start = window.start_at
            while start + timedelta(minutes=TASK_MINUTES) <= window.end_at:
                end = start + timedelta(minutes=TASK_MINUTES)
                block = Interval(start, end)
                if end <= task.deadline_at and not any(_overlaps(block, item) for item in context.busy_intervals):
                    placements.append((model.NewBoolVar(f"t{task_index}_{start.isoformat()}"), task_index,
                                       start, end, int(task.priority.value * 10)))
                start += timedelta(minutes=STEP_MINUTES)
    for task_index in range(len(context.tasks)):
        model.Add(sum(value for value, index, *_ in placements if index == task_index) <= 1)
    ticks: dict[datetime, list] = {}
    for value, _, start, end, _ in placements:
        tick = start
        while tick < end + timedelta(minutes=BREAK_MINUTES):
            ticks.setdefault(tick, []).append(value)
            tick += timedelta(minutes=STEP_MINUTES)
    for values in ticks.values():
        model.Add(sum(values) <= 1)
    for day in {start.date() for _, _, start, _, _ in placements}:
        model.Add(sum(value * TASK_MINUTES for value, _, start, _, _ in placements if start.date() == day)
                  <= context.policy.max_daily_minutes)
    model.Maximize(sum(value * 1000 + value * weight for value, _, _, _, weight in placements))
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 0
    solver.parameters.max_time_in_seconds = time_limit_seconds
    status = solver.Solve(model)
    if status != cp_model.OPTIMAL:
        raise RuntimeError(f"CP-SAT did not prove the evaluation workload optimal: {solver.StatusName(status)}")
    selected = [(index, weight) for value, index, _, _, weight in placements if solver.Value(value)]
    return {"status": "OPTIMAL", "completed": len(selected),
            "priority_score": sum(weight for _, weight in selected),
            "solver_wall_time_seconds": solver.WallTime()}


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else "UNKNOWN"


def metadata(time_limit_seconds: float) -> dict:
    import ortools

    sources = (Path(__file__), ROOT / "backend/app/f1/scheduler/engine.py")
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "git_commit": _git("rev-parse", "HEAD"),
            "git_dirty": bool(_git("status", "--porcelain")), "python": platform.python_version(),
            "os": platform.platform(), "ortools": ortools.__version__, "solver": "CP-SAT",
            "workers": 1, "random_seed": 0, "time_limit_seconds": time_limit_seconds,
            "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in sources}}


def evaluate(cases: int, seed: int, time_limit_seconds: float = 30.0) -> dict:
    records = []
    for offset in range(cases):
        context = make_context(seed + offset)
        result = generate_schedule(context)
        completed_ids = {summary.task_id for summary in result.task_summaries if summary.unallocated_minutes == 0}
        greedy = len(completed_ids)
        greedy_priority = sum(int(task.priority.value * 10) for task in context.tasks if task.task_id in completed_ids)
        try:
            optimum = optimal_solution(context, time_limit_seconds)
        except RuntimeError as exc:
            raise RuntimeError(f"seed {seed + offset}: {exc}") from exc
        records.append({"seed": seed + offset, "tasks": len(context.tasks), "greedy_completed": greedy,
                        "greedy_priority_score": greedy_priority, "optimal_completed": optimum["completed"],
                        "optimal_priority_score": optimum["priority_score"], "solver_status": optimum["status"],
                        "solver_wall_time_seconds": optimum["solver_wall_time_seconds"],
                        "coverage_gap": (optimum["completed"] - greedy) / optimum["completed"]
                        if optimum["completed"] else 0.0})
        records[-1]["priority_score_gap"] = (
            (optimum["priority_score"] - greedy_priority) / optimum["priority_score"]
            if greedy == optimum["completed"] and optimum["priority_score"] else None)
    priority_gaps = [record["priority_score_gap"] for record in records
                     if record["priority_score_gap"] is not None]
    return {"schema_version": "1.1", "metadata": metadata(time_limit_seconds),
            "subset": "60-minute tasks on a 5-minute grid with tight deadlines, priority, busy windows, daily limits and breaks; no retained or exact-start blocks",
            "objective": "maximize completed tasks, then priority score", "seed": seed, "case_count": cases,
            "records": records,
            "mean_coverage_gap": sum(record["coverage_gap"] for record in records) / len(records),
            "worst_coverage_gap": max(record["coverage_gap"] for record in records),
            "mean_priority_score_gap": sum(priority_gaps) / len(priority_gaps) if priority_gaps else None,
            "worst_priority_score_gap": max(priority_gaps) if priority_gaps else None,
            "greedy_never_exceeds_optimum": all(record["greedy_completed"] <= record["optimal_completed"]
                                                for record in records)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20261116)
    parser.add_argument("--time-limit", type=float, default=300.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.cases < 1 or args.time_limit <= 0:
        parser.error("--cases and --time-limit must be positive")
    report = evaluate(args.cases, args.seed, args.time_limit)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["greedy_never_exceeds_optimum"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
