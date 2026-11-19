import base64
import io
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from pypdf import PdfReader, PdfWriter

from backend.app.core import contract
from backend.app.ingestion.document import read_document
from backend.app.orchestrator.workflow_ports import WorkflowError
from backend.tests.unit.test_ingestion import small_pdf

USER = 'd2020000-0000-4000-8000-000000000001'
CONVERSATION = 'd2020000-0000-4000-8000-000000000003'
NOW = datetime(2026, 11, 16, 9, tzinfo=timezone.utc)


def upload_body(text='Giao thức TCP truyền dữ liệu tin cậy.'):
    return {'schema_version': '1.1', 'conversation_id': CONVERSATION, 'filename': 'mang.md',
            'mime_type': 'text/markdown', 'topics': ['Mạng máy tính'],
            'content_base64': base64.b64encode(text.encode()).decode()}


def pdf_pages(count):
    writer = PdfWriter()
    for page in range(count):
        pdf = small_pdf(f'BT /F1 12 Tf 10 100 Td (Page {page + 1}) Tj ET'.encode())
        writer.add_page(PdfReader(io.BytesIO(pdf)).pages[0])
    result = io.BytesIO()
    writer.write(result)
    return result.getvalue()


class MaterialParsingTests(unittest.TestCase):
    def prepare(self, body=None):
        from backend.app.assessment.materials import prepare_material
        return prepare_material(body or upload_body(), user_id=USER,
                                material_id='d2020000-0000-4000-8000-000000000006', now=NOW)

    def test_text_chunks_preserve_content_and_user_supplied_topic(self):
        text = 'Giao thức TCP truyền dữ liệu tin cậy.\n' * 240
        result = self.prepare(upload_body(text))
        self.assertTrue(contract.is_valid('StoreMaterialArguments', result))
        self.assertEqual(''.join(c['text'] for c in result['chunks']), text.strip())
        self.assertTrue(all(c['topic'] == 'Mạng máy tính' and c['page'] == 1 for c in result['chunks']))
        self.assertTrue(all(len(c['text']) <= 4000 for c in result['chunks']))
        self.assertEqual(result['char_count'], sum(len(c['text']) for c in result['chunks']))

    def test_pdf_retains_real_page_numbers_beyond_old_limit(self):
        body = upload_body()
        body.update(filename='mang.pdf', mime_type='application/pdf', content_base64=base64.b64encode(pdf_pages(21)).decode())
        result = self.prepare(body)
        self.assertEqual(result['page_count'], 21)
        self.assertEqual([c['page'] for c in result['chunks']], list(range(1, 22)))
        self.assertIn('Page 21', result['chunks'][-1]['text'])
        with self.assertRaises(WorkflowError):
            read_document(pdf_pages(21), 'application/pdf')

    def test_chunk_boundary_keeps_search_terms_whole(self):
        text = 'a ' * 999 + ' TCP truyền dữ liệu tin cậy'
        chunks = self.prepare(upload_body(text))['chunks']
        self.assertEqual(''.join(c['text'] for c in chunks), text)
        self.assertTrue(any('TCP' in c['text'] for c in chunks))
        self.assertTrue(all(len(c['text']) <= 2000 for c in chunks))

    def test_long_token_and_whitespace_boundaries_still_terminate_with_bounded_chunks(self):
        for text in ('x' * 6001, 'a\n' * 1001 + 'DNS', 'a\t' * 1001 + 'TCP', 'a' + ' ' * 4000 + 'DNS'):
            with self.subTest(size=len(text)):
                chunks = self.prepare(upload_body(text))['chunks']
                self.assertTrue(all(len(c['text']) <= 2000 for c in chunks))
                self.assertEqual(''.join(c['text'] for c in chunks).split(), text.split())

    def test_material_limits_do_not_raise_f1_limits(self):
        self.assertEqual(self.prepare(upload_body('x' * 200000))['char_count'], 200000)
        with self.assertRaises(WorkflowError):
            self.prepare(upload_body('x' * 200001))
        with self.assertRaises(WorkflowError):
            read_document(b'x' * 24001, 'text/plain')
        body = upload_body()
        body.update(filename='x.pdf', mime_type='application/pdf', content_base64=base64.b64encode(pdf_pages(101)).decode())
        with self.assertRaises(WorkflowError):
            self.prepare(body)

    def test_rejects_bad_bytes_and_ambiguous_topics_without_model_calls(self):
        for change in ({'content_base64': '!!!'}, {'filename': '../x.md'}, {'mime_type': 'image/png'},
                       {'topics': ['Mạng', 'Toán']}, {'topics': ['   ']}, {'content_base64': base64.b64encode(b'\x00').decode()}):
            with self.subTest(change=change), self.assertRaises(WorkflowError):
                self.prepare({**upload_body(), **change})

    def test_timeout_is_safe_and_does_not_return_partial_pdf(self):
        import subprocess
        body = {**upload_body(), 'filename': 'x.pdf', 'mime_type': 'application/pdf',
                'content_base64': base64.b64encode(b'%PDF-bad').decode()}
        with patch('backend.app.ingestion.document.subprocess.run', side_effect=subprocess.TimeoutExpired('pdf', 15)):
            with self.assertRaises(WorkflowError):
                self.prepare(body)


