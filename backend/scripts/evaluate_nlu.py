#!/usr/bin/env python3
"""Runs the production DeepSeek extractor over the 40-sentence Vietnamese set. Needs DEEPSEEK_API_KEY.

    DEEPSEEK_API_KEY=... python backend/scripts/evaluate_nlu.py

Exit code 0 only when at least 38 of 40 cases pass. Without a key it refuses to run (it never fakes a pass).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app.nlu.evaluation import THRESHOLD, evaluate  # noqa: E402
from backend.app.nlu.extractor import DeepSeekExtractor  # noqa: E402


def main() -> int:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        print("NOT_RUN: set DEEPSEEK_API_KEY to evaluate the real extractor.")
        return 2
    extractor = DeepSeekExtractor(os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"), key,
                                  os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"), None)
    passed, failures = evaluate(extractor)
    for text, reasons in failures:
        print(f"FAIL {text!r}\n    " + "\n    ".join(reasons))
    print(f"{passed}/40 passed (threshold {THRESHOLD})")
    return 0 if passed >= THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(main())
