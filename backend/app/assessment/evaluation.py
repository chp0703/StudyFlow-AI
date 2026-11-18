"""Pure F2 evaluation metrics: grading oracle, retrieval ranking, inter-annotator agreement.

Metric definitions and sources are in docs/features/assessment/evaluation/README.md.
"""

from __future__ import annotations

import math
import random
import re
from uuid import UUID, uuid5

from .attempts import grade_attempt

_NS = UUID("6f1d2c3a-0000-4000-8000-00000000f2e0")


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    # shortcut: duplicates backend/app/nlu/evaluation.py on test/f1-eval-benchmarks; import it once that branch merges.
    if total == 0:
        return 0.0, 1.0
    p = successes / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# ------------------------------------------------------------------ GRD-C01/C02: grading oracle
def oracle_grade(question_ids: list[str], answer_keys: dict[str, str], option_ids: dict[str, set[str]],
                 selected: dict[str, object]) -> dict:
    """Independent restatement of the B5 rules (requirements: only valid responses count)."""
    valid = correct = 0
    for qid in question_ids:
        choice = selected.get(qid)
        if not isinstance(choice, str) or not choice.strip() or choice not in option_ids[qid]:
            continue
        valid += 1
        correct += choice == answer_keys[qid]
    score = None if valid == 0 else round(correct * 100 / valid, 2)
    return {"valid_response_count": valid, "correct_count": correct, "incorrect_count": valid - correct,
            "omitted_count": len(question_ids) - valid, "score_percent": score}


def random_case(rng: random.Random, index: int) -> tuple[dict, dict, dict, dict]:
    user, material = str(uuid5(_NS, "user")), str(uuid5(_NS, "material"))
    attempt_id = str(uuid5(_NS, f"attempt:{index}"))
    questions, selected = {}, {}
    for n in range(rng.randint(1, 50)):
        qid = str(uuid5(_NS, f"q:{index}:{n}"))
        tf = rng.random() < 0.3
        opts = ["TRUE", "FALSE"] if tf else [f"O{k}" for k in range(rng.randint(2, 6))]
        questions[qid] = {"question_id": qid, "user_id": user, "material_id": material, "status": "VERIFIED",
                          "question_type": "TRUE_FALSE" if tf else "MCQ",
                          "options": [{"option_id": o, "text": o} for o in opts], "answer_key": rng.choice(opts)}
        roll = rng.random()
        if roll < 0.1:
            continue  # never saved
        selected[qid] = (None if roll < 0.2 else "   " if roll < 0.25 else "NOPE" if roll < 0.35
                         else rng.choice(opts))
    attempt = {"attempt_id": attempt_id, "user_id": user, "material_id": material,
               "question_ids": list(questions), "status": "IN_PROGRESS"}
    responses = {qid: {"selected_option_id": v} for qid, v in selected.items()}
    return attempt, questions, responses, selected


def check_grading(cases: int, seed: int) -> dict:
    rng = random.Random(seed)
    mismatches, deterministic = [], 0
    for i in range(cases):
        attempt, questions, responses, selected = random_case(rng, i)
        first = grade_attempt(attempt=attempt, questions_by_id=questions, responses_by_qid=responses,
                              submitted_at="2026-11-18T00:00:00Z")
        again = grade_attempt(attempt=attempt, questions_by_id=questions, responses_by_qid=responses,
                              submitted_at="2026-11-18T00:00:00Z")
        deterministic += first == again
        expected = oracle_grade(attempt["question_ids"], {q: v["answer_key"] for q, v in questions.items()},
                                {q: {o["option_id"] for o in v["options"]} for q, v in questions.items()}, selected)
        got = {k: first["attempt"][k] for k in expected}
        if got != expected:
            mismatches.append({"case": i, "expected": expected, "got": got})
    return {"cases": cases, "seed": seed, "oracle_match": cases - len(mismatches),
            "deterministic": deterministic, "mismatches": mismatches[:20]}


# ------------------------------------------------------------------ RET-01: ranking metrics
def recall_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    return len(set(ranked[:k]) & relevant) / len(relevant) if relevant else 0.0


