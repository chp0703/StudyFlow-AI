"""Chấm bộ trích xuất bằng tập đánh giá tiếng Việt (backend/tests/fixtures/nlu_eval_vi.json).

Một ca chỉ đạt khi thứ tự ý định khớp hoàn toàn và mọi điều kiện slot đều đúng. Các kiểu kiểm tra:
  "path": value            bằng nhau (đường dẫn có dấu chấm, ví dụ "window.weekday")
  "contains:path": text    chứa chuỗi con, không phân biệt hoa thường
  "instant:path": iso      cùng thời điểm, bất kể offset
  "absent:path": true      slot thiếu hoặc null
  "set:path": [..]         cùng phần tử, không xét thứ tự
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

DATASET = Path(__file__).resolve().parents[2] / "tests/fixtures/nlu_eval_vi.json"
THRESHOLD = 38  # trên tổng 40 ca (>= 95%)


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
    """Trả lý do ca đánh giá thất bại; danh sách rỗng nghĩa là đạt."""
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
        except Exception as exc:  # noqa: BLE001 - bộ trích xuất bị lỗi chỉ làm trượt ca đó, không dừng cả lượt đánh giá
            reasons = [f"error: {type(exc).__name__}"]
        if reasons:
            failures.append((case["text"], reasons))
        else:
            passed += 1
    return passed, failures
