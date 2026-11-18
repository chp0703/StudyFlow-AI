from uuid import UUID, uuid4, uuid5

from ..core import contract
from ..clients.rpc import child_key, iso
from ..orchestrator.workflow_ports import WorkflowError
from ..orchestrator.workflow_shared import Terminal, _ok, reply

_TRANSIENT_CODES = ('SERVICE_UNAVAILABLE', 'INTERNAL_ERROR', 'UNAUTHENTICATED')
_FIELD_QUESTIONS = {
    'start_at': 'Bạn muốn bắt đầu ôn tập khi nào?',
    'deadline_at': 'Bạn muốn hoàn thành ôn tập trước thời điểm nào?',
    'deadline_date': 'Bạn muốn hoàn thành ôn tập trước ngày nào?',
    'minutes': 'Bạn muốn dành bao nhiêu phút để ôn tập?',
    'priority': 'Mức độ ưu tiên của đề xuất ôn tập này là gì?',
    'material_id': 'Bạn muốn ôn tập dựa trên tài liệu nào?',
}


class RevisionRecommendationOperations:
    def __init__(self, rpc, clock):
        self.rpc = rpc
        self.clock = clock

    def _call(self, ctx, operation, args, schema=None, **kwargs):
        result = self.rpc(ctx, operation, args, **kwargs)
        if result.get('outcome') == 'ERROR':
            err = result.get('error') or {}
            code = err.get('code') or 'INTERNAL_ERROR'
            msg = err.get('message') or 'RPC failed'
            field = err.get('field')
            if code in _TRANSIENT_CODES:
                raise WorkflowError(code, msg, field=field, retryable=True, retry_after=1)
            raise Terminal(code, msg, field=field)
        if schema and not contract.is_valid(schema, result):
            raise WorkflowError('INTERNAL_ERROR', f'Invalid {schema} response')
        return result

    def _validate_reply(self, payload):
        if not contract.is_valid('OrchestratorReply', payload):
            raise WorkflowError('INTERNAL_ERROR', 'Invalid OrchestratorReply payload')
        return payload

    def create(self, ctx, receipt, key, body):
        action_id = receipt['action_id']
        recommendation_id = str(uuid5(UUID(action_id), 'revision-recommendation'))
        conversation = str(UUID(body['conversation_id']))
        material_id = str(UUID(body['material_id']))
        source_msg = {
            'message_id': receipt['message_id'],
            'user_id': ctx.user_id,
            'conversation_id': conversation,
            'source': 'UI',
            'role': 'USER',
            'text': 'Đề xuất ôn tập theo kết quả làm bài',
            'received_at': receipt['created_at'],
        }
        self._call(
            ctx, 'record_source_message', {'message': source_msg},
            idempotency_key=child_key(key, 'recommendation-message'),
            conversation_id=conversation, message_id=receipt['message_id'],
        )
        args = {
            'recommendation_id': recommendation_id, 'pending_action_id': action_id,
            'material_id': material_id, 'topic': body['topic'],
            'suggested_minutes': body['suggested_minutes'], 'priority': body['priority'],
        }
        result = self._call(
            ctx, 'create_revision_recommendation', args,
            schema='RevisionRecommendationResult',
            idempotency_key=child_key(key, 'create-recommendation'),
            conversation_id=conversation, message_id=receipt['message_id'],
        )
        p = result['data']
        a = p['pending_action']
        ref = {
            'action_id': a['action_id'], 'action_version': a['version'],
            'target_type': 'PENDING_ACTION',
            'target_id': a['action_id'], 'target_version': a['version'],
        }
        payload = reply(
            ctx.request_id, 'AWAITING_APPROVAL',
            'Mình đã chuẩn bị đề xuất ôn tập. Bạn xác nhận để áp dụng nhé.',
            reference=ref, result=_ok(ctx.request_id, 'DRAFTED', p),
        )
        return 200, self._validate_reply(payload)

    def decide(self, ctx, receipt, key, body, pending):
        ref = body['action_reference']
        decision = body['decision']
        approval_action = {
            'approval_action_id': str(uuid4()), 'user_id': ctx.user_id,
            'target_type': 'PENDING_ACTION', 'target_id': ref['action_id'],
            'target_version': ref['action_version'], 'decision': decision,
            'source': 'UI', 'source_message_id': None, 'created_at': iso(self.clock()),
        }
        args = {'recommendation_id': pending['draft_arguments']['recommendation_id'], 'decision': decision}
        result = self._call(
            ctx, 'decide_revision_recommendation', args,
            schema='DecideRevisionRecommendationResult', action_reference=ref,
            idempotency_key=child_key(key, 'revision-decision'),
            conversation_id=body['conversation_id'], message_id=receipt['message_id'],
            approval_action=approval_action,
        )
        pres = result['data']
        if decision == 'APPROVE':
            questions = [
                {'field': f, 'message': _FIELD_QUESTIONS.get(f, f'Vui lòng bổ sung {f}.'), 'choices': []}
                for f in pres['pending_action']['missing_fields']
            ]
            payload = reply(
                ctx.request_id, 'NEEDS_CLARIFICATION',
                'Cần bổ sung thêm thông tin trước khi áp dụng đề xuất ôn tập.',
                questions=questions, result=_ok(ctx.request_id, 'DRAFTED', pres),
            )
        else:
            payload = reply(
                ctx.request_id, 'SUCCEEDED', 'Đã hủy đề xuất ôn tập.',
                result=_ok(ctx.request_id, 'COMMITTED', pres),
            )
        return 200, self._validate_reply(payload)
