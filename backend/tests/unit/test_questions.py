"""Unit tests for F2 B3+B4 question normalization, DeepSeek protocol bounds, and read registration."""

from __future__ import annotations

import base64
import json
import unittest

import httpx

from backend.app.assessment.questions import (
    PROMPT_VERSION,
    DeepSeekQuestionGenerator,
    build_bounded_context,
    normalize_question,
    normalize_question_batch,
)
from backend.app.clients.rpc import READ_OPERATIONS
from backend.app.core.config import Settings
from backend.app.orchestrator.workflow_ports import WorkflowError

USER = "d2020000-0000-4000-8000-000000000001"
CONV = "d2020000-0000-4000-8000-000000000003"
MAT = "d2020000-0000-4000-8000-000000000201"
CHUNK_1 = "d2020000-0000-4000-8000-000000000211"
CHUNK_2 = "d2020000-0000-4000-8000-000000000212"
OTHER_CHUNK = "d2020000-0000-4000-8000-000000000299"
NOW = "2026-11-16T08:00:00Z"


def valid_mcq(**overrides) -> dict:
    item = {
        "topic": "Mạng máy tính",
        "question_type": "MCQ",
        "stem": "Giao thức nào truyền dữ liệu tin cậy?",
        "options": [
            {"option_id": "A", "text": "TCP"},
            {"option_id": "B", "text": "UDP"},
        ],
        "answer_key": "A",
        "explanation": "TCP có xác nhận và truyền lại.",
        "source_chunk_ids": [CHUNK_1],
    }
    item.update(overrides)
    return item


