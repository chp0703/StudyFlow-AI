"""Real source handlers/auth/error envelopes without a sandbox loopback socket.

Thread offloading is made synchronous only inside this test. ASGI/TestClient
acceptance remains a separate check; these tests do not claim to replace it.
"""

import base64
import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from starlette.requests import Request

from backend.app.api.v1.routes import Api
from backend.app.core.config import Settings
from backend.app.core.security import AuthError
from backend.app.ingestion.service import SourceExtractor
from backend.tests.unit.test_source_workflow import SourceStore, USER, CONVERSATION, ICS


class SourceRouteTests(unittest.TestCase):
    def setUp(self):
        self.store = SourceStore()
        store = self.store
        class Rpc:
            def call(inner, operation, arguments, **kwargs):
                return store(SimpleNamespace(user_id=kwargs['user_id'], request_id=kwargs['request_id']), operation, arguments)
        class Verifier:
            def verify(inner, header):
                if header != 'Bearer test-token':
                    raise AuthError()
                return USER
        settings = Settings(supabase_url='https://supabase.example.test', supabase_publishable_key='test',
                            rpc_signing_key_id='test', rpc_signing_secret_base64=base64.b64encode(b'x' * 32).decode())
        self.api = Api(settings, Rpc(), Verifier(), lambda: datetime(2026, 11, 13, tzinfo=timezone.utc), None,
                       SourceExtractor('https://api.deepseek.com', ''))

    def call(self, handler, *, body=None, source_id=None, query='', authenticated=True, key=True, post=True):
        headers = [(b'content-type', b'application/json')]
        if authenticated:
            headers.append((b'authorization', b'Bearer test-token'))
        if key:
            headers.append((b'idempotency-key', b'source-route-key-0001'))
        data = json.dumps(body or {}).encode()
        async def receive():
            return {'type': 'http.request', 'body': data, 'more_body': False}
        request = Request({'type': 'http', 'http_version': '1.1', 'method': 'POST' if post else 'GET',
                           'path': '/v1/sources', 'query_string': query.encode(), 'headers': headers,
                           'path_params': {'source_id': source_id} if source_id else {}}, receive)
        async def direct(function, *args, **kwargs):
            return function(*args, **kwargs)
        with patch('backend.app.api.v1.routes.run_in_threadpool', direct):
            coroutine = self.api._wrap(handler, post=post)(request)
            try:
                coroutine.send(None)
            except StopIteration as done:
                return done.value
            finally:
                coroutine.close()
        self.fail('Handler unexpectedly required an event loop')

    def upload(self):
        return self.call(self.api.post_sources, body={'schema_version': '1.1', 'conversation_id': CONVERSATION,
            'filename': 'class.ics', 'mime_type': 'text/calendar', 'content_base64': base64.b64encode(ICS).decode()})

    def test_unauthenticated_upload_and_missing_key_never_write(self):
        self.assertEqual(self.call(self.api.post_sources, authenticated=False).status_code, 401)
        self.assertEqual(self.call(self.api.post_sources, key=False).status_code, 400)
        self.assertEqual(self.store.calls, [])

    def test_upload_extract_get_returns_private_metadata_without_domain_writes(self):
        uploaded = self.upload()
        self.assertEqual(uploaded.status_code, 200)
        source_id = json.loads(uploaded.body)['data']['source_id']
        extracted = self.call(self.api.post_extract_source, body={'schema_version': '1.1', 'conversation_id': CONVERSATION}, source_id=source_id)
        self.assertEqual(extracted.status_code, 200)
        self.assertEqual(json.loads(extracted.body)['data']['status'], 'READY')
        fetched = self.call(self.api.get_source, source_id=source_id, query='conversation_id=' + CONVERSATION, post=False)
        self.assertEqual(fetched.status_code, 200)
        self.assertNotIn('content_base64', json.loads(fetched.body)['data'])
        self.assertNotIn('set_busy_interval', self.store.calls)

    def test_unknown_source_and_wrong_conversation_do_not_leak_content(self):
        source_id = json.loads(self.upload().body)['data']['source_id']
        result = self.call(self.api.get_source, source_id=source_id, query='conversation_id=00200000-0000-4000-8000-000000000099', post=False)
        self.assertEqual(result.status_code, 404)
        self.assertNotIn('Class', result.body.decode())

    def test_registered_extension_routes_match_published_openapi(self):
        app = FastAPI()
        self.api.register(app)
        paths = {(r.path, method) for r in app.routes for method in (r.methods or [])}
        self.assertTrue({('/v1/sources', 'POST'), ('/v1/sources/{source_id}', 'GET'), ('/v1/sources/{source_id}/extract', 'POST')} <= paths)


if __name__ == '__main__':
    unittest.main()
