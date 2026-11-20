"""Verify declared image signatures; the provider must also decode the image."""

from __future__ import annotations

import base64
import struct

from .models import invalid


def validate_image(content: bytes, mime_type: str) -> None:
    actual = None
    if len(content) >= 33 and content.startswith(b'\x89PNG\r\n\x1a\n') and content[12:16] == b'IHDR':
        width, height = struct.unpack('>II', content[16:24])
        if not (0 < width <= 8192 and 0 < height <= 8192):
            raise invalid('Kích thước ảnh vượt giới hạn 8192 pixel mỗi chiều.')
        actual = 'image/png'
    elif len(content) >= 4 and content.startswith(b'\xff\xd8\xff') and content.endswith(b'\xff\xd9'):
        actual = 'image/jpeg'
    elif len(content) >= 13 and content[:6] in (b'GIF87a', b'GIF89a') and content.endswith(b';'):
        actual = 'image/gif'
    elif len(content) >= 20 and content[:4] == b'RIFF' and content[8:12] == b'WEBP':
        actual = 'image/webp'
    if actual != mime_type:
        raise invalid('Nội dung ảnh không khớp MIME hoặc ảnh bị hỏng.')


def image_part(content: bytes, mime_type: str) -> dict:
    validate_image(content, mime_type)
    return {'type': 'image_url', 'image_url': {
        'url': f'data:{mime_type};base64,{base64.b64encode(content).decode("ascii")}',
        'detail': 'original',
    }}
