"""Daily AI Learning package for document extraction, indexing, and embedding."""

from .chunking import (
    chunk_f2_pages,
    chunk_f3_page,
    chunk_f3_pages,
    count_passage_tokens,
)
from .embedding import (
    clear_embedding_cache,
    embed_passages,
    get_embedding_model,
    get_tokenizer,
    set_cached_model,
)
from .exceptions import (
    IndexingError,
    IndexTimeoutError,
    IndexUnavailableError,
    InvalidDocumentError,
)
from .indexing import IndexDocumentResult, index_document

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
    "get_embedding_model",
    "get_tokenizer",
    "set_cached_model",
    "clear_embedding_cache",
]
