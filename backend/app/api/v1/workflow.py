"""POST processing behind an API receipt: claim -> replay or process -> complete.

Every database step uses a key derived from the client's Idempotency-Key, so a retry after a crash
repeats the same steps with the same keys and the database replays whatever already committed.
Transient failures release the receipt lease; terminal domain errors are stored so they replay.
"""

from __future__ import annotations

import copy
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ...clients.rpc import child_key, iso
from ...f1.planning.generate import generate
from .http import STATUS, ApiError, error_body, respond

POLICY_DEFAULT = {"min_block_minutes": 25, "max_block_minutes": 90, "allow_short_final_block": True,
                  "max_daily_minutes": 240, "break_minutes": 10}
INTENT = {"create_task_candidate": "CREATE_TASK", "set_availability": "SET_AVAILABILITY",
          "set_busy_interval": "SET_BUSY_INTERVAL", "set_scheduling_preferences": "SET_SCHEDULING_PREFERENCES"}
FORM_TEXT = {"create_task_candidate": "Thêm công việc bằng biểu mẫu", "set_availability": "Cập nhật giờ rảnh bằng biểu mẫu",
             "set_busy_interval": "Cập nhật giờ bận bằng biểu mẫu", "set_scheduling_preferences": "Cập nhật tùy chọn lập lịch bằng biểu mẫu",
             "generate_study_plan": "Tạo kế hoạch học bằng biểu mẫu"}
DONE_TEXT = {"confirm_task": "Đã lưu công việc.", "set_availability": "Đã cập nhật giờ rảnh.",
             "set_busy_interval": "Đã cập nhật giờ bận.", "set_scheduling_preferences": "Đã cập nhật tùy chọn lập lịch.",
             "approve_study_plan": "Đã duyệt kế hoạch học.", "reject_study_plan": "Đã từ chối kế hoạch."}
AWAITING = ("AWAITING_CLARIFICATION", "AWAITING_CONFIRMATION", "AWAITING_APPROVAL")


class Terminal(Exception):
    """A final domain answer (stored on the receipt, so retries replay it)."""

    def __init__(self, code: str, message: str, field: str | None = None):
        super().__init__(code)
        self.error = {"code": code, "message": message, "field": field, "details": {}, "retryable": False}
        self.status = STATUS.get(code, 500)


def _ok(request_id: str, outcome: str, data) -> dict:
    return {"schema_version": "1.1", "request_id": request_id, "outcome": outcome, "data": data, "error": None, "warnings": []}


def reply(request_id: str, state: str, message: str, *, reference=None, questions=None, result=None) -> dict:
    return {"schema_version": "1.1", "request_id": request_id, "state": state, "message": message,
            "action_reference": reference, "questions": questions or [], "result": result, "error": None}


def deadline_instant(slots: dict) -> str | None:
    """A date-only deadline ends at the start of the next local day (contract section 2)."""
    try:
        zone = ZoneInfo(slots["deadline_timezone"])
        local = datetime.combine(date.fromisoformat(slots["deadline_date"]) + timedelta(days=1), time.min, zone)
    except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError):
        return None
    return iso(local.astimezone(timezone.utc))


