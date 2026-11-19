"""Deterministic quiz attempt management and pure Python grading for F2 B5."""

from __future__ import annotations

from uuid import UUID, uuid5

from ..clients.rpc import child_key, iso
from ..core import contract
from ..orchestrator.workflow_ports import WorkflowError

VALID_QUESTION_TYPES = ("MCQ", "TRUE_FALSE")
VALID_ORIGINS = ("MANUAL", "SESSION_HANDOFF")


def classify_response(question: dict, selected_option_id: str | None) -> tuple[str, bool | None]:
    """Classify a single quiz response and compute correctness deterministically.

    Rules (B5):
    - Only VERIFIED questions of type MCQ or TRUE_FALSE may be graded.
    - Blank / None selected_option_id -> ('OMITTED', None).
    - Option ID not present in question['options'] -> ('INVALID', None).
    - Valid option ID -> ('VALID', selected_option_id == question['answer_key']).
    - Omitted and invalid responses never have is_correct = False.
    """
    if not isinstance(question, dict):
        raise WorkflowError("INVALID_PARAMETER", "Dữ liệu câu hỏi không hợp lệ.", field="question_ids")
    if question.get("status") != "VERIFIED":
        raise WorkflowError(
            "STALE_ENTITY_VERSION",
            "Chỉ câu hỏi đã xác minh (VERIFIED) mới được đưa vào bài làm và chấm điểm.",
            field="question_ids",
        )
    qtype = question.get("question_type")
    if qtype not in VALID_QUESTION_TYPES:
        raise WorkflowError(
            "INVALID_PARAMETER",
            "Loại câu hỏi không được hỗ trợ chấm điểm tự động.",
            field="question_type",
        )
    options = question.get("options")
    if not isinstance(options, list) or not options:
        raise WorkflowError("INVALID_PARAMETER", "Danh sách lựa chọn của câu hỏi không hợp lệ.", field="options")
    option_ids: set[str] = set()
    for opt in options:
        if not isinstance(opt, dict) or not isinstance(opt.get("option_id"), str) or not opt["option_id"].strip():
            raise WorkflowError("INVALID_PARAMETER", "Mã lựa chọn của câu hỏi không hợp lệ.", field="options")
        option_ids.add(opt["option_id"])
    answer_key = question.get("answer_key")
    if not isinstance(answer_key, str) or answer_key not in option_ids:
        raise WorkflowError("INVALID_PARAMETER", "Đáp án chuẩn của câu hỏi không hợp lệ.", field="answer_key")

    if selected_option_id is None:
        return "OMITTED", None
    if not isinstance(selected_option_id, str):
        return "INVALID", None
    if not selected_option_id.strip():
        return "OMITTED", None
    if selected_option_id not in option_ids:
        return "INVALID", None
    return "VALID", selected_option_id == answer_key


