"""Chuẩn bị, xem lại và xử lý quyết định cho action F1."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from ..clients.rpc import child_key, iso
from ..f1.planning.generate import generate
from ..nlu.extractor import Extractor
from .chat import ChatProcessor
from .workflow_ports import Clock, RpcCall, WorkflowError
from .workflow_shared import (
    AWAITING, DONE_TEXT, FORM_TEXT, INTENT, POLICY_DEFAULT, PRODUCT_TIMEZONE,
    Terminal, _ok, deadline_instant, end_instant_from_start, reply,
)


class ActionProcessor:
    def __init__(self, rpc: RpcCall, clock: Clock, extractor: Extractor, timezone: str = PRODUCT_TIMEZONE):
        if timezone != PRODUCT_TIMEZONE:
            raise ValueError(f"timezone must be {PRODUCT_TIMEZONE}")
        self.rpc, self.clock = rpc, clock
        self.chat = ChatProcessor(self, extractor, clock=clock, timezone=timezone)

    def step(self, ctx, operation: str, arguments: dict, **kwargs) -> dict:
        """Một bước database. Lỗi nghiệp vụ chuyển thành Terminal; lỗi tạm thời truyền lên để thử lại."""
        result = self.rpc(ctx, operation, arguments, **kwargs)
        if result.get("outcome") == "ERROR":
            error = result["error"]
            if error["code"] in ("SERVICE_UNAVAILABLE", "INTERNAL_ERROR", "UNAUTHENTICATED"):
                raise WorkflowError(error["code"], error["message"], retryable=True, retry_after=1)
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
        slots.pop("course_label", None)
        if type(slots.get("priority")) is float and slots["priority"] == 1.0:
            slots["priority"] = 1
        if slots.get("deadline_timezone") is None:
            slots["deadline_timezone"] = PRODUCT_TIMEZONE
        if slots.get("deadline_precision") is None and slots.get("deadline_date") is not None:
            slots["deadline_precision"] = "DATE"
        if slots.get("deadline_precision") == "DATE" and slots.get("deadline_at") is None:
            slots["deadline_at"] = deadline_instant(slots)
        if slots.get("start_at") is not None:
            if slots.get("available_from_at") is None:
                slots["available_from_at"] = slots["start_at"]
            if slots.get("deadline_precision") is None:
                slots["deadline_precision"] = "DATETIME"
            if (
                slots.get("deadline_precision") == "DATETIME"
                and slots.get("deadline_at") is None
                and slots.get("estimated_minutes") is not None
            ):
                slots["deadline_at"] = end_instant_from_start(slots["start_at"], slots["estimated_minutes"])
        elif slots.get("available_from_at") is not None:
            slots["start_at"] = slots["available_from_at"]
        return slots

    @staticmethod
    def report_reply(ctx, report: dict) -> dict:
        text = "Lịch hiện tại đã phù hợp, không có thay đổi." if report["coverage"] == "NO_CHANGE" \
            else "Chưa xếp được khối học nào trong khoảng thời gian này."
        return reply(ctx.request_id, "SUCCEEDED", text, result=_ok(ctx.request_id, "READ", report))

    def build_action(self, ctx, *, action_id, message_id, key, tag, conversation, operation, arguments, slots=None,
                     missing=None) -> dict:
        """Tạo bản nháp/đề xuất và nội dung hiển thị để duyệt do server cấp cho một thao tác.

        Trả {"presentation", "target"}, hoặc {"report"} khi engine không có thay đổi để đề xuất.
        `tag` phân biệt khóa chống ghi trùng của nhiều thao tác trong cùng một yêu cầu."""
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
        """Engine -> lưu đề xuất -> thao tác chờ duyệt. Chỉ trở thành lịch hiện hành sau khi được duyệt."""
        self.step(ctx, "ensure_user_context", {})
        snapshot = self.step(ctx, "get_scheduling_context", {"generation_scope": arguments["generation_scope"]},
                             conversation_id=conversation)["data"]
        try:
            generated = generate(snapshot, arguments, now=self.clock())
        except ValueError as exc:  # dữ liệu khung giờ trong snapshot không hợp lệ
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
        has_start = bool(slots.get("start_at"))
        has_deadline = (
            slots.get("deadline_precision") in ("DATE", "DATETIME")
            and slots.get("deadline_at") is not None
            and (slots["deadline_precision"] != "DATE" or slots.get("deadline_date") is not None)
        )
        if not has_start and not has_deadline:
            field = "deadline_at" if slots.get("deadline_precision") in ("DATE", "DATETIME") else "start_at"
            message = "Hạn nộp là khi nào?" if field == "deadline_at" else "Thời gian bắt đầu là khi nào?"
            ask.append((field, message))
        if slots.get("estimated_minutes") is None:
            ask.append(("estimated_minutes", "Bạn dự kiến cần bao nhiêu phút?"))
        return [{"field": field, "message": message, "choices": []} for field, message in ask]

    def effective_policy(self, ctx, arguments: dict) -> dict:
        profile = self.step(ctx, "ensure_user_context", {})["data"]
        return {**POLICY_DEFAULT, **profile["scheduling_policy"], **arguments["policy_patch"]}

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

    def decide(self, ctx, receipt, key, body):
        conversation, ref, decision = body["conversation_id"], body["action_reference"], body["decision"]
        data = self.workflow_context(ctx, conversation, ref["action_id"], key, False)
        action = data["selected_action"]
        pending = action["pending_action"]
        # Chuyển tiếp nguyên trạng thao tác đã xong: database phát lại quyết định khi dùng cùng khóa và
        # từ chối khóa khác, nhờ đó việc gửi lại sau sự cố không gây ghi trùng.
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
            try:
                result = self.step(ctx, "reject_study_plan", {"proposal_id": ref["target_id"],
                                                              "expected_proposal_version": ref["target_version"]},
                                   conversation_id=conversation, idempotency_key=child_key(key, "decision"),
                                   approval_action=approval, action_reference=ref, message_id=receipt["message_id"])
            except Terminal as exc:
                if exc.error["code"] != "STALE_PROPOSAL":
                    raise
                result = None  # Đề xuất đã stale: chỉ cần giải phóng thao tác đang chờ.
            if result is not None:
                done = reply(ctx.request_id, "SUCCEEDED", DONE_TEXT["reject_study_plan"],
                             result={**result, "request_id": ctx.request_id})
                return 200, self.chat.resume(ctx, receipt, key, conversation, ref, None, None, True, done) or done
        candidate_id = ref["target_id"] if ref["target_type"] == "TASK_CANDIDATE" else None
        cancelled = self.step(ctx, "cancel_pending_action", {"action_reference": ref, "candidate_id": candidate_id},
                              conversation_id=conversation, idempotency_key=child_key(key, "cancel"),
                              message_id=receipt["message_id"])["data"]
        # Contract không có tool result "cancelled", nên hiển thị thao tác đã hủy bằng presentation riêng.
        presentation = {"kind": "ACTION_PRESENTATION", "pending_action": cancelled, "candidate": None, "proposal": None,
                        "normalized_command": None, "effective_policy": None}
        done = reply(ctx.request_id, "SUCCEEDED", "Đã hủy thao tác. Không có dữ liệu nào được lưu.",
                     result=_ok(ctx.request_id, "DRAFTED", presentation))
        return 200, self.chat.resume(ctx, receipt, key, conversation, ref, None, None, True, done) or done
