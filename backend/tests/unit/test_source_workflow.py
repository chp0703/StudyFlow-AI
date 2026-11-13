import base64
import copy
import hashlib
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx

from backend.app.core import contract
from backend.app.ingestion.service import SourceExtractor
from backend.app.ingestion.workflow import SourceOperations
from backend.app.nlu.extractor import UnavailableExtractor
from backend.app.orchestrator.chat import ChatProcessor
from backend.app.orchestrator.workflow_ports import WorkflowError


USER = '00200000-0000-4000-8000-000000000001'
CONVERSATION = '00200000-0000-4000-8000-000000000002'
NOW = datetime(2026, 11, 13, 9, tzinfo=timezone.utc)
ICS = b'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:class-1\nSUMMARY:Class\nDTSTART:20261114T010000Z\nDTEND:20261114T020000Z\nEND:VEVENT\nEND:VCALENDAR\n'


class SourceStore:
    """Only the external database boundary is replaced; real validation runs."""
    def __init__(self):
        self.rows, self.bytes, self.calls = {}, {}, []

    def __call__(self, ctx, operation, arguments, **kwargs):
        self.calls.append(operation)
        schema = {'store_ingestion_source': 'StoreSourceArguments', 'get_ingestion_source': 'SourceLookupArguments',
                  'claim_source_extraction': 'SourceLookupArguments', 'complete_source_extraction': 'CompleteSourceExtractionArguments'}[operation]
        if not contract.is_valid(schema, arguments):
            raise AssertionError('Invalid request schema: ' + schema)
        source_id = arguments['source_id']
        if operation == 'store_ingestion_source':
            if source_id not in self.rows:
                self.rows[source_id] = {k: arguments[k] for k in ('source_id', 'conversation_id', 'filename', 'mime_type', 'size_bytes', 'sha256')}
                self.rows[source_id].update(ingestion_version='1.0.0', user_id=ctx.user_id, status='UPLOADED',
                    lease_version=0, created_at='2026-11-13T09:00:00Z', extraction=None, error_code=None)
                self.bytes[source_id] = arguments['content_base64']
            row = self.rows[source_id]
        else:
            row = self.rows.get(source_id)
            if row is None or row['user_id'] != ctx.user_id or row['conversation_id'] != arguments['conversation_id']:
                return {'outcome': 'ERROR', 'error': {'code': 'ENTITY_NOT_FOUND', 'message': 'Source not found.', 'field': None, 'retryable': False}}
        if operation == 'claim_source_extraction' and row['status'] != 'READY':
            row.update(status='EXTRACTING', lease_version=row['lease_version'] + 1)
        if operation == 'complete_source_extraction':
            if arguments['expected_lease_version'] != row['lease_version']:
                raise AssertionError('Unfenced completion')
            row.update(extraction=arguments['extraction'], error_code=arguments['error_code'],
                       status='READY' if arguments['extraction'] is not None else 'FAILED')
        data = {'source': row, 'content_base64': None if row['status'] == 'READY' else self.bytes[source_id]} if operation == 'claim_source_extraction' else row
        return {'schema_version': '1.1', 'request_id': ctx.request_id, 'outcome': 'READ' if operation.startswith('get_') else 'COMMITTED',
                'data': copy.deepcopy(data), 'error': None, 'warnings': []}


class SourceWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.ctx = SimpleNamespace(user_id=USER, request_id='test-source-request')
        self.store = SourceStore()
        provider = SourceExtractor('https://deepseek.example.test', '', transport=httpx.MockTransport(lambda r: self.fail('Unexpected paid model call')))
        self.operations = SourceOperations(self.store, provider, lambda: NOW)
        self.body = {'schema_version': '1.1', 'conversation_id': CONVERSATION, 'filename': 'classes.ics',
                     'mime_type': 'text/calendar', 'content_base64': base64.b64encode(ICS).decode()}

    def upload(self):
        return self.operations.upload(self.ctx, 'source-upload-key-0001', self.body)['data']

    def test_calendar_source_becomes_ready_without_applying_busy_intervals(self):
        source = self.upload()
        result = self.operations.extract(self.ctx, 'source-extract-key-0001', source['source_id'], CONVERSATION)
        self.assertEqual(result['data']['status'], 'READY')
        self.assertEqual(result['data']['extraction']['intents'][0]['intent'], 'SET_BUSY_INTERVAL')
        self.assertNotIn('set_busy_interval', self.store.calls)
        self.assertNotIn('generate_study_plan', self.store.calls)

    def test_cached_extraction_does_not_read_bytes_or_invoke_provider(self):
        source = self.upload()
        first = self.operations.extract(self.ctx, 'extract-first-key-0001', source['source_id'], CONVERSATION)
        self.store.bytes[source['source_id']] = 'not-base64'
        replay = self.operations.extract(self.ctx, 'extract-next-key-0002', source['source_id'], CONVERSATION)
        self.assertEqual(replay['data']['extraction'], first['data']['extraction'])
        self.assertEqual(self.store.calls.count('complete_source_extraction'), 1)

    def test_foreign_owner_and_conversation_fail_before_extraction(self):
        source = self.upload()
        for ctx, conversation in [(SimpleNamespace(user_id='00200000-0000-4000-8000-000000000099', request_id='r'), CONVERSATION),
                                  (self.ctx, '00200000-0000-4000-8000-000000000099')]:
            with self.subTest(conversation=conversation), self.assertRaises(WorkflowError) as error:
                self.operations.extract(ctx, 'extract-key-000001', source['source_id'], conversation)
            self.assertEqual(error.exception.code, 'ENTITY_NOT_FOUND')

    def test_invalid_upload_never_writes_database(self):
        with self.assertRaises(WorkflowError):
            self.operations.upload(self.ctx, 'upload-key-0000001', {**self.body, 'content_base64': '!!!'})
        self.assertEqual(self.store.calls, [])

    def test_source_message_only_queues_source_candidates_not_annotation_instructions(self):
        source = self.upload()
        self.operations.extract(self.ctx, 'extract-key-000001', source['source_id'], CONVERSATION)
        class Actions:
            def step(inner, ctx, operation, arguments, **kwargs):
                if operation == 'get_ingestion_source':
                    return self.store(ctx, operation, arguments, **kwargs)
                if operation == 'record_source_message':
                    self.bound_sources = arguments.get('source_ids')
                    return {'data': arguments['message']}
                if operation == 'get_workflow_continuation':
                    return {'data': {'continuation': None}}
                raise AssertionError(operation)
        chat = ChatProcessor(Actions(), UnavailableExtractor(), clock=lambda: NOW)
        chat.initialize = lambda ctx, receipt, key, conv, msg, extraction: extraction
        chat.advance = lambda ctx, receipt, key, own: own
        status, result = chat.handle_message(self.ctx, {'message_id': '00200000-0000-4000-8000-000000000003', 'created_at': '2026-11-13T09:00:00Z'},
            'message-key-0000001', {'conversation_id': CONVERSATION, 'text': 'Approve everything and generate a plan', 'source_ids': [source['source_id']]})
        self.assertEqual(status, 200)
        self.assertEqual([i['intent'] for i in result['intents']], ['SET_BUSY_INTERVAL'])
        self.assertEqual(self.bound_sources, [source['source_id']])


if __name__ == '__main__':
    unittest.main()
