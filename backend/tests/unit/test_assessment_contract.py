"""Unit tests for the F2 Assessment & Adaptive Revision 1.0.0 contract extension (B1)."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from backend.app.core import contract
from contracts.check_contract import validate_instance

ROOT = Path(__file__).resolve().parents[3]
CONTRACTS = ROOT / "contracts"
DEFS = contract.SCHEMA["$defs"]

USER = "00000000-0000-4000-8000-000000000001"
CONV = "00000000-0000-4000-8000-000000000003"
MATERIAL = "00000000-0000-4000-8000-000000000201"
CHUNK = "00000000-0000-4000-8000-000000000211"
QUESTION = "00000000-0000-4000-8000-000000000221"
ATTEMPT = "00000000-0000-4000-8000-000000000231"


def read_json(rel_path: str):
    return json.loads((CONTRACTS / rel_path).read_text(encoding="utf-8"))


class AssessmentContractTests(unittest.TestCase):
    def test_material_upload_request_is_closed_and_rejects_owner_injection(self) -> None:
        body = {
            "schema_version": "1.1",
            "conversation_id": CONV,
            "filename": "chuong_2_xac_suat.pdf",
            "mime_type": "application/pdf",
            "content_base64": "aGk=",
            "topics": ["Kỳ vọng", "Phương sai"],
        }
        self.assertTrue(contract.is_valid("MaterialUploadRequest", body))
        self.assertFalse(contract.is_valid("MaterialUploadRequest", {**body, "user_id": USER}))
        self.assertFalse(contract.is_valid("MaterialUploadRequest", {**body, "topics": []}))
        self.assertFalse(contract.is_valid("MaterialUploadRequest", {**body, "topics": ["Kỳ vọng", "Kỳ vọng"]}))

    def test_question_draft_enforces_source_chunks_answer_key_and_verified_timestamp(self) -> None:
        draft = read_json("examples/valid/QuestionDraft.json")
        self.assertEqual(validate_instance(DEFS, "QuestionDraft", draft), [])

        no_chunks = {**draft, "source_chunk_ids": []}
        self.assertTrue(validate_instance(DEFS, "QuestionDraft", no_chunks))

        bad_key = {**draft, "answer_key": "Z"}
        self.assertIn(
            "answer_key must match one of the question options",
            " ".join(validate_instance(DEFS, "QuestionDraft", bad_key)),
        )

        unverified_with_ts = {**draft, "status": "DRAFT", "verified_at": "2026-11-16T08:05:00Z"}
        self.assertIn(
            "verified_at must be present iff question status is VERIFIED",
            " ".join(validate_instance(DEFS, "QuestionDraft", unverified_with_ts)),
        )

        true_false = {
            **draft,
            "question_type": "TRUE_FALSE",
            "options": [
                {"option_id": "TRUE", "text": "Đúng"},
                {"option_id": "FALSE", "text": "Sai"},
            ],
            "answer_key": "TRUE",
        }
        self.assertEqual(validate_instance(DEFS, "QuestionDraft", true_false), [])

        bad_tf = {
            **true_false,
            "options": [
                {"option_id": "A", "text": "Đúng"},
                {"option_id": "B", "text": "Sai"},
            ],
            "answer_key": "A",
        }
        self.assertIn(
            "TRUE_FALSE question must have exact option_ids TRUE and FALSE",
            " ".join(validate_instance(DEFS, "QuestionDraft", bad_tf)),
        )

    def test_quiz_attempt_and_response_enforce_origin_and_omitted_invariants(self) -> None:
        attempt = read_json("examples/valid/QuizAttempt.json")
        self.assertEqual(validate_instance(DEFS, "QuizAttempt", attempt), [])

        handoff = {
            **attempt,
            "origin": "SESSION_HANDOFF",
            "session_outcome_id": "00000000-0000-4000-8000-000000000299",
        }
        self.assertEqual(validate_instance(DEFS, "QuizAttempt", handoff), [])
        self.assertTrue(validate_instance(DEFS, "QuizAttempt", {**handoff, "session_outcome_id": None}))

        response = read_json("examples/valid/QuizResponse.json")
        self.assertEqual(validate_instance(DEFS, "QuizResponse", response), [])
        self.assertTrue(validate_instance(DEFS, "QuizResponse", {**response, "is_correct": False}))
        self.assertTrue(
            validate_instance(
                DEFS,
                "QuizResponse",
                {**response, "validity": "INVALID", "selected_option_id": "X", "is_correct": False},
            )
        )

    def test_topic_stats_and_recommendations_preserve_evidence_and_insufficient_data(self) -> None:
        stats = read_json("examples/valid/TopicStatsData.json")
        self.assertEqual(validate_instance(DEFS, "TopicStatsData", stats), [])

        bad_stats = copy.deepcopy(stats)
        bad_stats["items"][1]["status"] = "AVAILABLE"
        bad_stats["items"][1]["error_rate"] = 0.0
        self.assertIn(
            "zero valid responses must report INSUFFICIENT_DATA",
            " ".join(validate_instance(DEFS, "TopicStatsData", bad_stats)),
        )

        rec = read_json("examples/valid/RevisionRecommendation.json")
        self.assertEqual(validate_instance(DEFS, "RevisionRecommendation", rec), [])

        bad_rec = copy.deepcopy(rec)
        bad_rec["evidence"]["error_count"] = 5
        self.assertIn(
            "recommendation evidence error_count cannot exceed valid_response_count",
            " ".join(validate_instance(DEFS, "RevisionRecommendation", bad_rec)),
        )

    def test_f2_b3_b4_pending_action_tool_result_command_and_receipt_contracts(self) -> None:
        presentation = read_json("examples/valid/QuestionDraftActionPresentation.json")
        self.assertEqual(validate_instance(DEFS, "ActionPresentation", presentation), [])

        # Existing F1 ActionPresentation payloads without question_drafts stay valid.
        f1_action = read_json("examples/valid/PendingAction.json")
        f1_presentation = {
            "kind": "ACTION_PRESENTATION",
            "pending_action": f1_action,
            "candidate": None,
            "proposal": None,
            "normalized_command": None,
            "effective_policy": None,
            "schedule_confirmation": None,
        }
        self.assertEqual(validate_instance(DEFS, "ActionPresentation", f1_presentation), [])

        batch_data = presentation["question_drafts"]
        for outcome in ("DRAFTED", "COMMITTED", "REJECTED"):
            tool_result = {
                "schema_version": "1.1",
                "request_id": "req-b3-b4-1",
                "outcome": outcome,
                "data": batch_data,
                "error": None,
                "warnings": [],
            }
            self.assertEqual(validate_instance(DEFS, "ToolResult", tool_result), [])

        list_result = {
            "schema_version": "1.1",
            "request_id": "req-b3-b4-2",
            "outcome": "READ",
            "data": {"items": batch_data["items"], "next_cursor": None},
            "error": None,
            "warnings": [],
        }
        self.assertEqual(validate_instance(DEFS, "ToolResult", list_result), [])

        self.assertTrue(
            contract.is_valid(
                "LookupOperationResultArguments",
                {
                    "operation": "create_question_drafts",
                    "idempotency_key": "b3-b4-idempotency-key",
                    "request_fingerprint": "0" * 64,
                },
            )
        )
        self.assertTrue(
            contract.is_valid(
                "ClaimApiReceiptArguments",
                {
                    "http_operation": "generate_question_drafts",
                    "idempotency_key": "b3-b4-idempotency-key",
                    "request_fingerprint": "0" * 64,
                    "conversation_id": CONV,
                },
            )
        )


if __name__ == "__main__":
    unittest.main()
