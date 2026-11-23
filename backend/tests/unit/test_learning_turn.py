"""Unit tests for LearningSessionOperations.add_turn error branches (F3 M2)."""

from __future__ import annotations

import asyncio
import unittest

from backend.app.api.v1.http import ApiError
from backend.app.learning.answer import LearningModelError
from backend.app.learning.exceptions import IndexingError
from backend.app.learning.sessions import LearningSessionOperations
from backend.tests.unit.test_learning_interaction import sample_chunks
from backend.tests.unit.test_learning_outcome import (
    CTX, SESSION, SETTINGS, FakeModel, FakeRpc, error, ok, session, turn,
)

KEY = "turn-key-000000000001"
BODY = {"schema_version": "1.1", "kind": "ASK", "text": "Tổng hai số chẵn là gì?"}


def raising(exc):
    def embedder(_):
        raise exc
    return embedder


class TestAddTurn(unittest.TestCase):
    def run_turn(self, *, session_row=None, chunks=None, retrieve=None, append=None, embedder=None, model=None):
        rpc = FakeRpc({
            "lookup_learning_turn_receipt": ok("READ", {"found": False}),
            "get_learning_session": ok("READ", {"session": session_row or session(),
                                                "turns": [turn(1, "USER", "q"), turn(2, "ASSISTANT", "a")]}),
            "search_learning_material_chunks": retrieve or ok("READ", {"chunks": chunks if chunks is not None else sample_chunks()}),
            "append_learning_turn": append or error("STALE_ENTITY_VERSION"),
        })
        ops = LearningSessionOperations(rpc, SETTINGS, embedder=embedder or (lambda _: [0.1]), model=model)
        return asyncio.run(ops.add_turn(CTX, KEY, SESSION, BODY)), rpc

    def assert_503(self, **kwargs):
        with self.assertRaises(ApiError) as caught:
            self.run_turn(**kwargs)
        self.assertEqual(caught.exception.status, 503)
        self.assertTrue(caught.exception.retryable)
        return caught

    def test_indexing_error_is_503_without_append(self):
        self.assert_503(embedder=raising(IndexingError("SERVICE_UNAVAILABLE", "x")))

    def test_unexpected_embedder_error_is_503(self):
        self.assert_503(embedder=raising(RuntimeError("boom")))

    def test_model_error_is_503(self):
        class Bad:
            def generate(self, messages):
                raise LearningModelError("bad payload")
        self.assert_503(model=Bad())

    def test_low_similarity_skips_model_and_sends_unsupported_answer(self):
        chunks = [{**c, "cosine_similarity": 0.1} for c in sample_chunks()]
        model = FakeModel({})
        response, rpc = self.run_turn(chunks=chunks, model=model)
        self.assertIsNone(model.messages)
        args = rpc.calls[-1][1]
        self.assertEqual(rpc.calls[-1][0], "append_learning_turn")
        self.assertFalse(args["supported"])
        self.assertEqual(args["citations"], [])
        self.assertEqual(args["expected_last_ordinal"], 2)
        self.assertEqual(response.status_code, 409)

    def test_stale_version_from_append_is_409(self):
        response, _ = self.run_turn(chunks=[])
        self.assertEqual(response.status_code, 409)

    def test_retrieval_invalid_parameter_is_400_and_skips_append(self):
        response, rpc = self.run_turn(retrieve=error("INVALID_PARAMETER"))
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("append_learning_turn", [c[0] for c in rpc.calls])

    def test_foreign_session_is_internal_error(self):
        with self.assertRaises(ApiError) as caught:
            self.run_turn(session_row={**session(), "owner_id": "someone-else"})
        self.assertEqual(caught.exception.code, "INTERNAL_ERROR")


if __name__ == "__main__":
    unittest.main()
