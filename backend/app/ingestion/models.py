"""Upload limits and validation shared by the HTTP and extraction boundaries."""

from __future__ import annotations

import base64
import binascii
from pathlib import PurePosixPath

from ..orchestrator.workflow_ports import WorkflowError

MAX_BYTES = 5 * 1024 * 1024
MAX_TEXT = 24000
MAX_CANDIDATES = 20
MIME_EXTENSIONS = {
    'text/plain': {'.txt'}, 'text/markdown': {'.md'}, 'application/pdf': {'.pdf'},
    'text/calendar': {'.ics'}, 'text/csv': {'.csv'},
    'image/png': {'.png'}, 'image/jpeg': {'.jpg', '.jpeg'},
    'image/webp': {'.webp'}, 'image/gif': {'.gif'},
}


def invalid(message='Không đọc được nguồn. Hãy kiểm tra định dạng và nội dung tệp.'):
    return WorkflowError('INVALID_PARAMETER', message)


def decode_upload(filename: str, mime_type: str, encoded: str) -> bytes:
    if (not isinstance(filename, str) or not filename.strip() or len(filename) > 255
            or '/' in filename or '\\' in filename or any(ord(c) < 32 for c in filename)):
        raise invalid('Tên tệp không hợp lệ.')
    if mime_type not in MIME_EXTENSIONS or PurePosixPath(filename).suffix.lower() not in MIME_EXTENSIONS[mime_type]:
        raise invalid('Định dạng tệp chưa được hỗ trợ hoặc không khớp MIME.')
    if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_BYTES + 2) // 3):
        raise WorkflowError('PAYLOAD_TOO_LARGE', 'Tệp vượt giới hạn 5 MiB.')
    try:
        content = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise invalid('Nội dung tệp không phải base64 hợp lệ.') from None
    if not content:
        raise invalid('Tệp rỗng.')
    if len(content) > MAX_BYTES:
        raise WorkflowError('PAYLOAD_TOO_LARGE', 'Tệp vượt giới hạn 5 MiB.')
    if mime_type.startswith('image/'):
        from .image import validate_image
        validate_image(content, mime_type)
    elif mime_type == 'application/pdf':
        if not content.startswith(b'%PDF-'):
            raise invalid('Nội dung không phải PDF.')
    else:
        decode_text(content)
    return content


def decode_text(content: bytes) -> str:
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise invalid('Tệp văn bản phải dùng UTF-8.') from None
    if any(ord(c) < 32 and c not in '\t\r\n\f' for c in text):
        raise invalid('Tệp chứa dữ liệu nhị phân thay vì văn bản.')
    return text
