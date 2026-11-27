import asyncio
import json
from pathlib import Path
from unittest.mock import patch

from starlette.requests import Request

from backend.app.api.v1.routes import Api, Ctx


def test_pending_read_uses_owner_scoped_rpc_and_returns_empty_state():
    calls = []

    class Rpc:
        def call(self, operation, arguments, **kwargs):
            calls.append((operation, arguments, kwargs))
            return {"outcome": "READ", "data": {"active_action": None}}

    api = object.__new__(Api)
    api.rpc_client = Rpc()
    conversation = "00200000-0000-4000-8000-000000000001"
    request = Request({"type": "http", "method": "GET", "path": f"/v1/conversations/{conversation}/pending",
                       "query_string": b"", "headers": [], "path_params": {"conversation_id": conversation}})
    ctx = Ctx("request-id", "user-id", "user-token")

    async def direct(function, *args, **kwargs):
        return function(*args, **kwargs)

    with patch("backend.app.api.v1.routes.run_in_threadpool", direct):
        response = asyncio.run(api.get_conversation_pending(request, ctx))

    assert response.status_code == 200
    assert json.loads(response.body) is None
    assert calls[0][0] == "get_workflow_context"
    assert calls[0][1] == {"conversation_id": conversation, "action_id": None, "message_id": None}
    assert calls[0][2]["token"] == "user-token"


def test_pending_read_restores_exact_server_reference_and_presentation():
    example = json.loads((Path(__file__).resolve().parents[3] / "contracts/examples/valid/OrchestratorReply.json")
                         .read_text(encoding="utf-8"))
    reference = example["action_reference"]
    presentation = example["result"]["data"]

    class Rpc:
        def call(self, operation, arguments, **kwargs):
            return {"outcome": "READ", "data": {"active_action": {
                "pending_action": presentation["pending_action"],
                "candidate": presentation["candidate"], "proposal": None,
                "last_presentation": {**{f"target_{field}": reference[f"target_{field}"]
                                         for field in ("type", "id", "version")},
                                      "presentation": presentation},
            }}}

    api = object.__new__(Api)
    api.rpc_client = Rpc()
    conversation = presentation["pending_action"]["conversation_id"]
    request = Request({"type": "http", "method": "GET", "path": f"/v1/conversations/{conversation}/pending",
                       "query_string": b"", "headers": [], "path_params": {"conversation_id": conversation}})
    ctx = Ctx("request-id", presentation["pending_action"]["user_id"], "user-token")

    async def direct(function, *args, **kwargs):
        return function(*args, **kwargs)

    with patch("backend.app.api.v1.routes.run_in_threadpool", direct):
        response = asyncio.run(api.get_conversation_pending(request, ctx))

    assert response.status_code == 200
    body = json.loads(response.body)
    assert body["state"] == "AWAITING_APPROVAL"
    assert body["action_reference"] == reference
    assert body["result"]["data"] == presentation
