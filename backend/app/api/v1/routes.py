"""The eight F1 endpoints. The user id comes only from the verified JWT; every database call
carries that same JWT, so RLS and the attested RPC boundary both see the real caller."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool

from ...clients.rpc import RpcClient, RpcUnavailable, child_key
from ...core import contract
from ...core.config import Settings
from ...core.security import AuthError, AuthUnavailable, JwtVerifier
from .http import STATUS, ApiError, error_body, error_response, respond
from .workflow import ActionProcessor

log = logging.getLogger("studyflow.api")
_KEY = re.compile(r"^[A-Za-z0-9._:-]{16,128}$")
_INT = re.compile(r"^[0-9]{1,16}$")
ACTION_OPERATIONS = ("create_task_candidate", "set_availability", "set_busy_interval",
                     "set_scheduling_preferences", "generate_study_plan")


@dataclass(frozen=True)
class Ctx:
    request_id: str
    user_id: str
    token: str


def _int(value: str, name: str) -> int:
    if not _INT.match(value):  # unparseable input is a 400; out-of-range values fail schema validation (422)
        raise ApiError("INVALID_PARAMETER", f"{name} must be an integer.", status=400, field=name)
    return int(value)


class Api:
    def __init__(self, settings: Settings, rpc: RpcClient, verifier: JwtVerifier):
        self.settings, self.rpc_client, self.verifier = settings, rpc, verifier
        self.processor = ActionProcessor(self)

    # ----------------------------------------------------------------- plumbing
    async def authenticate(self, request: Request, request_id: str) -> Ctx:
        header = request.headers.get("authorization")
        try:
            user = await run_in_threadpool(self.verifier.verify, header)
        except AuthUnavailable:
            raise ApiError("SERVICE_UNAVAILABLE", "The service is temporarily unavailable.", retryable=True,
                           retry_after=1) from None
        except AuthError:
            raise ApiError("UNAUTHENTICATED", "A valid access token is required.") from None
        return Ctx(request_id, user, header[len("Bearer "):].strip())

    def rpc(self, ctx: Ctx, operation: str, arguments: dict, **kwargs) -> dict:
        try:
            return self.rpc_client.call(operation, arguments, token=ctx.token, user_id=ctx.user_id,
                                        request_id=ctx.request_id, **kwargs)
        except RpcUnavailable as exc:
            if exc.unauthenticated:
                raise ApiError("UNAUTHENTICATED", "A valid access token is required.") from None
            if exc.retryable:
                raise ApiError("SERVICE_UNAVAILABLE", "The service is temporarily unavailable.", retryable=True,
                               retry_after=1) from None
            raise ApiError("INTERNAL_ERROR", "The request could not be completed.") from None

    @staticmethod
    def result_response(result: dict, ctx: Ctx):
        result = {**result, "request_id": ctx.request_id}
        if result.get("outcome") == "ERROR":
            code = (result.get("error") or {}).get("code", "INTERNAL_ERROR")
            return respond(result, STATUS.get(code, 500), ctx.request_id, post=False,
                           retry_after=1 if code == "SERVICE_UNAVAILABLE" else None)
        return respond(result, 200, ctx.request_id, post=False)

    @staticmethod
    def validated(name: str, value, field: str | None = None):
        if not contract.is_valid(name, value):
            raise ApiError("INVALID_PARAMETER", "The request does not match the approved contract.", field=field)
        return value

    # ----------------------------------------------------------------- GET endpoints
    @staticmethod
    def _query(request: Request, allowed: set[str], repeated: frozenset = frozenset()) -> dict:
        values: dict = {}
        for key, value in request.query_params.multi_items():
            if key not in allowed:
                raise ApiError("INVALID_PARAMETER", "Unknown query parameter.", field=key)
            if key in repeated:
                values.setdefault(key, []).append(value)
            elif key in values:
                raise ApiError("INVALID_PARAMETER", "Query parameter repeated.", field=key)
            else:
                values[key] = value
        return values

    async def get_tasks(self, request: Request, ctx: Ctx):
        q = self._query(request, {"query", "status_filter", "page_size", "cursor"}, frozenset({"status_filter"}))
        args = {"query": q.get("query"), "status_filter": q.get("status_filter", []),
                "page_size": _int(q["page_size"], "page_size") if "page_size" in q else 50, "cursor": q.get("cursor")}
        self.validated("search_tasksArguments", args)
        return self.result_response(await run_in_threadpool(self.rpc, ctx, "search_tasks", args), ctx)

    async def get_time_windows(self, request: Request, ctx: Ctx):
        q = self._query(request, {"kind", "include_archived", "page_size", "cursor"})
        flag = q.get("include_archived", "false")
        if flag not in ("true", "false"):
            raise ApiError("INVALID_PARAMETER", "include_archived must be true or false.", status=400, field="include_archived")
        args = {"kind": q.get("kind"), "include_archived": flag == "true",
                "page_size": _int(q["page_size"], "page_size") if "page_size" in q else 50, "cursor": q.get("cursor")}
        self.validated("ListTimeWindowsArguments", args)
        return self.result_response(await run_in_threadpool(self.rpc, ctx, "list_time_windows", args), ctx)

    async def get_preferences(self, request: Request, ctx: Ctx):
        self._query(request, set())
        result = await run_in_threadpool(self.rpc, ctx, "ensure_user_context", {})
        if result.get("outcome") == "ERROR":
            return self.result_response(result, ctx)
        user = result["data"]
        body = {"schema_version": "1.1", "request_id": ctx.request_id, "outcome": "READ",
                "data": {"scheduling_policy": user["scheduling_policy"], "schedule_revision": user["schedule_revision"]},
                "error": None, "warnings": []}
        return respond(body, 200, ctx.request_id, post=False)

    async def get_plans(self, request: Request, ctx: Ctx):
        q = self._query(request, {"view", "version", "proposal_id", "start_at", "end_at"})
        args = {"view": q.get("view", "CURRENT"), "version": _int(q["version"], "version") if "version" in q else None,
                "proposal_id": q.get("proposal_id"), "start_at": q.get("start_at"), "end_at": q.get("end_at")}
        if args["view"] == "PROPOSAL" and (args["start_at"] is not None or args["end_at"] is not None):
            raise ApiError("INVALID_PARAMETER", "A proposal view takes no time window.", field="start_at")
        self.validated("get_study_planArguments", args)
        return self.result_response(await run_in_threadpool(self.rpc, ctx, "get_study_plan", args), ctx)

    # ----------------------------------------------------------------- POST pipeline
    async def read_json(self, request: Request) -> dict:
        key = request.headers.get("idempotency-key")
        if key is None or not _KEY.match(key):
            raise ApiError("INVALID_PARAMETER", "A valid Idempotency-Key header is required.", status=400,
                           field="Idempotency-Key")
        limit = self.settings.max_body_bytes
        declared = request.headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            raise ApiError("PAYLOAD_TOO_LARGE", "The request body is too large.")
        body = b""
        async for chunk in request.stream():  # stop reading as soon as the byte limit is crossed
            body += chunk
            if len(body) > limit:
                raise ApiError("PAYLOAD_TOO_LARGE", "The request body is too large.")
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ApiError("INVALID_PARAMETER", "The body is not valid JSON.", status=400) from None
        if not isinstance(data, dict):
            raise ApiError("INVALID_PARAMETER", "The body must be a JSON object.")
        if "schema_version" in data and data["schema_version"] != "1.1":
            raise ApiError("INVALID_PARAMETER", "Unsupported schema_version.", status=400, field="schema_version")
        return data

    async def post_pipeline(self, request: Request, ctx: Ctx, http_operation: str, schema: str, *,
                            path: dict | None = None):
        body = await self.read_json(request)
        if http_operation == "prepare_action" and body.get("operation") not in ACTION_OPERATIONS:
            raise ApiError("UNSUPPORTED_OPERATION", "This operation is not available through actions.")
        self.validated(schema, body)
        key = request.headers["idempotency-key"]
        fingerprint = contract.sha256_hex({"http_operation": http_operation, "path": path or {}, "body": body})
        return await run_in_threadpool(self.processor.run, ctx, http_operation, key, fingerprint, body, path or {})

    async def post_messages(self, request: Request, ctx: Ctx):
        body = await self.read_json(request)
        self.validated("UserMessage", body)
        # Natural-language extraction is the workflow stage (WP4); nothing is claimed or stored yet.
        raise ApiError("UNSUPPORTED_OPERATION", "Free-text messages are not available in this build.")

    async def post_actions(self, request: Request, ctx: Ctx):
        return await self.post_pipeline(request, ctx, "prepare_action", "ActionRequest")

    async def post_review(self, request: Request, ctx: Ctx):
        action_id = request.path_params["action_id"]
        try:
            UUID(action_id)
        except ValueError:
            raise ApiError("INVALID_PARAMETER", "action_id must be a UUID.", status=400, field="action_id") from None
        return await self.post_pipeline(request, ctx, "review_action", "ReviewActionRequest", path={"action_id": action_id})

    async def post_decisions(self, request: Request, ctx: Ctx):
        return await self.post_pipeline(request, ctx, "submit_decision", "UserDecision")

    # ----------------------------------------------------------------- registration
    def register(self, app: FastAPI) -> None:
        routes = [
            ("GET", "/v1/tasks", self.get_tasks), ("GET", "/v1/time-windows", self.get_time_windows),
            ("GET", "/v1/preferences", self.get_preferences), ("GET", "/v1/plans", self.get_plans),
            ("POST", "/v1/messages", self.post_messages), ("POST", "/v1/actions", self.post_actions),
            ("POST", "/v1/actions/{action_id}/review", self.post_review), ("POST", "/v1/decisions", self.post_decisions),
        ]
        for method, path, handler in routes:
            app.add_api_route(path, self._wrap(handler, post=method == "POST"), methods=[method],
                              include_in_schema=False)

    def _wrap(self, handler, *, post: bool):
        async def endpoint(request: Request):
            request_id = str(uuid4())  # never taken from the client
            try:
                ctx = await self.authenticate(request, request_id)
                return await handler(request, ctx)
            except ApiError as exc:
                return error_response(exc, request_id, post=post)
            except Exception:  # noqa: BLE001 - last line of defence; details stay in the log, never in the reply
                log.exception("unhandled error request_id=%s", request_id)
                return error_response(ApiError("INTERNAL_ERROR", "The request could not be completed."), request_id, post=post)
        return endpoint


def fallback_response(request: Request, status: int):
    """404/405 from the router, in the catalog envelope."""
    code = "ENTITY_NOT_FOUND" if status == 404 else "INVALID_PARAMETER"
    request_id = str(uuid4())
    error = {"code": code, "message": "The requested resource was not found." if status == 404 else "Method not allowed.",
             "field": None, "details": {}, "retryable": False}
    return respond(error_body(error, request_id, post=request.method == "POST"), status, request_id,
                   post=request.method == "POST")

