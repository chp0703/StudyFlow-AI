"""Real ASGI HTTP tests; private persistence is replaced at the RPC boundary.

Database ownership, SQL signatures and transaction behavior are verified by pgTAP.
"""

import base64
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.tests.unit.test_source_routes import SourceRouteTests
from backend.tests.unit.test_source_workflow import CONVERSATION, ICS


class IngestionHttpAcceptance(unittest.TestCase):
    def setUp(self):
        self.fixture = SourceRouteTests(methodName='runTest')
        self.fixture.setUp()
        app = FastAPI()
        self.fixture.api.register(app)
        self.context = TestClient(app)
        self.client = self.context.__enter__()
        self.headers = {'Authorization': 'Bearer test-token', 'Idempotency-Key': 'source-http-key-0001'}

    def tearDown(self):
        self.context.__exit__(None, None, None)

    def upload(self):
        return self.client.post('/v1/sources', headers=self.headers, json={
            'schema_version': '1.1', 'conversation_id': CONVERSATION,
            'filename': 'class.ics', 'mime_type': 'text/calendar', 'content_base64': base64.b64encode(ICS).decode()})

    def test_upload_requires_authentication_before_any_persistence(self):
        response = self.client.post('/v1/sources', json={})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.fixture.store.calls, [])

    def test_uploaded_calendar_is_extracted_and_cached_without_applying_schedule(self):
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        source_id = response.json()['data']['source_id']
        url = f'/v1/sources/{source_id}/extract'
        body = {'schema_version': '1.1', 'conversation_id': CONVERSATION}
        first = self.client.post(url, headers=self.headers, json=body)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['data']['status'], 'READY')
        second = self.client.post(url, headers=self.headers, json=body)
        self.assertEqual(second.headers['Idempotency-Replayed'], 'true')
        self.assertEqual(self.fixture.store.calls.count('complete_source_extraction'), 1)
        self.assertNotIn('set_busy_interval', self.fixture.store.calls)
        self.assertNotIn('approve_study_plan', self.fixture.store.calls)

    def test_wrong_conversation_get_is_404_without_file_data(self):
        source_id = self.upload().json()['data']['source_id']
        response = self.client.get(f'/v1/sources/{source_id}', headers=self.headers,
            params={'conversation_id': '00200000-0000-4000-8000-000000000099'})
        self.assertEqual(response.status_code, 404)
        self.assertNotIn('content_base64', response.text)


if __name__ == '__main__':
    unittest.main()
