"""Unit tests for F2 B5 pure Python quiz response classification and deterministic grading."""

from __future__ import annotations

import unittest

from backend.app.assessment.attempts import classify_response, grade_attempt
from backend.app.core import contract
from backend.app.orchestrator.workflow_ports import WorkflowError

USER_A = "00000000-0000-4000-8000-000000000001"
USER_B = "00000000-0000-4000-8000-000000000002"
MAT_A = "00000000-0000-4000-8000-000000000101"
MAT_B = "00000000-0000-4000-8000-000000000102"
ATTEMPT_1 = "00000000-0000-4000-8000-000000000501"
Q_MCQ_1 = "00000000-0000-4000-8000-000000000301"
Q_MCQ_2 = "00000000-0000-4000-8000-000000000302"
Q_TF_1 = "00000000-0000-4000-8000-000000000303"
Q_MCQ_3 = "00000000-0000-4000-8000-000000000304"
STAMP = "2026-11-18T09:00:00.000000Z"


def _mcq_question(
    qid: str = Q_MCQ_1,
    *,
    answer_key: str = "B",
    status: str = "VERIFIED",
    user_id: str = USER_A,
    material_id: str = MAT_A,
) -> dict:
    return {
        "assessment_version": "1.0.0",
        "question_id": qid,
        "user_id": user_id,
        "conversation_id": "00000000-0000-4000-8000-000000000003",
        "material_id": material_id,
        "version": 1,
        "topic": "Mạng máy tính",
        "question_type": "MCQ",
        "stem": "Giao thức nào hướng kết nối ở tầng giao vận?",
        "options": [
            {"option_id": "A", "text": "UDP"},
            {"option_id": "B", "text": "TCP"},
            {"option_id": "C", "text": "ICMP"},
            {"option_id": "D", "text": "ARP"},
        ],
        "answer_key": answer_key,
        "explanation": "TCP thiết lập kết nối ba bước trước khi truyền dữ liệu.",
        "source_chunk_ids": ["00000000-0000-4000-8000-000000000201"],
        "status": status,
        "model": "deepseek-chat",
        "prompt_version": "f2-question-v1",
        "verified_at": "2026-11-18T08:05:00.000000Z" if status == "VERIFIED" else None,
        "created_at": "2026-11-18T08:00:00.000000Z",
        "updated_at": "2026-11-18T08:05:00.000000Z",
    }


def _tf_question(
    qid: str = Q_TF_1,
    *,
    answer_key: str = "TRUE",
    status: str = "VERIFIED",
    user_id: str = USER_A,
    material_id: str = MAT_A,
) -> dict:
    return {
        "assessment_version": "1.0.0",
        "question_id": qid,
        "user_id": user_id,
        "conversation_id": "00000000-0000-4000-8000-000000000003",
        "material_id": material_id,
        "version": 1,
        "topic": "Mạng máy tính",
        "question_type": "TRUE_FALSE",
        "stem": "UDP là giao thức không kết nối.",
        "options": [
            {"option_id": "TRUE", "text": "Đúng"},
            {"option_id": "FALSE", "text": "Sai"},
        ],
        "answer_key": answer_key,
        "explanation": "UDP gửi từng datagram độc lập không cần thiết lập kết nối.",
        "source_chunk_ids": ["00000000-0000-4000-8000-000000000202"],
        "status": status,
        "model": "deepseek-chat",
        "prompt_version": "f2-question-v1",
        "verified_at": "2026-11-18T08:05:00.000000Z" if status == "VERIFIED" else None,
        "created_at": "2026-11-18T08:00:00.000000Z",
        "updated_at": "2026-11-18T08:05:00.000000Z",
    }


def _attempt(
    question_ids: list[str],
    *,
    origin: str = "MANUAL",
    session_outcome_id: str | None = None,
    status: str = "IN_PROGRESS",
) -> dict:
    return {
        "assessment_version": "1.0.0",
        "attempt_id": ATTEMPT_1,
        "user_id": USER_A,
        "material_id": MAT_A,
        "origin": origin,
        "session_outcome_id": session_outcome_id,
        "status": status,
        "question_ids": question_ids,
        "total_questions": len(question_ids),
        "valid_response_count": 0,
        "correct_count": 0,
        "incorrect_count": 0,
        "omitted_count": len(question_ids),
        "score_percent": None,
        "started_at": "2026-11-18T08:30:00.000000Z",
        "submitted_at": None,
        "created_at": "2026-11-18T08:30:00.000000Z",
        "updated_at": "2026-11-18T08:30:00.000000Z",
    }


