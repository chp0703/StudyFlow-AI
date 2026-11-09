import copy
import unittest

from backend.app.nlu import evaluation

INTENTS = {"CREATE_TASK", "SEARCH_TASKS", "SET_AVAILABILITY", "SET_BUSY_INTERVAL", "SET_SCHEDULING_PREFERENCES",
           "GENERATE_STUDY_PLAN", "GET_STUDY_PLAN", "UNKNOWN", "UNSUPPORTED"}


def put(slots, path, value):
    *head, last = path.split(".")
    for part in head:
        slots = slots.setdefault(part, {})
    slots[last] = value


def perfect(case):
    """Kết quả trích xuất dựng từ kỳ vọng của chính ca đánh giá; bộ chấm phải chấp nhận."""
    intents = []
    for want in case["intents"]:
        slots = {}
        for check, expected in want.get("slots", {}).items():
            kind, _, path = check.partition(":") if check.split(":")[0] in ("contains", "instant", "absent", "set") else ("eq", "", check)
            if kind != "absent":
                put(slots, path, expected)
        intents.append({"intent": want["intent"].split("|")[0], "slots": slots, "raw_expressions": {}, "ambiguities": []})
    return {"intents": intents}


class EvaluationSetTests(unittest.TestCase):
    def test_dataset_is_the_agreed_size_and_well_formed(self):
        data = evaluation.load()
        self.assertEqual(len(data["cases"]), 40)
        self.assertEqual(len({c["text"] for c in data["cases"]}), 40)
        for case in data["cases"]:
            for want in case["intents"]:
                self.assertTrue(set(want["intent"].split("|")) <= INTENTS, want)

    def test_scorer_accepts_matching_answers_and_rejects_wrong_ones(self):
        for case in evaluation.load()["cases"]:
            with self.subTest(case["text"]):
                good = perfect(case)
                self.assertEqual(evaluation.score_case(case, good), [])
                wrong = copy.deepcopy(good)
                wrong["intents"][0]["intent"] = "GET_STUDY_PLAN" if wrong["intents"][0]["intent"] != "GET_STUDY_PLAN" else "SEARCH_TASKS"
                self.assertNotEqual(evaluation.score_case(case, wrong), [])
                self.assertNotEqual(evaluation.score_case(case, {"intents": good["intents"] * 2}), [])

    def test_slot_checks(self):
        slots = {"title": "Bài OOP", "when": "2026-11-06T17:00:00+07:00", "tags": ["B", "A"], "none": None}
        self.assertIsNone(evaluation.check_slot(slots, "contains:title", "oop"))
        self.assertIsNone(evaluation.check_slot(slots, "instant:when", "2026-11-06T10:00:00Z"))
        self.assertIsNone(evaluation.check_slot(slots, "set:tags", ["A", "B"]))
        self.assertIsNone(evaluation.check_slot(slots, "absent:none", True))
        self.assertIsNone(evaluation.check_slot(slots, "absent:missing", True))
        self.assertIsNotNone(evaluation.check_slot(slots, "instant:when", "2026-11-06T17:00:00Z"))
        self.assertIsNotNone(evaluation.check_slot({"when": "2026-11-06T10:00:00"}, "instant:when", "2026-11-06T10:00:00Z"))
        self.assertIsNotNone(evaluation.check_slot(slots, "title", "oop"))

    def test_whole_run_threshold_logic(self):
        class Perfect:
            def extract(self, text, **_):
                return perfect(next(c for c in evaluation.load()["cases"] if c["text"] == text))

        passed, failures = evaluation.evaluate(Perfect())
        self.assertEqual((passed, failures), (40, []))


if __name__ == "__main__":
    unittest.main()