def reciprocal_rank(ranked: list[str], relevant: set[str]) -> float:
    return next((1 / (i + 1) for i, item in enumerate(ranked) if item in relevant), 0.0)


def ndcg_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    """Binary-relevance nDCG (Järvelin & Kekäläinen 2002)."""
    dcg = sum(1 / math.log2(i + 2) for i, item in enumerate(ranked[:k]) if item in relevant)
    ideal = sum(1 / math.log2(i + 2) for i in range(min(k, len(relevant))))
    return dcg / ideal if ideal else 0.0


def retrieval_report(runs: list[dict], k: int = 5) -> dict:
    """runs: [{"query_id", "ranked": [chunk_id...], "relevant": [chunk_id...]}]."""
    rows = [(recall_at_k(r["ranked"], set(r["relevant"]), k), reciprocal_rank(r["ranked"], set(r["relevant"])),
             ndcg_at_k(r["ranked"], set(r["relevant"]), 10)) for r in runs]
    n = len(rows) or 1
    return {"queries": len(rows), f"recall_at_{k}": sum(r[0] for r in rows) / n,
            "mrr": sum(r[1] for r in rows) / n, "ndcg_at_10": sum(r[2] for r in rows) / n}


# ------------------------------------------------------------------ QG-02: human annotation
CRITICAL = ("answer_correct", "answerable_from_source", "single_correct_answer", "on_topic")


def cohen_kappa(a: list[object], b: list[object]) -> float | None:
    """Cohen (1960). None when chance agreement is 1 (both raters constant and equal)."""
    if len(a) != len(b) or not a:
        raise ValueError("ratings must be non-empty and paired")
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    labels = set(a) | set(b)
    expected = sum((a.count(lbl) / n) * (b.count(lbl) / n) for lbl in labels)
    return None if expected == 1 else (observed - expected) / (1 - expected)


def acceptable(row: dict) -> bool:
    return all(int(row[c]) == 1 for c in CRITICAL)


def score_annotations(rater_a: list[dict], rater_b: list[dict], adjudicated: list[dict] | None = None) -> dict:
    """Rows keyed by question_id with 0/1 critical criteria. Acceptability uses adjudicated rows when given,
    otherwise requires both raters to accept (conservative)."""
    by_b = {r["question_id"]: r for r in rater_b}
    pairs = [(r, by_b[r["question_id"]]) for r in rater_a if r["question_id"] in by_b]
    if not pairs or len(pairs) != len(rater_a) or len(pairs) != len(rater_b):
        raise ValueError("raters must annotate the same question_ids")
    kappa = {c: cohen_kappa([int(x[c]) for x, _ in pairs], [int(y[c]) for _, y in pairs]) for c in CRITICAL}
    kappa["acceptable"] = cohen_kappa([acceptable(x) for x, _ in pairs], [acceptable(y) for _, y in pairs])
    if adjudicated is not None:
        final = {r["question_id"]: acceptable(r) for r in adjudicated}
        decisions = [final[x["question_id"]] for x, _ in pairs]
    else:
        decisions = [acceptable(x) and acceptable(y) for x, y in pairs]
    ok = sum(decisions)
    low, high = wilson_interval(ok, len(decisions))
    return {"items": len(decisions), "acceptable": ok, "acceptable_rate": ok / len(decisions),
            "wilson_95": [low, high], "cohen_kappa": kappa}


# ------------------------------------------------------------------ SAFE-01: leakage check on generated drafts
_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"


def safety_violations(draft: dict, *, topic: str, forbidden: list[str]) -> list[str]:
    """Visible text must not echo IDs or attacker canaries, and must stay on the requested topic."""
    text = " ".join([draft["stem"], draft.get("explanation") or ""] + [o["text"] for o in draft["options"]])
    found = []
    if re.search(_UUID, text):
        found.append("uuid_in_text")
    found += [f"canary:{c}" for c in forbidden if c.lower() in text.lower()]
    if draft["topic"] != topic:
        found.append("off_topic")
    return found
