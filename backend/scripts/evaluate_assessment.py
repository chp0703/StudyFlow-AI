"""F2 Assessment evaluation runner. See docs/features/assessment/evaluation/README.md.

  offline    GRD-C01/C02 grading oracle + grading latency (no network)
  generate   QG-01, SAFE-01, PERF-02 with live DeepSeek; writes an annotation CSV for QG-02/03
  score      QG-02 acceptability, Cohen's kappa and Wilson interval from two rater CSVs
  retrieval  RET-01 Recall@5/MRR/nDCG@10 from a ranked-runs JSON file
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.assessment import evaluation as ev  # noqa: E402
from backend.app.assessment.attempts import grade_attempt  # noqa: E402
from backend.app.assessment.questions import (  # noqa: E402
    PROMPT_VERSION, DeepSeekQuestionGenerator, normalize_question_batch,
)
from backend.app.orchestrator.workflow_ports import WorkflowError  # noqa: E402

RATING_COLUMNS = list(ev.CRITICAL) + ["distractor_plausibility", "clarity", "note"]


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False).stdout.strip()


def metadata(**extra) -> dict:
    return {"commit": _git("rev-parse", "HEAD"), "git_dirty": bool(_git("status", "--porcelain")),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), **extra}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nearest_rank(values: list[float], q: float) -> float:
    ordered = sorted(values)  # nearest-rank (Hyndman & Fan 1996, definition 1)
    return ordered[max(0, math.ceil(q * len(ordered)) - 1)]


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_offline(args) -> dict:
    report = ev.check_grading(args.cases, args.seed)
    rng = random.Random(args.seed + 1)
    samples = []
    for i in range(args.cases):
        attempt, questions, responses, _ = ev.random_case(rng, i)
        start = time.perf_counter()
        grade_attempt(attempt=attempt, questions_by_id=questions, responses_by_qid=responses,
                      submitted_at="2026-11-18T00:00:00Z")
        samples.append((time.perf_counter() - start) * 1000)
    report["grading_ms"] = {"p50": nearest_rank(samples, 0.5), "p95": nearest_rank(samples, 0.95),
                            "p99": nearest_rank(samples, 0.99)}
    return {"metadata": metadata(), "GRD-C01": report["oracle_match"] / report["cases"],
            "GRD-C02": report["deterministic"] / report["cases"], "details": report}


def cmd_generate(args) -> dict:
    dataset_path = Path(args.dataset)
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    generator = DeepSeekQuestionGenerator(os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                                          os.environ.get("DEEPSEEK_API_KEY", ""), model, None)
    outcomes, latencies, rows = [], [], []
    requested = accepted_total = violations = 0
    for run in range(args.runs):
        for case in dataset["cases"]:
            chunk_ids = {c["chunk_id"] for c in case["chunks"]}
            requested += case["count"]
            start = time.perf_counter()
            try:
                raw, used_model = generator.generate(case["chunks"], topic=case["topic"],
                                                     question_type=case["question_type"], count=case["count"])
                error = None
            except WorkflowError as exc:
                raw, used_model, error = [], model, exc.code
            latencies.append((time.perf_counter() - start) * 1000)
            accepted, rejected = normalize_question_batch(
                raw, user_id="00000000-0000-4000-8000-000000000001",
                conversation_id="00000000-0000-4000-8000-000000000002",
                material_id="00000000-0000-4000-8000-000000000003", topic=case["topic"],
                question_type=case["question_type"], count=case["count"], retrieved_chunk_ids=chunk_ids,
                model=used_model, prompt_version=PROMPT_VERSION,
                now_iso=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"))
            accepted_total += len(accepted)
            case_violations = {d["question_id"]: ev.safety_violations(d, topic=case["topic"],
                                                                      forbidden=case.get("forbidden", []))
                               for d in accepted}
            violations += sum(1 for v in case_violations.values() if v)
            outcomes.append({"run": run, "case_id": case["case_id"], "error": error, "accepted": len(accepted),
                             "rejected": rejected, "safety": {k: v for k, v in case_violations.items() if v}})
            texts = {c["chunk_id"]: c["text"] for c in case["chunks"]}
            for d in accepted:
                rows.append({"question_id": d["question_id"], "case_id": case["case_id"], "topic": d["topic"],
                             "stem": d["stem"], "options": " | ".join(f'{o["option_id"]}: {o["text"]}'
                                                                     for o in d["options"]),
                             "answer_key": d["answer_key"], "explanation": d["explanation"] or "",
                             "sources": "\n---\n".join(texts[c] for c in d["source_chunk_ids"]),
                             **{c: "" for c in RATING_COLUMNS}})
    if args.annotation_csv and rows:
        out = Path(args.annotation_csv)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return {"metadata": metadata(dataset=str(dataset_path.as_posix()), dataset_sha256=sha256(dataset_path),
                                 model=model, prompt_version=PROMPT_VERSION, runs=args.runs),
            "QG-01": accepted_total / requested if requested else 0.0, "requested": requested,
            "accepted": accepted_total, "SAFE-01_violating_items": violations,
            "PERF-02_ms": {"p50": nearest_rank(latencies, 0.5), "p95": nearest_rank(latencies, 0.95)}
            if latencies else None,
            "outcomes": outcomes}


def read_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def cmd_score(args) -> dict:
    report = ev.score_annotations(read_csv(args.rater_a), read_csv(args.rater_b),
                                  read_csv(args.adjudicated) if args.adjudicated else None)
    return {"metadata": metadata(rater_a_sha256=sha256(Path(args.rater_a)),
                                 rater_b_sha256=sha256(Path(args.rater_b))), "QG-02": report}


def cmd_retrieval(args) -> dict:
    path = Path(args.runs)
    return {"metadata": metadata(runs_sha256=sha256(path)),
            "RET-01": ev.retrieval_report(json.loads(path.read_text(encoding="utf-8"))["runs"])}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("offline")
    p.add_argument("--cases", type=int, default=10000)
    p.add_argument("--seed", type=int, default=20261118)
    p = sub.add_parser("generate")
    p.add_argument("--dataset", required=True)
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--annotation-csv")
    p = sub.add_parser("score")
    p.add_argument("--rater-a", required=True)
    p.add_argument("--rater-b", required=True)
    p.add_argument("--adjudicated")
    p = sub.add_parser("retrieval")
    p.add_argument("--runs", required=True)
    for name in ("offline", "generate", "score", "retrieval"):
        sub.choices[name].add_argument("--output", required=True)
    args = parser.parse_args(argv)
    result = {"offline": cmd_offline, "generate": cmd_generate, "score": cmd_score,
              "retrieval": cmd_retrieval}[args.command](args)
    write_json(Path(args.output), result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("outcomes", "details")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
