"""Tám endpoint F1. ID người dùng chỉ lấy từ JWT đã xác minh; mỗi lần gọi database đều
mang cùng JWT đó, để RLS và ranh giới RPC có chứng thực cùng nhận đúng người gọi."""

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
from .http import ApiError, error_body, error_response, respond, result_response
from .workflow import ActionProcessor
from ...orchestrator.workflow_ports import WorkflowError
from ...ingestion.workflow import SourceOperations
from ...assessment.materials import MaterialOperations, MAX_BYTES as MATERIAL_MAX_BYTES
from ...assessment.questions import AssessmentQuestionOperations
from ...assessment.attempts import QuizAttemptOperations
from ...assessment.stats import TopicStatsOperations
from ...assessment.recommendations import RevisionRecommendationOperations
from ...learning.indexing import index_document
from ...learning.materials import LearningMaterialOperations, MAX_BODY_BYTES as LEARNING_MAX_BODY_BYTES
from ...learning.outcome import LearningOutcomeOperations
from ...learning.sessions import LearningSessionOperations

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
    if not _INT.match(value):  # đầu vào không phân tích được trả 400; giá trị ngoài giới hạn bị schema từ chối (422)
        raise ApiError("INVALID_PARAMETER", f"{name} must be an integer.", status=400, field=name)
    return int(value)


