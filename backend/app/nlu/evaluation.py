"""Đánh giá bộ trích xuất NLU bằng fixture tiếng Việt có version."""

from __future__ import annotations

import json
import math
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DATASET = Path(__file__).resolve().parents[2] / "tests/fixtures/nlu_eval_vi.json"
FREE_TEXT_FIELDS = {"title", "description", "query", "label"}
IGNORED_SEMANTIC_PATHS = {"window.label"}


def load(path: str | Path = DATASET) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def minimum_passes(dataset: dict) -> int:
    rate = dataset.get("minimum_rate")
    cases = dataset.get("cases")
    if not isinstance(rate, (int, float)) or isinstance(rate, bool) or not 0 < rate <= 1:
        raise ValueError("minimum_rate must be greater than 0 and at most 1")
    if not isinstance(cases, list) or not cases:
        raise ValueError("dataset cases must not be empty")
    return math.ceil(len(cases) * rate)


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
    """Chấm các assertion được liệt kê; đây không phải exact match toàn bộ slot."""
    got, wanted = extraction["intents"], case["intents"]
    names = [item["intent"] for item in got]
    if len(got) != len(wanted) or any(g not in w["intent"].split("|") for g, w in zip(names, wanted)):
        return [f"intents: expected {[w['intent'] for w in wanted]}, got {names}"]
    problems = []
    for item, want in zip(got, wanted):
        for check, expected in want.get("slots", {}).items():
            problem = check_slot(item["slots"], check, expected)
            if problem:
                problems.append(problem)
    return problems


def _canonical(path: str, value):
    field = path.rsplit(".", 1)[-1]
    if isinstance(value, dict):
        return {key: _canonical(child, item) for key, item in sorted(value.items())
                if (child := f"{path}.{key}" if path else key) not in IGNORED_SEMANTIC_PATHS}
    if isinstance(value, list):
        items = [_canonical(path, item) for item in value]
        return sorted(items, key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True))
    if isinstance(value, str) and field.endswith("_at"):
        parsed = _instant(value)
        if parsed is not None and parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, str) and field in FREE_TEXT_FIELDS:
        return " ".join(unicodedata.normalize("NFC", value).split()).casefold()
    return value


def _semantic_frame(extraction: dict) -> list[dict]:
    frames = []
    for item in extraction.get("intents", []):
        slots = dict(item.get("slots", {}))
        if item["intent"] == "SEARCH_TASKS":
            slots.setdefault("query", None)
            slots.setdefault("status_filter", [])
        frames.append({"intent": item["intent"], "slots": _canonical("", slots)})
    return frames


def score_exact_case(case: dict, extraction: dict) -> list[str]:
    expected = _semantic_frame({"intents": case["intents"]})
    actual = _semantic_frame(extraction)
    return [] if actual == expected else [f"semantic frame: expected {expected!r}, got {actual!r}"]


def _pairs(intents: list[dict]) -> Counter:
    pairs: Counter = Counter()

    def flatten(index: int, intent: str, value, path: str = "") -> None:
        if isinstance(value, dict) and value:
            for key, item in value.items():
                flatten(index, intent, item, f"{path}.{key}" if path else key)
        else:
            canonical = _canonical(path, value)
            pairs[(index, intent, path, json.dumps(canonical, ensure_ascii=False, sort_keys=True))] += 1

    for index, item in enumerate(_semantic_frame({"intents": intents})):
        flatten(index, item["intent"], item["slots"])
    return pairs


def _prf(expected: Counter, actual: Counter) -> tuple[int, int, int]:
    keys = expected.keys() | actual.keys()
    tp = sum(min(expected[key], actual[key]) for key in keys)
    fp = sum(max(0, actual[key] - expected[key]) for key in keys)
    fn = sum(max(0, expected[key] - actual[key]) for key in keys)
    return tp, fp, fn


def _f1(tp: int, fp: int, fn: int) -> float:
    return 2 * tp / (2 * tp + fp + fn) if tp or fp or fn else 1.0


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("successes and total must describe a non-empty proportion")
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def evaluate_cases(extractor, dataset: dict) -> list[dict]:
    now = datetime.fromisoformat(dataset["now"])
    exact = dataset.get("scoring_mode") == "exact"
    outcomes = []
    for index, case in enumerate(dataset["cases"]):
        prediction = None
        try:
            prediction = extractor.extract(case["text"], now=now, timezone=dataset["timezone"], active=None)
            reasons = (score_exact_case if exact else score_case)(case, prediction)
        except Exception as exc:  # noqa: BLE001 - một lỗi chỉ làm trượt ca tương ứng
            reasons = [f"error: {type(exc).__name__}"]
        outcomes.append({"case_id": case.get("id", f"case-{index + 1:03d}"), "text": case["text"],
                         "passed": not reasons, "reasons": reasons, "prediction": prediction})
    return outcomes


def exact_metrics(dataset: dict, outcomes: list[dict]) -> dict:
    intent_stats: dict[str, list[int]] = {}
    slot_tp = slot_fp = slot_fn = sequence_matches = frame_matches = 0
    labels = set()
    for case, outcome in zip(dataset["cases"], outcomes):
        expected = case["intents"]
        actual = (outcome["prediction"] or {}).get("intents", [])
        expected_names = [item["intent"] for item in expected]
        actual_names = [item.get("intent") for item in actual]
        sequence_matches += expected_names == actual_names
        frame_matches += not score_exact_case(case, outcome["prediction"]) if outcome["prediction"] else 0
        expected_counts, actual_counts = Counter(expected_names), Counter(actual_names)
        labels.update(expected_counts)
        labels.update(actual_counts)
        for label in expected_counts.keys() | actual_counts.keys():
            stats = intent_stats.setdefault(label, [0, 0, 0])
            matched = min(expected_counts[label], actual_counts[label])
            stats[0] += matched
            stats[1] += actual_counts[label] - matched
            stats[2] += expected_counts[label] - matched
        tp, fp, fn = _prf(_pairs(expected), _pairs(actual))
        slot_tp += tp
        slot_fp += fp
        slot_fn += fn
    macro_scores = []
    for label in labels:
        macro_scores.append(_f1(*intent_stats[label]))
    total = len(dataset["cases"])
    low, high = wilson_interval(frame_matches, total)
    return {"case_count": total, "intent_sequence_accuracy": sequence_matches / total,
            "intent_macro_f1": sum(macro_scores) / len(macro_scores) if macro_scores else 1.0,
            "slot_precision": slot_tp / (slot_tp + slot_fp) if slot_tp + slot_fp else 1.0,
            "slot_recall": slot_tp / (slot_tp + slot_fn) if slot_tp + slot_fn else 1.0,
            "slot_micro_f1": _f1(slot_tp, slot_fp, slot_fn), "frame_exact_matches": frame_matches,
            "frame_exact_match_rate": frame_matches / total, "frame_exact_match_wilson_95": [low, high]}


def evaluate(extractor, dataset: dict | None = None) -> tuple[int, list[tuple[str, list[str]]]]:
    dataset = dataset or load()
    outcomes = evaluate_cases(extractor, dataset)
    failures = [(outcome["text"], outcome["reasons"]) for outcome in outcomes if not outcome["passed"]]
    return len(outcomes) - len(failures), failures
