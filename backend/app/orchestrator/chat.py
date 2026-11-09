"""POST /v1/messages: văn bản tự do -> trích xuất chưa đáng tin cậy -> workflow có thứ tự, được lưu bền vững.

Kết quả trích xuất đầu tiên được lưu bằng initialize_workflow_continuation và không tính lại; các yêu cầu sau đó
(gửi lại, bổ sung thông tin, quyết định) đều dùng hàng đợi đã lưu. Chat chỉ chuẩn bị thao tác ghi:
việc phê duyệt luôn đi qua /v1/decisions với tham chiếu thao tác do server cấp.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from ..clients.rpc import child_key, iso
from ..core import contract
from ..nlu.extractor import ExtractionError, ExtractorUnavailable
from .workflow_ports import ChatActions, Clock, WorkflowError
from ..nlu.extractor import Extractor
from .workflow_shared import AWAITING, DONE_TEXT, INTENT, Terminal, _ok, reply

WRITE_INTENTS = {"CREATE_TASK", "SET_AVAILABILITY", "SET_BUSY_INTERVAL", "SET_SCHEDULING_PREFERENCES", "GENERATE_STUDY_PLAN"}
APPROVAL_OPERATIONS = {"confirm_task", "set_availability", "set_busy_interval", "set_scheduling_preferences",
                       "approve_study_plan", "reject_study_plan"}
GENERIC_QUESTION = {"field": "intent", "message": "Bạn muốn thêm công việc, tìm công việc, đặt giờ rảnh/bận hay lập kế hoạch?",
                    "choices": []}


def action_id_for(source_message_id: str, index: int) -> str:
    """Ổn định theo (tin nhắn, ý định): lần gửi lại suy ra cùng ID thay vì tạo ID khác."""
    return str(uuid.uuid5(uuid.UUID(source_message_id), f"action-{index}"))


def step_key(origin_key: str, source_message_id: str, index: int) -> str:
    return contract.sha256_hex({"api_key": origin_key, "source_message_id": source_message_id, "intent_index": index})


class ChatProcessor:
    def __init__(self, processor: ChatActions, extractor: Extractor, *, clock: Clock, timezone: str):
        self.proc, self.extractor = processor, extractor
        self.clock, self.timezone = clock, timezone

    # ------------------------------------------------------------ đầu vào: POST /v1/messages
    def handle_message(self, ctx, receipt, key, body):
        conversation, text, message_id = body["conversation_id"], body["text"], receipt["message_id"]
        self.proc.step(ctx, "record_source_message", {"message": {
            "message_id": message_id, "user_id": ctx.user_id, "conversation_id": conversation, "source": "CHAT",
            "role": "USER", "text": text, "received_at": receipt["created_at"]}},
            conversation_id=conversation, idempotency_key=child_key(key, "message"), message_id=message_id)
        own = self.continuation(ctx, conversation, message_id)
        if own is None:
            open_queue = self.continuation(ctx, conversation, None)
            if open_queue is not None:
                return self.answer_open_queue(ctx, receipt, key, conversation, text, open_queue)
            extraction = self.extract(ctx, conversation, text, None)
            if all(i["intent"] in ("UNKNOWN", "UNSUPPORTED") for i in extraction["intents"]):
                return 200, reply(ctx.request_id, "NEEDS_CLARIFICATION", "Mình chưa hiểu bạn muốn làm gì.", questions=[GENERIC_QUESTION])
            own = self.initialize(ctx, receipt, key, conversation, message_id, extraction)
        return 200, self.advance(ctx, receipt, key, own)

    def continuation(self, ctx, conversation: str, source_message_id: str | None):
        return self.proc.step(ctx, "get_workflow_continuation", {"conversation_id": conversation,
                                                                  "source_message_id": source_message_id},
                              conversation_id=conversation)["data"]["continuation"]

    def extract(self, ctx, conversation, text, active):
        try:
            result = self.extractor.extract(text, now=self.clock(), timezone=self.timezone, active=active)
        except ExtractorUnavailable:
            raise WorkflowError("SERVICE_UNAVAILABLE", "Dịch vụ hiểu ngôn ngữ chưa sẵn sàng.", retryable=True, retry_after=5) from None
        except ExtractionError:
            raise WorkflowError("SERVICE_UNAVAILABLE", "Chưa đọc được kết quả phân tích, hãy thử lại.", retryable=True, retry_after=2) from None
        if not contract.is_valid("ExtractionResult", result):
            raise WorkflowError("SERVICE_UNAVAILABLE", "Chưa đọc được kết quả phân tích, hãy thử lại.", retryable=True, retry_after=2)
        return result

    @staticmethod
    def dependencies(extraction: dict) -> list[list[int]]:
        """Yêu cầu lập lịch chờ mọi thao tác ghi đứng trước; các ý định còn lại độc lập."""
        depends, writes = [], []
        for index, item in enumerate(extraction["intents"]):
            depends.append(list(writes) if item["intent"] == "GENERATE_STUDY_PLAN" else [])
            if item["intent"] in WRITE_INTENTS:
                writes.append(index)
        return depends

    def initialize(self, ctx, receipt, key, conversation, message_id, extraction):
        return self.proc.step(ctx, "initialize_workflow_continuation", {
            "conversation_id": conversation, "source_message_id": message_id, "extraction": extraction,
            "depends_on": self.dependencies(extraction), "receipt_binding": self.binding(receipt, "send_message", key)},
            conversation_id=conversation, idempotency_key=child_key(key, "init"), message_id=message_id)["data"]

    @staticmethod
    def binding(receipt, http_operation, key):
        return {"http_operation": http_operation, "idempotency_key": key,
                "request_fingerprint": receipt["request_fingerprint"], "expected_lease_version": receipt["lease_version"]}

    # ------------------------------------------------------------ vòng lặp xử lý hàng đợi
    def advance(self, ctx, receipt, key, cont, http_operation="send_message", fallback=None):
        binding = self.binding(receipt, http_operation, key)
        conversation = cont["conversation_id"]
        total = len(cont["extraction"]["intents"])
        while cont["cursor"] < total and cont["awaiting_reference"] is None:
            index = cont["cursor"]
            outcome, wait = self.run_step(ctx, key, cont, index)
            if wait is not None:
                cont = self.checkpoint(ctx, key, cont, binding, "WAIT", reference=wait)
            else:
                cont = self.checkpoint(ctx, key, cont, binding, "ADVANCE", outcome=outcome)
        return self.compose(ctx, cont, conversation, fallback)

    def checkpoint(self, ctx, key, cont, binding, transition, *, reference=None, outcome=None):
        if outcome is not None and not contract.is_valid("WorkflowStepOutcome", outcome):
            outcome = self.outcome(cont, cont["cursor"], None, "FAILED",
                                   error=self.error("INTERNAL_ERROR", "Không ghi nhận được kết quả của bước này."))
        return self.proc.step(ctx, "checkpoint_workflow_continuation", {
            "conversation_id": cont["conversation_id"], "source_message_id": cont["source_message_id"],
            "expected_version": cont["version"], "expected_cursor": cont["cursor"], "transition": transition,
            "action_reference": reference, "outcome": outcome, "receipt_binding": binding},
            conversation_id=cont["conversation_id"], idempotency_key=child_key(key, f"cp:{cont['cursor']}:{transition}:{cont['version']}"),
            message_id=cont["source_message_id"])["data"]

    @staticmethod
    def error(code, message):
        return {"code": code, "message": message, "field": None, "details": {}, "retryable": False}

    @staticmethod
    def outcome(cont, index, operation, disposition, *, result=None, error=None):
        return {"intent_index": index, "step_key": step_key(cont["origin_idempotency_key"], cont["source_message_id"], index),
                "operation": operation, "disposition": disposition, "result": result, "error": error}

    def run_step(self, ctx, key, cont, index):
        """Chạy ý định tại `index`. Trả (outcome, None) khi xong hoặc (None, reference) khi phải chờ."""
        done = cont["completed_steps"]
        if any(done[d]["disposition"] != "SUCCEEDED" for d in cont["depends_on"][index]):
            return self.outcome(cont, index, None, "DEPENDENCY_CANCELLED"), None
        item = cont["extraction"]["intents"][index]
        conversation, message_id, kind = cont["conversation_id"], cont["source_message_id"], item["intent"]
        tag = f":{index}"
        try:
            if kind in ("UNKNOWN", "UNSUPPORTED"):
                return self.outcome(cont, index, None, "FAILED", error=self.error(
                    "UNSUPPORTED_OPERATION", "Mình chưa hỗ trợ yêu cầu này.")), None
            if kind == "SEARCH_TASKS":
                return self.read(ctx, cont, index, "search_tasks", self.search_args(item["slots"])), None
            if kind == "GET_STUDY_PLAN":
                return self.read(ctx, cont, index, "get_study_plan", self.plan_view_args(item["slots"])), None
            return self.write(ctx, key, cont, index, item, tag, conversation, message_id)
        except Terminal as exc:
            return self.outcome(cont, index, None, "FAILED", error=exc.error), None

    def read(self, ctx, cont, index, operation, arguments):
        if arguments is None:
            return self.outcome(cont, index, operation, "FAILED", error=self.error(
                "INVALID_PARAMETER", "Mình chưa hiểu điều kiện tìm kiếm."))
        result = self.proc.step(ctx, operation, arguments, conversation_id=cont["conversation_id"],
                                message_id=cont["source_message_id"])
        return self.outcome(cont, index, operation, "SUCCEEDED", result={**result, "request_id": ctx.request_id})

    @staticmethod
    def search_args(slots):
        args = {"query": slots.get("query"), "status_filter": slots.get("status_filter") or [], "page_size": 50, "cursor": None}
        return args if contract.is_valid("search_tasksArguments", args) else None

    @staticmethod
    def plan_view_args(slots):
        args = {"view": "CURRENT", "version": None, "proposal_id": None,
                "start_at": slots.get("start_at"), "end_at": slots.get("end_at")}
        return args if contract.is_valid("get_study_planArguments", args) else None

    def write(self, ctx, key, cont, index, item, tag, conversation, message_id):
        """Chuẩn bị thao tác ghi cần phê duyệt. Trả (None, reference) vì bước này chờ người dùng."""
        slots, kind = item["slots"], item["intent"]
        active = self.proc.workflow_context(ctx, conversation, None, key, True)["active_action"]
        if active is not None and active["pending_action"]["action_id"] == action_id_for(message_id, index):
            return None, self.reference_for(active)  # đã được tạo ở lần thử trước của chính bước này
        if active is not None:
            return self.outcome(cont, index, None, "FAILED", error=self.error(
                "ACTION_REVIEW_REQUIRED", "Đang có một thao tác chờ xác nhận; hãy xác nhận hoặc hủy trước.")), None
        action_id = action_id_for(message_id, index)
        if kind == "CREATE_TASK":
            fields = self.proc.normalize_slots(slots)
            if not contract.is_valid("CandidateTaskFields", fields):
                return self.outcome(cont, index, None, "FAILED", error=self.error(
                    "INVALID_PARAMETER", "Mình chưa hiểu thông tin công việc.")), None
            missing = [q["field"] for q in self.proc.questions(fields)]
            built = self.proc.build_action(ctx, action_id=action_id, message_id=message_id, key=key, tag=tag,
                                           conversation=conversation, operation="create_task_candidate",
                                           arguments={"slots": fields}, slots=fields, missing=missing)
        else:
            operation, arguments = self.operation_for(ctx, kind, slots)
            if arguments is None:
                return self.outcome(cont, index, None, "FAILED", error=self.error(
                    "INVALID_PARAMETER", "Mình chưa hiểu yêu cầu này, bạn thử dùng biểu mẫu nhé.")), None
            built = self.proc.build_action(ctx, action_id=action_id, message_id=message_id, key=key, tag=tag,
                                           conversation=conversation, operation=operation, arguments=arguments)
            if "report" in built:
                return self.outcome(cont, index, operation, "SUCCEEDED",
                                    result=_ok(ctx.request_id, "READ", built["report"])), None
        stored, target = built["presentation"], built["target"]
        action = stored["pending_action"]
        return None, {"action_id": action["action_id"], "action_version": action["version"], "target_type": target[0],
                      "target_id": target[1], "target_version": target[2]}

    @staticmethod
    def reference_for(action_context):
        pending = action_context["pending_action"]
        if action_context["candidate"] is not None:
            target = ("TASK_CANDIDATE", action_context["candidate"]["candidate_id"], action_context["candidate"]["version"])
        elif action_context["proposal"] is not None:
            target = ("PLAN_PROPOSAL", action_context["proposal"]["proposal_id"], action_context["proposal"]["version"])
        else:
            target = ("PENDING_ACTION", pending["action_id"], pending["version"])
        return {"action_id": pending["action_id"], "action_version": pending["version"], "target_type": target[0],
                "target_id": target[1], "target_version": target[2]}

    def operation_for(self, ctx, kind, slots):
        if kind in ("SET_AVAILABILITY", "SET_BUSY_INTERVAL"):
            operation = INTENT_TO_OPERATION[kind]
            arguments = {"change_type": slots.get("change_type", "ADD"), "window_id": None,
                         "expected_window_version": None, "window": slots.get("window")}
            return operation, arguments if arguments["change_type"] == "ADD" and contract.is_valid(f"{operation}Arguments", arguments) else None
        if kind == "SET_SCHEDULING_PREFERENCES":
            profile = self.proc.step(ctx, "ensure_user_context", {})["data"]
            arguments = {"policy_patch": slots.get("policy_patch"), "expected_schedule_revision": profile["schedule_revision"]}
            return "set_scheduling_preferences", arguments if contract.is_valid("set_scheduling_preferencesArguments", arguments) else None
        now = self.clock().replace(second=0, microsecond=0) + timedelta(minutes=1)
        scope = {"start_at": slots.get("start_at") or iso(now).replace(".000000", ""),
                 "end_at": slots.get("end_at") or iso(now + timedelta(days=7)).replace(".000000", ""),
                 "selection_mode": "ALL_ELIGIBLE", "task_ids": []}
        arguments = {"generation_scope": scope, "policy_overrides": {}}
        return "generate_study_plan", arguments if contract.is_valid("generate_study_planArguments", arguments) else None

    # ------------------------------------------------------------ hội thoại đã có hàng đợi chưa hoàn tất
    def answer_open_queue(self, ctx, receipt, key, conversation, text, queue):
        """Có tin nhắn mới khi tin trước vẫn đang chờ: chỉ nhận câu trả lời bổ sung thông tin."""
        reference = queue["awaiting_reference"]
        action = None
        if reference is not None:
            action = self.proc.workflow_context(ctx, conversation, reference["action_id"], key, False)["selected_action"]
        if action is not None and action["pending_action"]["state"] not in AWAITING:
            stale = self.outcome(queue, queue["cursor"], None, "FAILED",
                                 error=self.error("STALE_ENTITY_VERSION", "Thao tác trước đó không còn hiệu lực."))
            healed = self.checkpoint(ctx, key, queue, self.binding(receipt, "send_message", key), "ADVANCE", outcome=stale)
            return 200, self.advance(ctx, receipt, key, healed)
        if action is None or action["pending_action"]["state"] != "AWAITING_CLARIFICATION" or action["candidate"] is None:
            raise Terminal("ACTION_REVIEW_REQUIRED", "Bạn đang có một thao tác chờ xác nhận. Hãy xác nhận hoặc hủy trước khi gửi yêu cầu khác.")
        candidate, pending = action["candidate"], action["pending_action"]
        active = {"intent": "CREATE_TASK", "slots": candidate["slots"], "missing_fields": pending["missing_fields"]}
        extraction = self.extract(ctx, conversation, text, active)
        given = next((i for i in extraction["intents"] if i["intent"] == "CREATE_TASK"), None)
        if given is None:
            raise Terminal("ACTION_REVIEW_REQUIRED", "Bạn đang bổ sung thông tin cho một công việc; hãy trả lời câu hỏi hoặc hủy trước.")
        message_id = receipt["message_id"]
        patch = {k: v for k, v in given["slots"].items() if v is not None}
        merged = self.proc.normalize_slots({**candidate["slots"], **patch})
        if not contract.is_valid("CandidateTaskFields", merged):
            raise Terminal("INVALID_PARAMETER", "Mình chưa hiểu thông tin vừa nhập.")
        sources = {**{k: {"source": "USER_MESSAGE", "reference": message_id} for k in patch}}
        updated = self.proc.step(ctx, "update_candidate_draft", {
            "candidate_id": candidate["candidate_id"], "expected_candidate_version": candidate["version"], "slots": merged,
            "raw_expressions": given["raw_expressions"], "field_sources": {**candidate["field_sources"], **sources}},
            conversation_id=conversation, idempotency_key=child_key(key, "update"), message_id=message_id)["data"]
        missing = [q["field"] for q in self.proc.questions(merged)]
        new_pending = {**pending, "state": "AWAITING_CLARIFICATION" if missing else "AWAITING_CONFIRMATION",
                       "draft_arguments": {"slots": merged}, "missing_fields": missing}
        command = None if missing else {"schema_version": "1.1", "operation": "confirm_task", "arguments": {
            "candidate_id": updated["candidate_id"], "expected_candidate_version": updated["version"]}}
        presentation = {"kind": "ACTION_PRESENTATION", "pending_action": new_pending, "candidate": updated, "proposal": None,
                        "normalized_command": command, "effective_policy": None}
        stored = self.proc.step(ctx, "prepare_pending_action", {"presentation": presentation, "expected_action_version": pending["version"]},
                                conversation_id=conversation, idempotency_key=child_key(key, "reprepare"),
                                message_id=message_id)["data"]
        if missing:
            return 200, reply(ctx.request_id, "NEEDS_CLARIFICATION", "Mình cần thêm thông tin.", questions=self.proc.questions(merged))
        return 200, self.proc.awaiting_reply(ctx, stored, ("TASK_CANDIDATE", updated["candidate_id"], updated["version"]))

    # ------------------------------------------------------------ tiếp tục sau quyết định
    def resume(self, ctx, receipt, key, conversation, reference, operation, result, rejected, cancelled_reply=None):
        """Được gọi sau khi /v1/decisions xử lý xong thao tác đang chờ. Trả phản hồi tổng hợp, hoặc None nếu
        thao tác đó không thuộc hàng đợi tin nhắn (ví dụ: được tạo từ biểu mẫu)."""
        queue = self.continuation(ctx, conversation, None)
        if queue is None or queue["awaiting_reference"] is None or queue["awaiting_reference"]["action_id"] != reference["action_id"]:
            return None
        index = queue["cursor"]
        if rejected:
            outcome = self.outcome(queue, index, None, "REJECTED")
        else:
            outcome = self.outcome(queue, index, operation, "SUCCEEDED", result={**result, "request_id": ctx.request_id})
        queue = self.checkpoint(ctx, key, queue, self.binding(receipt, "submit_decision", key), "ADVANCE", outcome=outcome)
        # Các bước sau dùng ID tin nhắn gốc của hàng đợi; chỉ receipt và khóa con lấy từ yêu cầu này.
        return self.advance(ctx, receipt, key, queue, "submit_decision", fallback=cancelled_reply)

    # ------------------------------------------------------------ ghép phản hồi từ trạng thái đã lưu
    def compose(self, ctx, cont, conversation, fallback=None):
        lines, last_ok = [], None
        for step in cont["completed_steps"]:
            line, result = self.describe(step)
            lines.append(line)
            if result is not None:
                last_ok = result
        reference = cont["awaiting_reference"]
        if reference is not None:
            action = self.proc.workflow_context(ctx, conversation, reference["action_id"], "", False)["selected_action"]
            stored = (action["last_presentation"] or {})["presentation"]
            pending = action["pending_action"]
            if pending["state"] == "AWAITING_CLARIFICATION":
                return reply(ctx.request_id, "NEEDS_CLARIFICATION", " ".join(lines + ["Mình cần thêm thông tin."]),
                             questions=self.proc.questions(action["candidate"]["slots"]))
            target = (reference["target_type"], reference["target_id"], reference["target_version"])
            built = self.proc.awaiting_reply(ctx, stored, target)
            built["message"] = " ".join(lines + [built["message"]])
            return built
        if last_ok is not None:
            return reply(ctx.request_id, "SUCCEEDED", " ".join(lines), result={**last_ok, "request_id": ctx.request_id})
        errors = [s["error"] for s in cont["completed_steps"] if s["error"]]
        if fallback is not None and not errors:
            return fallback
        if errors:
            raise Terminal(errors[0]["code"], errors[0]["message"], errors[0].get("field"))
        raise Terminal("STALE_ENTITY_VERSION", "Thao tác đã được hủy.")

    @staticmethod
    def describe(step):
        disposition, operation, result = step["disposition"], step["operation"], step["result"]
        if disposition == "SUCCEEDED":
            if operation == "search_tasks":
                return f"Tìm thấy {len(result['data']['items'])} công việc.", result
            if operation == "get_study_plan":
                return ("Đây là kế hoạch hiện tại." if result["data"].get("plan") else "Bạn chưa có kế hoạch."), result
            if operation == "generate_study_plan":
                return "Chưa có thay đổi nào cho lịch.", result
            return DONE_TEXT.get(operation, "Đã hoàn tất."), result
        if disposition == "REJECTED":
            return "Đã hủy thao tác.", None
        if disposition == "FAILED":
            return step["error"]["message"], None
        return "Bỏ qua một bước vì bước trước chưa hoàn tất.", None


INTENT_TO_OPERATION = {"SET_AVAILABILITY": "set_availability", "SET_BUSY_INTERVAL": "set_busy_interval"}
_ = (APPROVAL_OPERATIONS, INTENT)
