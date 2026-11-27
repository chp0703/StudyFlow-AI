import json
import unittest
from datetime import datetime, timezone

import httpx

from backend.app.nlu.extractor import (
    DeepSeekExtractor, ExtractionError, ExtractorUnavailable, ScriptedExtractor, UnavailableExtractor,
)

NOW = datetime(2026, 11, 5, 3, 0, tzinfo=timezone.utc)
GOOD = {"intents": [{"intent": "SEARCH_TASKS", "slots": {"query": "OOP"}, "raw_expressions": {}, "ambiguities": []}]}


def extractor(handler):
    return DeepSeekExtractor("https://llm.example.test/v1", "test-key", "test-model", httpx.MockTransport(handler))


def answer(content):
    return lambda request: httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


class DeepSeekExtractorTests(unittest.TestCase):
    def run_extract(self, handler):
        return extractor(handler).extract("tìm OOP", now=NOW, timezone="Asia/Ho_Chi_Minh", active=None)

    def test_valid_answer_is_returned_and_the_request_is_deterministic_json(self):
        seen = []

        def handler(request):
            seen.append(request)
            return answer(json.dumps(GOOD))(request)

        self.assertEqual(self.run_extract(handler), GOOD)
        body = json.loads(seen[0].content)
        self.assertEqual((body["temperature"], body["response_format"]), (0, {"type": "json_object"}))
        self.assertEqual((body["max_tokens"], body["thinking"], body["reasoning_effort"]),
                         (4096, {"type": "enabled"}, "low"))
        self.assertEqual(seen[0].headers["Authorization"], "Bearer test-key")
        message = json.loads(body["messages"][1]["content"])
        self.assertEqual(message["message"], "tìm OOP")
        self.assertEqual(message["context"]["timezone"], "Asia/Ho_Chi_Minh")

    def test_answer_that_is_not_an_extraction_is_an_extraction_error(self):
        for content in ("not json", json.dumps({"intents": []}), json.dumps({"intents": [{"intent": "APPROVE"}]}),
                        json.dumps({"intents": [{"intent": "UNKNOWN", "slots": {}, "raw_expressions": {}, "ambiguities": [], "x": 1}]})):
            with self.subTest(content=content), self.assertRaises(ExtractionError):
                self.run_extract(answer(content))

    def test_string_ambiguities_become_issues_but_blank_ones_are_still_rejected(self):
        def with_notes(notes):
            return json.dumps({"intents": [{"intent": "UNKNOWN", "slots": {}, "raw_expressions": {}, "ambiguities": notes}]})

        got = self.run_extract(answer(with_notes(["không rõ"])))
        self.assertEqual(got["intents"][0]["ambiguities"],
                         [{"code": "AMBIGUOUS", "message": "không rõ", "field": None, "details": {}}])
        with self.assertRaises(ExtractionError):
            self.run_extract(answer(with_notes(["  "])))

    def test_missing_valid_from_and_view_get_deterministic_defaults(self):
        window = {"kind": "BUSY", "recurrence": "WEEKLY", "timezone": "Asia/Ho_Chi_Minh", "weekday": 2,
                  "start_time": "08:00", "end_time": "10:00"}
        content = json.dumps({"intents": [
            {"intent": "SET_BUSY_INTERVAL", "slots": {"change_type": "ADD", "window": window}, "raw_expressions": {}, "ambiguities": []},
            {"intent": "GET_STUDY_PLAN", "slots": {}, "raw_expressions": {}, "ambiguities": []}]})
        got = self.run_extract(answer(content))["intents"]
        self.assertEqual(got[0]["slots"]["window"]["valid_from"], "2026-11-05")
        self.assertEqual(got[1]["slots"]["view"], "CURRENT")

    def extract_text(self, text, intents, active=None):
        content = json.dumps({"intents": intents})
        return extractor(answer(content)).extract(text, now=NOW, timezone="Asia/Ho_Chi_Minh", active=active)["intents"]

    def test_t24_midnight_becomes_next_day(self):
        task = {"intent": "CREATE_TASK", "slots": {"title": "ôn", "deadline_precision": "DATETIME",
                                                    "deadline_at": "2026-11-06T24:00:00+07:00"},
                "raw_expressions": {"deadline_at": "12h đêm mai"}, "ambiguities": []}
        got = self.extract_text("ôn bài hạn 12h đêm mai", [task])
        self.assertEqual(got[0]["slots"]["deadline_at"], "2026-11-07T00:00:00+07:00")

    def test_invented_deadline_dropped_unless_user_gave_one(self):
        def task():
            return {"intent": "CREATE_TASK", "slots": {"title": "ôn", "start_at": "2026-11-06T09:00:00+07:00",
                                                        "deadline_precision": "DATETIME", "deadline_at": "2026-11-06T09:00:00+07:00"},
                    "raw_expressions": {"deadline_at": "lúc 9h mai"}, "ambiguities": []}
        self.assertNotIn("deadline_at", self.extract_text("học ôn lúc 9h mai", [task()])[0]["slots"])
        self.assertIn("deadline_at", self.extract_text("học ôn lúc 9h mai, hạn 9h", [task()])[0]["slots"])
        self.assertIn("deadline_at", self.extract_text("ngày mai", [task()], active={"intent": "CREATE_TASK"})[0]["slots"])

    def test_weekday_range_expands_to_one_intent_per_day(self):
        window = {"kind": "BUSY", "recurrence": "WEEKLY", "timezone": "Asia/Ho_Chi_Minh", "weekday": 1,
                  "start_time": "19:00", "end_time": "21:00"}
        item = {"intent": "SET_BUSY_INTERVAL", "slots": {"change_type": "ADD", "window": window}, "raw_expressions": {},
                "ambiguities": [{"code": "AMBIGUOUS", "message": "nhiều thứ", "field": None, "details": {"weekdays": [1, 2, 3, 4, 5]}}]}
        got = self.extract_text("bận 19h-21h", [item])
        self.assertEqual([i["slots"]["window"]["weekday"] for i in got], [1, 2, 3, 4, 5])
        item["ambiguities"] = []
        got = self.extract_text("thứ 2 đến thứ 6 bận 19h-21h", [item])
        self.assertEqual([i["slots"]["window"]["weekday"] for i in got], [1, 2, 3, 4, 5])

    def test_duration_after_trong_is_not_a_start_time(self):
        task = {"intent": "CREATE_TASK", "slots": {"title": "vi tích phân", "estimated_minutes": 120,
                                                    "start_at": "2026-11-06T02:00:00+07:00"},
                "raw_expressions": {"estimated_minutes": "trong 2h"}, "ambiguities": []}
        self.assertNotIn("start_at", self.extract_text("học vi tích phân trong 2h ngày mai", [task])[0]["slots"])

    def test_transport_failures_are_unavailable_not_extraction_errors(self):
        def boom(request):
            raise httpx.ConnectError("down")

        for handler in (boom, lambda r: httpx.Response(500), lambda r: httpx.Response(200, json={"unexpected": 1})):
            with self.subTest(handler=handler), self.assertRaises(ExtractorUnavailable):
                self.run_extract(handler)

    def test_scripted_and_unavailable_doubles(self):
        scripted = ScriptedExtractor({"a": GOOD})
        self.assertEqual(scripted.extract("a", now=NOW, timezone="Asia/Ho_Chi_Minh", active=None), GOOD)
        self.assertEqual(scripted.extract("b", now=NOW, timezone="Asia/Ho_Chi_Minh", active=None)["intents"][0]["intent"], "UNKNOWN")
        with self.assertRaises(ExtractorUnavailable):
            UnavailableExtractor().extract("a", now=NOW, timezone="Asia/Ho_Chi_Minh", active=None)

    def test_learning_and_assessment_intents_roundtrip(self):
        wanted = {
            "intents": [
                {"intent": "SUMMARIZE_LEARNING", "slots": {}, "raw_expressions": {}, "ambiguities": []},
                {"intent": "CREATE_QUIZ", "slots": {"topic": "Số chẵn", "count": 5, "question_type": "MCQ"},
                 "raw_expressions": {}, "ambiguities": []},
                {"intent": "PROPOSE_REVISION", "slots": {"topic": "Số chẵn", "suggested_minutes": 30, "priority": 0.5,
                                                         "material": "sohoc.pdf"},
                 "raw_expressions": {}, "ambiguities": []},
            ]
        }
        self.assertEqual(self.run_extract(answer(json.dumps(wanted))), wanted)

    def test_a_declared_free_time_is_unsupported_not_an_error(self):
        said = {"intents": [{"intent": "SET_AVAILABILITY", "slots": {"window": {"kind": "AVAILABILITY"}},
                             "raw_expressions": {}, "ambiguities": []}]}
        result = self.run_extract(answer(json.dumps(said)))
        self.assertEqual((result["intents"][0]["intent"], result["intents"][0]["slots"]), ("UNSUPPORTED", {}))

    def test_create_task_canonical_slots_roundtrip(self):
        canonical_task = {
            "intents": [{
                "intent": "CREATE_TASK",
                "slots": {
                    "title": "Ôn Giải tích",
                    "start_at": "2026-11-06T08:00:00+07:00",
                    "estimated_minutes": 90,
                    "priority": 1,
                    "color": "#596CF0",
                    "description": "Chương 1",
                },
                "raw_expressions": {},
                "ambiguities": [],
            }]
        }
        self.assertEqual(self.run_extract(answer(json.dumps(canonical_task))), canonical_task)

    def test_colloquial_task_time_corrects_model_omission_and_half_hour(self):
        for prompt, raw, expected in (
            ("Học Hóa lúc 8r tối nay trong 1 tiếng rưỡi", "8r tối nay", "2026-11-05T20:30:00+07:00"),
            ("Ngày mai học Lý lúc 11 giờ sáng trong 45 phút, hạn ngày mai lúc 18 giờ", "11 giờ sáng", "2026-11-06T11:00:00+07:00"),
            ("Mai 8h tối học Lịch sử trong 60 phút, à thôi đổi sang 9h tối nha", "8h tối",
             "2026-11-06T21:00:00+07:00"),
            ("lm bt toan mai 9h sang nha, 45p", "mai 9h sang", "2026-11-06T09:00:00+07:00"),
            ("Học Sinh lúc 10h kém 15 sáng mai", "10h kém 15 sáng mai", "2026-11-06T09:45:00+07:00"),
        ):
            with self.subTest(prompt=prompt):
                extracted = {"intents": [{"intent": "CREATE_TASK", "slots": {"title": "Toán", "estimated_minutes": 45},
                                          "raw_expressions": {"start_at": raw}, "ambiguities": []}]}
                result = extractor(answer(json.dumps(extracted))).extract(
                    prompt, now=NOW, timezone="Asia/Ho_Chi_Minh", active=None)
                self.assertEqual(result["intents"][0]["slots"]["start_at"], expected)

    def test_single_vietnamese_weekday_word_normalizes_off_by_one_error(self):
        for prompt, wrong_day, expected_day in (
            ("Tôi bận học thêm mỗi thứ Bảy từ 8h sáng đến 11h trưa.", 7, 6),
            ("Mỗi thứ Hai bận họp từ 14h đến 16h", 2, 1),
            ("Bận mỗi Chủ nhật từ 9h đến 12h", 1, 7),
        ):
            with self.subTest(prompt=prompt):
                window = {"kind": "BUSY", "recurrence": "WEEKLY", "timezone": "Asia/Ho_Chi_Minh",
                          "weekday": wrong_day, "start_time": "08:00", "end_time": "11:00"}
                item = {"intent": "SET_BUSY_INTERVAL", "slots": {"change_type": "ADD", "window": window},
                        "raw_expressions": {}, "ambiguities": []}
                got = self.extract_text(prompt, [item])
                self.assertEqual(got[0]["slots"]["window"]["weekday"], expected_day)

    def test_spelled_vietnamese_weekday_range_expands(self):
        window = {"kind": "BUSY", "recurrence": "WEEKLY", "timezone": "Asia/Ho_Chi_Minh",
                  "weekday": 1, "start_time": "07:00", "end_time": "11:00"}
        item = {"intent": "SET_BUSY_INTERVAL", "slots": {"change_type": "ADD", "window": window},
                "raw_expressions": {}, "ambiguities": []}
        got = self.extract_text("Tôi bận từ thứ Hai đến thứ Sáu lúc 7h đến 11h", [item])
        self.assertEqual([i["slots"]["window"]["weekday"] for i in got], [1, 2, 3, 4, 5])

    def test_timed_review_request_reclassifies_from_propose_revision_to_create_task(self):
        wrong = {"intent": "PROPOSE_REVISION",
                 "slots": {"topic": "Giải tích", "suggested_minutes": 60, "priority": 1},
                 "raw_expressions": {}, "ambiguities": []}
        got = self.extract_text("Ngày mai tôi muốn ôn Giải tích lúc 9h sáng trong 60 phút, ưu tiên cao.", [wrong])
        self.assertEqual(got[0]["intent"], "CREATE_TASK")
        self.assertEqual(got[0]["slots"]["title"], "Giải tích")
        self.assertEqual(got[0]["slots"]["estimated_minutes"], 60)
        self.assertEqual(got[0]["slots"]["priority"], 1)
        self.assertEqual(got[0]["slots"]["start_at"], "2026-11-06T09:00:00+07:00")

    def test_material_revision_request_stays_propose_revision(self):
        legit = {"intent": "PROPOSE_REVISION",
                 "slots": {"topic": "Giải tích", "suggested_minutes": 60, "priority": 1, "material": "gt.pdf"},
                 "raw_expressions": {}, "ambiguities": []}
        got = self.extract_text("Đề xuất ôn tập Giải tích từ tài liệu gt.pdf trong 60 phút", [legit])
        self.assertEqual(got[0]["intent"], "PROPOSE_REVISION")

    def test_vague_part_of_day_without_clock_drops_invented_start_at(self):
        vague = {"intent": "CREATE_TASK",
                 "slots": {"title": "Đại số tuyến tính", "start_at": "2026-11-06T18:00:00+07:00"},
                 "raw_expressions": {"start_at": "tối mai"}, "ambiguities": []}
        got = self.extract_text("Tối mai học bài Đại số tuyến tính", [vague])
        self.assertNotIn("start_at", got[0]["slots"])

    def test_context_uses_vietnam_local_date_before_0700_vn(self):
        seen = []

        def handler(request):
            seen.append(json.loads(request.content))
            return answer(json.dumps(GOOD))(request)

        early_vn_in_utc = datetime(2026, 11, 26, 19, 30, tzinfo=timezone.utc)  # 2026-11-27 02:30 +07:00
        extractor(handler).extract("tìm OOP", now=early_vn_in_utc, timezone="Asia/Ho_Chi_Minh", active=None)
        ctx = json.loads(seen[0]["messages"][1]["content"])["context"]
        self.assertEqual(ctx["current_time"], "2026-11-27T02:30:00+07:00")
        self.assertEqual(ctx["today"], "2026-11-27")


if __name__ == "__main__":
    unittest.main()
