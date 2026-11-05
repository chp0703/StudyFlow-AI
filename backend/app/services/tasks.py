"""A2 task use cases. Storage/evidence seam is PROPOSED pending TV1/TV3 review."""

import copy
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker

from backend.app.orchestrator.dispatcher import Principal, TrustedContext, _date_time, _error, _uuid

_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA = json.loads((_ROOT / 'contracts/schemas/validated_command.json').read_text(encoding='utf-8'))
_RESULT = json.loads((_ROOT / 'contracts/schemas/tool_result.json').read_text(encoding='utf-8'))
_FORMAT = FormatChecker()
_FORMAT.checks('date-time')(_date_time)
_SLOT_VALIDATOR = Draft202012Validator({'$ref': '#/$defs/candidate_fields', '$defs': _SCHEMA['$defs']}, format_checker=_FORMAT)
_COMMANDS = {branch['properties']['operation']['const']: Draft202012Validator(
    {**branch, '$defs': _SCHEMA['$defs']}, format_checker=_FORMAT) for branch in _SCHEMA['oneOf']}
_SEARCH_RESULT = Draft202012Validator({'$ref': '#/$defs/result_search_tasks', '$defs': _RESULT['$defs']}, format_checker=_FORMAT)
_OUTPUTS = {name: Draft202012Validator({'$ref': '#/$defs/result_' + name, '$defs': _RESULT['$defs']}, format_checker=_FORMAT)
            for name in ('create_task_candidate', 'confirm_task')}


class TaskError(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _require(condition, code):
    if not condition:
        raise TaskError(code)


def _owner(ctx, *, write=False):
    _require(isinstance(ctx, TrustedContext) and isinstance(ctx.principal, Principal)
             and _uuid(ctx.principal.user_id), 'FORBIDDEN')
    if write:
        _require(isinstance(ctx.idempotency_key, str) and bool(ctx.idempotency_key.strip()), 'INVALID_PARAMETER')
    return ctx.principal.user_id


def _command(operation, arguments):
    errors = list(_COMMANDS[operation].iter_errors({'schema_version': '1.1', 'operation': operation, 'arguments': arguments}))
    if errors:
        raise TaskError('MISSING_REQUIRED_FIELD' if any(e.validator == 'required' for e in errors) else 'INVALID_PARAMETER')


def _slots(value):
    _require(_SLOT_VALIDATOR.is_valid(value), 'INVALID_PARAMETER')
    result = copy.deepcopy(value)
    if result.get('title') is not None:
        result['title'] = result['title'].strip()
    for field in ('available_from_at', 'deadline_at'):
        if result.get(field) is not None:
            _minute_timestamp(result[field])
    if result.get('priority') is None:
        result['priority'] = 'NORMAL'
    return result


def _minute_timestamp(value):
    _require(isinstance(value, str) and _date_time(value), 'INVALID_PARAMETER')
    parsed = datetime.fromisoformat(value[:-1] + '+00:00' if value[-1] in 'Zz' else value)
    _require(parsed.second == 0 and parsed.microsecond == 0, 'INVALID_PARAMETER')
    return parsed


def _confirmed_fields(slots):
    for key in ('title', 'deadline_at', 'deadline_precision', 'deadline_timezone', 'estimated_minutes', 'priority'):
        _require(slots.get(key) is not None and slots.get(key) != '', 'MISSING_REQUIRED_FIELD')
    deadline = _minute_timestamp(slots['deadline_at'])
    if slots.get('available_from_at') is not None:
        _require(_minute_timestamp(slots['available_from_at']) <= deadline, 'INVALID_PARAMETER')
    try:
        zone = ZoneInfo(slots['deadline_timezone'])
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise TaskError('INVALID_PARAMETER') from None
    if slots['deadline_precision'] == 'DATE':
        _require(isinstance(slots.get('deadline_date'), str), 'MISSING_REQUIRED_FIELD')
        try:
            day = date.fromisoformat(slots['deadline_date'])
            _require(day.isoformat() == slots['deadline_date'], 'INVALID_PARAMETER')
            local = datetime.combine(day + timedelta(days=1), time.min)
            options = [local.replace(tzinfo=zone, fold=fold) for fold in (0, 1)]
            instants = {v.astimezone(timezone.utc) for v in options
                        if v.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == local}
            _require(len(instants) == 1 and deadline.astimezone(timezone.utc) in instants, 'INVALID_PARAMETER')
        except (ValueError, OverflowError):
            raise TaskError('INVALID_PARAMETER') from None
    else:
        _require(slots['deadline_precision'] == 'DATETIME' and slots.get('deadline_date') is None, 'INVALID_PARAMETER')
    return {k: slots.get(k) for k in ('title', 'description', 'course_label', 'available_from_at',
            'deadline_at', 'deadline_precision', 'deadline_date', 'deadline_timezone', 'estimated_minutes', 'priority')}


def _fingerprint(operation, arguments, ctx):
    payload = {'operation': operation, 'arguments': arguments, 'owner': ctx.principal.user_id,
               'conversation_id': ctx.conversation_id, 'message_id': ctx.message_id,
               'approval_action_id': ctx.approval_action_id}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def _same_json(left, right):
    try:
        return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError):
        return False