class MaterialOperationsTests(unittest.TestCase):
    def test_uppercase_UUIDs_use_same_material_for_upload_read_and_search(self):
        from backend.app.assessment.materials import MaterialOperations
        args = MaterialParsingTests().prepare()
        material = {k: v for k, v in args.items() if k != 'chunks'}
        material.update(assessment_version='1.0.0', user_id=USER, status='READY', error_code=None,
                        created_at='2026-11-16T09:00:00Z', updated_at='2026-11-16T09:00:00Z')
        def rpc(ctx, operation, arguments, **kwargs):
            if operation == 'search_material_chunks':
                data = {'material_id': material['material_id'], 'items': args['chunks']}
            else:
                data = {'material': material, 'chunks': args['chunks']}
            return {'schema_version': '1.1', 'request_id': ctx.request_id,
                    'outcome': 'COMMITTED' if operation == 'store_assessment_material' else 'READ',
                    'data': data, 'error': None, 'warnings': []}
        service = MaterialOperations(rpc, lambda: NOW)
        ctx = SimpleNamespace(user_id=USER, request_id='test')
        with patch('backend.app.assessment.materials.uuid5', return_value=UUID(material['material_id'])):
            operations = [lambda: service.upload(ctx, 'material-upload-key-0001', {**upload_body(), 'conversation_id': CONVERSATION.upper()}),
                          lambda: service.get(ctx, material['material_id'].upper(), CONVERSATION.upper()),
                          lambda: service.search(ctx, material['material_id'].upper(), query='TCP')]
            for operation in operations:
                with self.subTest(operation=operation):
                    self.assertIsNone(operation()['error'])

    def test_upload_calls_only_signed_store_and_stable_ids(self):
        from backend.app.assessment.materials import MaterialOperations
        calls = []
        def rpc(ctx, operation, arguments, **kwargs):
            calls.append((operation, arguments, kwargs))
            material = {k: v for k, v in arguments.items() if k != 'chunks'}
            material.update(assessment_version='1.0.0', user_id=USER, status='READY', error_code=None,
                            created_at='2026-11-16T09:00:00Z', updated_at='2026-11-16T09:00:00Z')
            return {'schema_version': '1.1', 'request_id': ctx.request_id, 'outcome': 'COMMITTED',
                    'data': {'material': material, 'chunks': arguments['chunks']}, 'error': None, 'warnings': []}
        service = MaterialOperations(rpc, lambda: NOW)
        ctx = SimpleNamespace(user_id=USER, request_id='test')
        first = service.upload(ctx, 'material-upload-key-0001', upload_body())
        second = service.upload(ctx, 'material-upload-key-0001', upload_body())
        self.assertEqual(first['data'], second['data'])
        self.assertEqual([c[0] for c in calls], ['store_assessment_material'] * 2)
        self.assertEqual(calls[0][2]['conversation_id'], CONVERSATION)

    def test_search_validates_input_and_rejects_foreign_response(self):
        from backend.app.assessment.materials import MaterialOperations
        def rpc(ctx, operation, arguments, **kwargs):
            args = MaterialParsingTests().prepare()
            chunk = {**args['chunks'][0], 'user_id': 'd2020000-0000-4000-8000-000000000002'}
            return {'schema_version': '1.1', 'request_id': ctx.request_id, 'outcome': 'READ',
                    'data': {'material_id': args['material_id'], 'items': [chunk]}, 'error': None, 'warnings': []}
        service = MaterialOperations(rpc, lambda: NOW)
        ctx = SimpleNamespace(user_id=USER, request_id='test')
        with self.assertRaises(WorkflowError) as error:
            service.search(ctx, 'd2020000-0000-4000-8000-000000000006', query='TCP')
        self.assertEqual(error.exception.code, 'ENTITY_NOT_FOUND')
        with self.assertRaises(WorkflowError):
            service.search(ctx, 'not-a-uuid', limit=100)