def grade_attempt(
    *,
    attempt: dict,
    questions_by_id: dict[str, dict],
    responses_by_qid: dict[str, dict] | None = None,
    submitted_at: str,
) -> dict:
    """Deterministically grade an IN_PROGRESS QuizAttempt in pure Python.

    - Rejects attempts that are already SUBMITTED.
    - Rejects missing, cross-owner, cross-material, or non-VERIFIED questions.
    - Excludes OMITTED and INVALID responses from valid_response_count and never
      counts them in incorrect_count.
    - Sets score_percent = None when valid_response_count == 0.
    """
    if not isinstance(attempt, dict):
        raise WorkflowError("INVALID_PARAMETER", "Dữ liệu lượt làm bài không hợp lệ.")
    if attempt.get("status") != "IN_PROGRESS":
        raise WorkflowError(
            "STALE_ENTITY_VERSION",
            "Lượt làm bài đã được nộp và không thể chấm điểm lại.",
        )
    attempt_id = attempt.get("attempt_id")
    user_id = attempt.get("user_id")
    material_id = attempt.get("material_id")
    question_ids = attempt.get("question_ids")
    if (
        not isinstance(attempt_id, str)
        or not isinstance(user_id, str)
        or not isinstance(material_id, str)
        or not isinstance(question_ids, list)
        or not (1 <= len(question_ids) <= 50)
        or len(set(question_ids)) != len(question_ids)
    ):
        raise WorkflowError("INVALID_PARAMETER", "Danh sách câu hỏi của lượt làm bài không hợp lệ.", field="question_ids")

    saved_map = dict(responses_by_qid or {})
    question_id_set = set(question_ids)
    for qid in saved_map:
        if qid not in question_id_set:
            raise WorkflowError(
                "INVALID_PARAMETER",
                "Câu trả lời không thuộc danh sách câu hỏi của lượt làm bài.",
                field="question_id",
            )

    graded_responses: list[dict] = []
    for qid in question_ids:
        question = (questions_by_id or {}).get(qid)
        if question is None:
            raise WorkflowError(
                "ENTITY_NOT_FOUND",
                "Không tìm thấy câu hỏi thuộc lượt làm bài.",
                field="question_ids",
            )
        if question.get("user_id") != user_id or question.get("material_id") != material_id:
            raise WorkflowError(
                "ENTITY_NOT_FOUND",
                "Câu hỏi không thuộc cùng người dùng hoặc tài liệu của lượt làm bài.",
                field="question_ids",
            )
        saved = saved_map.get(qid)
        raw_selected = saved.get("selected_option_id") if isinstance(saved, dict) else None
        selected_option_id = (
            None
            if raw_selected is None or (isinstance(raw_selected, str) and not raw_selected.strip())
            else raw_selected
        )
        validity, is_correct = classify_response(question, selected_option_id)
        response_id = (
            saved["response_id"]
            if isinstance(saved, dict) and isinstance(saved.get("response_id"), str)
            else str(uuid5(UUID(attempt_id), f"quiz-response:{qid}"))
        )
        created_at = (
            saved["created_at"]
            if isinstance(saved, dict) and isinstance(saved.get("created_at"), str)
            else submitted_at
        )
        graded_responses.append(
            {
                "response_id": response_id,
                "attempt_id": attempt_id,
                "question_id": qid,
                "user_id": user_id,
                "selected_option_id": selected_option_id,
                "validity": validity,
                "is_correct": is_correct,
                "graded_at": submitted_at,
                "created_at": created_at,
                "updated_at": submitted_at,
            }
        )

    total_questions = len(question_ids)
    valid_response_count = sum(1 for r in graded_responses if r["validity"] == "VALID")
    correct_count = sum(1 for r in graded_responses if r["validity"] == "VALID" and r["is_correct"] is True)
    incorrect_count = sum(1 for r in graded_responses if r["validity"] == "VALID" and r["is_correct"] is False)
    omitted_count = total_questions - valid_response_count
    if valid_response_count == 0:
        score_percent = None
    else:
        raw_score = round(correct_count * 100.0 / valid_response_count, 2)
        score_percent = int(raw_score) if raw_score.is_integer() else raw_score

    graded_attempt = {
        **attempt,
        "status": "SUBMITTED",
        "total_questions": total_questions,
        "valid_response_count": valid_response_count,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "omitted_count": omitted_count,
        "score_percent": score_percent,
        "submitted_at": submitted_at,
        "updated_at": submitted_at,
    }
    return {"attempt": graded_attempt, "responses": graded_responses}


