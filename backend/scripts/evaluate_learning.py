"""Đo truy hồi F3 trên bộ câu hỏi có trang đúng và chọn ngưỡng căn cứ τ.

Cách dùng: python backend/scripts/evaluate_learning.py [--corpus PATH] [--k 6] [--min-refusal 0.9]
Cần backend/requirements-embedding.txt (intfloat/multilingual-e5-small chạy CPU).

Chỉ số:
- hit@k: trang đúng nằm trong k chunk gần nhất (câu trong tài liệu).
- refusal: tỉ lệ câu ngoài tài liệu bị chặn bởi τ (không gọi model).
- coverage: tỉ lệ câu trong tài liệu vượt τ.
- fabrication: câu vượt τ nhưng trang đúng không nằm trong top-k (rủi ro trả lời sai căn cứ).
τ đề xuất = ngưỡng nhỏ nhất đạt refusal >= --min-refusal (bảo thủ: thà từ chối còn hơn bịa).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.app.learning.chunking import chunk_f3_pages  # noqa: E402
from backend.app.learning.embedding import embed_passages, embed_query, get_embedding_model  # noqa: E402

DEFAULT_CORPUS = ROOT / "backend" / "tests" / "fixtures" / "learning_eval" / "corpus_vi.json"


def evaluate(corpus: dict, model, *, k: int = 6, min_refusal: float = 0.9) -> dict:
    # shortcut: cosine-only top-k; the DB adds FTS via RRF, so hit@k here is a lower bound. τ uses the same
    # best-cosine gate as has_sufficient_grounding, so the threshold transfers unchanged.
    chunks = chunk_f3_pages(corpus["pages"], tokenizer=model.tokenizer, target_chars=800, overlap_chars=100,
                            max_tokens=512)
    vectors = embed_passages([c["text"] for c in chunks], model=model)
    rows = []
    for q in corpus["questions"]:
        qv = embed_query(q["text"], model=model)
        scored = sorted(((sum(a * b for a, b in zip(qv, v)), c) for v, c in zip(vectors, chunks)),
                        key=lambda x: x[0], reverse=True)[:k]
        pages = {p for _, c in scored for p in range(c["page_start"], c["page_end"] + 1)}
        rows.append({"id": q["id"], "page": q["page"], "best": scored[0][0],
                     "hit": q["page"] is not None and q["page"] in pages})
    inside = [r for r in rows if r["page"] is not None]
    outside = [r for r in rows if r["page"] is None]
    grid = []
    for step in range(50, 100):
        tau = step / 100
        passed = [r for r in inside if r["best"] >= tau]
        grid.append({
            "tau": tau,
            "refusal": sum(r["best"] < tau for r in outside) / len(outside),
            "coverage": len(passed) / len(inside),
            "fabrication": sum(not r["hit"] for r in passed) / len(inside),
        })
    chosen = next((g for g in grid if g["refusal"] >= min_refusal), grid[-1])
    return {
        "chunks": len(chunks), "questions_inside": len(inside), "questions_outside": len(outside),
        f"hit@{k}": sum(r["hit"] for r in inside) / len(inside),
        "recommended": chosen, "min_refusal": min_refusal,
        "best_scores": {r["id"]: round(r["best"], 4) for r in rows},
        "grid": grid,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--k", type=int, default=6)
    parser.add_argument("--min-refusal", type=float, default=0.9)
    args = parser.parse_args()
    raw = args.corpus.read_bytes()
    report = evaluate(json.loads(raw), get_embedding_model(), k=args.k, min_refusal=args.min_refusal)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    report = {"metadata": {"commit": commit, "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "corpus": args.corpus.name, "corpus_sha256": hashlib.sha256(raw).hexdigest(),
                           "model": "intfloat/multilingual-e5-small"}, **report}
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
