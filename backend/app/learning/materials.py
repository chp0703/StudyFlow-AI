"""Owner-scoped material uploads and polling over the signed learning RPCs."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import PurePosixPath
from uuid import UUID

from fastapi.concurrency import run_in_threadpool

from ..api.v1.http import ApiError, STATUS, respond
from ..core import contract
from ..ingestion.document import IndexingError, IndexUnavailableError
from ..ingestion.models import MIME_EXTENSIONS, decode_upload
from ..orchestrator.workflow_ports import WorkflowError
from .indexing import MAX_BYTES, index_document

MAX_BODY_BYTES = 7 * 1024 * 1024
MAX_ENCODED_BYTES = 4 * ((MAX_BYTES + 2) // 3)
INDEX_SECONDS = 90
log = logging.getLogger(__name__)
_index_worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="learning-index")
_worker_slot = threading.BoundedSemaphore()
_FORMATS = {"application/pdf", "text/plain", "text/markdown"}


def _upload_bytes(body: dict) -> bytes:
    mime, filename, encoded = body.get("mime_type"), body.get("filename"), body.get("content_base64")
    if isinstance(mime, str) and (
        mime not in _FORMATS or isinstance(filename, str)
        and filename.strip() and PurePosixPath(filename).suffix.lower() not in MIME_EXTENSIONS[mime]
    ):
        raise ApiError("INVALID_PARAMETER", "Định dạng tệp chưa được hỗ trợ.", status=415, field="mime_type")
    if isinstance(encoded, str) and len(encoded) > MAX_ENCODED_BYTES:
        raise ApiError("PAYLOAD_TOO_LARGE", "Tệp vượt giới hạn 5 MiB.")
    if not contract.is_valid("DailyMaterialUploadRequest", body):
        raise ApiError("INVALID_PARAMETER", "Yêu cầu tài liệu không đúng định dạng.", status=400)
    try:
        return decode_upload(filename, mime, encoded, max_bytes=MAX_BYTES, validate_text=False)
    except WorkflowError as exc:
        status = 413 if exc.code == "PAYLOAD_TOO_LARGE" else 400
        raise ApiError(exc.code, exc.message, status=status) from None


def _cursor(material: dict) -> str:
    position = json.dumps([material["created_at"], material["material_id"]], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(position).decode().rstrip("=")


def _read_cursor(cursor: str | None) -> tuple[str | None, str | None]:
    if cursor is None:
        return None, None
    try:
        if not 1 <= len(cursor) <= 512:
            raise ValueError
        raw = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
        timestamp, material_id = json.loads(raw)
        dt = datetime.fromisoformat(timestamp)
        if dt.utcoffset() is None:
            raise ValueError
        return dt.isoformat(), str(UUID(material_id))
    except (ValueError, AttributeError, TypeError, binascii.Error):
        raise ApiError("INVALID_PARAMETER", "Cursor tài liệu không hợp lệ.", status=400, field="cursor") from None


def _response(result: dict, ctx, schema: str, *, write=False, replayed=False):
    if not contract.is_valid(schema, result):
        raise ApiError("INTERNAL_ERROR", "Kết quả tài liệu không đúng contract.")
    if result["outcome"] == "ERROR":
        code = result["error"]["code"]
        return respond(result, STATUS.get(code, 500), ctx.request_id, post=write, retry_after=1 if code == "SERVICE_UNAVAILABLE" else None)
    return respond(result, 200, ctx.request_id, post=write, replayed=replayed)


class LearningMaterialOperations:
    def __init__(self, rpc, indexer=index_document):
        self.rpc, self.indexer = rpc, indexer

    async def upload(self, ctx, key: str, body: dict):
        content = await run_in_threadpool(_upload_bytes, body)
        metadata = {name: body.get(name) for name in ("filename", "mime_type", "course_label")}
        metadata.update(fingerprint=contract.sha256_hex(body), sha256=hashlib.sha256(content).hexdigest(),
                        byte_size=len(content))
        result = await run_in_threadpool(self.rpc, ctx, "reserve_learning_material", metadata, idempotency_key=key)
        if result["outcome"] == "ERROR":
            return _response(result, ctx, "DailyMaterialUploadResult", write=True)
        data = result["data"]
        material, claim = data["material"], data["claim"]
        if material['owner_id'] != ctx.user_id:
            raise ApiError('INTERNAL_ERROR', 'Kết quả tài liệu không đúng chủ sở hữu.')
        if claim is None:
            return _response({**result, "data": material}, ctx, "DailyMaterialUploadResult", write=True,
                             replayed=data["replayed"])

        args = {"material_id": material["material_id"], "claim": claim}
        try:
            indexed = await self.index(content, metadata["mime_type"])
            chunks = [{"page": c["page_start"], "chunk_index": c["chunk_index"], "text": c["text"],
                       "embedding": json.dumps(c["vector"], allow_nan=False, separators=(",", ":"))}
                      for c in indexed.f3_chunks]
            args.update(page_count=indexed.page_count, char_count=indexed.char_count,
                        assessment_chunks=indexed.f2_chunks, learning_chunks=chunks)
        except TimeoutError:
            result = await self.fail(ctx, key, args, "INDEX_TIMEOUT")
        except IndexingError as exc:
            result = await self.fail(ctx, key, args, exc.code)
        except Exception:
            log.error("Learning material indexing failed request_id=%s", ctx.request_id)
            result = await self.fail(ctx, key, args, "INDEX_UNAVAILABLE")
        else:
            result = await run_in_threadpool(self.rpc, ctx, "store_learning_material_chunks", args, idempotency_key=key)
            if result["outcome"] == "ERROR" and result["error"]["code"] in ("INVALID_PARAMETER", "INTERNAL_ERROR"):
                result = await self.fail(ctx, key, args, "INDEX_UNAVAILABLE")
        return _response(result, ctx, "DailyMaterialUploadResult", write=True)

    async def index(self, content: bytes, mime: str):
        if not _worker_slot.acquire(blocking=False):
            raise IndexUnavailableError("Bộ xử lý tài liệu đang bận.")
        try:
            future = _index_worker.submit(self.indexer, content, mime, deadline=time.monotonic() + INDEX_SECONDS)
        except BaseException:
            _worker_slot.release()
            raise
        future.add_done_callback(lambda _: _worker_slot.release())
        return await asyncio.wait_for(asyncio.wrap_future(future), INDEX_SECONDS)

    async def fail(self, ctx, key, args, code):
        failure = {"material_id": args["material_id"], "claim": args["claim"], "error_code": code}
        return await run_in_threadpool(self.rpc, ctx, "fail_learning_material", failure, idempotency_key=key)

    async def get(self, ctx, material_id: str):
        result = await run_in_threadpool(self.rpc, ctx, "get_learning_material", {"material_id": material_id})
        return _response(result, ctx, "DailyMaterialReadResult")

    async def list(self, ctx, limit: int, cursor: str | None):
        before_at, before_id = _read_cursor(cursor)
        args = {"limit": limit, "before_created_at": before_at, "before_material_id": before_id}
        result = await run_in_threadpool(self.rpc, ctx, "list_learning_materials", args)
        if result["outcome"] == "READ":
            materials = result["data"]["materials"]
            next_cursor = _cursor(materials[-1]) if result["data"]["has_more"] else None
            result = {**result, "data": {"materials": materials, "next_cursor": next_cursor}}
        return _response(result, ctx, "DailyMaterialListResult")

    async def delete(self, ctx, key: str, material_id: str):
        args = {"material_id": material_id}
        args["fingerprint"] = contract.sha256_hex(args)
        result = await run_in_threadpool(self.rpc, ctx, "delete_learning_material", args, idempotency_key=key)
        replayed = False
        if result["outcome"] == "COMMITTED":
            replayed = result["data"]["replayed"]
            result = {**result, "data": {"material_id": result["data"]["material_id"], "deleted": True}}
        return _response(result, ctx, "DailyMaterialDeleteResult", write=True, replayed=replayed)
