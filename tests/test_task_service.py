import copy
import itertools
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone

from backend.app.orchestrator.dispatcher import Dispatcher, Principal, TrustedContext
from backend.app.services.tasks import TaskService, TaskError, task_handlers

USER = '00000000-0000-4000-8000-000000000001'
OTHER = '00000000-0000-4000-8000-000000000002'
CONV = '00000000-0000-4000-8000-000000000003'
MSG = '00000000-0000-4000-8000-000000000004'
ACTION = '00000000-0000-4000-8000-000000000005'
APPROVAL = '00000000-0000-4000-8000-000000000006'
CANDIDATE = '00000000-0000-4000-8000-000000000007'
TASK = '00000000-0000-4000-8000-000000000008'
NOW = datetime(2026, 11, 5, 7, tzinfo=timezone.utc)
SLOTS = {'title': 'OOP', 'deadline_at': '2026-11-06T17:00:00+07:00',
         'deadline_precision': 'DATETIME', 'deadline_date': None,
         'deadline_timezone': 'Asia/Ho_Chi_Minh', 'estimated_minutes': 60}


class MemoryStore:
    """Test-only fake of the proposed TV1 seam; no real concurrency guarantees."""
    def __init__(self):
        self.data = {'candidates': {}, 'tasks': {}, 'idempotency': {}, 'revision': 0,
                     'messages': {MSG: {'message_id': MSG, 'user_id': USER, 'conversation_id': CONV}},
                     'pending': {}, 'decisions': {}, 'reviews': {}, 'approvals': {}, 'ui_events': {}, 'decision_sources': {},
                     'internal_edit_replays': {}}
        self.fail = False
        self.writes = 0

    @contextmanager
    def transaction(self, owner):
        snapshot = copy.deepcopy(self.data)
        try:
            yield self
        except Exception:
            self.data = snapshot
            raise

    def get_message(self, message_id): return copy.deepcopy(self.data['messages'].get(message_id))
    def get_pending(self, action_id): return copy.deepcopy(self.data['pending'].get(action_id))
    def get_decision(self, approval_id): return copy.deepcopy(self.data['decisions'].get(approval_id))
    def get_decision_source(self, approval_id): return copy.deepcopy(self.data['decision_sources'].get(approval_id))
    def get_review(self, action_id, version): return copy.deepcopy(self.data['reviews'].get((action_id, version)))
    def get_ui_event(self, event_id): return copy.deepcopy(self.data['ui_events'].get(event_id))
    def get_candidate(self, candidate_id): return copy.deepcopy(self.data['candidates'].get(candidate_id))
    def find_task_by_candidate(self, candidate_id):
        return next((copy.deepcopy(t) for t in self.data['tasks'].values() if t['candidate_id'] == candidate_id), None)
    def get_idempotency(self, owner, operation, key):
        return copy.deepcopy(self.data['idempotency'].get((owner, operation, key)))
    def put_idempotency(self, owner, operation, key, fingerprint, result):
        self.data['idempotency'][(owner, operation, key)] = {'fingerprint': fingerprint, 'state': 'COMPLETED', 'result': copy.deepcopy(result)}
    def get_internal_edit_replay(self, owner, key):
        return copy.deepcopy(self.data['internal_edit_replays'].get((owner, key)))
    def put_internal_edit_replay(self, owner, key, fingerprint, result):
        self.data['internal_edit_replays'][(owner, key)] = {'fingerprint': fingerprint, 'state': 'COMPLETED', 'result': copy.deepcopy(result)}
    def save_candidate(self, value):
        self.writes += 1
        self.data['candidates'][value['candidate_id']] = copy.deepcopy(value)
    def save_task(self, value):
        self.writes += 1
        if self.find_task_by_candidate(value['candidate_id']):
            raise RuntimeError('duplicate candidate')
        self.data['tasks'][value['task_id']] = copy.deepcopy(value)
        if self.fail:
            raise RuntimeError('injected failure')
    def save_approval(self, value): self.data['approvals'][value['approval_action_id']] = copy.deepcopy(value)
    def increment_schedule_revision(self, owner): self.data['revision'] += 1
    def complete_pending(self, action_id, version):
        action = self.data['pending'][action_id]
        if action['version'] != version:
            raise RuntimeError('stale pending')
        action['state'] = 'COMPLETED'
        action['version'] += 1
    def search_tasks(self, owner, query, statuses, page_size, cursor):
        values = [copy.deepcopy(t) for t in self.data['tasks'].values()
                  if t['user_id'] == owner and (not statuses or t['status'] in statuses)
                  and (query is None or query.casefold() in t['title'].casefold())]
        values.sort(key=lambda t: t['task_id'])
        values = [t for t in values if cursor is None or t['task_id'] > cursor]
        page = values[:page_size]
        return page, page[-1]['task_id'] if len(values) > page_size else None


class TaskServiceTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        ids = itertools.chain((CANDIDATE,), itertools.repeat(TASK))
        self.service = TaskService(self.store, clock=lambda: NOW, id_factory=lambda: next(ids))
        self.ctx = TrustedContext('req', Principal(USER), approval_action_id=APPROVAL,
                                  idempotency_key='create', conversation_id=CONV, message_id=MSG)

    def confirm_context(self, key='confirm', approval=APPROVAL):
        return TrustedContext('req-confirm', Principal(USER), approval_action_id=approval,
                              idempotency_key=key, conversation_id=CONV, message_id=MSG)

    def create(self, slots=None):
        return self.service.create_candidate(copy.deepcopy(SLOTS if slots is None else slots), self.ctx)

    def authorize(self, candidate, **overrides):
        ref = {'action_id': ACTION, 'action_version': 1, 'target_type': 'TASK_CANDIDATE',
               'target_id': CANDIDATE, 'target_version': candidate['version']}
        self.store.data['pending'][ACTION] = {'action_id': ACTION, 'user_id': USER, 'conversation_id': CONV,
            'version': 1, 'state': 'AWAITING_CONFIRMATION', 'requires_review': False,
            'candidate_id': CANDIDATE}
        self.store.data['reviews'][(ACTION, 1)] = {'user_id': USER, 'conversation_id': CONV,
            'action_id': ACTION, 'action_version': 1, 'target_id': CANDIDATE,
            'target_version': candidate['version'], 'displayed_slots': copy.deepcopy(candidate['slots'])}
        self.store.data['decisions'][APPROVAL] = {'user_id': USER, 'conversation_id': CONV,
            'source': 'CHAT', 'source_message_id': MSG,
            'decision': {'schema_version': '1.1', 'conversation_id': CONV,
                         'action_reference': ref, 'decision': 'APPROVE'}}
        self.store.data['decisions'][APPROVAL].update(overrides)
        self.store.data['decision_sources'][APPROVAL] = {'user_id': USER, 'conversation_id': CONV,
            'source': 'CHAT', 'source_message_id': MSG,
            'decision': copy.deepcopy(self.store.data['decisions'][APPROVAL]['decision'])}

    def assert_error(self, code, fn, *args):
        with self.assertRaises(TaskError) as caught:
            fn(*args)
        self.assertEqual(caught.exception.code, code)

    def test_dispatch_happy_path_and_replay(self):
        dispatcher = Dispatcher(task_handlers(self.service))
        draft = dispatcher.dispatch({'schema_version': '1.1', 'operation': 'create_task_candidate',
                                     'arguments': {'slots': SLOTS}}, self.ctx)
        self.assertEqual(draft['outcome'], 'DRAFTED', draft)
        self.authorize(draft['data'])
        cmd = {'schema_version': '1.1', 'operation': 'confirm_task',
               'arguments': {'candidate_id': CANDIDATE, 'expected_candidate_version': 1}}
        result = dispatcher.dispatch(cmd, self.confirm_context())
        self.assertEqual(result['outcome'], 'COMMITTED', result)
        self.assertEqual((result['data']['status'], result['data']['remaining_minutes']), ('TODO', 60))
        self.assertEqual(self.store.data['revision'], 1)
        self.assertEqual(self.store.data['approvals'][APPROVAL]['target_id'], CANDIDATE)
        self.assertEqual(self.store.data['pending'][ACTION]['state'], 'COMPLETED')
        self.assertEqual(self.store.data['candidates'][CANDIDATE]['status'], 'CONFIRMED')
        retry = dispatcher.dispatch(cmd, self.confirm_context())
        self.assertEqual(retry, result)
        retried_context = TrustedContext('req-after-timeout', Principal(USER), approval_action_id=APPROVAL,
            idempotency_key='confirm', conversation_id=CONV, message_id=MSG)
        retry_after_timeout = dispatcher.dispatch(cmd, retried_context)
        self.assertEqual(retry_after_timeout['request_id'], 'req-after-timeout')
        self.assertEqual(retry_after_timeout['data'], result['data'])
        self.assertEqual(len(self.store.data['tasks']), 1)
        read = dispatcher.dispatch({'schema_version': '1.1', 'operation': 'search_tasks',
            'arguments': {'query': None, 'status_filter': [], 'page_size': 10, 'cursor': None}}, self.ctx)
        self.assertEqual(read['outcome'], 'READ', read)
        self.assertEqual(read['data']['items'][0]['task_id'], TASK)

    def test_missing_draft_fields_and_forged_approval(self):
        draft = self.create({})
        self.assertEqual(draft['status'], 'DRAFT')
        self.authorize(draft)
        self.assert_error('MISSING_REQUIRED_FIELD', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())
        self.store.data['decisions'].clear()
        self.assert_error('APPROVAL_REQUIRED', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())

    def test_owner_source_and_review_must_match(self):
        draft = self.create()
        self.authorize(draft)
        for location, field, value, code in [('pending', 'user_id', OTHER, 'FORBIDDEN'),
                ('pending', 'candidate_id', OTHER, 'ACTION_REVIEW_REQUIRED'),
                ('pending', 'requires_review', True, 'ACTION_REVIEW_REQUIRED'),
                ('decisions', 'user_id', OTHER, 'FORBIDDEN'),
                ('reviews', 'displayed_slots', {}, 'ACTION_REVIEW_REQUIRED')]:
            with self.subTest(location=location, field=field):
                self.authorize(draft)
                key = (ACTION, 1) if location == 'reviews' else ACTION if location == 'pending' else APPROVAL
                self.store.data[location][key][field] = value
                self.assert_error(code, self.service.confirm_task, CANDIDATE, 1, self.confirm_context())
        self.authorize(draft)
        self.store.data['messages'][MSG]['user_id'] = OTHER
        self.assert_error('FORBIDDEN', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())

    def test_edit_makes_old_approval_stale(self):
        draft = self.create()
        self.authorize(draft)
        edit_ctx = TrustedContext('edit', Principal(USER), idempotency_key='edit', conversation_id=CONV, message_id=MSG)
        updated = self.service.edit_candidate(CANDIDATE, 1, {'title': 'OOP revised'}, edit_ctx)
        self.assertEqual(updated['version'], 2)
        self.assertEqual(updated, self.service.edit_candidate(CANDIDATE, 1, {'title': 'OOP revised'}, edit_ctx))
        self.assert_error('IDEMPOTENCY_CONFLICT', self.service.edit_candidate, CANDIDATE, 1, {'title': 'different'}, edit_ctx)
        self.assertFalse(any(k[1] == 'edit_task_candidate' for k in self.store.data['idempotency']))
        self.assert_error('STALE_ENTITY_VERSION', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())
        self.assert_error('ACTION_REVIEW_REQUIRED', self.service.confirm_task, CANDIDATE, 2, self.confirm_context())

    def test_idempotency_conflict_and_rollback(self):
        draft = self.create()
        self.assert_error('IDEMPOTENCY_CONFLICT', self.service.create_candidate, {'title': 'different'}, self.ctx)
        self.authorize(draft)
        self.store.fail = True
        with self.assertRaises(RuntimeError):
            self.service.confirm_task(CANDIDATE, 1, self.confirm_context())
        self.assertEqual(self.store.data['tasks'], {})
        self.assertEqual(self.store.data['candidates'][CANDIDATE]['status'], 'DRAFT')
        self.assertEqual(self.store.data['revision'], 0)
        self.assertEqual(self.store.data['approvals'], {})
        self.assertNotIn((USER, 'confirm_task', 'confirm'), self.store.data['idempotency'])
        self.store.fail = False
        self.assertEqual(self.service.confirm_task(CANDIDATE, 1, self.confirm_context())['task_id'], TASK)

    def test_search_is_owner_scoped_and_read_only(self):
        draft = self.create()
        self.authorize(draft)
        self.service.confirm_task(CANDIDATE, 1, self.confirm_context())
        before = copy.deepcopy(self.store.data)
        result = self.service.search_tasks(None, [], 10, None, self.ctx)
        self.assertEqual(len(result['items']), 1)
        other = TrustedContext('r', Principal(OTHER))
        self.assertEqual(self.service.search_tasks(None, [], 10, None, other)['items'], [])
        self.assertEqual(before, self.store.data)

    def test_date_cutoff_priority_display_and_past_deadline(self):
        slots = {**SLOTS, 'deadline_precision': 'DATE', 'deadline_date': '2026-11-03',
                 'deadline_at': '2026-11-04T00:00:00+07:00'}
        draft = self.create(slots)
        self.assertEqual(draft['slots']['priority'], 'NORMAL')
        self.authorize(draft)
        result = self.service.confirm_task(CANDIDATE, 1, self.confirm_context())
        self.assertEqual(result['deadline_date'], '2026-11-03')
        self.assertEqual(result['priority'], 'NORMAL')

    def test_invalid_date_cutoff_and_naive_timestamp_are_rejected(self):
        draft = self.create({**SLOTS, 'deadline_precision': 'DATE', 'deadline_date': '2026-11-03',
                             'deadline_at': '2026-11-03T00:00:00+07:00'})
        self.authorize(draft)
        self.assert_error('INVALID_PARAMETER', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())
        self.assertEqual(self.store.data['tasks'], {})
        with self.assertRaises(TaskError):
            self.service.create_candidate({**SLOTS, 'deadline_at': '2026-11-05T12:00:00'},
                TrustedContext('r', Principal(USER), idempotency_key='new', conversation_id=CONV, message_id=MSG))
        self.assert_error('INVALID_PARAMETER', self.service.create_candidate,
            {**SLOTS, 'deadline_at': '2026-11-05T12:00:10+07:00'},
            TrustedContext('r', Principal(USER), idempotency_key='new2', conversation_id=CONV, message_id=MSG))

    def test_same_key_different_request_and_different_key_same_candidate(self):
        draft = self.create()
        self.authorize(draft)
        self.service.confirm_task(CANDIDATE, 1, self.confirm_context())
        self.assert_error('IDEMPOTENCY_CONFLICT', self.service.confirm_task, CANDIDATE, 2, self.confirm_context())
        self.assert_error('STALE_ENTITY_VERSION', self.service.confirm_task, CANDIDATE, 1, self.confirm_context('other'))
        self.assertEqual(len(self.store.data['tasks']), 1)

    def test_in_progress_record_cannot_execute_again(self):
        draft = self.create()
        record = self.store.data['idempotency'][(USER, 'create_task_candidate', 'create')]
        record['state'] = 'IN_PROGRESS'
        record['result'] = None
        self.assert_error('INTERNAL_ERROR', self.service.create_candidate, SLOTS, self.ctx)
        self.assertEqual(len(self.store.data['candidates']), 1)

    def test_replay_does_not_return_cross_owner_result(self):
        self.create()
        self.store.data['idempotency'][(USER, 'create_task_candidate', 'create')]['result']['user_id'] = OTHER
        self.assert_error('INTERNAL_ERROR', self.service.create_candidate, SLOTS, self.ctx)

    def test_replay_revalidates_stored_result_structure(self):
        self.create()
        del self.store.data['idempotency'][(USER, 'create_task_candidate', 'create')]['result']['version']
        self.assert_error('INTERNAL_ERROR', self.service.create_candidate, SLOTS, self.ctx)

    def test_source_and_action_versions_and_unverified_ui_cannot_confirm(self):
        draft = self.create()
        self.authorize(draft)
        self.store.data['decisions'][APPROVAL]['decision']['action_reference']['action_version'] = 2
        self.store.data['decision_sources'][APPROVAL]['decision']['action_reference']['action_version'] = 2
        self.assert_error('ACTION_REVIEW_REQUIRED', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())
        self.authorize(draft, source='UI', source_message_id=None, source_event_id='unverified')
        self.assert_error('FORBIDDEN', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())

    def test_decision_must_match_independently_verified_source(self):
        draft = self.create()
        self.authorize(draft)
        del self.store.data['decision_sources'][APPROVAL]
        self.assert_error('FORBIDDEN', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())
        self.authorize(draft)
        self.store.data['decision_sources'][APPROVAL]['decision']['decision'] = 'REJECT'
        self.assert_error('FORBIDDEN', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())
        self.authorize(draft)
        self.store.data['decision_sources'][APPROVAL]['decision']['action_reference']['target_version'] = True
        self.assert_error('FORBIDDEN', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())

    def test_ui_decision_requires_matching_trusted_event(self):
        draft = self.create()
        event_id = '00000000-0000-4000-8000-000000000009'
        self.authorize(draft, source='UI', source_message_id=None, source_event_id=event_id)
        decision = copy.deepcopy(self.store.data['decisions'][APPROVAL]['decision'])
        self.store.data['decision_sources'][APPROVAL].update(source='UI', source_message_id=None, source_event_id=event_id)
        self.store.data['ui_events'][event_id] = {'event_id': event_id, 'user_id': USER,
            'conversation_id': CONV, 'decision': decision}
        task = self.service.confirm_task(CANDIDATE, 1, self.confirm_context())
        self.assertEqual(task['task_id'], TASK)
        self.assertEqual(self.store.data['approvals'][APPROVAL]['source'], 'UI')

    def test_revalidates_current_candidate_not_only_prior_command(self):
        draft = self.create()
        self.store.data['candidates'][CANDIDATE]['slots']['estimated_minutes'] = False
        self.authorize(self.store.data['candidates'][CANDIDATE])
        self.assert_error('INVALID_PARAMETER', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())
        self.assertEqual(self.store.data['tasks'], {})

    def test_boolean_target_version_is_not_integer_evidence(self):
        draft = self.create()
        self.authorize(draft)
        self.store.data['decisions'][APPROVAL]['decision']['action_reference']['target_version'] = True
        self.store.data['decision_sources'][APPROVAL]['decision']['action_reference']['target_version'] = True
        self.assert_error('ACTION_REVIEW_REQUIRED', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())

    def test_review_content_comparison_does_not_coerce_bool_to_number(self):
        draft = self.create({**SLOTS, 'estimated_minutes': 1})
        self.authorize(draft)
        self.store.data['reviews'][(ACTION, 1)]['displayed_slots']['estimated_minutes'] = True
        self.assert_error('ACTION_REVIEW_REQUIRED', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())

    def test_direct_service_cannot_confirm_other_users_candidate(self):
        draft = self.create()
        self.authorize(draft)
        context = TrustedContext('r', Principal(OTHER), approval_action_id=APPROVAL,
                                 idempotency_key='other', conversation_id=CONV, message_id=MSG)
        self.assert_error('FORBIDDEN', self.service.confirm_task, CANDIDATE, 1, context)
        self.assertEqual(self.store.data['tasks'], {})

    def test_decision_rejects_unrecognized_fields(self):
        draft = self.create()
        self.authorize(draft)
        self.store.data['decisions'][APPROVAL]['decision']['action_reference']['extra'] = 'x'
        self.store.data['decision_sources'][APPROVAL]['decision']['action_reference']['extra'] = 'x'
        self.assert_error('ACTION_REVIEW_REQUIRED', self.service.confirm_task, CANDIDATE, 1, self.confirm_context())

    def test_search_pagination_uses_store_cursor_and_never_exposes_other_owner(self):
        draft = self.create()
        self.authorize(draft)
        task = self.service.confirm_task(CANDIDATE, 1, self.confirm_context())
        second = {**task, 'task_id': '00000000-0000-4000-8000-000000000010'}
        foreign = {**task, 'task_id': '00000000-0000-4000-8000-000000000011', 'user_id': OTHER}
        self.store.data['tasks'][second['task_id']] = second
        self.store.data['tasks'][foreign['task_id']] = foreign
        first = self.service.search_tasks(None, ['TODO'], 1, None, self.ctx)
        following = self.service.search_tasks(None, ['TODO'], 1, first['next_cursor'], self.ctx)
        self.assertEqual(first['items'][0]['task_id'], TASK)
        self.assertEqual(following['items'][0]['task_id'], second['task_id'])
        self.assertIsNone(following['next_cursor'])


if __name__ == '__main__':
    unittest.main()