class QuizAttemptOperations:
    """Backend service boundary for B5 quiz attempts, response saving, and grading."""

    def __init__(self, rpc, questions, clock):
        self.rpc = rpc
        self.questions = questions
        self.clock = clock
        self._attempts: dict[tuple[str, str], dict] = {}
        self._responses: dict[tuple[str, str], dict[str, dict]] = {}
        self._submit_args: dict[tuple[str, str], dict] = {}
        self._idempotency: dict[tuple[str, str, str], str] = {}

    def _call_rpc(self, ctx, operation: str, arguments: dict, result_schema: str, *, idempotency_key: str) -> dict:
        result = self.rpc(ctx, operation, arguments, idempotency_key=idempotency_key)
        if not contract.is_valid(result_schema, result):
            raise WorkflowError("INTERNAL_ERROR", "Phản hồi bài kiểm tra từ database không đúng contract.")
        if result["outcome"] == "ERROR":
            error = result["error"]
            raise WorkflowError(
                error["code"],
                error["message"],
                field=error.get("field"),
                retryable=bool(error.get("retryable")),
            )
        return result

    def _load_questions_by_id(self, ctx, *, material_id: str | None = None, status: str | None = "VERIFIED") -> dict[str, dict]:
        items_by_id: dict[str, dict] = {}
        cursor: str | None = None
        for _ in range(20):
            res = self.questions.list_questions(
                ctx,
                {
                    "material_id": material_id,
                    "topic": None,
                    "status": status,
                    "page_size": 100,
                    "cursor": cursor,
                },
            )
            data = res["data"]
            for item in data["items"]:
                items_by_id[item["question_id"]] = item
            cursor = data["next_cursor"]
            if cursor is None:
                break
        return items_by_id

    def create_attempt(self, ctx, key: str, body: dict) -> dict:
        if not contract.is_valid("CreateQuizAttemptRequest", body):
            raise WorkflowError("INVALID_PARAMETER", "Yêu cầu tạo lượt làm bài không đúng contract.")
        origin = body["origin"]
        session_outcome_id = body["session_outcome_id"]
        if origin == "MANUAL" and session_outcome_id is not None:
            raise WorkflowError(
                "INVALID_PARAMETER",
                "Lượt làm bài MANUAL không được đính kèm session_outcome_id.",
                field="session_outcome_id",
            )
        if origin == "SESSION_HANDOFF" and session_outcome_id is None:
            raise WorkflowError(
                "INVALID_PARAMETER",
                "Lượt làm bài SESSION_HANDOFF bắt buộc có session_outcome_id.",
                field="session_outcome_id",
            )

        attempt_id = str(uuid5(UUID(ctx.user_id), "quiz-attempt:" + key))
        args = {
            "attempt_id": attempt_id,
            "material_id": str(UUID(body["material_id"])),
            "question_ids": [str(UUID(qid)) for qid in body["question_ids"]],
            "origin": origin,
            "session_outcome_id": str(UUID(session_outcome_id)) if session_outcome_id is not None else None,
        }
        if not contract.is_valid("CreateQuizAttemptArguments", args):
            raise WorkflowError("INVALID_PARAMETER", "Tham số tạo lượt làm bài không đúng contract.")

        result = self._call_rpc(
            ctx,
            "create_quiz_attempt",
            args,
            "QuizAttemptResult",
            idempotency_key=child_key(key, "create-quiz-attempt"),
        )
        attempt = result["data"]
        if (
            attempt["user_id"] != ctx.user_id
            or attempt["attempt_id"] != args["attempt_id"]
            or attempt["material_id"] != args["material_id"]
            or attempt["question_ids"] != args["question_ids"]
            or attempt["origin"] != args["origin"]
            or attempt["session_outcome_id"] != args["session_outcome_id"]
        ):
            raise WorkflowError("ENTITY_NOT_FOUND", "Không tìm thấy lượt làm bài.")
        self._attempts[(ctx.user_id, attempt["attempt_id"])] = dict(attempt)
        self._responses.setdefault((ctx.user_id, attempt["attempt_id"]), {})
        return result

    def save_response(self, ctx, key: str, attempt_id: str, question_id: str, body: dict) -> tuple[dict, bool]:
        if not contract.is_valid("SaveQuizResponseRequest", body):
            raise WorkflowError("INVALID_PARAMETER", "Yêu cầu lưu câu trả lời không đúng contract.")
        attempt_id = str(UUID(attempt_id))
        question_id = str(UUID(question_id))
        selected_option_id = body["selected_option_id"]

        cached_attempt = self._attempts.get((ctx.user_id, attempt_id))
        material_id = cached_attempt["material_id"] if cached_attempt is not None else None
        questions_by_id = self._load_questions_by_id(ctx, material_id=material_id, status="VERIFIED")
        question = questions_by_id.get(question_id)
        if question is None and material_id is not None:
            questions_by_id = self._load_questions_by_id(ctx, material_id=None, status="VERIFIED")
            question = questions_by_id.get(question_id)

        if question is not None:
            validity, _ = classify_response(question, selected_option_id)
        else:
            validity = (
                "OMITTED"
                if selected_option_id is None or (isinstance(selected_option_id, str) and not selected_option_id.strip())
                else "INVALID"
            )

        args = {
            "attempt_id": attempt_id,
            "question_id": question_id,
            "selected_option_id": selected_option_id,
            "validity": validity,
        }
        if not contract.is_valid("SaveQuizResponseArguments", args):
            raise WorkflowError("INVALID_PARAMETER", "Tham số lưu câu trả lời không đúng contract.")

        idem_key = child_key(key, "save-quiz-response")
        fp = contract.sha256_hex(args)
        replayed = self._idempotency.get((ctx.user_id, "save_quiz_response", idem_key)) == fp
        result = self._call_rpc(
            ctx,
            "save_quiz_response",
            args,
            "QuizResponseResult",
            idempotency_key=idem_key,
        )
        resp = result["data"]
        if (
            resp["user_id"] != ctx.user_id
            or resp["attempt_id"] != attempt_id
            or resp["question_id"] != question_id
            or resp["selected_option_id"] != selected_option_id
            or resp["validity"] != validity
            or resp["is_correct"] is not None
            or resp["graded_at"] is not None
        ):
            raise WorkflowError("ENTITY_NOT_FOUND", "Không tìm thấy lượt làm bài hoặc câu hỏi.")
        self._idempotency[(ctx.user_id, "save_quiz_response", idem_key)] = fp
        self._responses.setdefault((ctx.user_id, attempt_id), {})[question_id] = dict(resp)
        return result, replayed

    def submit_attempt(self, ctx, key: str, attempt_id: str, body: dict) -> tuple[dict, bool]:
        if not contract.is_valid("SubmitQuizAttemptRequest", body):
            raise WorkflowError("INVALID_PARAMETER", "Yêu cầu nộp bài không đúng contract.")
        attempt_id = str(UUID(attempt_id))
        idem_key = child_key(key, "submit-quiz-attempt")
        fp = contract.sha256_hex({"attempt_id": attempt_id})
        replayed = self._idempotency.get((ctx.user_id, "submit_quiz_attempt", idem_key)) == fp

        cached_attempt = self._attempts.get((ctx.user_id, attempt_id))
        if cached_attempt is not None and cached_attempt.get("status") == "IN_PROGRESS":
            questions_by_id = self._load_questions_by_id(
                ctx,
                material_id=cached_attempt["material_id"],
                status=None,
            )
            submitted_at = iso(self.clock())
            graded = grade_attempt(
                attempt=cached_attempt,
                questions_by_id=questions_by_id,
                responses_by_qid=self._responses.get((ctx.user_id, attempt_id), {}),
                submitted_at=submitted_at,
            )
            args = {
                "attempt_id": attempt_id,
                "graded_responses": graded["responses"],
                "valid_response_count": graded["attempt"]["valid_response_count"],
                "correct_count": graded["attempt"]["correct_count"],
                "incorrect_count": graded["attempt"]["incorrect_count"],
                "omitted_count": graded["attempt"]["omitted_count"],
                "score_percent": graded["attempt"]["score_percent"],
                "submitted_at": submitted_at,
            }
        elif (ctx.user_id, attempt_id) in self._submit_args:
            args = self._submit_args[(ctx.user_id, attempt_id)]
        else:
            now_iso = iso(self.clock())
            probe_qid = str(uuid5(UUID(attempt_id), "probe-question"))
            args = {
                "attempt_id": attempt_id,
                "graded_responses": [
                    {
                        "response_id": str(uuid5(UUID(attempt_id), f"quiz-response:{probe_qid}")),
                        "attempt_id": attempt_id,
                        "question_id": probe_qid,
                        "user_id": ctx.user_id,
                        "selected_option_id": None,
                        "validity": "OMITTED",
                        "is_correct": None,
                        "graded_at": now_iso,
                        "created_at": now_iso,
                        "updated_at": now_iso,
                    }
                ],
                "valid_response_count": 0,
                "correct_count": 0,
                "incorrect_count": 0,
                "omitted_count": 1,
                "score_percent": None,
                "submitted_at": now_iso,
            }

        if not contract.is_valid("SubmitQuizAttemptArguments", args):
            raise WorkflowError("INVALID_PARAMETER", "Tham số nộp bài không đúng contract.")

        result = self._call_rpc(
            ctx,
            "submit_quiz_attempt",
            args,
            "QuizAttemptSubmissionResult",
            idempotency_key=idem_key,
        )
        data = result["data"]
        sub_attempt = data["attempt"]
        sub_responses = data["responses"]
        if (
            sub_attempt["user_id"] != ctx.user_id
            or sub_attempt["attempt_id"] != attempt_id
            or sub_attempt["status"] != "SUBMITTED"
            or sub_attempt["submitted_at"] is None
            or len(sub_responses) != sub_attempt["total_questions"]
            or any(
                r["user_id"] != ctx.user_id
                or r["attempt_id"] != attempt_id
                or r["graded_at"] is None
                or (r["validity"] in ("OMITTED", "INVALID") and r["is_correct"] is not None)
                for r in sub_responses
            )
        ):
            raise WorkflowError("ENTITY_NOT_FOUND", "Không tìm thấy lượt làm bài.")

        self._attempts[(ctx.user_id, attempt_id)] = dict(sub_attempt)
        self._submit_args[(ctx.user_id, attempt_id)] = args
        self._idempotency[(ctx.user_id, "submit_quiz_attempt", idem_key)] = fp
        return result, replayed
