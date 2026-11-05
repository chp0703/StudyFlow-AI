"""POST processing behind an API receipt: claim -> replay or process -> complete."""

from __future__ import annotations

import copy

from ...clients.rpc import child_key
from .http import STATUS, ApiError, respond


class ActionProcessor:
    def __init__(self, api):
        self.api = api

    def run(self, ctx, http_operation: str, key: str, fingerprint: str, body: dict, path: dict):
        api = self.api
        conversation = body["conversation_id"]
        claim = api.rpc(ctx, "claim_api_receipt", {
            "http_operation": http_operation, "idempotency_key": key, "request_fingerprint": fingerprint,
            "conversation_id": conversation}, conversation_id=conversation, idempotency_key=child_key(key, "claim"))
        if claim.get("outcome") == "ERROR":
            error = claim["error"]
            raise ApiError(error["code"], error["message"], status=STATUS.get(error["code"], 500),
                           retryable=bool(error.get("retryable")), retry_after=2 if error["code"] == "SERVICE_UNAVAILABLE" else None)
        receipt = claim["data"]
        if receipt["state"] == "COMPLETED":
            return self.replay(ctx, receipt)
        return self.process(ctx, receipt, http_operation, key, body, path)

    @staticmethod
    def replay(ctx, receipt: dict):
        """The stored reply is the only source: nothing is re-extracted or re-executed."""
        reply = copy.deepcopy(receipt["response"])
        reply["request_id"] = ctx.request_id
        if reply.get("result") is not None:
            reply["result"]["request_id"] = ctx.request_id
        return respond(reply, receipt["http_status"], ctx.request_id, post=True, replayed=True)

    def process(self, ctx, receipt: dict, http_operation: str, key: str, body: dict, path: dict):
        # The processing steps arrive in the next stage; hand the lease back so a retry is not blocked.
        self.api.rpc(ctx, "release_api_receipt", {
            "http_operation": http_operation, "idempotency_key": key,
            "request_fingerprint": receipt["request_fingerprint"], "expected_lease_version": receipt["lease_version"]},
            conversation_id=body["conversation_id"], idempotency_key=child_key(key, "release"))
        raise ApiError("UNSUPPORTED_OPERATION", "This action is not available in this build.")
