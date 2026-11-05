"""Read-only plan views. Store and warning callback are PROPOSED integration seams."""

import copy
from datetime import datetime

from jsonschema import Draft202012Validator

from backend.app.orchestrator.dispatcher import _error
from backend.app.services.tasks import TaskError, _command, _owner, _require, _RESULT, _FORMAT

_READ = Draft202012Validator({'$ref': '#/$defs/result_get_study_plan', '$defs': _RESULT['$defs']}, format_checker=_FORMAT)


def _instant(value):
    return datetime.fromisoformat(value[:-1] + '+00:00' if value[-1] in 'Zz' else value)


class PlanReadService:
    def __init__(self, store, *, warnings):
        self.store, self.warnings = store, warnings

    def get_study_plan(self, args, context):
        owner = _owner(context)
        _command('get_study_plan', args)
        start, end = args['start_at'], args['end_at']
        if start is not None:
            start, end = _instant(start), _instant(end)
            _require(end > start, 'INVALID_PARAMETER')
        with self.store.transaction(owner) as tx:
            view = args['view']
            if view == 'PROPOSAL':
                proposal = tx.get_proposal(owner, args['proposal_id'])
                _require(isinstance(proposal, dict), 'ENTITY_NOT_FOUND')
                _require(proposal.get('user_id') == owner, 'FORBIDDEN')
                _require(proposal.get('proposal_id') == args['proposal_id'], 'INTERNAL_ERROR')
                data = {'kind': 'PROPOSAL_VIEW', 'proposal': copy.deepcopy(proposal)}
                payload = data['proposal'].get('payload')
                _require(isinstance(payload, dict), 'INTERNAL_ERROR')
                blocks = payload.get('study_blocks')
                _require(isinstance(blocks, list) and all(isinstance(b, dict) and b.get('user_id') == owner for b in blocks), 'FORBIDDEN')
            else:
                plan, stored_blocks = (tx.get_current_plan(owner) if view == 'CURRENT'
                                       else tx.get_plan_by_version(owner, args['version']))
                if plan is None:
                    _require(view == 'CURRENT', 'ENTITY_NOT_FOUND')
                    _require(stored_blocks == [], 'INTERNAL_ERROR')
                else:
                    _require(isinstance(plan, dict) and plan.get('user_id') == owner, 'FORBIDDEN')
                    if view == 'HISTORY':
                        _require(plan.get('version') == args['version'], 'INTERNAL_ERROR')
                _require(isinstance(stored_blocks, list) and all(isinstance(b, dict) and b.get('user_id') == owner
                         and plan is not None and b.get('plan_id') == plan.get('plan_id') for b in stored_blocks), 'FORBIDDEN')
                data = {'kind': 'PLAN_VIEW', 'plan': copy.deepcopy(plan), 'study_blocks': copy.deepcopy(stored_blocks)}
                blocks = data['study_blocks']
            issues = (self.warnings(copy.deepcopy(tx.get_warning_context(owner)), copy.deepcopy(data))
                      if view == 'CURRENT' and data['plan'] is not None else [])
            envelope = {'schema_version':'1.1', 'request_id':'validate', 'outcome':'READ',
                        'data':data, 'error':None, 'warnings':issues}
            _require(_READ.is_valid(envelope), 'INTERNAL_ERROR')
            if start is not None:
                blocks[:] = [b for b in blocks if _instant(b['start_at']) < end and _instant(b['end_at']) > start]
            return data, copy.deepcopy(issues)


def plan_read_handler(service):
    def handle(arguments, context):
        try:
            data, warnings = service.get_study_plan(arguments, context)
            return {'schema_version':'1.1', 'request_id':context.request_id, 'outcome':'READ',
                    'data':data, 'error':None, 'warnings':warnings}
        except TaskError as exc:
            return _error(context.request_id, exc.code, 'Plan could not be read.')
    return handle