def _timestamp(clock):
    value = clock()
    _require(isinstance(value, datetime), 'INTERNAL_ERROR')
    formatted = value.isoformat()
    _require(_date_time(formatted), 'INTERNAL_ERROR')
    return formatted


def _output(operation, outcome, data):
    envelope = {'schema_version': '1.1', 'request_id': 'validate', 'outcome': outcome,
                'data': data, 'error': None, 'warnings': []}
    _require(_OUTPUTS[operation].is_valid(envelope), 'INTERNAL_ERROR')


def _replay(tx, owner, operation, key, fingerprint):
    prior = tx.get_idempotency(owner, operation, key)
    return _replay_result(prior, fingerprint, owner)


def _replay_result(prior, fingerprint, owner):
    if prior is None:
        return None
    _require(prior.get('fingerprint') == fingerprint, 'IDEMPOTENCY_CONFLICT')
    _require(prior.get('state') == 'COMPLETED' and isinstance(prior.get('result'), dict), 'INTERNAL_ERROR')
    _require(prior['result'].get('user_id') == owner, 'INTERNAL_ERROR')
    return copy.deepcopy(prior['result'])


def _message(tx, owner, conversation, message):
    _require(_uuid(conversation) and _uuid(message), 'INVALID_PARAMETER')
    record = tx.get_message(message)
    _require(isinstance(record, dict), 'FORBIDDEN')
    _require(record.get('message_id') == message and record.get('user_id') == owner
             and record.get('conversation_id') == conversation, 'FORBIDDEN')


def _verify_decision(tx, owner, ctx, candidate, candidate_id, expected_version, *, target_type='TASK_CANDIDATE', intent=None):
    evidence = tx.get_decision(ctx.approval_action_id)
    _require(isinstance(evidence, dict), 'APPROVAL_REQUIRED')
    _require(evidence.get('user_id') == owner and evidence.get('conversation_id') == candidate['conversation_id'], 'FORBIDDEN')
    decision = evidence.get('decision')
    _require(isinstance(decision, dict)
             and set(decision) == {'schema_version', 'conversation_id', 'action_reference', 'decision'}
             and decision.get('schema_version') == '1.1'
             and decision.get('conversation_id') == candidate['conversation_id']
             and decision.get('decision') == 'APPROVE', 'APPROVAL_REQUIRED')
    source = tx.get_decision_source(ctx.approval_action_id)
    _require(isinstance(source, dict) and source.get('user_id') == owner
             and source.get('conversation_id') == candidate['conversation_id']
             and source.get('source') == evidence.get('source')
             and source.get('source_message_id') == evidence.get('source_message_id')
             and source.get('source_event_id') == evidence.get('source_event_id')
             and _same_json(source.get('decision'), decision), 'FORBIDDEN')
    ref = decision.get('action_reference')
    _require(isinstance(ref, dict)
             and set(ref) == {'action_id', 'action_version', 'target_type', 'target_id', 'target_version'}
             and _uuid(ref.get('action_id')) and type(ref.get('action_version')) is int
             and ref.get('action_version') >= 1 and ref.get('target_type') == target_type
             and ref.get('target_id') == candidate_id and type(ref.get('target_version')) is int
             and ref.get('target_version') == expected_version,
             'ACTION_REVIEW_REQUIRED')
    pending = tx.get_pending(ref['action_id'])
    review = tx.get_review(ref['action_id'], ref['action_version'])
    _require(isinstance(pending, dict) and isinstance(review, dict), 'ACTION_REVIEW_REQUIRED')
    _require(pending.get('user_id') == owner and pending.get('conversation_id') == candidate['conversation_id']
             and review.get('user_id') == owner and review.get('conversation_id') == candidate['conversation_id'], 'FORBIDDEN')
    _require(pending.get('action_id') == ref['action_id'] and type(pending.get('version')) is int
             and pending.get('version') == ref['action_version']
             and (pending.get('candidate_id') == candidate_id if target_type == 'TASK_CANDIDATE' else
             ref['action_id'] == candidate_id and ref['action_version'] == expected_version
             and pending.get('intent') == intent and _same_json(pending.get('draft_arguments'), candidate['slots']['arguments']))
             and pending.get('state') == 'AWAITING_CONFIRMATION'
             and pending.get('requires_review') is False and review.get('action_id') == ref['action_id']
             and type(review.get('action_version')) is int and review.get('action_version') == ref['action_version']
             and review.get('target_id') == candidate_id and type(review.get('target_version')) is int
             and review.get('target_version') == expected_version
             and _same_json(review.get('displayed_slots' if target_type == 'TASK_CANDIDATE' else 'displayed_action'), candidate['slots']),
             'ACTION_REVIEW_REQUIRED')
    if evidence.get('source') == 'CHAT':
        _require(evidence.get('source_message_id') == ctx.message_id, 'FORBIDDEN')
        _message(tx, owner, candidate['conversation_id'], evidence.get('source_message_id'))
    elif evidence.get('source') == 'UI':
        _require(_uuid(evidence.get('source_event_id')), 'FORBIDDEN')
        event = tx.get_ui_event(evidence.get('source_event_id'))
        _require(isinstance(event, dict) and event.get('user_id') == owner
                 and event.get('conversation_id') == candidate['conversation_id']
                 and event.get('event_id') == evidence.get('source_event_id')
                 and _same_json(event.get('decision'), decision), 'FORBIDDEN')
    else:
        raise TaskError('APPROVAL_REQUIRED')
    return evidence, ref


