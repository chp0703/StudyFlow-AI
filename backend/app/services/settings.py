"""Các ca sử dụng A3; giao diện lưu trữ và hàm kiểm tra/cảnh báo TV4 đang được đề xuất."""

import copy
from datetime import datetime, timezone
from uuid import uuid4

from jsonschema import Draft202012Validator

from backend.app.orchestrator.dispatcher import _error, _uuid
from backend.app.services.scheduling_policy import merge_scheduling_policy
from backend.app.services.tasks import (TaskError, _command, _fingerprint, _owner, _replay,
    _require, _timestamp, _verify_decision, _RESULT, _FORMAT)

_OPERATIONS = ('set_availability', 'set_busy_interval', 'set_scheduling_preferences')
_RESULTS = {op: Draft202012Validator({'$ref':'#/$defs/result_'+op, '$defs':_RESULT['$defs']}, format_checker=_FORMAT)
            for op in _OPERATIONS}


def _validate_result(op, data, warnings):
    response = {'schema_version':'1.1','request_id':'validate','outcome':'COMMITTED',
                'data':data,'error':None,'warnings':warnings}
    _require(_RESULTS[op].is_valid(response), 'INTERNAL_ERROR')


class SettingsService:
    def __init__(self, store, *, validate_window, warnings,
                 clock=lambda:datetime.now(timezone.utc), id_factory=uuid4):
        self.store, self.validate_window, self.warnings = store, validate_window, warnings
        self.clock, self.id_factory = clock, id_factory

    def _run(self, op, args, ctx):
        owner = _owner(ctx, write=True)
        _command(op, args)
        _require(_uuid(ctx.approval_action_id), 'APPROVAL_REQUIRED')
        _require(_uuid(ctx.conversation_id), 'FORBIDDEN')
        fingerprint = _fingerprint(op, args, ctx)
        with self.store.transaction(owner) as tx:
            prior = _replay(tx, owner, op, ctx.idempotency_key, fingerprint)
            if prior is not None:
                _validate_result(op, prior.get('data'), prior.get('warnings'))
                if op != 'set_scheduling_preferences':
                    _require(prior['data'].get('user_id') == owner, 'INTERNAL_ERROR')
                return copy.deepcopy(prior['data']), copy.deepcopy(prior['warnings'])
            profile = tx.get_profile(owner)
            _require(isinstance(profile, dict) and profile.get('user_id') == owner, 'FORBIDDEN')
            revision = profile.get('schedule_revision')
            _require(type(revision) is int and revision >= 0, 'INTERNAL_ERROR')
            now = _timestamp(self.clock)
            if op == 'set_scheduling_preferences':
                _require(revision == args['expected_schedule_revision'], 'STALE_ENTITY_VERSION')
                try:
                    policy = merge_scheduling_policy(profile.get('scheduling_policy'), args['policy_patch'])
                except ValueError:
                    raise TaskError('INVALID_PARAMETER') from None
                data = {'scheduling_policy': policy, 'schedule_revision':revision+1}
                change = {'operation':op,'arguments':copy.deepcopy(args),'effective_policy':copy.deepcopy(policy)}
            else:
                kind = 'AVAILABILITY' if op == 'set_availability' else 'BUSY'
                window = args['window']
                previous = None
                if args['change_type'] != 'ADD':
                    previous = tx.get_window(args['window_id'])
                    _require(isinstance(previous, dict), 'ENTITY_NOT_FOUND')
                    _require(previous.get('user_id') == owner, 'FORBIDDEN')
                    _require(previous.get('window_id') == args['window_id'] and previous.get('kind') == kind, 'INVALID_PARAMETER')
                    _require(type(previous.get('version')) is int and previous['version'] == args['expected_window_version']
                             and previous.get('archived_at') is None, 'STALE_ENTITY_VERSION')
                if window is not None:
                    issues = self.validate_window(copy.deepcopy(window))
                    _require(isinstance(issues, list), 'INTERNAL_ERROR')
                    _require(not issues, 'INVALID_PARAMETER')
                if args['change_type'] == 'ADD':
                    data = {'window_id':str(self.id_factory()),'user_id':owner,'version':1,**copy.deepcopy(window),
                            'archived_at':None,'created_at':now,'updated_at':now}
                elif args['change_type'] == 'UPDATE':
                    data = {**previous,**copy.deepcopy(window),'version':previous['version']+1,'updated_at':now}
                else:
                    data = {**previous,'version':previous['version']+1,'updated_at':now,'archived_at':now}
                change = {'operation':op,'arguments':copy.deepcopy(args),'effective_policy':None}
            evidence = tx.get_decision(ctx.approval_action_id)
            _require(isinstance(evidence, dict), 'APPROVAL_REQUIRED')
            ref = evidence.get('decision', {}).get('action_reference', {}) if isinstance(evidence.get('decision'), dict) else {}
            _require(isinstance(ref, dict) and _uuid(ref.get('action_id')) and type(ref.get('action_version')) is int
                     and ref['action_version'] >= 1, 'ACTION_REVIEW_REQUIRED')
            subject = {'conversation_id':ctx.conversation_id,'slots':change}
            evidence, ref = _verify_decision(tx, owner, ctx, subject, ref['action_id'], ref['action_version'],
                                             target_type='PENDING_ACTION', intent=op.upper())
            warning_list = self.warnings(copy.deepcopy(tx.get_warning_context(owner)), copy.deepcopy(change))
            _validate_result(op, data, warning_list)
            tx.save_approval({'approval_action_id':ctx.approval_action_id,'user_id':owner,'target_type':'PENDING_ACTION',
                'target_id':ref['action_id'],'target_version':ref['action_version'],'decision':'APPROVE',
                'source':evidence['source'],'source_message_id':evidence.get('source_message_id'),'created_at':now})
            if op == 'set_scheduling_preferences': tx.save_policy(owner, policy)
            else: tx.save_window(data)
            tx.complete_pending(ref['action_id'], ref['action_version'])
            tx.increment_schedule_revision(owner)
            tx.put_idempotency(owner, op, ctx.idempotency_key, fingerprint,
                               {'user_id':owner,'data':copy.deepcopy(data),'warnings':copy.deepcopy(warning_list)})
            return copy.deepcopy(data), copy.deepcopy(warning_list)

    def change_window(self, operation, args, ctx):
        _require(operation in ('set_availability','set_busy_interval'), 'UNSUPPORTED_OPERATION')
        return self._run(operation, args, ctx)

    def set_preferences(self, args, ctx):
        return self._run('set_scheduling_preferences', args, ctx)


def settings_handlers(service):
    def handler(op):
        def execute(args, context):
            try:
                data, warnings = service.set_preferences(args, context) if op == 'set_scheduling_preferences' else service.change_window(op, args, context)
                return {'schema_version':'1.1','request_id':context.request_id,'outcome':'COMMITTED',
                        'data':data,'error':None,'warnings':warnings}
            except TaskError as exc:
                return _error(context.request_id, exc.code, 'Settings operation could not be completed.')
        return execute
    return {op:handler(op) for op in _OPERATIONS}
