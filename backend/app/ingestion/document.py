"""Text extraction. PDFs run in a bounded-time subprocess with stderr suppressed."""

from __future__ import annotations

import json
import subprocess
import sys

from ..orchestrator.workflow_ports import WorkflowError
from .models import MAX_BYTES, MAX_TEXT, decode_text, invalid


class IndexingError(WorkflowError):
    """Base exception for document extraction and indexing errors."""


class IndexTimeoutError(IndexingError):
    def __init__(self, message: str = "Quá thời gian xử lý tài liệu."):
        super().__init__("INDEX_TIMEOUT", message, retryable=True)


class InvalidDocumentError(IndexingError):
    def __init__(self, message: str = "Tài liệu không hợp lệ hoặc vượt giới hạn xử lý."):
        super().__init__("INVALID_DOCUMENT", message, retryable=False)


class IndexUnavailableError(IndexingError):
    def __init__(self, message: str = "Chưa cài bộ đọc PDF hoặc mô hình trên server."):
        super().__init__("INDEX_UNAVAILABLE", message, retryable=True)


def read_document(content: bytes, mime_type: str) -> str:
    return '\n'.join(read_document_pages(content, mime_type))


def read_document_pages(content: bytes, mime_type: str, *, max_bytes=MAX_BYTES,
                        max_pages=20, max_text=MAX_TEXT, timeout=5,
                        typed_errors: bool = False) -> list[str]:
    if len(content) > max_bytes:
        if typed_errors:
            raise InvalidDocumentError('Tệp vượt giới hạn xử lý.')
        raise invalid('Tệp vượt giới hạn xử lý.')
    if mime_type in ('text/plain', 'text/markdown'):
        try:
            pages = [decode_text(content)]
        except WorkflowError as exc:
            if typed_errors:
                raise InvalidDocumentError(exc.message) from None
            raise
    elif mime_type == 'application/pdf':
        try:
            run = subprocess.run([sys.executable, '-m', 'backend.app.ingestion.pdf_worker',
                                  str(max_bytes), str(max_pages), str(max_text)], input=content,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
        except subprocess.TimeoutExpired:
            if typed_errors:
                raise IndexTimeoutError('Quá thời gian xử lý PDF.') from None
            raise invalid('PDF không hợp lệ hoặc vượt giới hạn xử lý.') from None
        except (OSError, ValueError):
            if typed_errors:
                raise InvalidDocumentError('PDF không hợp lệ hoặc vượt giới hạn xử lý.') from None
            raise invalid('PDF không hợp lệ hoặc vượt giới hạn xử lý.') from None
        try:
            result = json.loads(run.stdout)
        except (OSError, ValueError, TypeError):
            if typed_errors:
                raise InvalidDocumentError('PDF không hợp lệ hoặc vượt giới hạn xử lý.') from None
            raise invalid('PDF không hợp lệ hoặc vượt giới hạn xử lý.') from None
        if result.get('error') == 'DEPENDENCY_MISSING':
            if typed_errors:
                raise IndexUnavailableError('Chưa cài bộ đọc PDF trên server.')
            raise WorkflowError('SERVICE_UNAVAILABLE', 'Chưa cài bộ đọc PDF trên server.')
        if run.returncode or 'pages' not in result:
            msg = f'PDF cần 1–{max_pages} trang có chữ, không mã hóa; chưa hỗ trợ PDF scan.'
            if typed_errors:
                raise InvalidDocumentError(msg)
            raise invalid(msg)
        pages = result['pages']
    else:
        if typed_errors:
            raise InvalidDocumentError(f'Định dạng {mime_type} không được hỗ trợ.')
        raise invalid()
    if (not isinstance(pages, list) or not 1 <= len(pages) <= max_pages
            or any(not isinstance(p, str) or not p.strip() for p in pages)
            or len('\n'.join(pages)) > max_text):
        msg = f'Văn bản rỗng hoặc vượt giới hạn {max_text} ký tự.'
        if typed_errors:
            raise InvalidDocumentError(msg)
        raise invalid(msg)
    return pages
