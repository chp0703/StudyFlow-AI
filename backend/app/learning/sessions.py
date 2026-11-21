"""Daily AI Learning session, grounded Q&A, and progressive hint endpoints (F3 M2 + M3)."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from fastapi.concurrency import run_in_threadpool

from ..api.v1.http import STATUS, ApiError, respond
from ..core import contract
from ..core.config import Settings
from .answer import (
    PROMPT_VERSION_ASK,
    PROMPT_VERSION_HINT,
    UNSUPPORTED_ANSWER,
    LearningModel,
    LearningModelError,
    LearningModelUnavailable,
    NormalizedAnswer,
    build_ask_messages,
    build_hint_messages,
    build_session_context,
    has_sufficient_grounding,
    normalize_learning_answer,
)
from .embedding import embed_query
from .exceptions import IndexingError
from .hints import normalize_hint_answer, resolve_hint_target_and_level

log = logging.getLogger(__name__)
DEFAULT_RETRIEVAL_K = 6
_LEARNING_STATUS = {
    **STATUS,
    "INVALID_PARAMETER": 400,
    "MISSING_REQUIRED_FIELD": 400,
}


def _response(result: dict[str, Any], ctx, schema: str, *, write: bool = False, replayed: bool = False):
    if not contract.is_valid(schema, result):
        raise ApiError("INTERNAL_ERROR", "Kết quả phiên học không đúng contract.")
    if result["outcome"] == "ERROR":
        code = result["error"]["code"]
        return respond(
            result,
            _LEARNING_STATUS.get(code, 500),
            ctx.request_id,
            post=write,
            retry_after=1 if code == "SERVICE_UNAVAILABLE" else None,
        )
    return respond(result, 200, ctx.request_id, post=write, replayed=replayed)


class LearningSessionOperations:
    def __init__(
        self,
        rpc,
        settings: Settings,
        *,
        embedder: Callable[[str], list[float]] | None = None,
        model: LearningModel | None = None,
    ):
        self.rpc = rpc
        self.settings = settings
        self.embedder = embedder or embed_query
        self.model = model

    async def create_session(self, ctx, key: str, body: dict[str, Any]):
        if not contract.is_valid("DailyLearningSessionCreateRequest", body):
            raise ApiError("INVALID_PARAMETER", "Yêu cầu tạo phiên học không đúng định dạng.", status=400)
        args = {
            "goal": body["goal"],
            "material_ids": body["material_ids"],
            "planner_block_id": body.get("planner_block_id"),
            "fingerprint": contract.sha256_hex(body),
        }
        result = await run_in_threadpool(self.rpc, ctx, "create_learning_session", args, idempotency_key=key)
        if result["outcome"] == "ERROR":
            return _response(result, ctx, "DailyLearningSessionCreateResult", write=True)
        data = result["data"]
        session = data["session"]
        if session["owner_id"] != ctx.user_id:
            raise ApiError("INTERNAL_ERROR", "Kết quả phiên học không đúng chủ sở hữu.")
        return _response(
            {**result, "data": session},
            ctx,
            "DailyLearningSessionCreateResult",
            write=True,
            replayed=bool(data["replayed"]),
        )

    async def get_session(self, ctx, session_id: str):
        result = await run_in_threadpool(self.rpc, ctx, "get_learning_session", {"session_id": session_id})
        if result["outcome"] == "READ":
            session = result["data"]["session"]
            if session["owner_id"] != ctx.user_id:
                raise ApiError("INTERNAL_ERROR", "Kết quả phiên học không đúng chủ sở hữu.")
        return _response(result, ctx, "DailyLearningSessionReadResult")

    async def add_turn(self, ctx, key: str, session_id: str, body: dict[str, Any]):
        if not contract.is_valid("DailyLearningTurnRequest", body):
            raise ApiError("INVALID_PARAMETER", "Yêu cầu lượt học không đúng định dạng.", status=400)

        fingerprint = contract.sha256_hex({"session_id": session_id, "body": body})
        receipt = await run_in_threadpool(
            self.rpc,
            ctx,
            "lookup_learning_turn_receipt",
            {"session_id": session_id, "idempotency_key": key, "fingerprint": fingerprint},
        )
        if receipt["outcome"] == "ERROR":
            return _response(receipt, ctx, "DailyLearningTurnResult", write=True)
        if receipt["data"]["found"]:
            return _response(
                {**receipt, "outcome": "COMMITTED", "data": receipt["data"]["data"]},
                ctx,
                "DailyLearningTurnResult",
                write=True,
                replayed=True,
            )

        loaded = await run_in_threadpool(self.rpc, ctx, "get_learning_session", {"session_id": session_id})
        if loaded["outcome"] == "ERROR":
            return _response(loaded, ctx, "DailyLearningTurnResult", write=True)

        session = loaded["data"]["session"]
        turns = loaded["data"]["turns"]
        if session["owner_id"] != ctx.user_id:
            raise ApiError("INTERNAL_ERROR", "Kết quả phiên học không đúng chủ sở hữu.")
        if session["status"] != "ACTIVE":
            raise ApiError(
                "TIME_CONFLICT",
                "Phiên học không còn ở trạng thái hoạt động.",
                status=409,
            )

        kind = body["kind"]
        if kind == "ASK":
            target_question = body["text"].strip()
            user_content = target_question
            hint_level: int | None = None
            prior_answer: str | None = None
        else:
            target = resolve_hint_target_and_level(turns, body.get("text"))
            target_question = target.question
            user_content = target.user_content
            hint_level = target.hint_level
            prior_answer = target.prior_answer

        try:
            query_vector = await run_in_threadpool(self.embedder, target_question)
        except IndexingError:
            raise ApiError(
                "SERVICE_UNAVAILABLE",
                "Dịch vụ embedding hiện không khả dụng.",
                status=503,
                retryable=True,
                retry_after=1,
            ) from None
        except Exception:
            log.error("Learning query embedding failed request_id=%s", ctx.request_id)
            raise ApiError(
                "SERVICE_UNAVAILABLE",
                "Không thể tạo vector truy vấn lúc này.",
                status=503,
                retryable=True,
                retry_after=1,
            ) from None

        embedding_literal = json.dumps(query_vector, allow_nan=False, separators=(",", ":"))
        retrieved = await run_in_threadpool(
            self.rpc,
            ctx,
            "search_learning_material_chunks",
            {
                "session_id": session_id,
                "query_embedding": embedding_literal,
                "query_text": target_question,
                "k": DEFAULT_RETRIEVAL_K,
            },
        )
        if retrieved["outcome"] == "ERROR":
            return _response(retrieved, ctx, "DailyLearningTurnResult", write=True)

        chunks = retrieved["data"]["chunks"]
        if not has_sufficient_grounding(chunks, threshold=self.settings.learning_grounding_threshold):
            normalized = NormalizedAnswer(
                content=UNSUPPORTED_ANSWER,
                citations=[],
                supported=False,
                model=None,
                prompt_version=None,
            )
        else:
            if self.model is None:
                raise ApiError(
                    "SERVICE_UNAVAILABLE",
                    "Chưa cấu hình dịch vụ mô hình học tập trên server.",
                    status=503,
                    retryable=True,
                    retry_after=1,
                )
            session_context = build_session_context(
                turns, recent_limit=self.settings.learning_context_recent_turns
            )
            if kind == "ASK":
                messages = build_ask_messages(
                    goal=session["goal"],
                    question=target_question,
                    chunks=chunks,
                    session_context=session_context,
                )
                prompt_version = PROMPT_VERSION_ASK
            else:
                assert hint_level is not None
                messages = build_hint_messages(
                    goal=session["goal"],
                    question=target_question,
                    hint_level=hint_level,
                    chunks=chunks,
                    session_context=session_context,
                )
                prompt_version = PROMPT_VERSION_HINT

            try:
                raw_output, model_name = await run_in_threadpool(self.model.generate, messages)
            except (LearningModelUnavailable, LearningModelError) as exc:
                raise ApiError(
                    "SERVICE_UNAVAILABLE",
                    str(exc),
                    status=503,
                    retryable=True,
                    retry_after=1,
                ) from None

            if kind == "ASK":
                normalized = normalize_learning_answer(
                    raw_output, chunks, model=model_name, prompt_version=prompt_version
                )
            else:
                assert hint_level is not None
                normalized = normalize_hint_answer(
                    raw_output,
                    chunks,
                    hint_level=hint_level,
                    prior_answer=prior_answer,
                    model=model_name,
                    prompt_version=prompt_version,
                )

        last_ordinal = max((int(t["ordinal"]) for t in turns), default=0)
        append_args = {
            "session_id": session_id,
            "fingerprint": fingerprint,
            "expected_last_ordinal": last_ordinal,
            "kind": kind,
            "user_content": user_content,
            "assistant_content": normalized.content,
            "hint_level": hint_level,
            "citations": normalized.citations,
            "supported": normalized.supported,
            "model": normalized.model,
            "prompt_version": normalized.prompt_version,
        }
        persisted = await run_in_threadpool(
            self.rpc, ctx, "append_learning_turn", append_args, idempotency_key=key
        )
        if persisted["outcome"] == "ERROR":
            return _response(persisted, ctx, "DailyLearningTurnResult", write=True)

        data = persisted["data"]
        replayed = bool(data["replayed"])
        payload = {"user_turn": data["user_turn"], "assistant_turn": data["assistant_turn"]}
        return _response(
            {**persisted, "data": payload},
            ctx,
            "DailyLearningTurnResult",
            write=True,
            replayed=replayed,
        )
