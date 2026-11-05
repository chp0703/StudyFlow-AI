"""HTTP plumbing shared by every endpoint: request IDs, catalog error envelopes, status mapping."""

from __future__ import annotations

from fastapi.responses import JSONResponse

# Domain/transport error code -> HTTP status (contracts/README.md section 3.1).
STATUS = {
    "INVALID_PARAMETER": 422, "MISSING_REQUIRED_FIELD": 422, "UNSUPPORTED_OPERATION": 422,
    "UNAUTHENTICATED": 401, "FORBIDDEN": 403, "ENTITY_NOT_FOUND": 404,
    "APPROVAL_REQUIRED": 409, "ACTION_REVIEW_REQUIRED": 409, "AMBIGUOUS_REFERENCE": 409,
    "STALE_ENTITY_VERSION": 409, "STALE_PROPOSAL": 409, "STALE_PLAN_VERSION": 409,
    "IDEMPOTENCY_CONFLICT": 409, "TIME_CONFLICT": 409, "ACTIVE_BLOCK_REQUIRES_REVIEW": 409,
    "PAYLOAD_TOO_LARGE": 413, "RATE_LIMITED": 429, "INTERNAL_ERROR": 500, "SERVICE_UNAVAILABLE": 503,
}


class ApiError(Exception):
    def __init__(self, code: str, message: str, *, status: int | None = None, field: str | None = None,
                 retryable: bool = False, retry_after: int | None = None):
        super().__init__(code)
        self.code, self.message, self.field = code, message, field
        self.status = status or STATUS[code]
        self.retryable, self.retry_after = retryable, retry_after

    def error(self) -> dict:
        return {"code": self.code, "message": self.message, "field": self.field, "details": {}, "retryable": self.retryable}


def error_body(error: dict, request_id: str, *, post: bool) -> dict:
    if post:
        return {"schema_version": "1.1", "request_id": request_id, "state": "ERROR", "message": error["message"],
                "action_reference": None, "questions": [], "result": None, "error": error}
    return {"schema_version": "1.1", "request_id": request_id, "outcome": "ERROR", "data": None,
            "error": error, "warnings": []}


def respond(body: dict, status: int, request_id: str, *, post: bool, replayed: bool = False,
            retry_after: int | None = None) -> JSONResponse:
    headers = {"X-Request-ID": request_id}
    if post:
        headers["Idempotency-Replayed"] = "true" if replayed else "false"
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(body, status_code=status, headers=headers)


def error_response(exc: ApiError, request_id: str, *, post: bool) -> JSONResponse:
    return respond(error_body(exc.error(), request_id, post=post), exc.status, request_id, post=post,
                   retry_after=exc.retry_after if exc.retry_after is not None else (1 if exc.status == 503 else None))
