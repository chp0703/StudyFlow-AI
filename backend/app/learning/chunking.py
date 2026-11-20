"""Chunking algorithms for F3 Daily Learning (E5) and F2 Assessment projection."""

from __future__ import annotations

from typing import Any

from .exceptions import InvalidDocumentError

F3_TARGET_CHARS = 800
F3_OVERLAP_CHARS = 100
F3_MAX_TOKENS = 512
E5_PREFIX = "passage: "
F2_CHUNK_SIZE = 2000
F2_MAX_ROWS = 500


def count_passage_tokens(text: str, tokenizer: Any, *, prefix: str = E5_PREFIX) -> int:
    """Count tokens for text formatted with passage prefix and special tokens."""
    if tokenizer is None:
        return 0
    full_text = f"{prefix}{text}"
    if hasattr(tokenizer, "encode"):
        try:
            tokens = tokenizer.encode(full_text, add_special_tokens=True)
            return len(tokens)
        except TypeError:
            tokens = tokenizer.encode(full_text)
            return len(tokens)
    elif callable(tokenizer):
        res = tokenizer(full_text)
        if isinstance(res, dict) and "input_ids" in res:
            return len(res["input_ids"])
        if isinstance(res, list):
            return len(res)
        if isinstance(res, int):
            return res
    return 0


def chunk_f3_page(
    text: str,
    page_number: int,
    *,
    tokenizer: Any = None,
    target_chars: int = F3_TARGET_CHARS,
    overlap_chars: int = F3_OVERLAP_CHARS,
    max_tokens: int = F3_MAX_TOKENS,
    prefix: str = E5_PREFIX,
) -> list[str]:
    """Chunk a single page into overlapping segments fitting tokenizer limits without truncation."""
    text = text.strip()
    if not text:
        return []

    n = len(text)
    chunks: list[str] = []
    start = 0

    while start < n:
        # Advance past leading whitespace
        while start < n and text[start].isspace():
            start += 1
        if start >= n:
            break

        # Candidate end based on target character length
        end = min(start + target_chars, n)

        # Look for whitespace boundary if not at end of text
        if end < n:
            lookback_limit = max(start + 1, end - overlap_chars)
            boundary = end
            while boundary > lookback_limit and not text[boundary - 1].isspace():
                boundary -= 1

            if boundary > lookback_limit:
                end = boundary
            else:
                boundary = end
                while boundary > start + 1 and not text[boundary - 1].isspace():
                    boundary -= 1
                if boundary > start + 1:
                    end = boundary
                # Else: no whitespace found between start and end (handle no whitespace case)

        # Enforce tokenizer constraint without truncation
        if tokenizer is not None:
            candidate = text[start:end].strip()
            if candidate and count_passage_tokens(candidate, tokenizer, prefix=prefix) > max_tokens:
                low = start + 1
                high = end
                best = start + 1
                while low <= high:
                    mid = (low + high) // 2
                    cand = text[start:mid].strip()
                    if not cand:
                        low = mid + 1
                        continue
                    if count_passage_tokens(cand, tokenizer, prefix=prefix) <= max_tokens:
                        best = mid
                        low = mid + 1
                    else:
                        high = mid - 1

                # Try to break at whitespace within bounded slice
                w_boundary = best
                while w_boundary > start + 1 and not text[w_boundary - 1].isspace():
                    w_boundary -= 1
                if w_boundary > start + 1:
                    end = w_boundary
                else:
                    end = best

                candidate = text[start:end].strip()
                if candidate and count_passage_tokens(candidate, tokenizer, prefix=prefix) > max_tokens:
                    raise InvalidDocumentError(
                        "Không thể chia văn bản thành các đoạn thỏa mãn giới hạn token."
                    )

        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)

        if end >= n:
            break

        # Next start calculation with overlap
        next_start = end - overlap_chars if end - start > 2 * overlap_chars else end
        while next_start < end and text[next_start].isspace():
            next_start += 1

        if next_start <= start:
            next_start = start + 1

        start = next_start

    return chunks


def chunk_f3_pages(
    pages: list[str],
    *,
    tokenizer: Any = None,
    target_chars: int = F3_TARGET_CHARS,
    overlap_chars: int = F3_OVERLAP_CHARS,
    max_tokens: int = F3_MAX_TOKENS,
    prefix: str = E5_PREFIX,
) -> list[dict[str, Any]]:
    """Chunk all document pages for F3.

    Each chunk has one-based page_start/page_end equal to the same physical page,
    and a contiguous zero-based chunk_index.
    """
    records: list[dict[str, Any]] = []
    chunk_index = 0

    for page_num, page_text in enumerate(pages, 1):
        page_chunks = chunk_f3_page(
            page_text,
            page_num,
            tokenizer=tokenizer,
            target_chars=target_chars,
            overlap_chars=overlap_chars,
            max_tokens=max_tokens,
            prefix=prefix,
        )
        for piece in page_chunks:
            records.append({
                "chunk_index": chunk_index,
                "page_start": page_num,
                "page_end": page_num,
                "text": piece,
            })
            chunk_index += 1

    return records


def chunk_f2_pages(
    pages: list[str],
    *,
    max_chunk_size: int = F2_CHUNK_SIZE,
    max_rows: int = F2_MAX_ROWS,
) -> list[dict[str, Any]]:
    """Chunk document pages for F2 Assessment projection.

    Reuses Assessment chunking shape: page, chunk_index, text (no embedding),
    <= 2000 chars, no overlap, linked to canonical 1-based page, <= 500 rows.
    """
    chunks: list[dict[str, Any]] = []
    for page_num, page_text in enumerate(pages, 1):
        text = page_text.strip()
        start = 0
        while start < len(text):
            end = min(start + max_chunk_size, len(text))
            if end < len(text):
                boundary = end
                while boundary > start and not text[boundary - 1].isspace():
                    boundary -= 1
                if boundary > start:
                    end = boundary
            piece = text[start:end]
            start = end
            if not piece.strip():
                continue
            index = len(chunks)
            if index >= max_rows:
                raise InvalidDocumentError(
                    f"Số lượng chunk F2 vượt quá giới hạn tối đa ({max_rows} chunk)."
                )
            chunks.append({
                "page": page_num,
                "chunk_index": index,
                "text": piece,
            })
    return chunks
