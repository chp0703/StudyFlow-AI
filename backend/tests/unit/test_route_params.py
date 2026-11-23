import unittest
from types import SimpleNamespace

from backend.app.api.v1.http import ApiError
from backend.app.api.v1.routes import Api

UUID_LOWER = "0b3d6f2e-5c1a-4f7e-9a42-1d2e3f4a5b6c"


def req(headers=None, **path):
    return SimpleNamespace(headers=headers or {}, path_params=path)


class RouteParamTests(unittest.TestCase):
    def test_uuid_param_normalises(self):
        self.assertEqual(Api._uuid_param(req(x=UUID_LOWER.upper()), "x"), UUID_LOWER)

    def test_uuid_param_rejects(self):
        with self.assertRaises(ApiError) as cm:
            Api._uuid_param(req(x="nope"), "x")
        self.assertEqual((cm.exception.status, cm.exception.field), (400, "x"))

    def test_idempotency_key(self):
        key = "k" * 16
        self.assertEqual(Api._idempotency_key(req({"idempotency-key": key})), key)
        for headers in ({}, {"idempotency-key": "short"}, {"idempotency-key": key + "\n"}):
            with self.assertRaises(ApiError) as cm:
                Api._idempotency_key(req(headers))
            self.assertEqual((cm.exception.status, cm.exception.field), (400, "Idempotency-Key"))

    def test_post_review_keeps_raw_action_id(self):
        api = Api.__new__(Api)
        seen = {}

        async def pipeline(request, ctx, op, schema, *, path=None):
            seen.update(path)

        api.post_pipeline = pipeline
        import asyncio
        asyncio.run(api.post_review(req(action_id=UUID_LOWER.upper()), None))
        self.assertEqual(seen, {"action_id": UUID_LOWER.upper()})


if __name__ == "__main__":
    unittest.main()
