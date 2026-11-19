"""Independent real-PostgreSQL concurrency acceptance tests for durable quiz attempts."""
from __future__ import annotations

import hashlib
import unittest
from uuid import uuid4

from psycopg import sql

from harness import Call, Database, Fixture, stamp, uid


class RealDatabaseQuizAttemptConcurrency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = Database()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        self.fixture = Fixture(self.db)

    def scalar(self, query, params=()):
        return self.db.admin.execute(query, params).fetchone()[0]

    def count(self, table, suffix="", params=()):
        query = sql.SQL("select count(*) from app_private.{} where user_id=%s ").format(sql.Identifier(table)) + sql.SQL(suffix)
        return self.scalar(query, (self.fixture.owner, *params))

    def db_response_version(self, attempt_id: str) -> int:
        return self.scalar(
            "select response_version from app_private.quiz_attempts where user_id=%s and attempt_id=%s",
            (self.fixture.owner, attempt_id),
        )

    def context(self, attempt_id: str) -> dict:
        return self.db.success(
            self.fixture,
            Call("get_quiz_attempt_context", {"attempt_id": attempt_id}, None, uid(), None),
            "READ",
        )

    def error(self, result: dict, codes: set[str], *, field: str | None = None):
        self.assertEqual("ERROR", result["outcome"], result)
        self.assertIsNone(result["data"])
        self.assertIn(result["error"]["code"], codes, result)
        if field is not None:
            self.assertEqual(field, result["error"]["field"], result)

    def quiz_fixture(self) -> tuple[str, str, str, list[str]]:
        conversation, message = self.fixture.source("Create durable quiz attempt concurrency fixture")
        material_id = uid()
        chunk_id = uid()
        text = "TCP truyền dữ liệu hướng kết nối. UDP truyền datagram không kết nối."
        now_iso = stamp()
        self.db.success(
            self.fixture,
            Call(
                "store_assessment_material",
                {
                    "conversation_id": conversation,
                    "material_id": material_id,
                    "filename": "concurrency-quiz.md",
                    "mime_type": "text/markdown",
                    "size_bytes": len(text.encode("utf-8")),
                    "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "page_count": 1,
                    "char_count": len(text),
                    "topics": ["Mạng máy tính"],
                    "chunks": [
                        {
                            "chunk_id": chunk_id,
                            "material_id": material_id,
                            "user_id": self.fixture.owner,
                            "page": 1,
                            "topic": "Mạng máy tính",
                            "chunk_index": 0,
                            "text": text,
                            "created_at": now_iso,
                        }
                    ],
                },
                conversation,
                message,
                self.fixture.key(),
            ),
            "COMMITTED",
        )

        q1_id, q2_id = uid(), uid()
        action_id = uid()

        def make_draft(qid: str, stem: str) -> dict:
            return {
                "assessment_version": "1.0.0",
                "question_id": qid,
                "user_id": self.fixture.owner,
                "conversation_id": conversation,
                "material_id": material_id,
                "version": 1,
                "topic": "Mạng máy tính",
                "question_type": "MCQ",
                "stem": stem,
                "options": [
                    {"option_id": "A", "text": "UDP"},
                    {"option_id": "B", "text": "TCP"},
                    {"option_id": "C", "text": "ICMP"},
                    {"option_id": "D", "text": "ARP"},
                ],
                "answer_key": "B",
                "explanation": "TCP truyền hướng kết nối.",
                "source_chunk_ids": [chunk_id],
                "status": "DRAFT",
                "model": "deepseek-chat",
                "prompt_version": "f2-question-v1",
                "verified_at": None,
                "created_at": now_iso,
                "updated_at": now_iso,
            }

        self.db.success(
            self.fixture,
            Call(
                "create_question_drafts",
                {
                    "conversation_id": conversation,
                    "material_id": material_id,
                    "action_id": action_id,
                    "generation_params": {"topic": "Mạng máy tính", "question_type": "MCQ", "count": 2},
                    "drafts": [
                        make_draft(q1_id, "Giao thức hướng kết nối là gì?"),
                        make_draft(q2_id, "Giao thức đảm bảo thứ tự gói tin là gì?"),
                    ],
                },
                conversation,
                message,
                self.fixture.key(),
            ),
            "DRAFTED",
        )

        approval = {
            "approval_action_id": uid(),
            "user_id": self.fixture.owner,
            "target_type": "PENDING_ACTION",
            "target_id": action_id,
            "target_version": 1,
            "decision": "APPROVE",
            "source": "UI",
            "source_message_id": None,
            "created_at": stamp(),
        }
        reference = {
            "action_id": action_id,
            "action_version": 1,
            "target_type": "PENDING_ACTION",
            "target_id": action_id,
            "target_version": 1,
        }
        self.db.success(
            self.fixture,
            Call(
                "verify_question_drafts",
                {
                    "conversation_id": conversation,
                    "action_id": action_id,
                    "expected_action_version": 1,
                    "question_ids": [q1_id, q2_id],
                    "decision": "APPROVE",
                },
                conversation,
                message,
                self.fixture.key(),
                approval=approval,
                reference=reference,
            ),
            "COMMITTED",
        )

        attempt_id = uid()
        attempt = self.db.success(
            self.fixture,
            Call(
                "create_quiz_attempt",
                {
                    "attempt_id": attempt_id,
                    "material_id": material_id,
                    "question_ids": [q1_id, q2_id],
                    "origin": "MANUAL",
                    "session_outcome_id": None,
                },
                conversation,
                message,
                self.fixture.key(),
            ),
            "COMMITTED",
        )
        self.assertNotIn("response_version", attempt)
        return conversation, message, attempt_id, [q1_id, q2_id]

    def build_submit_args(
        self,
        attempt_id: str,
        question_ids: list[str],
        saved_by_qid: dict[str, dict],
        *,
        expected_response_version: int,
        include_replay_status: bool = True,
    ) -> dict:
        submitted_at = stamp()
        graded_responses = []
        valid_count = 0
        correct_count = 0
        incorrect_count = 0
        for qid in question_ids:
            saved = saved_by_qid.get(qid)
            selected = saved["selected_option_id"] if saved else None
            if selected is None:
                validity = "OMITTED"
                is_correct = None
            elif selected in {"A", "B", "C", "D"}:
                validity = "VALID"
                is_correct = selected == "B"
                valid_count += 1
                if is_correct:
                    correct_count += 1
                else:
                    incorrect_count += 1
            else:
                validity = "INVALID"
                is_correct = None
            graded_responses.append(
                {
                    "response_id": saved["response_id"] if saved else str(uuid4()),
                    "attempt_id": attempt_id,
                    "question_id": qid,
                    "user_id": self.fixture.owner,
                    "selected_option_id": selected,
                    "validity": validity,
                    "is_correct": is_correct,
                    "graded_at": submitted_at,
                    "created_at": saved["created_at"] if saved else submitted_at,
                    "updated_at": submitted_at,
                }
            )
        omitted_count = len(question_ids) - valid_count
        score_percent = None if valid_count == 0 else (correct_count * 100) // valid_count
        return {
            "attempt_id": attempt_id,
            "graded_responses": graded_responses,
            "valid_response_count": valid_count,
            "correct_count": correct_count,
            "incorrect_count": incorrect_count,
            "omitted_count": omitted_count,
            "score_percent": score_percent,
            "submitted_at": submitted_at,
            "expected_response_version": expected_response_version,
            "include_replay_status": include_replay_status,
        }

    def test_same_key_save_quiz_response_race_commits_once_and_replays_as_read(self):
        conversation, message, attempt_id, qids = self.quiz_fixture()
        self.assertEqual(0, self.context(attempt_id)["response_version"])
        self.assertEqual(0, self.db_response_version(attempt_id))

        save_call = Call(
            "save_quiz_response",
            {
                "attempt_id": attempt_id,
                "question_id": qids[0],
                "selected_option_id": "B",
                "validity": "VALID",
                "include_replay_status": True,
            },
            conversation,
            message,
            self.fixture.key(),
        )
        first, second = self.db.race(self.fixture, [save_call, save_call])
        self.assertEqual(["COMMITTED", "READ"], sorted([first["outcome"], second["outcome"]]))
        self.assertNotEqual(first["request_id"], second["request_id"])
        self.assertEqual(first["data"], second["data"])
        self.assertNotIn("response_version", first["data"])
        self.assertEqual("B", first["data"]["selected_option_id"])
        self.assertEqual("VALID", first["data"]["validity"])

        self.assertEqual(1, self.db_response_version(attempt_id))
        ctx = self.context(attempt_id)
        self.assertEqual(1, ctx["response_version"])
        self.assertEqual(1, len(ctx["responses"]))
        self.assertEqual(1, self.count("quiz_responses", "and attempt_id=%s", (attempt_id,)))
        self.assertEqual(
            1,
            self.count("idempotency_records", "and operation='save_quiz_response' and idempotency_key=%s", (save_call.key,)),
        )

        replay = self.db.invoke(self.fixture, save_call)
        self.assertEqual("READ", replay["outcome"])
        self.assertEqual(first["data"], replay["data"])
        self.assertNotIn(replay["request_id"], {first["request_id"], second["request_id"]})
        self.assertEqual(1, self.db_response_version(attempt_id))

    def test_same_key_submit_quiz_attempt_race_commits_once_and_replays_as_read(self):
        conversation, message, attempt_id, qids = self.quiz_fixture()
        saved_q1 = self.db.success(
            self.fixture,
            Call(
                "save_quiz_response",
                {
                    "attempt_id": attempt_id,
                    "question_id": qids[0],
                    "selected_option_id": "B",
                    "validity": "VALID",
                    "include_replay_status": True,
                },
                conversation,
                message,
                self.fixture.key(),
            ),
            "COMMITTED",
        )
        self.assertEqual(1, self.context(attempt_id)["response_version"])

        submit_args = self.build_submit_args(
            attempt_id,
            qids,
            {qids[0]: saved_q1},
            expected_response_version=1,
            include_replay_status=True,
        )
        submit_call = Call("submit_quiz_attempt", submit_args, conversation, message, self.fixture.key())

        first, second = self.db.race(self.fixture, [submit_call, submit_call])
        self.assertEqual(["COMMITTED", "READ"], sorted([first["outcome"], second["outcome"]]))
        self.assertNotEqual(first["request_id"], second["request_id"])
        self.assertEqual(first["data"], second["data"])
        self.assertNotIn("response_version", first["data"]["attempt"])
        self.assertEqual("SUBMITTED", first["data"]["attempt"]["status"])
        self.assertEqual(100, first["data"]["attempt"]["score_percent"])
        self.assertEqual(1, first["data"]["attempt"]["valid_response_count"])
        self.assertEqual(1, first["data"]["attempt"]["omitted_count"])

        self.assertEqual(1, self.db_response_version(attempt_id))
        ctx = self.context(attempt_id)
        self.assertEqual(1, ctx["response_version"])
        self.assertEqual("SUBMITTED", ctx["attempt"]["status"])
        self.assertEqual(
            1,
            self.count("idempotency_records", "and operation='submit_quiz_attempt' and idempotency_key=%s", (submit_call.key,)),
        )

        replay = self.db.invoke(self.fixture, submit_call)
        self.assertEqual("READ", replay["outcome"])
        self.assertEqual(first["data"], replay["data"])
        self.assertNotIn(replay["request_id"], {first["request_id"], second["request_id"]})
        self.assertEqual(1, self.db_response_version(attempt_id))

    def test_save_vs_submit_distinct_keys_race_enforces_snapshot_or_submission_immutability(self):
        conversation, message, attempt_id, qids = self.quiz_fixture()
        saved_q1 = self.db.success(
            self.fixture,
            Call(
                "save_quiz_response",
                {
                    "attempt_id": attempt_id,
                    "question_id": qids[0],
                    "selected_option_id": "B",
                    "validity": "VALID",
                    "include_replay_status": True,
                },
                conversation,
                message,
                self.fixture.key(),
            ),
            "COMMITTED",
        )
        self.assertEqual(1, self.context(attempt_id)["response_version"])

        save_q2_call = Call(
            "save_quiz_response",
            {
                "attempt_id": attempt_id,
                "question_id": qids[1],
                "selected_option_id": "A",
                "validity": "VALID",
                "include_replay_status": True,
            },
            conversation,
            message,
            self.fixture.key(),
        )
        submit_v1_call = Call(
            "submit_quiz_attempt",
            self.build_submit_args(
                attempt_id,
                qids,
                {qids[0]: saved_q1},
                expected_response_version=1,
                include_replay_status=True,
            ),
            conversation,
            message,
            self.fixture.key(),
        )

        save_res, submit_res = self.db.race(self.fixture, [save_q2_call, submit_v1_call])
        self.assertEqual(1, sum(r["outcome"] == "COMMITTED" for r in (save_res, submit_res)), (save_res, submit_res))

        if save_res["outcome"] == "COMMITTED":
            self.error(submit_res, {"STALE_ENTITY_VERSION"}, field="expected_response_version")
            ctx = self.context(attempt_id)
            self.assertEqual("IN_PROGRESS", ctx["attempt"]["status"])
            self.assertEqual(2, ctx["response_version"])
            self.assertEqual(2, self.db_response_version(attempt_id))
            saved_by_qid = {r["question_id"]: r for r in ctx["responses"]}
            self.assertEqual("A", saved_by_qid[qids[1]]["selected_option_id"])

            next_submit = Call(
                "submit_quiz_attempt",
                self.build_submit_args(
                    attempt_id,
                    qids,
                    saved_by_qid,
                    expected_response_version=2,
                    include_replay_status=True,
                ),
                conversation,
                message,
                self.fixture.key(),
            )
            final = self.db.success(self.fixture, next_submit, "COMMITTED")
            self.assertEqual("SUBMITTED", final["attempt"]["status"])
            self.assertEqual(2, final["attempt"]["valid_response_count"])
            self.assertEqual(1, final["attempt"]["correct_count"])
            self.assertEqual(1, final["attempt"]["incorrect_count"])
            self.assertEqual(0, final["attempt"]["omitted_count"])
            self.assertEqual(50, final["attempt"]["score_percent"])
            final_by_qid = {r["question_id"]: r for r in final["responses"]}
            self.assertEqual("A", final_by_qid[qids[1]]["selected_option_id"])
            self.assertIs(False, final_by_qid[qids[1]]["is_correct"])
            self.assertEqual(2, self.db_response_version(attempt_id))
        else:
            self.error(save_res, {"STALE_ENTITY_VERSION"})
            self.assertEqual("SUBMITTED", submit_res["data"]["attempt"]["status"])
            self.assertEqual(100, submit_res["data"]["attempt"]["score_percent"])
            self.assertEqual(1, submit_res["data"]["attempt"]["valid_response_count"])
            self.assertEqual(1, submit_res["data"]["attempt"]["omitted_count"])
            ctx = self.context(attempt_id)
            self.assertEqual("SUBMITTED", ctx["attempt"]["status"])
            self.assertEqual(1, ctx["response_version"])
            self.assertEqual(1, self.db_response_version(attempt_id))
            ctx_by_qid = {r["question_id"]: r for r in ctx["responses"]}
            self.assertIsNone(ctx_by_qid[qids[1]]["selected_option_id"])
            self.assertEqual("OMITTED", ctx_by_qid[qids[1]]["validity"])
            self.assertIsNone(ctx_by_qid[qids[1]]["is_correct"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