class QuestionUnitTests(unittest.TestCase):
    def test_list_questions_is_registered_read_operation(self) -> None:
        self.assertIn("list_questions", READ_OPERATIONS)

    def test_settings_validate_question_generation_bounds(self) -> None:
        secret = base64.b64encode(b"k" * 32).decode()
        ok = Settings(
            supabase_url="https://supabase.example.test",
            supabase_publishable_key="anon",
            rpc_signing_key_id="k1",
            rpc_signing_secret_base64=secret,
        )
        self.assertEqual(ok.question_max_tokens, 2048)
        for bad in (
            {"question_model_timeout_seconds": 0},
            {"question_max_tokens": 100},
            {"question_max_input_chars": 500},
            {"question_max_context_chunks": 21},
            {"question_max_response_bytes": 1024},
        ):
            with self.assertRaises(ValueError):
                Settings(
                    supabase_url="https://supabase.example.test",
                    supabase_publishable_key="anon",
                    rpc_signing_key_id="k1",
                    rpc_signing_secret_base64=secret,
                    **bad,
                )

    def test_bounded_context_caps_chunks_and_chars(self) -> None:
        chunks = [
            {"chunk_id": CHUNK_1, "page": 1, "topic": "T", "text": "A" * 60},
            {"chunk_id": CHUNK_2, "page": 2, "topic": "T", "text": "B" * 60},
        ]
        bounded = build_bounded_context(chunks, max_chunks=5, max_chars=80)
        self.assertEqual([c["chunk_id"] for c in bounded], [CHUNK_1])
        first_only = build_bounded_context(chunks, max_chunks=1, max_chars=40)
        self.assertEqual(len(first_only[0]["text"]), 40)

    def test_normalize_overrides_model_ids_status_and_rejects_bad_items(self) -> None:
        spoofed = valid_mcq(
            question_id="11111111-1111-4111-8111-111111111111",
            user_id="22222222-2222-4222-8222-222222222222",
            status="VERIFIED",
            verified_at="2026-11-16T00:00:00Z",
        )
        normalized = normalize_question(
            spoofed,
            question_id="33333333-3333-4333-8333-333333333333",
            user_id=USER,
            conversation_id=CONV,
            material_id=MAT,
            topic="Mạng máy tính",
            question_type="MCQ",
            retrieved_chunk_ids={CHUNK_1},
            model="deepseek-chat",
            prompt_version=PROMPT_VERSION,
            now_iso=NOW,
        )
        self.assertIsNotNone(normalized)
        assert normalized is not None
        self.assertEqual(normalized["question_id"], "33333333-3333-4333-8333-333333333333")
        self.assertEqual(normalized["user_id"], USER)
        self.assertEqual(normalized["status"], "DRAFT")
        self.assertEqual(normalized["version"], 1)
        self.assertIsNone(normalized["verified_at"])
        self.assertEqual(normalized["prompt_version"], PROMPT_VERSION)

        bad_cases = [
            valid_mcq(options=[{"option_id": "A", "text": "1"}, {"option_id": "A", "text": "2"}]),
            valid_mcq(answer_key="Z"),
            valid_mcq(question_type="TRUE_FALSE"),
            valid_mcq(topic="Chủ đề khác"),
            valid_mcq(source_chunk_ids=[]),
            valid_mcq(source_chunk_ids=[OTHER_CHUNK]),
            valid_mcq(
                question_type="TRUE_FALSE",
                options=[{"option_id": "A", "text": "Đúng"}, {"option_id": "B", "text": "Sai"}],
                answer_key="A",
            ),
        ]
        for bad in bad_cases:
            req_type = bad["question_type"] if bad.get("options") != [{"option_id": "A", "text": "Đúng"}, {"option_id": "B", "text": "Sai"}] else "TRUE_FALSE"
            if bad.get("question_type") == "TRUE_FALSE" and bad.get("answer_key") == "A":
                # Could be wrong type (when checking wrong type) OR bad TRUE_FALSE options
                pass
            self.assertIsNone(
                normalize_question(
                    bad,
                    question_id="33333333-3333-4333-8333-333333333333",
                    user_id=USER,
                    conversation_id=CONV,
                    material_id=MAT,
                    topic="Mạng máy tính",
                    question_type="TRUE_FALSE" if "Đúng" in str(bad) else "MCQ",
                    retrieved_chunk_ids={CHUNK_1},
                    model="deepseek-chat",
                    prompt_version=PROMPT_VERSION,
                    now_iso=NOW,
                )
            )

    def test_partial_batch_keeps_valid_and_true_false(self) -> None:
        tf_ok = {
            "topic": "Mạng máy tính",
            "question_type": "TRUE_FALSE",
            "stem": "UDP không bảo đảm thứ tự gói tin.",
            "options": [{"option_id": "TRUE", "text": "Đúng"}, {"option_id": "FALSE", "text": "Sai"}],
            "answer_key": "TRUE",
            "explanation": None,
            "source_chunk_ids": [CHUNK_1],
        }
        accepted_tf, rej_tf = normalize_question_batch(
            [tf_ok, {**tf_ok, "answer_key": "NOPE"}],
            user_id=USER,
            conversation_id=CONV,
            material_id=MAT,
            topic="Mạng máy tính",
            question_type="TRUE_FALSE",
            count=2,
            retrieved_chunk_ids={CHUNK_1},
            model="deepseek-chat",
            prompt_version=PROMPT_VERSION,
            now_iso=NOW,
        )
        self.assertEqual(len(accepted_tf), 1)
        self.assertEqual(rej_tf, 1)

        accepted, rejected = normalize_question_batch(
            [valid_mcq(), valid_mcq(answer_key="Z"), valid_mcq(), valid_mcq(), valid_mcq()],
            user_id=USER,
            conversation_id=CONV,
            material_id=MAT,
            topic="Mạng máy tính",
            question_type="MCQ",
            count=5,
            retrieved_chunk_ids={CHUNK_1},
            model="deepseek-chat",
            prompt_version=PROMPT_VERSION,
            now_iso=NOW,
        )
        self.assertEqual(len(accepted), 4)
        self.assertEqual(rejected, 1)

    def test_padded_topic_preserved_exactly_on_normalized_draft(self) -> None:
        padded = "  Mạng máy tính  "
        raw = valid_mcq(topic="Mạng máy tính")
        normalized = normalize_question(
            raw,
            question_id="33333333-3333-4333-8333-333333333333",
            user_id=USER,
            conversation_id=CONV,
            material_id=MAT,
            topic=padded,
            question_type="MCQ",
            retrieved_chunk_ids={CHUNK_1},
            model="deepseek-chat",
            prompt_version=PROMPT_VERSION,
            now_iso=NOW,
        )
        self.assertIsNotNone(normalized)
        assert normalized is not None
        self.assertEqual(normalized["topic"], padded)

    def test_deepseek_single_bounded_call_no_retry_and_protocol_validation(self) -> None:
        chunks = [{"chunk_id": CHUNK_1, "page": 1, "topic": "Mạng máy tính", "text": "TCP tin cậy."}]
        scenarios = (
            "timeout", "status_500", "length_finish", "malformed_json", "extra_top_key",
            "too_large", "null_choice", "bad_message", "duplicate_top_key", "duplicate_nested_key", "nonfinite_nan",
        )
        for scenario in scenarios:
            calls = []

            def handler(request: httpx.Request, kind=scenario):
                calls.append(json.loads(request.content.decode()))
                if kind == "timeout":
                    raise httpx.ReadTimeout("timed out", request=request)
                if kind == "status_500":
                    return httpx.Response(500, json={"error": "down"})
                if kind == "length_finish":
                    return httpx.Response(200, json={
                        "choices": [{"finish_reason": "length", "message": {"content": json.dumps({"questions": [valid_mcq()]})}}]
                    })
                if kind == "malformed_json":
                    return httpx.Response(200, json={
                        "choices": [{"finish_reason": "stop", "message": {"content": "{truncated"}}]
                    })
                if kind == "extra_top_key":
                    return httpx.Response(200, json={
                        "choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"questions": [valid_mcq()], "approve": True})}}]
                    })
                if kind == "null_choice":
                    return httpx.Response(200, json={"choices": [None]})
                if kind == "bad_message":
                    return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": "not-a-dict"}]})
                if kind == "duplicate_top_key":
                    raw_dup = '{"questions": [], "questions": [' + json.dumps(valid_mcq()) + "]}"
                    return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": raw_dup}}]})
                if kind == "duplicate_nested_key":
                    q_dup = '{"topic":"Mạng máy tính","topic":"Mạng máy tính","question_type":"MCQ","stem":"Q","options":[{"option_id":"A","text":"1"},{"option_id":"B","text":"2"}],"answer_key":"A","source_chunk_ids":["' + CHUNK_1 + '"]}'
                    return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": '{"questions": [' + q_dup + "]}"}}]})
                if kind == "nonfinite_nan":
                    raw_nan = '{"questions": [{"score": NaN}]}'
                    return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": raw_nan}}]})
                return httpx.Response(200, content=b"{" + b" " * 5000 + b"}")

            gen = DeepSeekQuestionGenerator(
                "https://deepseek.example.test/v1",
                "k-test",
                "deepseek-chat",
                httpx.MockTransport(handler),
                timeout_seconds=5.0,
                max_tokens=512,
                max_input_chars=2000,
                max_context_chunks=4,
                max_response_bytes=4096,
            )
            with self.assertRaises(WorkflowError) as ctx:
                gen.generate(chunks, topic="Mạng máy tính", question_type="MCQ", count=1)
            self.assertEqual(ctx.exception.code, "SERVICE_UNAVAILABLE")
            self.assertIs(ctx.exception.retryable, False)
            self.assertEqual(len(calls), 1, f"{scenario} must never auto-retry")
            self.assertEqual(calls[0]["max_tokens"], 512)


if __name__ == "__main__":
    unittest.main()