class TaskService:
    def __init__(self, store, *, clock=lambda: datetime.now(timezone.utc), id_factory=uuid4):
        self.store, self.clock, self.id_factory = store, clock, id_factory

    def create_candidate(self, slots, ctx):
        owner = _owner(ctx, write=True)
        _command('create_task_candidate', {'slots': slots})
        normalized = _slots(slots)
        fingerprint = _fingerprint('create_task_candidate', {'slots': normalized}, ctx)
        with self.store.transaction(owner) as tx:
            prior = _replay(tx, owner, 'create_task_candidate', ctx.idempotency_key, fingerprint)
            if prior is not None:
                _output('create_task_candidate', 'DRAFTED', prior)
                return prior
            _message(tx, owner, ctx.conversation_id, ctx.message_id)
            now = _timestamp(self.clock)
            candidate = {'candidate_id': str(self.id_factory()), 'user_id': owner,
                         'conversation_id': ctx.conversation_id, 'version': 1, 'status': 'DRAFT',
                         'slots': normalized, 'raw_expressions': {},
                         'field_sources': {'priority': {'source': 'SYSTEM_DEFAULT', 'reference': None}}
                         if slots.get('priority') is None else {},
                         'source_message_id': ctx.message_id, 'confirmed_task_id': None,
                         'created_at': now, 'updated_at': now}
            _output('create_task_candidate', 'DRAFTED', candidate)
            tx.save_candidate(candidate)
            tx.put_idempotency(owner, 'create_task_candidate', ctx.idempotency_key, fingerprint, candidate)
            return copy.deepcopy(candidate)

    def edit_candidate(self, candidate_id, expected_version, patch, ctx):
        owner = _owner(ctx, write=True)
        _require(_uuid(candidate_id) and type(expected_version) is int and expected_version >= 1
                 and isinstance(patch, dict) and bool(patch) and _SLOT_VALIDATOR.is_valid(patch), 'INVALID_PARAMETER')
        patch = copy.deepcopy(patch)
        if patch.get('title') is not None:
            patch['title'] = patch['title'].strip()
        if 'priority' in patch and patch['priority'] is None:
            patch['priority'] = 'NORMAL'
        fingerprint = _fingerprint('edit_task_candidate', {'candidate_id': candidate_id,
                                   'expected_version': expected_version, 'patch': patch}, ctx)
        with self.store.transaction(owner) as tx:
            prior = _replay_result(tx.get_internal_edit_replay(owner, ctx.idempotency_key), fingerprint, owner)
            if prior is not None:
                _output('create_task_candidate', 'DRAFTED', prior)
                return prior
            _message(tx, owner, ctx.conversation_id, ctx.message_id)
            candidate = tx.get_candidate(candidate_id)
            _require(isinstance(candidate, dict), 'ENTITY_NOT_FOUND')
            _require(candidate['user_id'] == owner and candidate['conversation_id'] == ctx.conversation_id, 'FORBIDDEN')
            _require(type(candidate['version']) is int and candidate['version'] == expected_version
                     and candidate['status'] == 'DRAFT', 'STALE_ENTITY_VERSION')
            candidate['slots'] = _slots({**candidate['slots'], **patch})
            for field in patch:
                candidate['field_sources'].pop(field, None)
            candidate['version'] += 1
            candidate['updated_at'] = _timestamp(self.clock)
            _output('create_task_candidate', 'DRAFTED', candidate)
            tx.save_candidate(candidate)
            tx.put_internal_edit_replay(owner, ctx.idempotency_key, fingerprint, candidate)
            return copy.deepcopy(candidate)

    def confirm_task(self, candidate_id, expected_version, ctx):
        owner = _owner(ctx, write=True)
        _command('confirm_task', {'candidate_id': candidate_id, 'expected_candidate_version': expected_version})
        _require(_uuid(ctx.approval_action_id), 'APPROVAL_REQUIRED')
        fingerprint = _fingerprint('confirm_task', {'candidate_id': candidate_id,
                                   'expected_candidate_version': expected_version}, ctx)
        with self.store.transaction(owner) as tx:
            prior = _replay(tx, owner, 'confirm_task', ctx.idempotency_key, fingerprint)
            if prior is not None:
                _output('confirm_task', 'COMMITTED', prior)
                return prior
            candidate = tx.get_candidate(candidate_id)
            _require(isinstance(candidate, dict), 'ENTITY_NOT_FOUND')
            _require(candidate['user_id'] == owner and candidate['conversation_id'] == ctx.conversation_id, 'FORBIDDEN')
            _require(type(candidate['version']) is int and candidate['version'] == expected_version
                     and candidate['status'] == 'DRAFT', 'STALE_ENTITY_VERSION')
            _require(tx.find_task_by_candidate(candidate_id) is None, 'STALE_ENTITY_VERSION')
            _require(_SLOT_VALIDATOR.is_valid(candidate['slots']), 'INVALID_PARAMETER')
            _message(tx, owner, candidate['conversation_id'], candidate['source_message_id'])
            evidence, ref = _verify_decision(tx, owner, ctx, candidate, candidate_id, expected_version)
            fields = _confirmed_fields(candidate['slots'])
            now = _timestamp(self.clock)
            task = {'task_id': str(self.id_factory()), 'user_id': owner, 'candidate_id': candidate_id,
                    'version': 1, **fields, 'remaining_minutes': fields['estimated_minutes'],
                    'status': 'TODO', 'confirmed_at': now, 'created_at': now, 'updated_at': now}
            _output('confirm_task', 'COMMITTED', task)
            tx.save_approval({'approval_action_id': ctx.approval_action_id, 'user_id': owner,
                              'target_type': 'TASK_CANDIDATE', 'target_id': candidate_id,
                              'target_version': expected_version, 'decision': 'APPROVE',
                              'source': evidence['source'], 'source_message_id': evidence.get('source_message_id'),
                              'created_at': now})
            tx.save_task(task)
            candidate.update(status='CONFIRMED', confirmed_task_id=task['task_id'],
                             version=candidate['version'] + 1, updated_at=now)
            tx.save_candidate(candidate)
            tx.complete_pending(ref['action_id'], ref['action_version'])
            tx.increment_schedule_revision(owner)
            tx.put_idempotency(owner, 'confirm_task', ctx.idempotency_key, fingerprint, task)
            return copy.deepcopy(task)

    def search_tasks(self, query, statuses, page_size, cursor, ctx):
        owner = _owner(ctx)
        args = {'query': query, 'status_filter': statuses, 'page_size': page_size, 'cursor': cursor}
        _command('search_tasks', args)
        with self.store.transaction(owner) as tx:
            items, next_cursor = tx.search_tasks(owner, query, statuses, page_size, cursor)
            _require(isinstance(items, list) and len(items) <= page_size
                     and all(isinstance(item, dict) and item.get('user_id') == owner for item in items), 'INTERNAL_ERROR')
            data = {'items': items, 'next_cursor': next_cursor}
            result = {'schema_version': '1.1', 'request_id': 'validate', 'outcome': 'READ',
                      'data': data, 'error': None, 'warnings': []}
            _require(_SEARCH_RESULT.is_valid(result), 'INTERNAL_ERROR')
            return copy.deepcopy(data)


def task_handlers(service):
    def wrap(fn, outcome):
        def handle(arguments, ctx):
            try:
                data = fn(arguments, ctx)
                return {'schema_version': '1.1', 'request_id': ctx.request_id, 'outcome': outcome,
                        'data': data, 'error': None, 'warnings': []}
            except TaskError as exc:
                return _error(ctx.request_id, exc.code, 'Task operation could not be completed.')
        return handle
    return {
        'create_task_candidate': wrap(lambda a, c: service.create_candidate(a['slots'], c), 'DRAFTED'),
        'confirm_task': wrap(lambda a, c: service.confirm_task(a['candidate_id'], a['expected_candidate_version'], c), 'COMMITTED'),
        'search_tasks': wrap(lambda a, c: service.search_tasks(a['query'], a['status_filter'], a['page_size'], a['cursor'], c), 'READ'),
    }
