"""Signed source persistence and leased extraction; no domain writes live here."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid5

from ..clients.rpc import child_key
from ..core import contract
from ..orchestrator.workflow_ports import WorkflowError
from .models import decode_upload


class SourceOperations:
    def __init__(self, rpc, extractor, clock):
        self.rpc, self.extractor, self.clock = rpc, extractor, clock

    def step(self, ctx, operation, arguments, **kwargs):
        result = self.rpc(ctx, operation, arguments, **kwargs)
        if result.get('outcome') == 'ERROR':
            error = result.get('error') or {}
            raise WorkflowError(error.get('code', 'INTERNAL_ERROR'), error.get('message', 'Không đọc được nguồn.'),
                                retryable=bool(error.get('retryable')))
        name = 'SourceClaimResult' if operation == 'claim_source_extraction' else 'IngestionSourceResult'
        if not contract.is_valid(name, result):
            raise WorkflowError('INTERNAL_ERROR', 'Dữ liệu nguồn không đúng contract.')
        source = result['data']['source'] if operation == 'claim_source_extraction' else result['data']
        if source['user_id'] != ctx.user_id or source['conversation_id'] != arguments['conversation_id']:
            raise WorkflowError('ENTITY_NOT_FOUND', 'Không tìm thấy nguồn.')
        return result

    def upload(self, ctx, key, body):
        content = decode_upload(body['filename'], body['mime_type'], body['content_base64'])
        args = {k: v for k, v in body.items() if k != 'schema_version'}
        args.update(source_id=str(uuid5(UUID(ctx.user_id), 'source-upload:' + key)), size_bytes=len(content),
                    sha256=hashlib.sha256(content).hexdigest())
        return self.step(ctx, 'store_ingestion_source', args, conversation_id=body['conversation_id'],
                         idempotency_key=child_key(key, 'source-upload'))

    def get(self, ctx, source_id, conversation):
        return self.step(ctx, 'get_ingestion_source', {'source_id': source_id, 'conversation_id': conversation},
                         conversation_id=conversation)

    def extract(self, ctx, key, source_id, conversation):
        lookup = {'source_id': source_id, 'conversation_id': conversation}
        claim = self.step(ctx, 'claim_source_extraction', lookup, conversation_id=conversation,
                          idempotency_key=child_key(key, 'source-claim'))['data']
        source = claim['source']
        if source['status'] == 'READY':
            return {'schema_version': '1.1', 'request_id': ctx.request_id, 'outcome': 'READ',
                    'data': source, 'error': None, 'warnings': []}
        completion = {**lookup, 'expected_lease_version': source['lease_version'], 'extraction': None, 'error_code': None}
        try:
            content = decode_upload(source['filename'], source['mime_type'], claim['content_base64'])
            if len(content) != source['size_bytes'] or hashlib.sha256(content).hexdigest() != source['sha256']:
                raise WorkflowError('INTERNAL_ERROR', 'Dữ liệu nguồn không khớp dấu kiểm tra.')
            extraction = self.extractor.extract(content, source['mime_type'], now=self.clock())
            if not contract.is_valid('SourceExtraction', extraction):
                raise WorkflowError('SERVICE_UNAVAILABLE', 'Kết quả trích xuất chưa hợp lệ.')
            completion['extraction'] = extraction
        except Exception as exc:
            error = exc if isinstance(exc, WorkflowError) else WorkflowError('INTERNAL_ERROR', 'Chưa xử lý được nguồn.')
            completion['error_code'] = error.code if error.code in ('INVALID_PARAMETER', 'SERVICE_UNAVAILABLE', 'INTERNAL_ERROR') else 'INTERNAL_ERROR'
            try:
                self.step(ctx, 'complete_source_extraction', completion, conversation_id=conversation,
                          idempotency_key=child_key(key, 'source-failed'))
            except WorkflowError:
                pass  # A lost lease cannot overwrite the newer worker's state.
            raise WorkflowError(error.code, error.message, retryable=False) from None
        return self.step(ctx, 'complete_source_extraction', completion, conversation_id=conversation,
                         idempotency_key=child_key(key, 'source-complete'))
