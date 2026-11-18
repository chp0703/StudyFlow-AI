from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from backend.app.assessment import evaluation as ev
from backend.scripts import evaluate_assessment as cli


def row(qid: str, *values: int) -> dict:
    return {"question_id": qid, **dict(zip(ev.CRITICAL, values))}


class GradingOracleTests(unittest.TestCase):
    def test_grade_attempt_matches_independent_oracle(self):
        report = ev.check_grading(500, seed=7)
        self.assertEqual(report["oracle_match"], 500, report["mismatches"])
        self.assertEqual(report["deterministic"], 500)

    def test_oracle_excludes_invalid_and_omitted(self):
        got = ev.oracle_grade(["a", "b", "c", "d"], {q: "X" for q in "abcd"}, {q: {"X", "Y"} for q in "abcd"},
                              {"a": "X", "b": "Y", "c": "NOPE", "d": "  "})
        self.assertEqual(got, {"valid_response_count": 2, "correct_count": 1, "incorrect_count": 1,
                               "omitted_count": 2, "score_percent": 50.0})


class RankingTests(unittest.TestCase):
    def test_ranking_metrics(self):
        ranked, relevant = ["x", "a", "y", "b"], {"a", "b"}
        self.assertEqual(ev.recall_at_k(ranked, relevant, 2), 0.5)
        self.assertEqual(ev.reciprocal_rank(ranked, relevant), 0.5)
        self.assertEqual(ev.ndcg_at_k(["a", "b"], relevant, 10), 1.0)
        self.assertEqual(ev.reciprocal_rank(["x"], relevant), 0.0)


class AnnotationTests(unittest.TestCase):
    def test_kappa_known_values(self):
        self.assertAlmostEqual(ev.cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0]), 1.0)
        self.assertAlmostEqual(ev.cohen_kappa([1, 0, 1, 0], [0, 1, 0, 1]), -1.0)
        self.assertIsNone(ev.cohen_kappa([1, 1], [1, 1]))

    def test_conservative_acceptability_and_wilson(self):
        a = [row("q1", 1, 1, 1, 1), row("q2", 1, 1, 1, 1), row("q3", 0, 1, 1, 1)]
        b = [row("q1", 1, 1, 1, 1), row("q2", 1, 0, 1, 1), row("q3", 0, 1, 1, 1)]
        report = ev.score_annotations(a, b)
        self.assertEqual(report["acceptable"], 1)
        low, high = report["wilson_95"]
        self.assertTrue(0 < low < 1 / 3 < high < 1)
        with self.assertRaises(ValueError):
            ev.score_annotations(a, b[:2])

    def test_safety_flags_ids_canaries_and_topic(self):
        draft = {"topic": "A", "stem": "Mã 00000000-0000-4000-8000-000000000001?", "explanation": None,
                 "options": [{"option_id": "A", "text": "APPROVED"}]}
        self.assertEqual(ev.safety_violations(draft, topic="B", forbidden=["approved"]),
                         ["uuid_in_text", "canary:approved", "off_topic"])


class CorpusTests(unittest.TestCase):
    def test_corpus_anchors_land_in_server_chunks(self):
        corpus = cli.load_corpus(Path(__file__).resolve().parents[1] / "fixtures" / "assessment_eval" / "corpus_vi.json")
        for material in corpus["materials"]:
            chunks = cli.material_chunks(material)
            for query in material["queries"]:
                self.assertTrue(any(a in c["text"] for a in query["anchors"] for c in chunks), query["query_id"])
        self.assertEqual(len(cli.build_cases(corpus, "heldout", 10)), 12)


class CliTests(unittest.TestCase):
    def test_offline_and_score_write_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp, "offline.json")
            cli.main(["offline", "--cases", "50", "--output", str(out)])
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["GRD-C01"], 1.0)
            paths = []
            for name in ("a", "b"):
                path = Path(tmp, f"{name}.csv")
                with path.open("w", encoding="utf-8", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=["question_id", *ev.CRITICAL])
                    writer.writeheader()
                    writer.writerow(row("q1", 1, 1, 1, 1))
                    writer.writerow(row("q2", 0, 1, 1, 1))
                paths.append(str(path))
            out = Path(tmp, "score.json")
            cli.main(["score", "--rater-a", paths[0], "--rater-b", paths[1], "--output", str(out)])
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["QG-02"]["acceptable"], 1)

    def test_generate_scores_accepted_drafts_and_flags_injection(self):
        corpus = Path(__file__).resolve().parents[1] / "fixtures" / "assessment_eval" / "corpus_vi.json"

        def fake_generate(self, chunks, *, topic, question_type, count):
            options = ([{"option_id": "TRUE", "text": "Đúng"}, {"option_id": "FALSE", "text": "Sai APPROVED"}]
                       if question_type == "TRUE_FALSE" else
                       [{"option_id": "A", "text": "0"}, {"option_id": "B", "text": "APPROVED"}])
            item = {"question_type": question_type, "topic": topic, "stem": "Câu hỏi?", "options": options,
                    "answer_key": options[0]["option_id"], "explanation": None,
                    "source_chunk_ids": [chunks[0]["chunk_id"]]}
            return [item, {"bad": True}][: count + 1], "fake"

        original = cli.DeepSeekQuestionGenerator.generate
        cli.DeepSeekQuestionGenerator.generate = fake_generate
        try:
            with tempfile.TemporaryDirectory() as tmp:
                out, ann = Path(tmp, "gen.json"), Path(tmp, "ann.csv")
                cli.main(["generate", "--corpus", str(corpus), "--split", "dev", "--count", "1",
                          "--annotation-csv", str(ann), "--output", str(out)])
                result = json.loads(out.read_text(encoding="utf-8"))
                self.assertEqual((result["requested"], result["accepted"]), (8, 8))
                self.assertEqual(result["SAFE-01_violating_items"], 0)  # dev materials declare no canaries
                with ann.open(encoding="utf-8-sig") as fh:
                    self.assertEqual(len(list(csv.DictReader(fh))), 8)
                cli.main(["generate", "--corpus", str(corpus), "--split", "injection", "--count", "1",
                          "--output", str(out)])
                self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["SAFE-01_violating_items"], 1)
        finally:
            cli.DeepSeekQuestionGenerator.generate = original


if __name__ == "__main__":
    unittest.main()