class QuizGradingUnitTests(unittest.TestCase):
    def test_classify_mcq_correct_and_incorrect(self):
        q = _mcq_question(answer_key="B")
        self.assertEqual(classify_response(q, "B"), ("VALID", True))
        self.assertEqual(classify_response(q, "A"), ("VALID", False))
        self.assertEqual(classify_response(q, "C"), ("VALID", False))

    def test_classify_true_false_correct_and_incorrect(self):
        q = _tf_question(answer_key="TRUE")
        self.assertEqual(classify_response(q, "TRUE"), ("VALID", True))
        self.assertEqual(classify_response(q, "FALSE"), ("VALID", False))

    def test_classify_omitted_and_invalid_never_counted_as_wrong(self):
        q = _mcq_question(answer_key="B")
        self.assertEqual(classify_response(q, None), ("OMITTED", None))
        self.assertEqual(classify_response(q, ""), ("OMITTED", None))
        self.assertEqual(classify_response(q, "   "), ("OMITTED", None))
        self.assertEqual(classify_response(q, "Z"), ("INVALID", None))
        self.assertEqual(classify_response(q, "OPTION_99"), ("INVALID", None))

    def test_classify_rejects_unverified_questions(self):
        for bad_status in ("DRAFT", "REJECTED"):
            with self.subTest(status=bad_status):
                q = _mcq_question(status=bad_status)
                with self.assertRaises(WorkflowError) as ctx:
                    classify_response(q, "B")
                self.assertEqual(ctx.exception.code, "STALE_ENTITY_VERSION")

    def test_grade_attempt_mixed_correct_wrong_omitted_invalid(self):
        questions = {
            Q_MCQ_1: _mcq_question(Q_MCQ_1, answer_key="B"),
            Q_MCQ_2: _mcq_question(Q_MCQ_2, answer_key="D"),
            Q_TF_1: _tf_question(Q_TF_1, answer_key="TRUE"),
            Q_MCQ_3: _mcq_question(Q_MCQ_3, answer_key="A"),
        }
        attempt = _attempt([Q_MCQ_1, Q_MCQ_2, Q_TF_1, Q_MCQ_3])
        responses = {
            Q_MCQ_1: {
                "response_id": "00000000-0000-4000-8000-000000000601",
                "selected_option_id": "B",
                "created_at": "2026-11-18T08:31:00.000000Z",
            },
            Q_MCQ_2: {
                "response_id": "00000000-0000-4000-8000-000000000602",
                "selected_option_id": "A",
                "created_at": "2026-11-18T08:32:00.000000Z",
            },
            Q_TF_1: {
                "response_id": "00000000-0000-4000-8000-000000000603",
                "selected_option_id": "INVALID_OPT",
                "created_at": "2026-11-18T08:33:00.000000Z",
            },
            # Q_MCQ_3 is omitted (not saved at all)
        }

        result = grade_attempt(
            attempt=attempt,
            questions_by_id=questions,
            responses_by_qid=responses,
            submitted_at=STAMP,
        )
        self.assertTrue(contract.is_valid("QuizAttemptSubmissionData", result))

        graded_attempt = result["attempt"]
        self.assertEqual(graded_attempt["status"], "SUBMITTED")
        self.assertEqual(graded_attempt["total_questions"], 4)
        self.assertEqual(graded_attempt["valid_response_count"], 2)
        self.assertEqual(graded_attempt["correct_count"], 1)
        self.assertEqual(graded_attempt["incorrect_count"], 1)
        self.assertEqual(graded_attempt["omitted_count"], 2)
        self.assertEqual(graded_attempt["score_percent"], 50)
        self.assertIs(type(graded_attempt["score_percent"]), int)
        self.assertEqual(graded_attempt["submitted_at"], STAMP)

        by_qid = {r["question_id"]: r for r in result["responses"]}
        self.assertEqual(by_qid[Q_MCQ_1]["validity"], "VALID")
        self.assertIs(by_qid[Q_MCQ_1]["is_correct"], True)
        self.assertEqual(by_qid[Q_MCQ_2]["validity"], "VALID")
        self.assertIs(by_qid[Q_MCQ_2]["is_correct"], False)
        self.assertEqual(by_qid[Q_TF_1]["validity"], "INVALID")
        self.assertIsNone(by_qid[Q_TF_1]["is_correct"])
        self.assertEqual(by_qid[Q_MCQ_3]["validity"], "OMITTED")
        self.assertIsNone(by_qid[Q_MCQ_3]["is_correct"])

    def test_grade_attempt_all_omitted_or_invalid_sets_score_percent_none(self):
        questions = {
            Q_MCQ_1: _mcq_question(Q_MCQ_1, answer_key="B"),
            Q_TF_1: _tf_question(Q_TF_1, answer_key="TRUE"),
        }
        attempt = _attempt(
            [Q_MCQ_1, Q_TF_1],
            origin="SESSION_HANDOFF",
            session_outcome_id="00000000-0000-4000-8000-000000000999",
        )
        responses = {
            Q_MCQ_1: {"selected_option_id": None},
            Q_TF_1: {"selected_option_id": "OUT_OF_RANGE"},
        }

        result = grade_attempt(
            attempt=attempt,
            questions_by_id=questions,
            responses_by_qid=responses,
            submitted_at=STAMP,
        )
        self.assertTrue(contract.is_valid("QuizAttemptSubmissionData", result))
        graded_attempt = result["attempt"]
        self.assertEqual(graded_attempt["valid_response_count"], 0)
        self.assertEqual(graded_attempt["correct_count"], 0)
        self.assertEqual(graded_attempt["incorrect_count"], 0)
        self.assertEqual(graded_attempt["omitted_count"], 2)
        self.assertIsNone(graded_attempt["score_percent"])
        for resp in result["responses"]:
            self.assertIsNone(resp["is_correct"])

    def test_grade_attempt_fractional_score_percent_rounds_to_two_decimals(self):
        questions = {
            Q_MCQ_1: _mcq_question(Q_MCQ_1, answer_key="B"),
            Q_MCQ_2: _mcq_question(Q_MCQ_2, answer_key="D"),
            Q_TF_1: _tf_question(Q_TF_1, answer_key="TRUE"),
        }
        attempt = _attempt([Q_MCQ_1, Q_MCQ_2, Q_TF_1])
        responses = {
            Q_MCQ_1: {"selected_option_id": "B"},
            Q_MCQ_2: {"selected_option_id": "D"},
            Q_TF_1: {"selected_option_id": "FALSE"},
        }
        result = grade_attempt(
            attempt=attempt,
            questions_by_id=questions,
            responses_by_qid=responses,
            submitted_at=STAMP,
        )
        self.assertTrue(contract.is_valid("QuizAttemptSubmissionData", result))
        self.assertEqual(result["attempt"]["score_percent"], 66.67)

    def test_grade_attempt_half_up_rounding_to_two_decimals(self):
        qids = [f"00000000-0000-4000-8000-{i + 1:012d}" for i in range(32)]
        questions = {qid: _mcq_question(qid, answer_key="B") for qid in qids}
        for correct_count, expected_score in ((1, 3.13), (25, 78.13)):
            with self.subTest(correct_count=correct_count):
                attempt = _attempt(qids)
                responses = {
                    qid: {"selected_option_id": "B" if idx < correct_count else "A"}
                    for idx, qid in enumerate(qids)
                }
                result = grade_attempt(
                    attempt=attempt,
                    questions_by_id=questions,
                    responses_by_qid=responses,
                    submitted_at=STAMP,
                )
                self.assertTrue(contract.is_valid("QuizAttemptSubmissionData", result))
                graded_attempt = result["attempt"]
                self.assertEqual(graded_attempt["valid_response_count"], 32)
                self.assertEqual(graded_attempt["correct_count"], correct_count)
                self.assertEqual(graded_attempt["incorrect_count"], 32 - correct_count)
                self.assertEqual(graded_attempt["omitted_count"], 0)
                self.assertEqual(graded_attempt["score_percent"], expected_score)

    def test_grade_attempt_rejects_draft_or_rejected_question(self):
        for bad_status in ("DRAFT", "REJECTED"):
            with self.subTest(status=bad_status):
                questions = {
                    Q_MCQ_1: _mcq_question(Q_MCQ_1, status="VERIFIED"),
                    Q_MCQ_2: _mcq_question(Q_MCQ_2, status=bad_status),
                }
                attempt = _attempt([Q_MCQ_1, Q_MCQ_2])
                with self.assertRaises(WorkflowError) as ctx:
                    grade_attempt(
                        attempt=attempt,
                        questions_by_id=questions,
                        responses_by_qid={Q_MCQ_1: {"selected_option_id": "B"}},
                        submitted_at=STAMP,
                    )
                self.assertEqual(ctx.exception.code, "STALE_ENTITY_VERSION")

    def test_grade_attempt_rejects_missing_or_cross_owner_question(self):
        attempt = _attempt([Q_MCQ_1])
        with self.assertRaises(WorkflowError) as missing_ctx:
            grade_attempt(attempt=attempt, questions_by_id={}, responses_by_qid={}, submitted_at=STAMP)
        self.assertEqual(missing_ctx.exception.code, "ENTITY_NOT_FOUND")

        cross_owner = {Q_MCQ_1: _mcq_question(Q_MCQ_1, user_id=USER_B)}
        with self.assertRaises(WorkflowError) as owner_ctx:
            grade_attempt(attempt=attempt, questions_by_id=cross_owner, responses_by_qid={}, submitted_at=STAMP)
        self.assertEqual(owner_ctx.exception.code, "ENTITY_NOT_FOUND")

        cross_mat = {Q_MCQ_1: _mcq_question(Q_MCQ_1, material_id=MAT_B)}
        with self.assertRaises(WorkflowError) as mat_ctx:
            grade_attempt(attempt=attempt, questions_by_id=cross_mat, responses_by_qid={}, submitted_at=STAMP)
        self.assertEqual(mat_ctx.exception.code, "ENTITY_NOT_FOUND")

    def test_grade_attempt_rejects_already_submitted_attempt(self):
        questions = {Q_MCQ_1: _mcq_question(Q_MCQ_1)}
        attempt = _attempt([Q_MCQ_1], status="SUBMITTED")
        with self.assertRaises(WorkflowError) as ctx:
            grade_attempt(attempt=attempt, questions_by_id=questions, responses_by_qid={}, submitted_at=STAMP)
        self.assertEqual(ctx.exception.code, "STALE_ENTITY_VERSION")


if __name__ == "__main__":
    unittest.main()
