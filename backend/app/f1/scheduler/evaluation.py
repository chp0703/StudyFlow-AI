from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from time import perf_counter

from .engine import generate_schedule
from .models import SchedulingContext, SchedulingResult


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    hard_constraint_violations: int
    scheduled_ratio: float
    fully_covered_tasks: int
    unallocated_minutes: int
    generated_block_count: int
    mean_latency_ms: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_samples_ms: tuple[float, ...]
    deterministic: bool


def percentile(values: list[float], quantile: float) -> float:
    """Return the nearest-rank percentile."""
    if not values:
        raise ValueError("values must not be empty")
    if not 0 < quantile <= 1:
        raise ValueError("quantile must be greater than 0 and at most 1")
    ordered = sorted(values)
    return ordered[ceil(quantile * len(ordered)) - 1]


def evaluate_context(
    context: SchedulingContext,
    repetitions: int = 3,
    warmup_repetitions: int = 0,
) -> tuple[SchedulingResult, EvaluationMetrics]:
    if repetitions <= 0:
        raise ValueError("repetitions must be positive")
    if warmup_repetitions < 0:
        raise ValueError("warmup_repetitions must not be negative")
    for _ in range(warmup_repetitions):
        generate_schedule(context)
    results: list[SchedulingResult] = []
    durations: list[float] = []
    for _ in range(repetitions):
        started = perf_counter()
        results.append(generate_schedule(context))
        durations.append((perf_counter() - started) * 1000)
    first = results[0]
    total = sum(item.remaining_minutes for item in first.task_summaries)
    covered = sum(item.retained_future_minutes + item.newly_scheduled_minutes for item in first.task_summaries)
    metrics = EvaluationMetrics(
        hard_constraint_violations=len(first.conflicts),
        scheduled_ratio=(min(covered, total) / total) if total else 1.0,
        fully_covered_tasks=sum(item.unallocated_minutes == 0 for item in first.task_summaries),
        unallocated_minutes=sum(item.unallocated_minutes for item in first.task_summaries),
        generated_block_count=len(first.generated_blocks),
        mean_latency_ms=sum(durations) / len(durations),
        latency_p50_ms=percentile(durations, 0.50),
        latency_p95_ms=percentile(durations, 0.95),
        latency_p99_ms=percentile(durations, 0.99),
        latency_samples_ms=tuple(durations),
        deterministic=all(result == first for result in results[1:]),
    )
    return first, metrics

