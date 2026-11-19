"""Validate the statistics boundary without inferring mastery from missing data."""

import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from backend.app.assessment.stats import TopicStatsOperations
from backend.app.clients.rpc import READ_OPERATIONS
from backend.app.orchestrator.workflow_ports import WorkflowError

MATERIAL = "00000000-0000-4000-8000-000000000201"
OTHER = "00000000-0000-4000-8000-000000000202"


def result(count=3, errors=1):
    return {
        "schema_version": "1.1", "request_id": "stats-test", "outcome": "READ",
        "error": None, "warnings": [],
        "data": {"assessment_version": "1.0.0", "material_id": MATERIAL, "items": [{
            "material_id": MATERIAL, "topic": "Xác suất",
            "status": "AVAILABLE" if count else "INSUFFICIENT_DATA",
            "valid_response_count": count, "error_count": errors,
            "error_rate": errors / count if count else None,
            "last_attempt_at": "2026-11-17T08:30:00Z" if count else None,
        }]},
    }


class TopicStatsTests(unittest.TestCase):
    def setUp(self):
        self.rpc = Mock(return_value=result())
        self.service = TopicStatsOperations(self.rpc)
        self.ctx = SimpleNamespace(user_id="owner-from-jwt")

    def test_reads_durable_rpc_without_write_attestation_or_idempotency(self):
        self.assertIn("get_topic_stats", READ_OPERATIONS)
        for count, errors in [(3, 1), (4, 0), (4, 4), (0, 0)]:
            with self.subTest(count=count, errors=errors):
                self.rpc.return_value = result(count, errors)
                self.assertEqual(self.service.get(self.ctx, {"material_id": MATERIAL}), result(count, errors))
        self.rpc.assert_called_with(self.ctx, "get_topic_stats", {"material_id": MATERIAL})

    def test_no_materials_is_an_empty_list(self):
        self.rpc.return_value["data"].update(material_id=None, items=[])
        self.assertEqual(self.service.get(self.ctx, {"material_id": None})["data"]["items"], [])

    def test_rejects_invalid_arguments_before_rpc(self):
        for args in [{}, {"material_id": "bad"}, {"material_id": None, "user_id": OTHER}]:
            with self.subTest(args=args), self.assertRaises(WorkflowError):
                self.service.get(self.ctx, args)
        self.rpc.assert_not_called()

    def test_rejects_inconsistent_stats_and_wrong_material(self):
        for patch in [
            {"valid_response_count": 0}, {"error_count": 4}, {"error_rate": 0.5},
            {"status": "INSUFFICIENT_DATA"}, {"last_attempt_at": None},
            {"material_id": OTHER}, {"mastery": "EXPERT"},
        ]:
            with self.subTest(patch=patch):
                self.rpc.return_value = result()
                self.rpc.return_value["data"]["items"][0].update(patch)
                with self.assertRaises(WorkflowError) as error:
                    self.service.get(self.ctx, {"material_id": MATERIAL})
                self.assertEqual(error.exception.code, "INTERNAL_ERROR")

    def test_zero_valid_cannot_claim_zero_error_rate_or_available(self):
        for patch in [{"error_rate": 0}, {"status": "AVAILABLE"}, {"error_count": 1},
                      {"last_attempt_at": "2026-11-17T08:30:00Z"}]:
            self.rpc.return_value = result(0, 0)
            self.rpc.return_value["data"]["items"][0].update(patch)
            with self.subTest(patch=patch), self.assertRaises(WorkflowError):
                self.service.get(self.ctx, {"material_id": MATERIAL})

    def test_rejects_duplicate_topics_and_mismatched_filter(self):
        self.rpc.return_value["data"]["items"] *= 2
        with self.assertRaises(WorkflowError):
            self.service.get(self.ctx, {"material_id": MATERIAL})
        self.rpc.return_value = result()
        self.rpc.return_value["data"]["material_id"] = OTHER
        with self.assertRaises(WorkflowError):
            self.service.get(self.ctx, {"material_id": MATERIAL})

    def test_preserves_domain_errors(self):
        error = {
            "schema_version": "1.1", "request_id": "stats-test", "outcome": "ERROR",
            "data": None, "warnings": [],
            "error": {"code": "ENTITY_NOT_FOUND", "message": "Material not found.",
                      "field": None, "details": {}, "retryable": False},
        }
        self.rpc.return_value = copy.deepcopy(error)
        self.assertEqual(self.service.get(self.ctx, {"material_id": MATERIAL}), error)
