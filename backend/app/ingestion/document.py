"""Text extraction. PDFs run in a bounded-time subprocess with stderr suppressed."""

from __future__ import annotations

import json
import subprocess
import sys

from ..orchestrator.workflow_ports import WorkflowError
from .models import MAX_BYTES, MAX_TEXT, decode_text, invalid


def read_document(content: bytes, mime_type: str) -> str:
    return '\n'.join(read_document_pages(content, mime_type))


def read_document_pages(content: bytes, mime_type: str, *, max_bytes=MAX_BYTES,
                        max_pages=20, max_text=MAX_TEXT, timeout=5) -> list[str]:
    if len(content) > max_bytes:
        raise invalid('Tệp vượt giới hạn xử lý.')
    if mime_type in ('text/plain', 'text/markdown'):
        pages = [decode_text(content)]
    elif mime_type == 'application/pdf':
        try:
            run = subprocess.run([sys.executable, '-m', 'backend.app.ingestion.pdf_worker',
                                  str(max_bytes), str(max_pages), str(max_text)], input=content,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
            result = json.loads(run.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            raise invalid('PDF không hợp lệ hoặc vượt giới hạn xử lý.') from None
        if result.get('error') == 'DEPENDENCY_MISSING':
            raise WorkflowError('SERVICE_UNAVAILABLE', 'Chưa cài bộ đọc PDF trên server.')
        if run.returncode or 'pages' not in result:
            raise invalid(f'PDF cần 1–{max_pages} trang có chữ, không mã hóa; chưa hỗ trợ PDF scan.')
        pages = result['pages']
    else:
        raise invalid()
    if (not isinstance(pages, list) or not 1 <= len(pages) <= max_pages
            or any(not isinstance(p, str) or not p.strip() for p in pages)
            or len('\n'.join(pages)) > max_text):
        raise invalid(f'Văn bản rỗng hoặc vượt giới hạn {max_text} ký tự.')
    return pages
