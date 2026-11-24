"""Bounded document parsing and the B1 material RPC boundary; no model calls."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid5

from ..clients.rpc import child_key, iso
from ..core import contract
from ..ingestion.document import read_document_pages
from ..ingestion.models import decode_upload, invalid
from ..orchestrator.workflow_ports import WorkflowError

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 100
MAX_TEXT = 200000
CHUNK_SIZE = 2000


def prepare_material(body: dict, *, user_id: str, material_id: str, now) -> dict:
    if not contract.is_valid('MaterialUploadRequest', body):
        raise invalid('Yêu cầu tài liệu không đúng contract.')
    if len(body['topics']) != 1:
        raise invalid('B2 nhận một chủ đề do bạn đặt cho mỗi tài liệu; hãy tách upload theo chủ đề.')
    content = decode_upload(body['filename'], body['mime_type'], body['content_base64'], max_bytes=MAX_BYTES)
    pages = read_document_pages(content, body['mime_type'], max_bytes=MAX_BYTES,
                                max_pages=MAX_PAGES, max_text=MAX_TEXT, timeout=15)
    chunks = []
    for page, text in enumerate(pages, 1):
        text = text.strip()
        start = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            if end < len(text):
                boundary = end
                while boundary > start and not text[boundary - 1].isspace():
                    boundary -= 1
                # shortcut: tokens longer than CHUNK_SIZE use a hard cut; revisit for code/token retrieval.
                if boundary > start:
                    end = boundary
            piece = text[start:end]
            start = end
            if not piece.strip():
                continue
            index = len(chunks)
            chunks.append({'chunk_id': str(uuid5(UUID(material_id), f'chunk:{index}')), 'material_id': material_id,
                           'user_id': user_id, 'page': page, 'topic': body['topics'][0], 'chunk_index': index,
                           'text': piece, 'created_at': iso(now)})
    args = {k: body[k] for k in ('conversation_id', 'filename', 'mime_type', 'topics')}
    args['conversation_id'] = str(UUID(args['conversation_id']))
    args.update(material_id=material_id, size_bytes=len(content), sha256=hashlib.sha256(content).hexdigest(),
                page_count=len(pages), char_count=sum(len(c['text']) for c in chunks), chunks=chunks)
    if not contract.is_valid('StoreMaterialArguments', args):
        raise invalid('Không thể chia tài liệu trong giới hạn chunk của B2.')
    return args


class MaterialOperations:
    def __init__(self, rpc, clock):
        self.rpc, self.clock = rpc, clock

    def step(self, ctx, operation, arguments, **kwargs):
        schema = 'MaterialChunkSearchResult' if operation == 'search_material_chunks' else 'AssessmentMaterialDetailResult'
        result = self.rpc(ctx, operation, arguments, **kwargs)
        if not contract.is_valid(schema, result):
            raise WorkflowError('INTERNAL_ERROR', 'Dữ liệu tài liệu không đúng contract.')
        if result['outcome'] == 'ERROR':
            error = result['error']
            raise WorkflowError(error['code'], error['message'], retryable=error['retryable'])
        data = result['data']
        chunks = data['items'] if operation == 'search_material_chunks' else data['chunks']
        material = data.get('material')
        # Conversation scope is enforced by the RPC (own conversation or a READY F3 material), so it is not rechecked here.
        if (material is not None and (material['user_id'] != ctx.user_id or material['material_id'] != arguments['material_id'])
                or material is None and data['material_id'] != arguments['material_id']
                or any(c['user_id'] != ctx.user_id or c['material_id'] != arguments['material_id'] for c in chunks)):
            raise WorkflowError('ENTITY_NOT_FOUND', 'Không tìm thấy tài liệu.')
        return result

    def upload(self, ctx, key, body):
        material_id = str(uuid5(UUID(ctx.user_id), 'assessment-material:' + key))
        args = prepare_material(body, user_id=ctx.user_id, material_id=material_id, now=self.clock())
        return self.step(ctx, 'store_assessment_material', args, conversation_id=args['conversation_id'],
                         idempotency_key=child_key(key, 'assessment-material'))

    def get(self, ctx, material_id, conversation_id):
        args = {'material_id': material_id, 'conversation_id': conversation_id}
        if not contract.is_valid('MaterialLookupArguments', args):
            raise invalid('ID tài liệu hoặc cuộc hội thoại không hợp lệ.')
        args = {k: str(UUID(v)) for k, v in args.items()}
        return self.step(ctx, 'get_assessment_material', args, conversation_id=args['conversation_id'])

    def search(self, ctx, material_id, *, topic=None, query=None, limit=20):
        args = {'material_id': material_id, 'topic': topic, 'query': query, 'limit': limit}
        if not contract.is_valid('SearchMaterialChunksArguments', args):
            raise invalid('Tham số truy xuất tài liệu không hợp lệ.')
        args['material_id'] = str(UUID(args['material_id']))
        return self.step(ctx, 'search_material_chunks', args)
