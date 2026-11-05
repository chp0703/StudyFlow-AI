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
        self.assertEqual(seen[0].headers["Authorization"], "Bearer test-key")
        message = json.loads(body["messages"][1]["content"])
        self.assertEqual(message["message"], "tìm OOP")
        self.assertEqual(message["context"]["timezone"], "Asia/Ho_Chi_Minh")

    def test_answer_that_is_not_an_extraction_is_an_extraction_error(self):
        for content in ("not json", json.dumps({"intents": []}), json.dumps({"intents": [{"intent": "APPROVE"}]}),
                        json.dumps({"intents": [{"intent": "UNKNOWN", "slots": {}, "raw_expressions": {}, "ambiguities": [], "x": 1}]})):
            with self.subTest(content=content), self.assertRaises(ExtractionError):
                self.run_extract(answer(content))

    def test_transport_failures_are_unavailable_not_extraction_errors(self):
        def boom(request):
            raise httpx.ConnectError("down")

        for handler in (boom, lambda r: httpx.Response(500), lambda r: httpx.Response(200, json={"unexpected": 1})):
            with self.subTest(handler=handler), self.assertRaises(ExtractorUnavailable):
                self.run_extract(handler)

    def test_scripted_and_unavailable_doubles(self):
        scripted = ScriptedExtractor({"a": GOOD})
        self.assertEqual(scripted.extract("a", now=NOW, timezone="UTC", active=None), GOOD)
        self.assertEqual(scripted.extract("b", now=NOW, timezone="UTC", active=None)["intents"][0]["intent"], "UNKNOWN")
        with self.assertRaises(ExtractorUnavailable):
            UnavailableExtractor().extract("a", now=NOW, timezone="UTC", active=None)


if __name__ == "__main__":
    unittest.main()