class Api:
    def __init__(self, settings: Settings, rpc: RpcClient, verifier: JwtVerifier, clock, extractor, source_extractor=None,
                 question_generator=None, learning_indexer=None, learning_embedder=None, learning_model=None):
        self.settings, self.rpc_client, self.verifier, self.clock = settings, rpc, verifier, clock
        self.extractor = extractor
        self.materials = MaterialOperations(self.rpc, clock)
        self.learning_materials = LearningMaterialOperations(self.rpc, learning_indexer or index_document)
        self.learning_sessions = LearningSessionOperations(
            self.rpc,
            settings,
            embedder=learning_embedder,
            model=learning_model,
        )
        self.questions = AssessmentQuestionOperations(
            self.rpc,
            self.materials,
            clock,
            question_generator,
            max_context_chunks=settings.question_max_context_chunks,
        )
        self.attempts = QuizAttemptOperations(self.rpc, clock)
        self.topic_stats = TopicStatsOperations(self.rpc)
        self.recommendations = RevisionRecommendationOperations(self.rpc, clock)
        self.learning_outcomes = LearningOutcomeOperations(self.rpc, clock)
        self.processor = ActionProcessor(self.rpc, clock, extractor, settings.default_timezone, questions=self.questions,
                                         recommendations=self.recommendations, learning_outcomes=self.learning_outcomes)
        self.sources = SourceOperations(self.rpc, source_extractor, clock)

    # ----------------------------------------------------------------- xử lý chung
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
    def validated(name: str, value, field: str | None = None):
        if not contract.is_valid(name, value):
            raise ApiError("INVALID_PARAMETER", "The request does not match the approved contract.", field=field)
        return value

    # ----------------------------------------------------------------- các endpoint GET
    @staticmethod
    def _query(request: Request, allowed: set[str], repeated: frozenset = frozenset(), *,
               error_status: int | None = None) -> dict:
        values: dict = {}
        for key, value in request.query_params.multi_items():
            if key not in allowed:
                raise ApiError("INVALID_PARAMETER", "Unknown query parameter.", field=key, status=error_status)
            if key in repeated:
                values.setdefault(key, []).append(value)
            elif key in values:
                raise ApiError("INVALID_PARAMETER", "Query parameter repeated.", field=key, status=error_status)
            else:
                values[key] = value
        return values

    async def get_tasks(self, request: Request, ctx: Ctx):
        q = self._query(request, {"query", "status_filter", "page_size", "cursor"}, frozenset({"status_filter"}))
        args = {"query": q.get("query"), "status_filter": q.get("status_filter", []),
                "page_size": _int(q["page_size"], "page_size") if "page_size" in q else 50, "cursor": q.get("cursor")}
        self.validated("search_tasksArguments", args)
        return result_response(await run_in_threadpool(self.rpc, ctx, "search_tasks", args), ctx.request_id)

    async def get_time_windows(self, request: Request, ctx: Ctx):
        q = self._query(request, {"kind", "include_archived", "page_size", "cursor"})
        flag = q.get("include_archived", "false")
        if flag not in ("true", "false"):
            raise ApiError("INVALID_PARAMETER", "include_archived must be true or false.", status=400, field="include_archived")
        args = {"kind": q.get("kind"), "include_archived": flag == "true",
                "page_size": _int(q["page_size"], "page_size") if "page_size" in q else 50, "cursor": q.get("cursor")}
        self.validated("ListTimeWindowsArguments", args)
        return result_response(await run_in_threadpool(self.rpc, ctx, "list_time_windows", args), ctx.request_id)

    async def get_preferences(self, request: Request, ctx: Ctx):
        self._query(request, set())
        result = await run_in_threadpool(self.rpc, ctx, "ensure_user_context", {})
        if result.get("outcome") == "ERROR":
            return result_response(result, ctx.request_id)
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
        return result_response(await run_in_threadpool(self.rpc, ctx, "get_study_plan", args), ctx.request_id)

    # ----------------------------------------------------------------- quy trình POST
    @staticmethod
    def _idempotency_key(request: Request) -> str:
        key = request.headers.get("idempotency-key")
        if key is None or not _KEY.fullmatch(key):
            raise ApiError("INVALID_PARAMETER", "A valid Idempotency-Key header is required.", status=400,
                           field="Idempotency-Key")
        return key

    async def read_json(self, request: Request, *, max_bytes: int | None = None,
                        invalid_object_status: int | None = None) -> dict:
        self._idempotency_key(request)
        limit = max_bytes if max_bytes is not None else self.settings.max_body_bytes
        declared = request.headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            raise ApiError("PAYLOAD_TOO_LARGE", "The request body is too large.")
        body = b""
        async for chunk in request.stream():  # dừng đọc ngay khi vượt giới hạn số byte
            body += chunk
            if len(body) > limit:
                raise ApiError("PAYLOAD_TOO_LARGE", "The request body is too large.")
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise ApiError("INVALID_PARAMETER", "The body is not valid JSON.", status=400) from None
        if not isinstance(data, dict):
            raise ApiError("INVALID_PARAMETER", "The body must be a JSON object.", status=invalid_object_status)
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
        return await self.post_pipeline(request, ctx, "send_message", "UserMessage")

    async def post_actions(self, request: Request, ctx: Ctx):
        return await self.post_pipeline(request, ctx, "prepare_action", "ActionRequest")

    async def post_review(self, request: Request, ctx: Ctx):
        self._uuid_param(request, "action_id")  # chỉ kiểm tra; path giữ giá trị gốc vì nó nằm trong fingerprint receipt
        return await self.post_pipeline(request, ctx, "review_action", "ReviewActionRequest",
                                        path={"action_id": request.path_params["action_id"]})

    async def post_decisions(self, request: Request, ctx: Ctx):
        return await self.post_pipeline(request, ctx, "submit_decision", "UserDecision")

    async def post_sources(self, request: Request, ctx: Ctx):
        body = await self.read_json(request, max_bytes=7 * 1024 * 1024)
        self.validated('SourceUploadRequest', body)
        result = await run_in_threadpool(self.sources.upload, ctx, request.headers['idempotency-key'], body)
        return result_response(result, ctx.request_id, write=True)

    async def get_source(self, request: Request, ctx: Ctx):
        query = self._query(request, {'conversation_id'})
        args = {'source_id': self._uuid_param(request, 'source_id'), 'conversation_id': query.get('conversation_id')}
        self.validated('SourceLookupArguments', args)
        result = await run_in_threadpool(self.sources.get, ctx, args['source_id'], args['conversation_id'])
        return result_response(result, ctx.request_id)

    async def post_extract_source(self, request: Request, ctx: Ctx):
        source_id = self._uuid_param(request, 'source_id')
        body = await self.read_json(request)
        self.validated('SourceExtractRequest', body)
        result = await run_in_threadpool(self.sources.extract, ctx, request.headers['idempotency-key'], source_id, body['conversation_id'])
        return result_response(result, ctx.request_id, write=True)

    async def post_materials(self, request: Request, ctx: Ctx):
        body = await self.read_json(request, max_bytes=4 * ((MATERIAL_MAX_BYTES + 2) // 3) + 65536)
        self.validated('MaterialUploadRequest', body)
        result = await run_in_threadpool(self.materials.upload, ctx, request.headers['idempotency-key'], body)
        return result_response(result, ctx.request_id, write=True)

    async def get_material(self, request: Request, ctx: Ctx):
        query = self._query(request, {'conversation_id'})
        material_id = self._uuid_param(request, 'material_id')
        result = await run_in_threadpool(self.materials.get, ctx, material_id, query.get('conversation_id'))
        return result_response(result, ctx.request_id)

    async def post_assessment_drafts(self, request: Request, ctx: Ctx):
        return await self.post_pipeline(request, ctx, "generate_question_drafts", "GenerateQuestionDraftsRequest")

    async def get_assessment_questions(self, request: Request, ctx: Ctx):
        q = self._query(request, {"material_id", "topic", "status", "page_size", "cursor"})
        args = {
            "material_id": q.get("material_id"),
            "topic": q.get("topic"),
            "status": q.get("status"),
            "page_size": _int(q["page_size"], "page_size") if "page_size" in q else 50,
            "cursor": q.get("cursor"),
        }
        self.validated("ListQuestionsArguments", args)
        result = await run_in_threadpool(self.questions.list_questions, ctx, args)
        return result_response(result, ctx.request_id)

    @staticmethod
    def _uuid_param(request: Request, name: str) -> str:
        value = request.path_params[name]
        try:
            return str(UUID(value))
        except ValueError:
            raise ApiError("INVALID_PARAMETER", f"{name} must be a UUID.", status=400, field=name) from None

    async def post_assessment_attempts(self, request: Request, ctx: Ctx):
        body = await self.read_json(request)
        self.validated("CreateQuizAttemptRequest", body)
        result = await run_in_threadpool(self.attempts.create_attempt, ctx, request.headers["idempotency-key"], body)
        return result_response(result, ctx.request_id, write=True)

    async def put_assessment_attempt_response(self, request: Request, ctx: Ctx):
        attempt_id = self._uuid_param(request, "attempt_id")
        question_id = self._uuid_param(request, "question_id")
        body = await self.read_json(request)
        self.validated("SaveQuizResponseRequest", body)
        result, replayed = await run_in_threadpool(
            self.attempts.save_response, ctx, request.headers["idempotency-key"], attempt_id, question_id, body
        )
        return result_response(result, ctx.request_id, write=True, replayed=replayed)

    async def post_assessment_attempt_submit(self, request: Request, ctx: Ctx):
        attempt_id = self._uuid_param(request, "attempt_id")
        body = await self.read_json(request)
        self.validated("SubmitQuizAttemptRequest", body)
        result, replayed = await run_in_threadpool(
            self.attempts.submit_attempt, ctx, request.headers["idempotency-key"], attempt_id, body
        )
        return result_response(result, ctx.request_id, write=True, replayed=replayed)

    async def post_assessment_recommendations(self, request: Request, ctx: Ctx):
        return await self.post_pipeline(request, ctx, "create_revision_recommendation", "CreateRevisionRecommendationRequest")

    async def get_assessment_topic_stats(self, request: Request, ctx: Ctx):
        query = self._query(request, {"material_id"})
        args = {"material_id": query.get("material_id")}
        self.validated("GetTopicStatsArguments", args)
        if args["material_id"] is not None:
            args["material_id"] = str(UUID(args["material_id"]))
        result = await run_in_threadpool(self.topic_stats.get, ctx, args)
        return result_response(result, ctx.request_id)

    async def upload_learning_material(self, request: Request, ctx: Ctx):
        body = await self.read_json(request, max_bytes=LEARNING_MAX_BODY_BYTES, invalid_object_status=400)
        return await self.learning_materials.upload(ctx, request.headers["idempotency-key"], body)

    async def get_learning_material(self, request: Request, ctx: Ctx):
        self._query(request, set(), error_status=400)
        return await self.learning_materials.get(ctx, self._uuid_param(request, "material_id"))

    async def list_learning_materials(self, request: Request, ctx: Ctx):
        query = self._query(request, {"cursor", "limit"}, error_status=400)
        limit = _int(query.get("limit", "20"), "limit")
        if not 1 <= limit <= 20:
            raise ApiError("INVALID_PARAMETER", "Limit phải từ 1 đến 20.", status=400, field="limit")
        return await self.learning_materials.list(ctx, limit, query.get("cursor"))

    async def delete_learning_material(self, request: Request, ctx: Ctx):
        self._query(request, set(), error_status=400)
        key = self._idempotency_key(request)
        return await self.learning_materials.delete(ctx, key,self._uuid_param(request, "material_id"))

    async def create_learning_session(self, request: Request, ctx: Ctx):
        self._query(request, set(), error_status=400)
        body = await self.read_json(request, invalid_object_status=400)
        return await self.learning_sessions.create_session(ctx, request.headers["idempotency-key"], body)

    async def get_learning_session(self, request: Request, ctx: Ctx):
        self._query(request, set(), error_status=400)
        return await self.learning_sessions.get_session(ctx, self._uuid_param(request, "session_id"))

    async def add_learning_turn(self, request: Request, ctx: Ctx):
        self._query(request, set(), error_status=400)
        session_id = self._uuid_param(request, "session_id")
        body = await self.read_json(request, invalid_object_status=400)
        return await self.learning_sessions.add_turn(ctx, request.headers["idempotency-key"], session_id, body)

    async def get_learning_planner_context(self, request: Request, ctx: Ctx):
        self._query(request, set(), error_status=400)
        return await self.learning_sessions.get_planner_context(ctx, self._uuid_param(request, "block_id"))

    async def prepare_learning_summary(self, request: Request, ctx: Ctx):
        self._query(request, set(), error_status=400)
        session_id = self._uuid_param(request, "session_id")
        body = await self.read_json(request, invalid_object_status=400)
        return await self.learning_sessions.prepare_summary(ctx, request.headers["idempotency-key"], session_id, body)

    # ----------------------------------------------------------------- đăng ký endpoint
    def register(self, app: FastAPI) -> None:
        routes = [
            ("GET", "/v1/tasks", self.get_tasks), ("GET", "/v1/time-windows", self.get_time_windows),
            ("GET", "/v1/preferences", self.get_preferences), ("GET", "/v1/plans", self.get_plans),
            ("POST", "/v1/messages", self.post_messages), ("POST", "/v1/actions", self.post_actions),
            ("POST", "/v1/actions/{action_id}/review", self.post_review), ("POST", "/v1/decisions", self.post_decisions),
            ("POST", "/v1/sources", self.post_sources), ("GET", "/v1/sources/{source_id}", self.get_source),
            ("POST", "/v1/sources/{source_id}/extract", self.post_extract_source),
            ("POST", "/v1/assessment/materials", self.post_materials),
            ("GET", "/v1/assessment/materials/{material_id}", self.get_material),
            ("POST", "/v1/assessment/drafts", self.post_assessment_drafts),
            ("GET", "/v1/assessment/questions", self.get_assessment_questions),
            ("POST", "/v1/assessment/attempts", self.post_assessment_attempts),
            ("PUT", "/v1/assessment/attempts/{attempt_id}/responses/{question_id}", self.put_assessment_attempt_response),
            ("POST", "/v1/assessment/attempts/{attempt_id}/submit", self.post_assessment_attempt_submit),
            ("GET", "/v1/assessment/topics/stats", self.get_assessment_topic_stats),
            ("POST", "/v1/assessment/recommendations", self.post_assessment_recommendations),
        ]
        for method, path, handler in routes:
            app.add_api_route(path, self._wrap(handler, post=method in ("POST", "PUT")), methods=[method],
                              include_in_schema=False)

        learning_routes = [
            ("POST", "/v1/materials", self.upload_learning_material),
            ("GET", "/v1/materials", self.list_learning_materials),
            ("GET", "/v1/materials/{material_id}", self.get_learning_material),
            ("DELETE", "/v1/materials/{material_id}", self.delete_learning_material),
            ("POST", "/v1/learning/sessions", self.create_learning_session),
            ("GET", "/v1/learning/sessions/{session_id}", self.get_learning_session),
            ("POST", "/v1/learning/sessions/{session_id}/turns", self.add_learning_turn),
            ("POST", "/v1/learning/sessions/{session_id}/summary", self.prepare_learning_summary),
            ("GET", "/v1/learning/planner-blocks/{block_id}/context", self.get_learning_planner_context),
        ]
        for method, path, handler in learning_routes:
            app.add_api_route(path, self._wrap(handler, post=False), methods=[method], include_in_schema=False)

    def _wrap(self, handler, *, post: bool):
        async def endpoint(request: Request):
            request_id = str(uuid4())  # không bao giờ lấy từ client
            try:
                ctx = await self.authenticate(request, request_id)
                return await handler(request, ctx)
            except WorkflowError as exc:
                return error_response(exc, request_id, post=post)
            except Exception:  # noqa: BLE001 - lớp bảo vệ cuối; chi tiết chỉ nằm trong log, không trả về client
                log.exception("unhandled error request_id=%s", request_id)
                return error_response(ApiError("INTERNAL_ERROR", "The request could not be completed."), request_id, post=post)
        return endpoint


def fallback_response(request: Request, status: int):
    """Lỗi 404/405 từ router, được bọc theo cấu trúc lỗi trong danh mục."""
    code = "ENTITY_NOT_FOUND" if status == 404 else "INVALID_PARAMETER"
    request_id = str(uuid4())
    error = {"code": code, "message": "The requested resource was not found." if status == 404 else "Method not allowed.",
             "field": None, "details": {}, "retryable": False}
    is_write = request.method in ("POST", "PUT")
    return respond(error_body(error, request_id, post=is_write), status, request_id,
                   post=is_write)

