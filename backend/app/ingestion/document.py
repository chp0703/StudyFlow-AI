"""Text extraction. PDFs run in a bounded-time subprocess with stderr suppressed."""

from __future__ import annotations

import json
import subprocess
import sys

from ..orchestrator.workflow_ports import WorkflowError
from .models import MAX_TEXT, decode_text, invalid


def read_document(content: bytes, mime_type: str) -> str:
    if mime_type in ('text/plain', 'text/markdown'):
        text = decode_text(content)
    elif mime_type == 'application/pdf':
        try:
            run = subprocess.run([sys.executable, '-m', 'backend.app.ingestion.pdf_worker'], input=content,
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5, check=False)
            result = json.loads(run.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired):
            raise invalid('PDF không hợp lệ hoặc vượt giới hạn xử lý.') from None
        if result.get('error') == 'DEPENDENCY_MISSING':
            raise WorkflowError('SERVICE_UNAVAILABLE', 'Chưa cài bộ đọc PDF trên server.')
        if run.returncode or 'text' not in result:
            raise invalid('PDF cần 1–20 trang có chữ, không mã hóa; trang scan hãy gửi dưới dạng ảnh.')
        text = result['text']
    else:
        raise invalid()
    if not text.strip() or len(text) > MAX_TEXT:
        raise invalid('Văn bản rỗng hoặc vượt giới hạn 24.000 ký tự.')
    return text
