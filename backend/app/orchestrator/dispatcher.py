import json
import logging
import re
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from uuid import UUID

from jsonschema import Draft202012Validator, FormatChecker

from .registry import OPERATIONS

logger = logging.getLogger(__name__)
_RFC3339 = re.compile(r'\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-](?:[01]\d|2[0-3]):[0-5]\d)', re.ASCII)


def _date_time(value):
    if not isinstance(value, str):
        return True
    if not _RFC3339.fullmatch(value):
        return False
    try:
        # đơn giản hóa: từ chối giây nhuận và năm 0000; mở rộng nếu contract thời gian đã thống nhất yêu cầu
        datetime.fromisoformat(value[:-1] + '+00:00' if value[-1] in 'Zz' else value)
        return True
    except ValueError:
        return False


@dataclass(frozen=True)
class Principal:
    user_id: str


@dataclass(frozen=True)
class TrustedContext:
    # Bên gọi chỉ được tạo sau xác thực; các service kiểm tra bằng chứng.
    request_id: str
    principal: Principal | None
    approval_action_id: str | None = None
    idempotency_key: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None


def _uuid(value):
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def _error(request_id, code, message):
    return {'schema_version': '1.1', 'request_id': request_id, 'outcome': 'ERROR',
            'data': None, 'error': {'code': code, 'message': message, 'field': None,
                                    'details': {}, 'retryable': False}, 'warnings': []}


class Dispatcher:
    def __init__(self, handlers):
        self.handlers = dict(handlers)
        root = Path(__file__).resolve().parents[3] / 'contracts' / 'schemas'
        command = json.loads((root / 'validated_command.json').read_text(encoding='utf-8'))
        result = json.loads((root / 'tool_result.json').read_text(encoding='utf-8'))
        format_checker = FormatChecker()
        format_checker.checks('date-time')(_date_time)
        branches = {branch['properties']['operation']['const']: branch for branch in command['oneOf']}
        self.command_validators = {
            name: Draft202012Validator({**branches[name], '$defs': command['$defs']}, format_checker=format_checker)
            for name in OPERATIONS
        }
        self.result_validators = {
            name: Draft202012Validator({'$ref': '#/$defs/result_' + name, '$defs': result['$defs']},
                                       format_checker=format_checker)
            for name in OPERATIONS
        }

    def dispatch(self, command, context):
        started = perf_counter()
        name = command.get('operation') if isinstance(command, dict) else None
        name = name if isinstance(name, str) and name in OPERATIONS else 'UNKNOWN'
        request_id = context.request_id if (isinstance(context, TrustedContext)
                     and isinstance(context.request_id, str) and context.request_id.strip()) else None
        result = None
        try:
            result = self._dispatch(command, context)
            return result
        finally:
            outcome = result['outcome'] if result is not None else 'ERROR'
            code = result['error']['code'] if result is not None and result['error'] is not None else None
            if result is None:
                code = 'INTERNAL_ERROR'
            try:
                logger.info('tool_execution', extra={'request_id': request_id, 'operation': name,
                            'outcome': outcome, 'error_code': code,
                            'duration_ms': (perf_counter() - started) * 1000})
            except Exception:
                # Lỗi ghi log không được che mất kết quả service đã commit.
                pass

    def _dispatch(self, command, context):
        if not isinstance(context, TrustedContext) or not isinstance(context.request_id, str) or not context.request_id.strip():
            raise ValueError('A server-issued request_id and trusted context are required')
        request_id = context.request_id
        if not isinstance(context.principal, Principal) or not _uuid(context.principal.user_id):
            return _error(request_id, 'FORBIDDEN', 'Authenticated principal required.')
        if not isinstance(command, dict):
            return _error(request_id, 'INVALID_PARAMETER', 'Command must be an object.')
        if 'operation' not in command:
            return _error(request_id, 'MISSING_REQUIRED_FIELD', 'Operation is required.')
        name = command['operation']
        if not isinstance(name, str):
            return _error(request_id, 'INVALID_PARAMETER', 'Operation must be a string.')
        if name not in OPERATIONS:
            return _error(request_id, 'UNSUPPORTED_OPERATION', 'Operation is not supported.')
        errors = list(self.command_validators[name].iter_errors(command))
        if errors:
            code = 'MISSING_REQUIRED_FIELD' if any(e.validator == 'required' for e in errors) else 'INVALID_PARAMETER'
            return _error(request_id, code, 'Invalid command.')
        spec = OPERATIONS[name]
        if spec.requires_approval and not _uuid(context.approval_action_id):
            return _error(request_id, 'APPROVAL_REQUIRED', 'Approval evidence is required.')
        if spec.writes and (not isinstance(context.idempotency_key, str) or not context.idempotency_key.strip()):
            return _error(request_id, 'INVALID_PARAMETER', 'Idempotency key is required.')
        if name == 'create_task_candidate' and not (_uuid(context.conversation_id) and _uuid(context.message_id)):
            return _error(request_id, 'INVALID_PARAMETER', 'Verified conversation and message are required.')
        try:
            handler = self.handlers[name]
            result = handler(command['arguments'], context)
            if list(self.result_validators[name].iter_errors(result)) or result['request_id'] != request_id:
                return _error(request_id, 'INTERNAL_ERROR', 'Invalid service result.')
            if name == 'get_study_plan' and result['outcome'] == 'READ':
                expected = 'PROPOSAL_VIEW' if command['arguments']['view'] == 'PROPOSAL' else 'PLAN_VIEW'
                if result['data']['kind'] != expected:
                    return _error(request_id, 'INTERNAL_ERROR', 'Invalid service result.')
            return result
        except Exception:
            return _error(request_id, 'INTERNAL_ERROR', 'Service execution failed.')
