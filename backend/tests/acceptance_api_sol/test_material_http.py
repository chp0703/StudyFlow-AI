"""Real HTTP/auth/contract path. RPC persistence is stubbed; pgTAP covers SQL."""
import base64
import copy
import unittest
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.routes import Api
from backend.app.core import contract
from backend.app.core.config import Settings
from backend.app.core.security import AuthError
from backend.tests.unit.test_materials import CONVERSATION, USER, upload_body

OTHER = 'd2020000-0000-4000-8000-000000000002'


class MaterialHttpAcceptance(unittest.TestCase):
    def setUp(self):
        self.calls, self.records = [], {}
        fixture = self
        class Rpc:
            def call(self, operation, args, **kwargs):
                fixture.calls.append((operation, copy.deepcopy(args), kwargs))
                uid, material_id = kwargs['user_id'], args['material_id']
                outcome, error, data = 'READ', None, None
                if operation == 'store_assessment_material':
                    if material_id not in fixture.records:
                        material = {k: v for k, v in args.items() if k != 'chunks'}
                        material.update(assessment_version='1.0.0', user_id=uid, status='READY', error_code=None,
                                        created_at='2026-11-16T09:00:00Z', updated_at='2026-11-16T09:00:00Z')
                        fixture.records[material_id] = {'material': material, 'chunks': args['chunks']}
                        outcome = 'COMMITTED'
                    data = fixture.records[material_id]
                elif operation == 'get_assessment_material':
                    record = fixture.records.get(material_id)
                    if record and record['material']['user_id'] == uid and record['material']['conversation_id'] == args['conversation_id']:
                        data = record
                    else:
                        outcome = 'ERROR'
                        error = {'code': 'ENTITY_NOT_FOUND', 'message': 'Material not found.', 'field': None, 'details': {}, 'retryable': False}
                else:
                    raise AssertionError('Unexpected operation: ' + operation)
                return {'schema_version': '1.1', 'request_id': kwargs['request_id'], 'outcome': outcome,
                        'data': data, 'error': error, 'warnings': []}
        class Verifier:
            def verify(self, header):
                if header not in ('Bearer test-token', 'Bearer other-token'):
                    raise AuthError()
                return USER if header == 'Bearer test-token' else OTHER
        settings = Settings(supabase_url='https://supabase.example.test', supabase_publishable_key='test',
                            rpc_signing_key_id='test', rpc_signing_secret_base64=base64.b64encode(b'x' * 32).decode())
        api = Api(settings, Rpc(), Verifier(), lambda: datetime(2026, 11, 16, tzinfo=timezone.utc), None)
        self.app = FastAPI()
        api.register(self.app)
        self.context = TestClient(self.app)
        self.client = self.context.__enter__()
        self.headers = {'Authorization': 'Bearer test-token', 'Idempotency-Key': 'material-http-key-0001'}

    def tearDown(self):
        self.context.__exit__(None, None, None)

    def upload(self, body=None, headers=None):
        return self.client.post('/v1/assessment/materials', headers=headers or self.headers, json=body or upload_body())

    def test_upload_read_replay_match_B1_contract(self):
        uploaded = self.upload()
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        self.assertTrue(contract.is_valid('AssessmentMaterialDetailResult', uploaded.json()))
        self.assertEqual(uploaded.headers['Idempotency-Replayed'], 'false')
        data = uploaded.json()['data']
        self.assertEqual(data['chunks'][0]['page'], 1)
        self.assertEqual(data['chunks'][0]['topic'], 'Mạng máy tính')
        replay = self.upload()
        self.assertEqual(replay.headers['Idempotency-Replayed'], 'true')
        url = '/v1/assessment/materials/' + data['material']['material_id']
        fetched = self.client.get(url, headers=self.headers, params={'conversation_id': CONVERSATION})
        self.assertEqual(fetched.status_code, 200, fetched.text)
        self.assertEqual(fetched.json()['data'], data)
        self.assertNotIn('content_base64', fetched.text)
        self.assertEqual({c[0] for c in self.calls}, {'store_assessment_material', 'get_assessment_material'})

    def test_auth_key_owner_injection_and_wrong_mime_reject_before_rpc(self):
        self.assertEqual(self.client.post('/v1/assessment/materials', json=upload_body()).status_code, 401)
        self.assertEqual(self.upload(headers={'Authorization': 'Bearer test-token'}).status_code, 400)
        for change in ({'user_id': OTHER}, {'mime_type': 'application/pdf'}, {'topics': ['Mạng', 'Toán']}):
            response = self.upload({**upload_body(), **change})
            self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.calls, [])

    def test_get_cross_user_wrong_conversation_and_unknown_params_fail_closed(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200, response.text)
        url = '/v1/assessment/materials/' + response.json()['data']['material']['material_id']
        for headers, query in (({'Authorization': 'Bearer other-token'}, {'conversation_id': CONVERSATION}),
                               (self.headers, {'conversation_id': OTHER})):
            result = self.client.get(url, headers=headers, params=query)
            self.assertEqual(result.status_code, 404, result.text)
            self.assertNotIn('TCP', result.text)
        self.assertEqual(self.client.get(url, headers=self.headers, params={'conversation_id': CONVERSATION, 'user_id': USER}).status_code, 422)

    def test_large_body_rejected_before_rpc(self):
        result = self.client.post('/v1/assessment/materials', headers={**self.headers, 'Content-Length': str(15 * 1024 * 1024)}, content=b'{}')
        self.assertEqual(result.status_code, 413, result.text)
        self.assertEqual(self.calls, [])
