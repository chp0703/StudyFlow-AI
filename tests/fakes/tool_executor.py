"""Bộ thực thi chỉ dùng fixture cho test hội thoại; không bao giờ ghi dữ liệu nghiệp vụ."""

import copy
import json
from pathlib import Path

from backend.app.orchestrator.dispatcher import Dispatcher
from backend.app.orchestrator.registry import OPERATIONS


_ERRORS = {'APPROVAL_REQUIRED', 'ACTION_REVIEW_REQUIRED', 'ENTITY_NOT_FOUND',
           'FORBIDDEN', 'STALE_ENTITY_VERSION', 'STALE_PROPOSAL',
           'STALE_PLAN_VERSION', 'IDEMPOTENCY_CONFLICT'}


class FakeToolExecutor:
    def __init__(self, scenarios=None):
        scenarios = dict(scenarios or {})
        allowed = {op: {'success'} | _ERRORS for op in OPERATIONS}
        allowed['get_study_plan'] |= {'proposal', 'history'}
        if any(op not in allowed or scenario not in allowed[op] for op, scenario in scenarios.items()):
            raise ValueError('Unknown operation or fixture scenario')
        root = Path(__file__).resolve().parents[2]
        cases = json.loads((root / 'contracts/examples/result_cases.json').read_text(encoding='utf-8'))
        results = {case['operation']: case['result'] for case in cases
                   if case['valid'] and case['name'] == case['operation']}
        self._dispatcher = Dispatcher({
            op: self._handler(op, scenarios.get(op, 'success'), results)
            for op in OPERATIONS
        })

    @staticmethod
    def _handler(operation, scenario, results):
        def handler(arguments, context):
            if scenario in _ERRORS:
                return {'schema_version': '1.1', 'request_id': context.request_id,
                        'outcome': 'ERROR', 'data': None, 'warnings': [],
                        'error': {'code': scenario, 'message': 'Fixed fake scenario.',
                                  'field': None, 'details': {}, 'retryable': False}}
            result = copy.deepcopy(results[operation])
            result['request_id'] = context.request_id
            if scenario == 'proposal':
                result['data'] = {'kind': 'PROPOSAL_VIEW',
                                  'proposal': copy.deepcopy(results['generate_study_plan']['data'])}
            elif scenario == 'history':
                result['data'] = {'kind': 'PLAN_VIEW', 'plan': copy.deepcopy(results['approve_study_plan']['data']),
                                  'study_blocks': []}
            return result
        return handler

    def execute(self, command, trusted_context):
        return self._dispatcher.dispatch(command, trusted_context)