class ActionProcessor:
    def __init__(self, api):
        from .chat import ChatProcessor  # chat builds on this module, so import it late

        self.api = api
        self.chat = ChatProcessor(api, self, api.extractor)

    # ------------------------------------------------------------ receipt lifecycle
    def run(self, ctx, http_operation: str, key: str, fingerprint: str, body: dict, path: dict):
        conversation = body["conversation_id"]
        claim = self.api.rpc(ctx, "claim_api_receipt", {
            "http_operation": http_operation, "idempotency_key": key, "request_fingerprint": fingerprint,
            "conversation_id": conversation}, conversation_id=conversation, idempotency_key=child_key(key, "claim"))
        if claim.get("outcome") == "ERROR":
            error = claim["error"]
            raise ApiError(error["code"], error["message"], status=STATUS.get(error["code"], 500),
                           retryable=bool(error.get("retryable")), retry_after=2 if error["code"] == "SERVICE_UNAVAILABLE" else None)
        receipt = claim["data"]
        if receipt["state"] == "COMPLETED":
            return self.replay(ctx, receipt)
        binding = {"http_operation": http_operation, "idempotency_key": key,
                   "request_fingerprint": receipt["request_fingerprint"], "expected_lease_version": receipt["lease_version"]}
        try:
            status, answer = self.dispatch(ctx, receipt, http_operation, key, body, path)
        except Terminal as exc:
            status, answer = exc.status, error_body(exc.error, ctx.request_id, post=True)
        except Exception:
            self._release(ctx, binding, key, conversation)  # transient or unexpected: let a retry reclaim the lease
            raise
        done = self.api.rpc(ctx, "complete_api_receipt", {**binding, "http_status": status, "response": answer},
                            conversation_id=conversation, idempotency_key=child_key(key, "complete"))
        if done.get("outcome") == "ERROR":
            # The lease was lost; domain work is replay-safe, so the client simply retries.
            raise ApiError("SERVICE_UNAVAILABLE", "The request is being completed; retry shortly.", retryable=True, retry_after=2)
        return respond(answer, status, ctx.request_id, post=True)

    def _release(self, ctx, binding: dict, key: str, conversation: str) -> None:
        try:
            self.api.rpc(ctx, "release_api_receipt", binding, conversation_id=conversation,
                         idempotency_key=child_key(key, "release"))
        except ApiError:
            pass  # the lease expires by itself after 120 seconds

    @staticmethod
    def replay(ctx, receipt: dict):
        """The stored reply is the only source: nothing is re-extracted or re-executed."""
        stored = copy.deepcopy(receipt["response"])
        stored["request_id"] = ctx.request_id
        if stored.get("result") is not None:
            stored["result"]["request_id"] = ctx.request_id
        return respond(stored, receipt["http_status"], ctx.request_id, post=True, replayed=True)

    # ------------------------------------------------------------ helpers
    def step(self, ctx, operation: str, arguments: dict, **kwargs) -> dict:
        """One database step. Domain errors become Terminal; transient ones propagate for a retry."""
        result = self.api.rpc(ctx, operation, arguments, **kwargs)
        if result.get("outcome") == "ERROR":
            error = result["error"]
            if error["code"] in ("SERVICE_UNAVAILABLE", "INTERNAL_ERROR", "UNAUTHENTICATED"):
                raise ApiError(error["code"], error["message"], retryable=True, retry_after=1)
            raise Terminal(error["code"], error["message"], error.get("field"))
        return result

    def dispatch(self, ctx, receipt, http_operation, key, body, path):
        if http_operation == "send_message":
            return self.chat.handle_message(ctx, receipt, key, body)
        if http_operation == "prepare_action":
            return self.prepare(ctx, receipt, key, body)
        if http_operation == "submit_decision":
            return self.decide(ctx, receipt, key, body)
        return self.review(ctx, receipt, key, body, path["action_id"])

    def workflow_context(self, ctx, conversation: str, action_id: str | None, key: str, tolerate_absent: bool):
        try:
            return self.step(ctx, "get_workflow_context", {"conversation_id": conversation, "action_id": action_id,
                                                           "message_id": None}, conversation_id=conversation)["data"]
        except Terminal as exc:
            if tolerate_absent and exc.error["code"] == "ENTITY_NOT_FOUND":
                return {"active_action": None, "selected_action": None}
            raise

    @staticmethod
    def pending_shell(ctx, action_id, conversation, intent, state, *, candidate_id, draft, missing):
        now = iso(datetime.now(timezone.utc))
        return {"action_id": action_id, "user_id": ctx.user_id, "conversation_id": conversation, "version": 1,
                "intent": intent, "state": state, "requires_review": False, "candidate_id": candidate_id,
                "proposal_id": None, "draft_arguments": draft, "missing_fields": missing, "ambiguities": [],
                "depends_on_action_id": None, "created_at": now, "updated_at": now}

    # ------------------------------------------------------------ prepare (POST /v1/actions)
    def prepare(self, ctx, receipt, key, body):
        operation, arguments, conversation = body["operation"], body["arguments"], body["conversation_id"]
        slots = None
        if operation == "create_task_candidate":
            slots = self.normalize_slots(arguments["slots"])
            questions = self.questions(slots)
            if questions:
                return 200, reply(ctx.request_id, "NEEDS_CLARIFICATION", "Cần thêm thông tin để lưu công việc.", questions=questions)
        if self.workflow_context(ctx, conversation, None, key, True)["active_action"] is not None:
            raise Terminal("ACTION_REVIEW_REQUIRED", "Hãy xem lại hoặc hủy thao tác đang chờ trước khi tạo thao tác mới.")
        message_id = receipt["message_id"]
        self.step(ctx, "record_source_message", {"message": {
            "message_id": message_id, "user_id": ctx.user_id, "conversation_id": conversation, "source": "UI",
            "role": "USER", "text": FORM_TEXT[operation], "received_at": receipt["created_at"]}},
            conversation_id=conversation, idempotency_key=child_key(key, "message"), message_id=message_id)
        built = self.build_action(ctx, action_id=receipt["action_id"], message_id=message_id, key=key, tag="",
                                  conversation=conversation, operation=operation, arguments=arguments, slots=slots)
        if "report" in built:
            return 200, self.report_reply(ctx, built["report"])
        return 200, self.awaiting_reply(ctx, built["presentation"], built["target"])

    @staticmethod
    def normalize_slots(raw: dict) -> dict:
        slots = dict(raw)
        if slots.get("deadline_precision") == "DATE" and slots.get("deadline_at") is None:
            slots["deadline_at"] = deadline_instant(slots)
        return slots

    @staticmethod
    def report_reply(ctx, report: dict) -> dict:
        text = "Lịch hiện tại đã phù hợp, không có thay đổi." if report["coverage"] == "NO_CHANGE" \
            else "Chưa xếp được khối học nào trong khoảng thời gian này."
        return reply(ctx.request_id, "SUCCEEDED", text, result=_ok(ctx.request_id, "READ", report))

    def build_action(self, ctx, *, action_id, message_id, key, tag, conversation, operation, arguments, slots=None,
                     missing=None) -> dict:
        """Creates the draft/proposal and the server-issued presentation for one action.

        Returns {"presentation", "target"} or, when the engine has nothing to propose, {"report"}.
        `tag` keeps the database idempotency keys of several actions from one request apart."""
        if operation == "generate_study_plan":
            return self.build_plan(ctx, action_id, message_id, key, tag, conversation, arguments)
        if operation == "create_task_candidate":
            candidate = self.step(ctx, "create_task_candidate", {"slots": slots}, conversation_id=conversation,
                                  idempotency_key=child_key(key, f"candidate{tag}"), message_id=message_id)["data"]
            pending = self.pending_shell(ctx, action_id, conversation, "CREATE_TASK",
                                         "AWAITING_CLARIFICATION" if missing else "AWAITING_CONFIRMATION",
                                         candidate_id=candidate["candidate_id"], draft={"slots": slots}, missing=missing or [])
            command = None if missing else {"schema_version": "1.1", "operation": "confirm_task", "arguments": {
                "candidate_id": candidate["candidate_id"], "expected_candidate_version": candidate["version"]}}
            presentation = {"kind": "ACTION_PRESENTATION", "pending_action": pending, "candidate": candidate,
                            "proposal": None, "normalized_command": command, "effective_policy": None}
            target = ("TASK_CANDIDATE", candidate["candidate_id"], candidate["version"])
        else:
            command = {"schema_version": "1.1", "operation": operation, "arguments": arguments}
            policy = self.effective_policy(ctx, arguments) if operation == "set_scheduling_preferences" else None
            pending = self.pending_shell(ctx, action_id, conversation, INTENT[operation], "AWAITING_APPROVAL",
                                         candidate_id=None, draft=arguments, missing=[])
            presentation = {"kind": "ACTION_PRESENTATION", "pending_action": pending, "candidate": None, "proposal": None,
                            "normalized_command": command, "effective_policy": policy}
            target = ("PENDING_ACTION", action_id, 1)
        stored = self.step(ctx, "prepare_pending_action", {"presentation": presentation, "expected_action_version": None},
                           conversation_id=conversation, idempotency_key=child_key(key, f"prepare{tag}"),
                           message_id=message_id)["data"]
        return {"presentation": stored, "target": target}

    def build_plan(self, ctx, action_id, message_id, key, tag, conversation, arguments) -> dict:
        """Engine -> persisted proposal -> pending action. Nothing becomes the current plan until approved."""
        self.step(ctx, "ensure_user_context", {})
        snapshot = self.step(ctx, "get_scheduling_context", {"generation_scope": arguments["generation_scope"]},
                             conversation_id=conversation)["data"]
        try:
            generated = generate(snapshot, arguments, now=self.api.clock())
        except ValueError as exc:  # malformed window data in the snapshot
            raise Terminal("INVALID_PARAMETER", f"Dữ liệu giờ rảnh/bận không hợp lệ: {exc}") from None
        if generated.conflicts:
            first = generated.conflicts[0]
            code = "ACTIVE_BLOCK_REQUIRES_REVIEW" if first.code == "ACTIVE_BLOCK_REQUIRES_REVIEW" else "INVALID_PARAMETER"
            raise Terminal(code, first.message)
        if generated.report is not None:
            return {"report": generated.report}
        proposal = self.step(ctx, "persist_plan_proposal", {"command_arguments": arguments, "proposal": generated.proposal},
                             conversation_id=conversation, idempotency_key=child_key(key, f"generate{tag}"),
                             message_id=message_id)["data"]
        pending = self.pending_shell(ctx, action_id, conversation, "GENERATE_STUDY_PLAN", "AWAITING_APPROVAL",
                                     candidate_id=None, draft=arguments, missing=[])
        pending["proposal_id"] = proposal["proposal_id"]
        command = {"schema_version": "1.1", "operation": "approve_study_plan", "arguments": {
            "proposal_id": proposal["proposal_id"], "expected_proposal_version": proposal["version"],
            "expected_plan_version": proposal["base_plan_version"]}}
        presentation = {"kind": "ACTION_PRESENTATION", "pending_action": pending, "candidate": None, "proposal": proposal,
                        "normalized_command": command, "effective_policy": proposal["policy_snapshot"]}
        stored = self.step(ctx, "prepare_pending_action", {"presentation": presentation, "expected_action_version": None},
                           conversation_id=conversation, idempotency_key=child_key(key, f"prepare{tag}"),
                           message_id=message_id)["data"]
        return {"presentation": stored, "target": ("PLAN_PROPOSAL", proposal["proposal_id"], proposal["version"])}

    @staticmethod
    def awaiting_reply(ctx, presentation: dict, target: tuple) -> dict:
        action = presentation["pending_action"]
        reference = {"action_id": action["action_id"], "action_version": action["version"], "target_type": target[0],
                     "target_id": target[1], "target_version": target[2]}
        return reply(ctx.request_id, "AWAITING_APPROVAL", "Xem nội dung và xác nhận thao tác.", reference=reference,
                     result=_ok(ctx.request_id, "DRAFTED", presentation))

    @staticmethod
    def questions(slots: dict) -> list[dict]:
        ask = []
        if not (slots.get("title") or "").strip():
            ask.append(("title", "Tên công việc là gì?"))
        if slots.get("deadline_precision") not in ("DATE", "DATETIME") or slots.get("deadline_at") is None \
                or (slots["deadline_precision"] == "DATE" and slots.get("deadline_date") is None):
            ask.append(("deadline_at", "Hạn nộp là khi nào?"))
        if not slots.get("deadline_timezone"):
            ask.append(("deadline_timezone", "Hạn nộp tính theo múi giờ nào?"))
        if slots.get("estimated_minutes") is None:
            ask.append(("estimated_minutes", "Bạn dự kiến cần bao nhiêu phút?"))
        return [{"field": field, "message": message, "choices": []} for field, message in ask]

    def effective_policy(self, ctx, arguments: dict) -> dict:
        profile = self.step(ctx, "ensure_user_context", {})["data"]
        return {**POLICY_DEFAULT, **profile["scheduling_policy"], **arguments["policy_patch"]}

    # ------------------------------------------------------------ review (POST /v1/actions/{id}/review)
    def review(self, ctx, receipt, key, body, action_id):
        conversation = body["conversation_id"]
        data = self.workflow_context(ctx, conversation, action_id, key, False)
        action = data["selected_action"]
        pending = action["pending_action"]
        if pending["state"] not in AWAITING:
            raise Terminal("STALE_ENTITY_VERSION", "Thao tác này đã kết thúc.")
        last = (action["last_presentation"] or {}).get("presentation") or {}
        presentation = {"kind": "ACTION_PRESENTATION", "pending_action": pending, "candidate": action["candidate"],
                        "proposal": action["proposal"], "normalized_command": last.get("normalized_command"),
                        "effective_policy": last.get("effective_policy")}
        stored = self.step(ctx, "review_pending_action", {
            "action_id": action_id, "expected_action_version": body["expected_action_version"], "presentation": presentation},
            conversation_id=conversation, idempotency_key=child_key(key, "review"), message_id=receipt["message_id"])["data"]
        new = stored["pending_action"]
        if stored["candidate"] is not None:
            target = ("TASK_CANDIDATE", stored["candidate"]["candidate_id"], stored["candidate"]["version"])
        elif stored["proposal"] is not None:
            target = ("PLAN_PROPOSAL", stored["proposal"]["proposal_id"], stored["proposal"]["version"])
        else:
            target = ("PENDING_ACTION", new["action_id"], new["version"])
        return 200, self.awaiting_reply(ctx, stored, target)

    # ------------------------------------------------------------ decide (POST /v1/decisions)
    def decide(self, ctx, receipt, key, body):
        conversation, ref, decision = body["conversation_id"], body["action_reference"], body["decision"]
        data = self.workflow_context(ctx, conversation, ref["action_id"], key, False)
        action = data["selected_action"]
        pending = action["pending_action"]
        # A finished action is passed on as is: the database replays the same decision for the same key and
        # refuses any other key, which is what makes a retry after a crash safe.
        if pending["state"] in AWAITING:
            if pending["requires_review"]:
                raise Terminal("ACTION_REVIEW_REQUIRED", "Hãy xem lại thao tác hiện tại trước khi quyết định.")
            if pending["version"] != ref["action_version"]:
                raise Terminal("STALE_ENTITY_VERSION", "Thao tác đã thay đổi; hãy tải lại trước khi quyết định.")
        last = (action["last_presentation"] or {}).get("presentation") or {}
        command = last.get("normalized_command")
        if decision == "REJECT":
            return self.reject(ctx, receipt, key, conversation, ref, action, command)
        if command is None:
            raise Terminal("INVALID_PARAMETER", "Thao tác này chưa có nội dung để xác nhận.")
        operation = command["operation"]
        approval = {"approval_action_id": str(uuid4()), "user_id": ctx.user_id, "target_type": ref["target_type"],
                    "target_id": ref["target_id"], "target_version": ref["target_version"], "decision": "APPROVE",
                    "source": "UI", "source_message_id": None, "created_at": iso(datetime.now(timezone.utc))}
        result = self.step(ctx, operation, command["arguments"], conversation_id=conversation,
                           idempotency_key=child_key(key, "decision"), approval_action=approval,
                           action_reference=ref, message_id=receipt["message_id"])
        result = {**result, "request_id": ctx.request_id}
        resumed = self.chat.resume(ctx, receipt, key, conversation, ref, operation, result, False)
        if resumed is not None:
            return 200, resumed
        return 200, reply(ctx.request_id, "SUCCEEDED", DONE_TEXT.get(operation, "Đã hoàn tất."), result=result)

    def reject(self, ctx, receipt, key, conversation, ref, action, command):
        if ref["target_type"] == "PLAN_PROPOSAL":
            approval = {"approval_action_id": str(uuid4()), "user_id": ctx.user_id, "target_type": "PLAN_PROPOSAL",
                        "target_id": ref["target_id"], "target_version": ref["target_version"], "decision": "REJECT",
                        "source": "UI", "source_message_id": None, "created_at": iso(datetime.now(timezone.utc))}
            result = self.step(ctx, "reject_study_plan", {"proposal_id": ref["target_id"],
                                                          "expected_proposal_version": ref["target_version"]},
                               conversation_id=conversation, idempotency_key=child_key(key, "decision"),
                               approval_action=approval, action_reference=ref, message_id=receipt["message_id"])
            done = reply(ctx.request_id, "SUCCEEDED", DONE_TEXT["reject_study_plan"],
                         result={**result, "request_id": ctx.request_id})
            return 200, self.chat.resume(ctx, receipt, key, conversation, ref, None, None, True, done) or done
        candidate_id = ref["target_id"] if ref["target_type"] == "TASK_CANDIDATE" else None
        cancelled = self.step(ctx, "cancel_pending_action", {"action_reference": ref, "candidate_id": candidate_id},
                              conversation_id=conversation, idempotency_key=child_key(key, "cancel"),
                              message_id=receipt["message_id"])["data"]
        # The contract has no "cancelled" tool result, so the cancelled action is shown as its own presentation.
        presentation = {"kind": "ACTION_PRESENTATION", "pending_action": cancelled, "candidate": None, "proposal": None,
                        "normalized_command": None, "effective_policy": None}
        done = reply(ctx.request_id, "SUCCEEDED", "Đã hủy thao tác. Không có dữ liệu nào được lưu.",
                     result=_ok(ctx.request_id, "DRAFTED", presentation))
        return 200, self.chat.resume(ctx, receipt, key, conversation, ref, None, None, True, done) or done
