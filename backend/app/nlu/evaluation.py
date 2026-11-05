"""Scoring of an extractor against the Vietnamese evaluation set (backend/tests/fixtures/nlu_eval_vi.json).

A case passes only when the intent sequence matches exactly and every listed slot check holds. Checks:
  "path": value            equality (dotted path, e.g. "window.weekday")
  "contains:path": text    case-insensitive substring
  "instant:path": iso      same instant, whatever the offset
  "absent:path": true      slot missing or null
  "set:path": [..]         same elements, any order
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

DATASET = Path(__file__).resolve().parents[2] / "tests/fixtures/nlu_eval_vi.json"
THRESHOLD = 38  # of 40 (>= 95%)


def load() -> dict:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def _get(slots: dict, path: str):
    value = slots
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _instant(text) -> datetime | None:
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None


def check_slot(slots: dict, check: str, expected) -> str | None:
    kind, _, path = check.partition(":") if check.split(":")[0] in ("contains", "instant", "absent", "set") else ("eq", "", check)
    actual = _get(slots, path)
    if kind == "eq":
        ok = actual == expected
    elif kind == "contains":
        ok = isinstance(actual, str) and expected.lower() in actual.lower()
    elif kind == "instant":
        a, b = _instant(actual), _instant(expected)
        ok = a is not None and b is not None and a.tzinfo is not None and a == b
    elif kind == "absent":
        ok = actual is None
    else:
        ok = isinstance(actual, list) and sorted(actual) == sorted(expected)
    return None if ok else f"{check}: expected {expected!r}, got {actual!r}"


def score_case(case: dict, extraction: dict) -> list[str]:
    """Returns the reasons a case failed; empty means it passed."""
    got, wanted = extraction["intents"], case["intents"]
    names = [i["intent"] for i in got]
    if len(got) != len(wanted) or any(g not in w["intent"].split("|") for g, w in zip(names, wanted)):
        return [f"intents: expected {[w['intent'] for w in wanted]}, got {names}"]
    problems = []
    for item, want in zip(got, wanted):
        for check, expected in want.get("slots", {}).items():
            problem = check_slot(item["slots"], check, expected)
            if problem:
                problems.append(problem)
    return problems


def evaluate(extractor, dataset: dict | None = None) -> tuple[int, list[tuple[str, list[str]]]]:
    dataset = dataset or load()
    now = datetime.fromisoformat(dataset["now"])
    passed, failures = 0, []
    for case in dataset["cases"]:
        try:
            reasons = score_case(case, extractor.extract(case["text"], now=now, timezone=dataset["timezone"], active=None))
        except Exception as exc:  # noqa: BLE001 - a crashing extractor fails the case, not the run
            reasons = [f"error: {type(exc).__name__}"]
        if reasons:
            failures.append((case["text"], reasons))
        else:
            passed += 1
    return passed, failures
