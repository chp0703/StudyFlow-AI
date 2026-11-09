#!/usr/bin/env python3
"""Chạy bộ trích xuất DeepSeek thật trên tập 40 câu tiếng Việt. Cần DEEPSEEK_API_KEY.

    DEEPSEEK_API_KEY=... python backend/scripts/evaluate_nlu.py

Chỉ trả mã thoát 0 khi đạt ít nhất 38/40 ca. Thiếu khóa thì từ chối chạy, không giả kết quả đạt.
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
