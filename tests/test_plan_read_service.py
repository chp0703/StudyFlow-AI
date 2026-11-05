import copy
import json
import unittest
from contextlib import contextmanager
from pathlib import Path

from backend.app.orchestrator.dispatcher import Dispatcher, Principal, TrustedContext
from backend.app.services.plans import PlanReadService, plan_read_handler
from backend.app.services.tasks import TaskError

ROOT = Path(__file__).resolve().parents[1]
RESULTS = json.loads((ROOT / 'contracts/examples/result_cases.json').read_text(encoding='utf-8'))
def result(name): return copy.deepcopy(next(x['result'] for x in RESULTS if x['name'] == name))
U = '0b86db05-7591-4ec1-a8b2-95cf6848c732'
OTHER = '00000000-0000-4000-8000-000000000002'


class FakeReadStore:
    def __init__(self):
        self.plan = result('approve_study_plan')['data']
        self.proposal = result('generate_study_plan')['data']
        self.blocks = []
        self.writes = 0
    @contextmanager
    def transaction(self, owner): yield self
    def get_current_plan(self, owner): return copy.deepcopy(self.plan), copy.deepcopy(self.blocks)
    def get_plan_by_version(self, owner, version):
        return (copy.deepcopy(self.plan), copy.deepcopy(self.blocks)) if self.plan and self.plan['version'] == version else (None, [])
    def get_proposal(self, owner, proposal_id):
        return copy.deepcopy(self.proposal) if self.proposal and self.proposal['proposal_id'] == proposal_id else None
    def get_warning_context(self, owner): return {'owner':owner}


def args(view='CURRENT'):
    return {'view': view, 'version': None, 'proposal_id': None, 'start_at': None, 'end_at': None}


class PlanReadServiceTests(unittest.TestCase):
    def setUp(self):
        self.store = FakeReadStore()
        self.ctx = TrustedContext('req-read', Principal(U))
        self.service = PlanReadService(self.store, warnings=lambda snapshot, view: [])

    def test_empty_current_and_missing_history_proposal(self):
        self.store.plan = None
        self.assertEqual(self.service.get_study_plan(args(), self.ctx)[0], {'kind':'PLAN_VIEW','plan':None,'study_blocks':[]})
        for options in ({**args('HISTORY'), 'version': 1}, {**args('PROPOSAL'), 'proposal_id': U}):
            self.store.proposal = None
            with self.assertRaises(TaskError) as caught:
                self.service.get_study_plan(options, self.ctx)
            self.assertEqual(caught.exception.code, 'ENTITY_NOT_FOUND')

    def test_cross_owner_is_forbidden_without_leaking(self):
        self.store.plan['user_id'] = OTHER
        with self.assertRaises(TaskError) as caught:
            self.service.get_study_plan(args(), self.ctx)
        self.assertEqual(caught.exception.code, 'FORBIDDEN')
        self.store.proposal['payload']['study_blocks'] = [{'block_id':U, 'user_id':OTHER, 'task_id':U,
            'start_at':'2026-11-05T08:00:00+07:00','end_at':'2026-11-05T09:00:00+07:00','is_locked':False}]
        with self.assertRaises(TaskError):
            self.service.get_study_plan({**args('PROPOSAL'), 'proposal_id':U}, self.ctx)

    def test_half_open_filter_does_not_mutate_snapshot(self):
        self.store.blocks = [{'plan_id': U, 'block_id': U, 'user_id': U, 'task_id': U,
            'start_at':'2026-11-05T08:00:00+07:00','end_at':'2026-11-05T09:00:00+07:00',
            'is_locked':False,'created_at':'2026-11-05T07:00:00+07:00'}]
        before = copy.deepcopy(self.store.blocks)
        query = {**args(), 'start_at':'2026-11-05T09:00:00+07:00','end_at':'2026-11-05T10:00:00+07:00'}
        self.assertEqual(self.service.get_study_plan(query, self.ctx)[0]['study_blocks'], [])
        self.assertEqual(self.store.blocks, before)
        self.assertEqual(self.store.writes, 0)

    def test_plan_warning_and_dispatcher(self):
        issue = {'code':'CHANGED','message':'Review current plan','field':None,'details':{}}
        service = PlanReadService(self.store, warnings=lambda snapshot, view: [issue])
        handler = plan_read_handler(service)
        response = Dispatcher({'get_study_plan':handler}).dispatch(
            {'schema_version':'1.1','operation':'get_study_plan','arguments':args()}, self.ctx)
        self.assertEqual(response['outcome'], 'READ', response)
        self.assertEqual(response['warnings'], [issue])

    def test_reversed_or_one_sided_range_is_invalid(self):
        for start, end in [('2026-11-05T09:00:00+07:00','2026-11-05T08:00:00+07:00'),
                           ('2026-11-05T09:00:00+07:00',None)]:
            with self.subTest(start=start, end=end):
                with self.assertRaises(TaskError) as caught:
                    self.service.get_study_plan({**args(),'start_at':start,'end_at':end}, self.ctx)
                self.assertEqual(caught.exception.code, 'INVALID_PARAMETER')

    def test_filtered_proposal_is_read_copy_with_full_stored_payload(self):
        block = {'block_id':U,'user_id':U,'task_id':U,'start_at':'2026-11-05T08:00:00+07:00',
                 'end_at':'2026-11-05T09:00:00+07:00','is_locked':False}
        self.store.proposal['payload']['study_blocks'] = [block]
        before = copy.deepcopy(self.store.proposal)
        query = {**args('PROPOSAL'),'proposal_id':U,'start_at':'2026-11-05T09:00:00+07:00',
                 'end_at':'2026-11-05T10:00:00+07:00'}
        data, _ = self.service.get_study_plan(query, self.ctx)
        self.assertEqual(data['proposal']['payload']['study_blocks'], [])
        self.assertEqual(self.store.proposal, before)
        self.assertEqual(self.store.writes, 0)

    def test_missing_principal_and_mismatched_history(self):
        with self.assertRaises(TaskError) as caught:
            self.service.get_study_plan(args(), TrustedContext('req', None))
        self.assertEqual(caught.exception.code, 'FORBIDDEN')
        plan = copy.deepcopy(self.store.plan)
        self.store.get_plan_by_version = lambda owner, version: (plan, [])
        with self.assertRaises(TaskError) as caught:
            self.service.get_study_plan({**args('HISTORY'),'version':2},self.ctx)
        self.assertEqual(caught.exception.code, 'INTERNAL_ERROR')

    def test_malformed_proposal_payload_returns_structured_internal_error(self):
        self.store.proposal['payload'] = None
        with self.assertRaises(TaskError) as caught:
            self.service.get_study_plan({**args('PROPOSAL'),'proposal_id':U},self.ctx)
        self.assertEqual(caught.exception.code, 'INTERNAL_ERROR')


if __name__ == '__main__': unittest.main()
