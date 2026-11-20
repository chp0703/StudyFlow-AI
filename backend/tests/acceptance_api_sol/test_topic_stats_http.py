"""B6 HTTP authentication, query validation and RPC boundary tests."""

import copy
import json
import unittest

import httpx

from backend.tests.acceptance_api_sol import test_attempt_http as attempts
from backend.tests.unit.test_topic_stats import result


class TopicStatsHttpTests(unittest.TestCase):
    # Reuse the existing JWT and application fixtures without inheriting B5 tests.
    setUpClass = classmethod(attempts.AttemptHttpAcceptanceTests.setUpClass.__func__)
    setUp = attempts.AttemptHttpAcceptanceTests.setUp
    tearDown = attempts.AttemptHttpAcceptanceTests.tearDown
    _new_client = attempts.AttemptHttpAcceptanceTests._new_client
    _token = attempts.AttemptHttpAcceptanceTests._token
    _rpc_err = attempts.AttemptHttpAcceptanceTests._rpc_err

    def _rpc_handler(self, request):
        envelope = json.loads(request.content)["p_request"]
        self.rpc_calls.append((request.url.path.rsplit("/", 1)[-1], envelope))
        self.assertIsNone(envelope["attestation"])
        self.assertIsNone(envelope["execution_context"]["idempotency_key"])
        args = envelope["arguments"]
        if args["material_id"] == attempts.MAT_B:
            return self._rpc_err(envelope["request_id"], "ENTITY_NOT_FOUND", "Material not found.")
        body = copy.deepcopy(getattr(self, "response_body", result()))
        body["request_id"] = envelope["request_id"]
        body["data"]["material_id"] = args["material_id"]
        for item in body["data"]["items"]:
            item["material_id"] = attempts.MAT_A
        return httpx.Response(200, json=body)

    def get(self, query="", token=True):
        return self.client.get(
            "/v1/assessment/topics/stats" + query,
            headers={"Authorization": "Bearer " + self._token()} if token else {},
        )

    def test_get_all_or_filtered_stats_without_idempotency_key(self):
        for query in ["", "?material_id=" + attempts.MAT_A]:
            response = self.get(query)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["data"]["items"][0]["error_rate"], 1 / 3)
            op, env = self.rpc_calls[-1]
            self.assertEqual(op, "get_topic_stats")
            self.assertEqual(env["execution_context"]["trusted_context"]["principal"]["user_id"], attempts.USER_A)

    def test_requires_authentication(self):
        self.assertEqual(self.get(token=False).status_code, 401)
        self.assertEqual(self.rpc_calls, [])

    def test_rejects_invalid_unknown_and_repeated_query_parameters(self):
        for query in ["?material_id=bad", "?material_id=", "?user_id=" + attempts.USER_B,
                      "?material_id=" + attempts.MAT_A + "&material_id=" + attempts.MAT_A]:
            with self.subTest(query=query):
                self.assertIn(self.get(query).status_code, (400, 422))
        self.assertEqual(self.rpc_calls, [])

    def test_cross_user_material_returns_404(self):
        response = self.get("?material_id=" + attempts.MAT_B)
        self.assertEqual(response.status_code, 404, response.text)

    def test_insufficient_data_is_not_zero_error_rate(self):
        self.response_body = result(0, 0)
        response = self.get()
        self.assertEqual(response.status_code, 200, response.text)
        item = response.json()["data"]["items"][0]
        self.assertEqual(item["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(item["error_rate"])

    def test_invalid_rpc_statistics_fail_closed(self):
        self.response_body = result(0, 0)
        self.response_body["data"]["items"][0]["error_rate"] = 0
        self.assertEqual(self.get().status_code, 500)
