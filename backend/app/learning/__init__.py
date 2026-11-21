"""Daily AI Learning package for document extraction, indexing, retrieval, Q&A, and hints."""

from .answer import (
    PROMPT_VERSION_ASK,
    PROMPT_VERSION_HINT,
    QUOTE_CLOSE,
    QUOTE_OPEN,
    UNSUPPORTED_ANSWER,
    DeepSeekLearningModel,
    LearningModelError,
    LearningModelUnavailable,
    NormalizedAnswer,
    build_ask_messages,
    build_hint_messages,
    build_session_context,
    has_sufficient_grounding,
    normalize_learning_answer,
)
from .chunking import (
    chunk_f2_pages,
    chunk_f3_page,
    chunk_f3_pages,
    count_passage_tokens,
)
from .embedding import (
    clear_embedding_cache,
    embed_passages,
    embed_query,
    get_embedding_model,
    set_cached_model,
)
from .exceptions import (
    IndexingError,
    IndexTimeoutError,
    IndexUnavailableError,
    InvalidDocumentError,
)
from .hints import (
    IMPLICIT_HINT_USER_CONTENT,
    HintTarget,
    build_safe_hint_fallback,
    is_hint_too_close_to_answer,
    normalize_hint_answer,
    resolve_hint_target_and_level,
)
from .indexing import IndexDocumentResult, index_document
from .sessions import LearningSessionOperations

__all__ = [
    "IndexDocumentResult",
    "index_document",
    "IndexingError",
    "IndexTimeoutError",
    "InvalidDocumentError",
    "IndexUnavailableError",
    "chunk_f2_pages",
    "chunk_f3_page",
    "chunk_f3_pages",
    "count_passage_tokens",
    "embed_passages",
    "embed_query",
    "get_embedding_model",
    "set_cached_model",
    "clear_embedding_cache",
    "UNSUPPORTED_ANSWER",
    "PROMPT_VERSION_ASK",
    "PROMPT_VERSION_HINT",
    "QUOTE_OPEN",
    "QUOTE_CLOSE",
    "DeepSeekLearningModel",
    "LearningModelError",
    "LearningModelUnavailable",
    "NormalizedAnswer",
    "build_ask_messages",
    "build_hint_messages",
    "build_session_context",
    "has_sufficient_grounding",
    "normalize_learning_answer",
    "IMPLICIT_HINT_USER_CONTENT",
    "HintTarget",
    "resolve_hint_target_and_level",
    "is_hint_too_close_to_answer",
    "build_safe_hint_fallback",
    "normalize_hint_answer",
    "LearningSessionOperations",
]
