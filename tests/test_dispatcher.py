import copy
import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from backend.app.orchestrator.dispatcher import Dispatcher, Principal, TrustedContext
from backend.app.orchestrator.registry import OPERATIONS

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = json.loads((ROOT / 'contracts/examples/command_cases.json').read_text(encoding='utf-8'))
RESULTS = json.loads((ROOT / 'contracts/examples/result_cases.json').read_text(encoding='utf-8'))
UUID = '0b86db05-7591-4ec1-a8b2-95cf6848c732'


def valid_command(operation):
    return copy.deepcopy(next(c['command'] for c in COMMANDS if c['name'] == operation))


def valid_result(operation):
    return copy.deepcopy(next(c['result'] for c in RESULTS if c['name'] == operation))


class DispatcherTest(unittest.TestCase):
    def setUp(self):
        self.context = TrustedContext(request_id='req-test', principal=Principal(UUID),
                                      approval_action_id=UUID, idempotency_key='key',
                                      conversation_id=UUID, message_id=UUID)
        self.handlers = {name: Mock(return_value=valid_result(name)) for name in OPERATIONS}
        self.dispatcher = Dispatcher(self.handlers)

    def test_catalog_and_dispatch_every_operation(self):
        self.assertEqual(len(OPERATIONS), 10)
        for name in OPERATIONS:
            with self.subTest(operation=name):
                command = valid_command(name)
                expected = valid_result(name)
                self.assertEqual(self.dispatcher.dispatch(command, self.context), expected)
                self.handlers[name].assert_called_once_with(command['arguments'], self.context)

    def test_unknown_operation_cannot_invoke_handler(self):
        command = valid_command('search_tasks')
        command['operation'] = 'list_tasks'
        result = self.dispatcher.dispatch(command, self.context)
        self.assertEqual(result['error']['code'], 'UNSUPPORTED_OPERATION')
        self.assertFalse(any(h.called for h in self.handlers.values()))

    def test_invalid_command_rejected_before_handler(self):
        command = valid_command('confirm_task')
        command['arguments']['approval'] = True
        self.assertEqual(self.dispatcher.dispatch(command, self.context)['error']['code'], 'INVALID_PARAMETER')
        self.handlers['confirm_task'].assert_not_called()

    def test_missing_required_argument(self):
        command = valid_command('confirm_task')
        del command['arguments']['candidate_id']
        self.assertEqual(self.dispatcher.dispatch(command, self.context)['error']['code'], 'MISSING_REQUIRED_FIELD')
        self.handlers['confirm_task'].assert_not_called()

    def test_missing_nested_required_field(self):
        command = valid_command('generate_study_plan')
        del command['arguments']['generation_scope']['start_at']
        self.assertEqual(self.dispatcher.dispatch(command, self.context)['error']['code'], 'MISSING_REQUIRED_FIELD')
        self.handlers['generate_study_plan'].assert_not_called()

    def test_context_guards(self):
        cases = [
            ('search_tasks', TrustedContext('req-test', None), 'FORBIDDEN'),
            ('search_tasks', TrustedContext('req-test', Principal('not-a-uuid')), 'FORBIDDEN'),
            ('confirm_task', TrustedContext('req-test', Principal(UUID), idempotency_key='k'), 'APPROVAL_REQUIRED'),
            ('confirm_task', TrustedContext('req-test', Principal(UUID), approval_action_id=True, idempotency_key='k'), 'APPROVAL_REQUIRED'),
            ('create_task_candidate', TrustedContext('req-test', Principal(UUID)), 'INVALID_PARAMETER'),
        ]
        for op, context, code in cases:
            with self.subTest(operation=op, code=code):
                self.assertEqual(self.dispatcher.dispatch(valid_command(op), context)['error']['code'], code)
                self.handlers[op].assert_not_called()

    def test_reads_do_not_require_approval_or_idempotency(self):
        context = TrustedContext('req-test', Principal(UUID))
        for op in ('search_tasks', 'get_study_plan'):
            with self.subTest(operation=op):
                self.assertEqual(self.dispatcher.dispatch(valid_command(op), context), valid_result(op))

    def test_candidate_requires_trusted_conversation_and_message(self):
        for conversation_id, message_id in ((None, UUID), (UUID, None), ('bad', UUID)):
            with self.subTest(conversation_id=conversation_id, message_id=message_id):
                context = TrustedContext('req-test', Principal(UUID), idempotency_key='k',
                                         conversation_id=conversation_id, message_id=message_id)
                result = self.dispatcher.dispatch(valid_command('create_task_candidate'), context)
                self.assertEqual(result['error']['code'], 'INVALID_PARAMETER')
                self.handlers['create_task_candidate'].assert_not_called()

    def test_every_write_requires_idempotency(self):
        for op, spec in OPERATIONS.items():
            if spec.writes:
                with self.subTest(operation=op):
                    ctx = TrustedContext('req-test', Principal(UUID), approval_action_id=UUID)
                    self.assertEqual(self.dispatcher.dispatch(valid_command(op), ctx)['error']['code'], 'INVALID_PARAMETER')
                    self.handlers[op].assert_not_called()

    def test_approval_required_by_each_confirmation_operation(self):
        names = ('confirm_task', 'set_availability', 'set_busy_interval',
                 'set_scheduling_preferences', 'approve_study_plan')
        self.assertEqual({name for name, spec in OPERATIONS.items() if spec.requires_approval}, set(names))
        for op in names:
            with self.subTest(operation=op):
                ctx = TrustedContext('req-test', Principal(UUID), idempotency_key='key')
                self.assertEqual(self.dispatcher.dispatch(valid_command(op), ctx)['error']['code'], 'APPROVAL_REQUIRED')
                self.handlers[op].assert_not_called()

    def test_generate_read_still_requires_idempotency(self):
        ctx = TrustedContext('req-test', Principal(UUID))
        result = self.dispatcher.dispatch(valid_command('generate_study_plan'), ctx)
        self.assertEqual(result['error']['code'], 'INVALID_PARAMETER')
        self.handlers['generate_study_plan'].assert_not_called()

    def test_wrong_result_and_mismatched_request_id_are_internal_errors(self):
        op = 'search_tasks'
        for output in (valid_result('get_study_plan'), {**valid_result(op), 'request_id': 'other'}, None):
            with self.subTest(output=output):
                self.handlers[op].return_value = output
                response = self.dispatcher.dispatch(valid_command(op), self.context)
                self.assertEqual(response['error']['code'], 'INTERNAL_ERROR')
                self.assertEqual(response['request_id'], 'req-test')

    def test_get_plan_view_must_match_requested_view(self):
        command = valid_command('get_study_plan')
        command['arguments'].update(view='PROPOSAL', proposal_id=UUID)
        response = self.dispatcher.dispatch(command, self.context)
        self.assertEqual(response['error']['code'], 'INTERNAL_ERROR')
        proposal = valid_result('generate_study_plan')['data']
        result = {**valid_result('get_study_plan'),
                  'data': {'kind': 'PROPOSAL_VIEW', 'proposal': proposal}}
        self.handlers['get_study_plan'].return_value = result
        self.assertEqual(self.dispatcher.dispatch(command, self.context), result)
        command['arguments'].update(view='CURRENT', proposal_id=None)
        self.assertEqual(self.dispatcher.dispatch(command, self.context)['error']['code'], 'INTERNAL_ERROR')

    def test_unexpected_error_is_not_leaked(self):
        self.handlers['search_tasks'].side_effect = RuntimeError('private details')
        result = self.dispatcher.dispatch(valid_command('search_tasks'), self.context)
        self.assertEqual(result['error']['code'], 'INTERNAL_ERROR')
        self.assertNotIn('private details', str(result))

    def test_missing_handler_is_internal_error(self):
        result = Dispatcher({}).dispatch(valid_command('search_tasks'), self.context)
        self.assertEqual(result['error']['code'], 'INTERNAL_ERROR')

    def test_missing_request_id_is_caller_error(self):
        with self.assertRaises(ValueError):
            self.dispatcher.dispatch(valid_command('search_tasks'), TrustedContext('', Principal(UUID)))

    def test_service_error_is_returned_when_well_formed(self):
        op = 'search_tasks'
        error = {'schema_version':'1.1', 'request_id':'req-test', 'outcome':'ERROR',
                 'data':None, 'error':{'code':'FORBIDDEN','message':'Forbidden',
                 'field':None,'details':{},'retryable':False}, 'warnings':[]}
        self.handlers[op].return_value = error
        self.assertEqual(self.dispatcher.dispatch(valid_command(op), self.context), error)

    def test_execution_log_records_safe_fields_for_success(self):
        command = valid_command('search_tasks')
        command['arguments']['query'] = 'private search text'
        context = TrustedContext('req-test', Principal(UUID), idempotency_key='secret-key')
        with self.assertLogs('backend.app.orchestrator.dispatcher', level='INFO') as captured:
            result = self.dispatcher.dispatch(command, context)
        record, = captured.records
        self.assertEqual((record.request_id, record.operation, record.outcome, record.error_code),
                         ('req-test', 'search_tasks', 'READ', None))
        self.assertGreaterEqual(record.duration_ms, 0)
        self.assertEqual(result, valid_result('search_tasks'))
        self.assertEqual(record.getMessage(), 'tool_execution')
        for secret in ('private search text', 'secret-key', UUID):
            self.assertNotIn(secret, str(record.__dict__))

    def test_execution_log_redacts_unknown_operation_and_exception(self):
        command = valid_command('search_tasks')
        command['operation'] = 'private unknown operation'
        with self.assertLogs('backend.app.orchestrator.dispatcher', level='INFO') as captured:
            result = self.dispatcher.dispatch(command, self.context)
        record, = captured.records
        self.assertEqual((record.operation, record.outcome, record.error_code),
                         ('UNKNOWN', 'ERROR', 'UNSUPPORTED_OPERATION'))
        self.assertEqual(result['error']['code'], 'UNSUPPORTED_OPERATION')
        self.assertNotIn('private unknown operation', str(record.__dict__))

        self.handlers['search_tasks'].side_effect = RuntimeError('private error details')
        with self.assertLogs('backend.app.orchestrator.dispatcher', level='INFO') as captured:
            result = self.dispatcher.dispatch(valid_command('search_tasks'), self.context)
        record, = captured.records
        self.assertEqual((record.operation, record.outcome, record.error_code),
                         ('search_tasks', 'ERROR', 'INTERNAL_ERROR'))
        self.assertEqual(result['request_id'], 'req-test')
        self.assertNotIn('private error details', str(record.__dict__))

    def test_invalid_trusted_context_keeps_exception_without_logging_contents(self):
        with self.assertLogs('backend.app.orchestrator.dispatcher', level='INFO') as captured:
            with self.assertRaises(ValueError):
                self.dispatcher.dispatch(valid_command('search_tasks'), TrustedContext('', Principal(UUID)))
        record, = captured.records
        self.assertIsNone(record.request_id)
        self.assertEqual((record.outcome, record.error_code), ('ERROR', 'INTERNAL_ERROR'))
        self.assertNotIn(UUID, str(record.__dict__))

    def test_invalid_timestamp_is_rejected_before_dispatch(self):
        for timestamp in ('2026-11-05T08:00:00', '2026-13-05T08:00:00Z',
                          'not-a-timestamp', '2026-11-05 08:00:00+07:00',
                          '2026-11-05T08:00:00+07:99'):
            with self.subTest(timestamp=timestamp):
                command = valid_command('generate_study_plan')
                command['arguments']['generation_scope']['start_at'] = timestamp
                self.assertEqual(self.dispatcher.dispatch(command, self.context)['error']['code'], 'INVALID_PARAMETER')
                self.handlers['generate_study_plan'].assert_not_called()

    def test_timestamp_offsets_are_accepted(self):
        for timestamp in ('2026-11-05T01:00:00Z', '2026-11-05t08:00:00.123+07:00',
                          '2026-11-05T01:00:00-00:00'):
            with self.subTest(timestamp=timestamp):
                command = valid_command('generate_study_plan')
                command['arguments']['generation_scope']['start_at'] = timestamp
                self.assertEqual(self.dispatcher.dispatch(command, self.context)['outcome'], 'PROPOSED')

    def test_invalid_output_timestamp_is_internal_error(self):
        for timestamp in ('2026-11-05T08:00:00', '2026-02-30T08:00:00Z'):
            with self.subTest(timestamp=timestamp):
                result = valid_result('search_tasks')
                result['data']['items'][0]['deadline_at'] = timestamp
                self.handlers['search_tasks'].return_value = result
                self.assertEqual(self.dispatcher.dispatch(valid_command('search_tasks'), self.context)['error']['code'], 'INTERNAL_ERROR')

    def test_logging_failure_does_not_hide_service_result(self):
        with patch('backend.app.orchestrator.dispatcher.logger.info', side_effect=RuntimeError('log error')):
            self.assertEqual(self.dispatcher.dispatch(valid_command('search_tasks'), self.context), valid_result('search_tasks'))


if __name__ == '__main__':
    unittest.main()
