"""Progressive 3-level hints and anti-spoiler server checks for Daily AI Learning (F3 M3)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from ..api.v1.http import ApiError
from .answer import NormalizedAnswer, normalize_learning_answer

IMPLICIT_HINT_USER_CONTENT = "Cho mình một gợi ý"

_SPOILER_PHRASES_L1 = (
    "đáp án là",
    "đáp án đúng là",
    "câu trả lời là",
    "câu trả lời đúng là",
    "kết quả cuối cùng là",
    "kết quả là",
    "vậy đáp án",
    "final answer",
    "the answer is",
)
_SPOILER_PHRASES_L2 = (
    "đáp án là",
    "đáp án đúng là",
    "câu trả lời là",
    "câu trả lời đúng là",
    "kết quả cuối cùng là",
    "vậy đáp án",
    "final answer",
    "the answer is",
)


@dataclass(frozen=True)
class HintTarget:
    question: str
    user_content: str
    hint_level: int
    prior_answer: str | None


def _normalize_text(text: str) -> str:
    nfkc = unicodedata.normalize("NFC", text).lower()
    collapsed = re.sub(r"\s+", " ", nfkc).strip()
    return collapsed.strip("?.!,:;\"'()[]{}")


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).lower(), flags=re.UNICODE)


def _token_jaccard(a: str, b: str) -> float:
    ta, tb = set(_tokenize(a)), set(_tokenize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _token_containment(needle: str, haystack: str) -> float:
    tn, th = set(_tokenize(needle)), set(_tokenize(haystack))
    if not tn:
        return 0.0
    return len(tn & th) / len(tn)


def resolve_hint_target_and_level(
    turns: list[dict[str, Any]],
    requested_text: str | None,
) -> HintTarget:
    """Infer target question (if omitted) and assign progressive server-side hint_level 1..3."""
    ordered = sorted(turns, key=lambda t: int(t.get("ordinal", 0)))
    active_question: str | None = None
    hint_counts: dict[str, int] = {}
    last_supported_answer: dict[str, str] = {}

    for turn in ordered:
        role = turn.get("role")
        kind = turn.get("kind")
        content = str(turn.get("content", "")).strip()
        if role == "USER":
            if kind == "ASK" and content:
                active_question = content
            elif kind == "HINT" and content and content != IMPLICIT_HINT_USER_CONTENT:
                active_question = content
        elif role == "ASSISTANT" and active_question:
            key = _normalize_text(active_question)
            if kind == "HINT":
                hint_counts[key] = hint_counts.get(key, 0) + 1
            elif kind == "ASK" and turn.get("supported") is True and content:
                last_supported_answer[key] = content

    if requested_text is None:
        if not active_question:
            raise ApiError(
                "INVALID_PARAMETER",
                "Chưa có câu hỏi trước đó trong phiên để suy ra gợi ý. Hãy nhập nội dung câu hỏi.",
                status=400,
                field="text",
            )
        target_question = active_question
        user_content = IMPLICIT_HINT_USER_CONTENT
    else:
        cleaned = requested_text.strip()
        if not cleaned:
            raise ApiError(
                "INVALID_PARAMETER",
                "Nội dung yêu cầu gợi ý không được rỗng.",
                status=400,
                field="text",
            )
        target_question = cleaned
        user_content = cleaned

    norm_key = _normalize_text(target_question)
    prior_hints = hint_counts.get(norm_key, 0)
    hint_level = min(3, prior_hints + 1)
    prior_answer = last_supported_answer.get(norm_key)
    return HintTarget(
        question=target_question,
        user_content=user_content,
        hint_level=hint_level,
        prior_answer=prior_answer,
    )


def is_hint_too_close_to_answer(
    hint_text: str,
    *,
    hint_level: int,
    prior_answer: str | None = None,
    chunks: list[dict[str, Any]] | None = None,
) -> bool:
    """Reject level 1-2 hints that leak the final answer too directly."""
    # shortcut: heuristic lexical overlap + spoiler-marker check for M3 level 1-2 hints;
    # recalibrate against M5 evaluation data once available.
    if hint_level >= 3:
        return False
    norm_hint = _normalize_text(hint_text)
    if not norm_hint:
        return True

    phrases = _SPOILER_PHRASES_L1 if hint_level == 1 else _SPOILER_PHRASES_L2
    if any(phrase in norm_hint for phrase in phrases):
        return True

    if prior_answer:
        norm_answer = _normalize_text(prior_answer)
        if norm_answer:
            jaccard = _token_jaccard(norm_hint, norm_answer)
            seq_ratio = SequenceMatcher(None, norm_hint, norm_answer).ratio()
            prior_tokens = _tokenize(norm_answer)
            containment = _token_containment(norm_answer, norm_hint) if len(prior_tokens) >= 4 else 0.0
            if jaccard >= 0.65 or seq_ratio >= 0.70 or containment >= 0.80:
                return True

    if chunks:
        jaccard_limit = 0.72 if hint_level == 1 else 0.80
        for chunk in chunks:
            chunk_text = str(chunk.get("text", "")).strip()
            if not chunk_text:
                continue
            norm_chunk = _normalize_text(chunk_text)
            if _token_jaccard(norm_hint, norm_chunk) >= jaccard_limit:
                return True
            if len(norm_chunk) >= 25 and norm_chunk in norm_hint:
                return True
            if hint_level == 1:
                for sentence in re.split(r"[.!?\n]+", chunk_text):
                    norm_sent = _normalize_text(sentence)
                    if len(norm_sent) >= 25 and norm_sent in norm_hint:
                        return True
    return False


def build_safe_hint_fallback(hint_level: int, citations: list[dict[str, Any]]) -> str:
    """Grounded non-spoiler fallback cue when a level 1-2 model draft reveals too much."""
    pages = sorted({int(c["page"]) for c in citations if "page" in c})
    if hint_level == 1:
        return (
            "Hãy bắt đầu bằng cách xem lại định nghĩa và khái niệm nền tảng liên quan đến câu hỏi này "
            "trong tài liệu đã chọn trước khi rút ra kết luận cuối cùng."
        )
    if pages:
        page_label = ", ".join(str(p) for p in pages)
        return (
            f"Hãy đọc kỹ lại đoạn liên quan ở trang {page_label} trong tài liệu đã chọn "
            "và đối chiếu điều kiện đề bài với các dữ kiện nêu ở đó."
        )
    return (
        "Hãy xem lại đoạn trích dẫn liên quan trong tài liệu đã chọn "
        "và tách từng dữ kiện trước khi đi đến bước giải tiếp theo."
    )


def normalize_hint_answer(
    raw: object,
    retrieved_chunks: list[dict[str, Any]],
    *,
    hint_level: int,
    prior_answer: str | None,
    model: str | None,
    prompt_version: str | None,
) -> NormalizedAnswer:
    """Normalize model hint JSON and enforce level 1-2 anti-spoiler guard."""
    normalized = normalize_learning_answer(
        raw,
        retrieved_chunks,
        model=model,
        prompt_version=prompt_version,
    )
    if not normalized.supported:
        return normalized

    if hint_level in (1, 2) and is_hint_too_close_to_answer(
        normalized.content,
        hint_level=hint_level,
        prior_answer=prior_answer,
        chunks=retrieved_chunks,
    ):
        return NormalizedAnswer(
            content=build_safe_hint_fallback(hint_level, normalized.citations),
            citations=normalized.citations,
            supported=True,
            model=normalized.model,
            prompt_version=normalized.prompt_version,
            spoiler_filtered=True,
        )
    return normalized
