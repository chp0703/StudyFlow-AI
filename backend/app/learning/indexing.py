"""Document indexing pipeline for F3 Daily AI Learning."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from ..core.config import LEARNING_EMBEDDING_MODEL
from ..ingestion.document import read_document_pages
from .chunking import chunk_f2_pages, chunk_f3_pages
from .embedding import (
    check_deadline,
    embed_passages,
    get_embedding_model,
    resolve_deadline,
)
from .exceptions import IndexTimeoutError, IndexUnavailableError, InvalidDocumentError

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGES = 50
MAX_TEXT = 200_000
DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class IndexDocumentResult:
    """Result of material indexing containing physical stats, F3 and F2 chunks."""

    page_count: int
    char_count: int
    f3_chunks: list[dict[str, Any]]
    f2_chunks: list[dict[str, Any]]


def index_document(
    content: bytes,
    mime_type: str,
    *,
    deadline: float | None = None,
    timeout_seconds: float | None = None,
    model: Any = None,
    tokenizer: Any = None,
    batch_size: int = 16,
    max_bytes: int = MAX_BYTES,
    max_pages: int = MAX_PAGES,
    max_text: int = MAX_TEXT,
    model_name: str = LEARNING_EMBEDDING_MODEL,
) -> IndexDocumentResult:
    """Extract pages, chunk for F3 and F2, and embed F3 chunks on CPU.

    Deterministic public API designed for next HTTP phase and background workers.
    Raises:
        IndexTimeoutError: if deadline exceeded or PDF worker timed out
        InvalidDocumentError: corrupt, encrypted, scan, empty, or bounds exceeded
        IndexUnavailableError: missing pypdf or sentence-transformers dependencies
    """
    dl = resolve_deadline(deadline, timeout_seconds)
    check_deadline(dl)

    pdf_timeout = DEFAULT_TIMEOUT_SECONDS
    if dl is not None:
        remaining = dl - time.monotonic()
        if remaining <= 0:
            raise IndexTimeoutError("Quá thời gian xử lý tài liệu.")
        pdf_timeout = max(0.1, min(DEFAULT_TIMEOUT_SECONDS, remaining))

    # Page extraction reusing read_document_pages with typed failure mode
    pages = read_document_pages(
        content,
        mime_type,
        max_bytes=max_bytes,
        max_pages=max_pages,
        max_text=max_text,
        timeout=pdf_timeout,
        typed_errors=True,
    )

    check_deadline(dl)

    page_count = len(pages)
    char_count = len("\n".join(pages))

    # F2 projection chunking
    f2_chunks = chunk_f2_pages(pages, max_chunk_size=2000, max_rows=500)
    check_deadline(dl)

    if any('\x00' in page for page in pages):
        raise InvalidDocumentError('Văn bản chứa ký tự không hợp lệ.')
    if model is None:
        model = get_embedding_model(model_name)
    active_tokenizer = tokenizer if tokenizer is not None else getattr(model, 'tokenizer', None)
    if active_tokenizer is None:
        raise IndexUnavailableError('Không thể khởi tạo tokenizer cho embedding.')
    check_deadline(dl)

    # F3 chunking with tokenizer token budget enforcement
    f3_chunk_records = chunk_f3_pages(
        pages,
        tokenizer=active_tokenizer,
        target_chars=800,
        overlap_chars=100,
        max_tokens=512,
    )
    check_deadline(dl)

    # CPU Embedding generation for F3 chunks
    if f3_chunk_records:
        passages = [chunk["text"] for chunk in f3_chunk_records]
        vectors = embed_passages(
            passages,
            model=model,
            model_name=model_name,
            batch_size=batch_size,
            deadline=dl,
        )
        if len(vectors) != len(f3_chunk_records):
            raise IndexUnavailableError('Số vector embedding không khớp số chunk.')
        for chunk, vec in zip(f3_chunk_records, vectors):
            chunk["vector"] = vec
            chunk["embedding_model"] = model_name

    check_deadline(dl)

    return IndexDocumentResult(
        page_count=page_count,
        char_count=char_count,
        f3_chunks=f3_chunk_records,
        f2_chunks=f2_chunks,
    )
