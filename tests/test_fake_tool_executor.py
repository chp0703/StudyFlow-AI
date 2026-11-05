import copy
import json
import unittest
from pathlib import Path

from backend.app.orchestrator.dispatcher import Principal, TrustedContext
from tests.fakes.tool_executor import FakeToolExecutor

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = json.loads((ROOT / 'contracts/examples/command_cases.json').read_text(encoding='utf-8'))
USER = '0b86db05-7591-4ec1-a8b2-95cf6848c732'


def command(name):
    return copy.deepcopy(next(c['command'] for c in COMMANDS if c['name'] == name))


class FakeToolExecutorTests(unittest.TestCase):
    def setUp(self):
        self.context = TrustedContext('req-one', Principal(USER), approval_action_id=USER,
                                      idempotency_key='key', conversation_id=USER, message_id=USER)

    def test_all_ten_operations_and_request_id(self):
        executor = FakeToolExecutor()
        expected = {'create_task_candidate': 'DRAFTED', 'confirm_task': 'COMMITTED',
                    'search_tasks': 'READ', 'set_availability': 'COMMITTED',
                    'set_busy_interval': 'COMMITTED', 'set_scheduling_preferences': 'COMMITTED',
                    'generate_study_plan': 'PROPOSED', 'get_study_plan': 'READ',
                    'approve_study_plan': 'COMMITTED', 'reject_study_plan': 'REJECTED'}
        for op, outcome in expected.items():
            with self.subTest(operation=op):
                result = executor.execute(command(op), self.context)
                self.assertEqual(result['outcome'], outcome, result)
                self.assertEqual(result['request_id'], 'req-one')

    def test_selected_error_and_read_view(self):
        fake = FakeToolExecutor({'confirm_task': 'STALE_ENTITY_VERSION', 'get_study_plan': 'proposal'})
        self.assertEqual(fake.execute(command('confirm_task'), self.context)['error']['code'], 'STALE_ENTITY_VERSION')
        cmd = command('get_study_plan')
        cmd['arguments'].update(view='PROPOSAL', proposal_id=USER)
        self.assertEqual(fake.execute(cmd, self.context)['data']['kind'], 'PROPOSAL_VIEW')
        history = FakeToolExecutor({'get_study_plan': 'history'})
        cmd['arguments'].update(view='HISTORY', proposal_id=None, version=1)
        self.assertEqual(history.execute(cmd, self.context)['data']['plan']['version'], 1)

    def test_candidate_fixture_can_be_incomplete(self):
        result = FakeToolExecutor().execute(command('create_task_candidate'), self.context)
        self.assertEqual(result['outcome'], 'DRAFTED')
        self.assertEqual(result['data']['slots'], {})

    def test_principal_approval_and_idempotency_gates_are_not_bypassed(self):
        fake = FakeToolExecutor()
        self.assertEqual(fake.execute(command('search_tasks'), TrustedContext('r', None))['error']['code'], 'FORBIDDEN')
        self.assertEqual(fake.execute(command('confirm_task'), TrustedContext('r', Principal(USER), idempotency_key='k'))['error']['code'], 'APPROVAL_REQUIRED')
        self.assertEqual(fake.execute(command('confirm_task'), TrustedContext('r', Principal(USER), approval_action_id=USER))['error']['code'], 'INVALID_PARAMETER')

    def test_result_mutation_does_not_change_later_requests_or_fixture(self):
        fake = FakeToolExecutor()
        first = fake.execute(command('search_tasks'), self.context)
        first['data']['items'][0]['title'] = 'modified'
        other = TrustedContext('req-two', Principal(USER))
        second = fake.execute(command('search_tasks'), other)
        self.assertNotEqual(second['data']['items'][0]['title'], 'modified')
        self.assertEqual(second['request_id'], 'req-two')
        self.assertNotEqual(FakeToolExecutor().execute(command('search_tasks'), other)['data']['items'][0]['title'], 'modified')

    def test_unknown_operation_and_invalid_command(self):
        fake = FakeToolExecutor()
        cmd = command('search_tasks')
        cmd['operation'] = 'not-supported'
        self.assertEqual(fake.execute(cmd, self.context)['error']['code'], 'UNSUPPORTED_OPERATION')
        cmd = command('confirm_task')
        cmd['arguments']['approval'] = True
        self.assertEqual(fake.execute(cmd, self.context)['error']['code'], 'INVALID_PARAMETER')

    def test_configuration_rejects_unknown_or_provisional_scenarios(self):
        with self.assertRaises(ValueError):
            FakeToolExecutor({'generate_study_plan': 'READ'})
        with self.assertRaises(ValueError):
            FakeToolExecutor({'invented': 'success'})


if __name__ == '__main__':
    unittest.main()
