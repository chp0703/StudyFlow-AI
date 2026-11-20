#!/usr/bin/env python3
"""Chạy verification Planner và xuất báo cáo JSON tái lập."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from uuid import UUID
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.f1.scheduler.evaluation import evaluate_context, percentile  # noqa: E402
from backend.app.f1.scheduler.models import (  # noqa: E402
    AcademicTask, GenerationScope, Interval, Priority, SchedulingContext, SchedulingPolicy, SelectionMode)
from backend.app.nlu.evaluation import (  # noqa: E402
    DATASET, evaluate_cases, exact_metrics, load, minimum_passes, wilson_interval)
from backend.app.nlu.extractor import DeepSeekExtractor, PROMPT  # noqa: E402

TZ = ZoneInfo("Asia/Ho_Chi_Minh")
USER = UUID(int=1)
SCALES = ((10, 3), (50, 7), (200, 14))


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must not be negative")
    return parsed


def scale_context(tasks: int, days: int) -> SchedulingContext:
    day0 = datetime(2026, 11, 4, tzinfo=TZ)
    items = tuple(
        AcademicTask(task_id=UUID(int=100 + i), user_id=USER, title=f"Task {i}",
                     deadline_at=day0 + timedelta(days=i % days, hours=22), estimated_minutes=60,
                     remaining_minutes=60, priority=(Priority.LOW, Priority.NORMAL, Priority.HIGH)[i % 3])
        for i in range(tasks))
    ids = tuple(item.task_id for item in items)
    return SchedulingContext(
        now=day0 + timedelta(hours=7), timezone="Asia/Ho_Chi_Minh",
        generation_scope=GenerationScope(day0 + timedelta(hours=8), day0 + timedelta(days=days, hours=23),
                                         SelectionMode.SELECTED_TASKS, ids),
        selected_task_ids=ids, tasks=items,
        available_intervals=tuple(Interval(day0 + timedelta(days=day, hours=8),
                                           day0 + timedelta(days=day, hours=22)) for day in range(days)),
        busy_intervals=(), retained_blocks=(), policy=SchedulingPolicy())


def run_scheduler(repetitions: int, warmups: int = 0) -> dict:
    cases = {}
    for tasks, days in SCALES:
        _, metrics = evaluate_context(scale_context(tasks, days), repetitions, warmups)
        cases[f"{tasks}_tasks_{days}_days"] = {
            "hard_constraint_violations": metrics.hard_constraint_violations,
            "deterministic": metrics.deterministic,
            "scheduled_ratio": round(metrics.scheduled_ratio, 4),
            "mean_latency_ms": round(metrics.mean_latency_ms, 3),
            "latency_ms_p50": round(metrics.latency_p50_ms, 3),
            "latency_ms_p95": round(metrics.latency_p95_ms, 3),
            "latency_ms_p99": round(metrics.latency_p99_ms, 3),
            "latency_sample_count": len(metrics.latency_samples_ms),
            "latency_samples_sha256": _sha256(json.dumps(metrics.latency_samples_ms).encode("utf-8")),
            "ok": metrics.deterministic and metrics.hard_constraint_violations == 0,
        }
    return {"ok": all(case["ok"] for case in cases.values()), "repetitions": repetitions,
            "warmups": warmups, "cases": cases}


def run_command(command: list[str]) -> dict:
    started = perf_counter()
    done = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    tail = (done.stdout + done.stderr).strip().splitlines()[-3:]
    return {"ok": done.returncode == 0, "seconds": round(perf_counter() - started, 1), "tail": tail}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else "UNKNOWN"


def metadata(dataset_path: Path) -> dict:
    source_files = (
        ROOT / "backend/app/f1/scheduler/engine.py",
        ROOT / "backend/app/f1/scheduler/evaluation.py",
        ROOT / "backend/app/nlu/evaluation.py",
        Path(__file__),
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "environment": {"python": platform.python_version(), "os": platform.platform(),
                        "processor": platform.processor() or "UNKNOWN"},
        "dataset": {"path": str(dataset_path.relative_to(ROOT)),
                    "sha256": _sha256(dataset_path.read_bytes())},
        "prompt_sha256": _sha256(PROMPT.encode("utf-8")),
        "source_sha256": {str(path.relative_to(ROOT)): _sha256(path.read_bytes()) for path in source_files},
    }


def run_nlu(runs: int, dataset_path: Path) -> dict:
    key = os.environ.get("DEEPSEEK_API_KEY")
    dataset = load(dataset_path)
    required = minimum_passes(dataset)
    if not key:
        return {"ok": None, "status": "NOT_RUN", "reason": "DEEPSEEK_API_KEY is not set",
                "case_count": len(dataset["cases"]), "minimum_passes": required}
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    extractor = DeepSeekExtractor(base_url, key, model, None)
    records = []
    for run_index in range(runs):
        latencies: list[float] = []
        inner = extractor.extract

        def timed(*args, **kwargs):
            started = perf_counter()
            try:
                return inner(*args, **kwargs)
            finally:
                latencies.append((perf_counter() - started) * 1000)

        extractor.extract = timed
        outcomes = evaluate_cases(extractor, dataset)
        extractor.extract = inner
        passed = sum(outcome["passed"] for outcome in outcomes)
        record = {"run": run_index + 1, "passed": passed, "case_pass_rate": passed / len(outcomes),
                  "case_pass_wilson_95": list(wilson_interval(passed, len(outcomes))),
                  "latency_ms_p50": percentile(latencies, 0.50),
                  "latency_ms_p95": percentile(latencies, 0.95),
                  "latency_ms_p99": percentile(latencies, 0.99),
                  "latency_sample_count": len(latencies),
                  "latency_samples_sha256": _sha256(json.dumps(latencies).encode("utf-8")),
                  "outcomes": outcomes}
        if dataset.get("scoring_mode") == "exact":
            record.update(exact_metrics(dataset, outcomes))
        records.append(record)
    rates = [record["case_pass_rate"] for record in records]
    return {"ok": min(record["passed"] for record in records) >= required, "status": "RUN",
            "provider": "DeepSeek", "model": model, "base_url": base_url, "runs": records,
            "case_count": len(dataset["cases"]), "minimum_rate": dataset["minimum_rate"],
            "minimum_passes": required, "mean_case_pass_rate": sum(rates) / len(rates),
            "worst_case_pass_rate": min(rates)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nlu-runs", type=positive_int, default=1)
    parser.add_argument("--nlu-dataset", type=Path, default=DATASET)
    parser.add_argument("--repetitions", type=positive_int, default=1000)
    parser.add_argument("--warmups", type=non_negative_int, default=10)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--nlu-only", action="store_true", help="skip offline checks and scheduler benchmark")
    args = parser.parse_args()
    dataset_path = args.nlu_dataset.resolve()
    if not dataset_path.is_file():
        parser.error(f"dataset does not exist: {dataset_path}")
    py = sys.executable
    report = {"schema_version": "1.0", "metadata": metadata(dataset_path)}
    if not args.nlu_only:
        report.update({
            "unit": run_command([py, "-m", "unittest", "discover", "-s", "backend/tests/unit", "-t", "."]),
            "contract": run_command([py, "contracts/check_contract.py"]),
            "generated_schema": run_command([py, "backend/scripts/generate_contract_schema_migration.py", "--check"]),
            "scheduler": run_scheduler(args.repetitions, args.warmups),
        })
    report["nlu"] = run_nlu(args.nlu_runs, dataset_path)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print(rendered)
    return 0 if all(part.get("ok") is not False for part in report.values() if isinstance(part, dict)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
