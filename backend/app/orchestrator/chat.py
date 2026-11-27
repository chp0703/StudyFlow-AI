"""POST /v1/messages: văn bản tự do -> trích xuất chưa đáng tin cậy -> workflow có thứ tự, được lưu bền vững.

Kết quả trích xuất đầu tiên được lưu bằng initialize_workflow_continuation và không tính lại; các yêu cầu sau đó
(gửi lại, bổ sung thông tin, quyết định) đều dùng hàng đợi đã lưu. Chat chỉ chuẩn bị thao tác ghi:
việc phê duyệt luôn đi qua /v1/decisions với tham chiếu thao tác do server cấp.
"""

from __future__ import annotations

import uuid
import copy
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ..clients.rpc import child_key, iso
from ..core import contract
from ..nlu.extractor import ExtractionError, ExtractorUnavailable
from .workflow_ports import ChatActions, Clock, WorkflowError
from ..nlu.extractor import Extractor
from .workflow_shared import AWAITING, DONE_TEXT, INTENT, PRODUCT_TIMEZONE, Terminal, _ok, minute_instant, reply

WRITE_INTENTS = {"CREATE_TASK", "SET_BUSY_INTERVAL", "SET_SCHEDULING_PREFERENCES", "GENERATE_STUDY_PLAN",
                 "PROPOSE_REVISION"}
APPROVAL_OPERATIONS = {"confirm_task", "set_busy_interval", "set_scheduling_preferences",
                       "approve_study_plan", "reject_study_plan"}
DEFAULT_MATERIAL_TOPIC = "Tài liệu học tập"  # topic the database gives a material uploaded without a course label
GENERIC_QUESTION = {"field": "intent", "message": "Bạn muốn thêm công việc, tìm công việc, đặt giờ bận, lập kế hoạch, tạo câu hỏi ôn tập hay đề xuất ôn tập?",
                    "choices": []}


def action_id_for(source_message_id: str, index: int) -> str:
    """Ổn định theo (tin nhắn, ý định): lần gửi lại suy ra cùng ID thay vì tạo ID khác."""
    return str(uuid.uuid5(uuid.UUID(source_message_id), f"action-{index}"))


def step_key(origin_key: str, source_message_id: str, index: int) -> str:
    return contract.sha256_hex({"api_key": origin_key, "source_message_id": source_message_id, "intent_index": index})


class ChatProcessor:
    def __init__(self, processor: ChatActions, extractor: Extractor, *, clock: Clock, timezone: str = PRODUCT_TIMEZONE):
        if timezone != PRODUCT_TIMEZONE:
            raise ValueError(f"timezone must be {PRODUCT_TIMEZONE}")
        self.proc, self.extractor = processor, extractor
        self.clock, self.timezone = clock, timezone

    # ------------------------------------------------------------ đầu vào: POST /v1/messages
    def handle_message(self, ctx, receipt, key, body):
        conversation, text, message_id = body["conversation_id"], body.get("text", ""), receipt["message_id"]
        source_ids = body.get('source_ids', [])
        source_intents = self.source_intents(ctx, conversation, source_ids)
        self.proc.step(ctx, "record_source_message", {"message": {
            "message_id": message_id, "user_id": ctx.user_id, "conversation_id": conversation, "source": "CHAT",
            "role": "USER", "text": text, "received_at": receipt["created_at"]},
            **({'source_ids': source_ids} if source_ids else {})},
            conversation_id=conversation, idempotency_key=child_key(key, "message"), message_id=message_id)
        own = None if receipt.get("lease_version") == 1 else self.continuation(ctx, conversation, message_id)
        if own is None:
            open_queue = self.continuation(ctx, conversation, None)
            if open_queue is not None:
                if source_ids:
                    raise Terminal('ACTION_REVIEW_REQUIRED', 'Hãy xử lý thao tác đang chờ trước khi nhập nguồn mới.')
                return self.answer_open_queue(ctx, receipt, key, conversation, text, open_queue)
            extraction = {'intents': source_intents} if source_ids else self.with_revision_plan(self.extract(ctx, conversation, text, None))
            if source_ids and not extraction['intents']:
                return 200, reply(ctx.request_id, 'SUCCEEDED', 'Không tìm thấy công việc hoặc sự kiện trong nguồn đã gửi.')
            if source_ids and text.strip():
                # Only the user's separate text can request a plan, after source confirmations.
                direct = self.extract(ctx, conversation, text, None)
                plan = next((i for i in direct['intents'] if i['intent'] == 'GENERATE_STUDY_PLAN'), None)
                if plan is not None:
                    extraction['intents'].append(plan)
            if all(i["intent"] in ("UNKNOWN", "UNSUPPORTED") for i in extraction["intents"]):
                return 200, reply(ctx.request_id, "NEEDS_CLARIFICATION", "Mình chưa hiểu bạn muốn làm gì.", questions=[GENERIC_QUESTION])
            own = self.initialize(ctx, receipt, key, conversation, message_id, extraction)
        return 200, self.advance(ctx, receipt, key, own)

    @staticmethod
    def with_revision_plan(extraction: dict) -> dict:
        """Đề xuất ôn tập tạo task nháp; nếu người dùng chưa yêu cầu lập kế hoạch thì nối thêm một bước lập kế hoạch cuối hàng đợi."""
        intents = extraction["intents"]
        last = max((i for i, item in enumerate(intents) if item["intent"] == "PROPOSE_REVISION"), default=None)
        if last is None or any(item["intent"] == "GENERATE_STUDY_PLAN" for item in intents[last + 1:]):
            return extraction
        plan = {"intent": "GENERATE_STUDY_PLAN", "slots": {}, "raw_expressions": {}, "ambiguities": []}
        return {**extraction, "intents": [*intents, plan]}

    def source_intents(self, ctx, conversation, source_ids):
        intents = []
        for source_id in source_ids:
            source = self.proc.step(ctx, 'get_ingestion_source', {'source_id': source_id, 'conversation_id': conversation},
                                    conversation_id=conversation)['data']
            if (source.get('user_id') != ctx.user_id or source.get('conversation_id') != conversation
                    or source.get('status') != 'READY'):
                raise Terminal('ENTITY_NOT_FOUND', 'Không tìm thấy nguồn đã trích xuất trong cuộc hội thoại này.')
            extraction = source.get('extraction')
            if not contract.is_valid('SourceExtraction', extraction):
                raise Terminal('INVALID_PARAMETER', 'Nguồn chưa có dữ liệu trích xuất hợp lệ.')
            intents.extend(copy.deepcopy(extraction['intents']))
        if len(intents) > 20:
            raise Terminal('INVALID_PARAMETER', 'Một tin nhắn chỉ nhập tối đa 20 công việc hoặc sự kiện.')
        return intents

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
        for item in result.get("intents", []):
            slots = item.get("slots")
            if isinstance(slots, dict) and type(slots.get("priority")) is float and slots["priority"] == 1.0:
                slots["priority"] = 1
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
            if kind == "SUMMARIZE_LEARNING":
                return self.outcome(cont, index, None, "FAILED", error=self.error(
                    "UNSUPPORTED_OPERATION", "Tóm tắt phiên học hiện chưa dùng được trong chat; hãy dùng màn hình học.")), None
            if kind in ("CREATE_QUIZ", "PROPOSE_REVISION"):
                return self.write_learning(ctx, key, cont, index, item)
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
            self.proc.validate_task_slots(fields, now=self.proc.clock())
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

    def write_learning(self, ctx, key, cont, index, item):
        """CREATE_QUIZ / PROPOSE_REVISION: chọn tài liệu, gọi thao tác F2 có sẵn để tạo pending action chờ duyệt."""
        message_id, conversation = cont["source_message_id"], cont["conversation_id"]
        action_id = action_id_for(message_id, index)
        active = self.proc.workflow_context(ctx, conversation, None, key, True)["active_action"]
        if active is not None and active["pending_action"]["action_id"] == action_id:
            return None, self.reference_for(active)  # đã được tạo ở lần thử trước của chính bước này
        if active is not None:
            return self.outcome(cont, index, None, "FAILED", error=self.error(
                "ACTION_REVIEW_REQUIRED", "Đang có một thao tác chờ xác nhận; hãy xác nhận hoặc hủy trước.")), None
        slots = item["slots"]
        topic = slots.get("topic")
        if not isinstance(topic, str) or not topic.strip():
            return self.outcome(cont, index, None, "FAILED", error=self.error(
                "INVALID_PARAMETER", "Bạn muốn ôn chủ đề nào? Hãy nêu tên chủ đề.")), None
        material = self.pick_material(ctx, slots.get("material"))
        # F3 materials carry one topic (their course label, else the default); F2 only accepts topics of the material.
        body = {"schema_version": "1.1", "conversation_id": conversation, "material_id": material["material_id"],
                "topic": material.get("course_label") or DEFAULT_MATERIAL_TOPIC}
        receipt = {"action_id": action_id, "message_id": message_id}
        step_key = child_key(key, f"learning{index}")
        if item["intent"] == "CREATE_QUIZ":
            body |= {"question_type": slots.get("question_type") or "MCQ", "count": slots.get("count") or 5}
            if not contract.is_valid("GenerateQuestionDraftsRequest", body):
                return self.outcome(cont, index, None, "FAILED", error=self.error(
                    "INVALID_PARAMETER", "Mình chưa hiểu yêu cầu tạo câu hỏi (số câu 1-10, dạng MCQ hoặc TRUE_FALSE).")), None
            _, payload = self.proc.questions_ops.generate_drafts(ctx, receipt, step_key, body)
        else:
            priority = slots.get("priority", 0.5)
            body |= {"suggested_minutes": slots.get("suggested_minutes") or 30, "priority": 1 if priority == 1 else priority}
            if not contract.is_valid("CreateRevisionRecommendationRequest", body):
                return self.outcome(cont, index, None, "FAILED", error=self.error(
                    "INVALID_PARAMETER", "Mình chưa hiểu đề xuất ôn tập (15-240 phút, ưu tiên 0.1, 0.5 hoặc 1).")), None
            _, payload = self.proc.recommendations_ops.create(ctx, receipt, step_key, body, record_message=False)
        if payload.get("state") != "AWAITING_APPROVAL" or payload.get("action_reference") is None:
            return self.outcome(cont, index, None, "FAILED", error=self.error(
                "INVALID_PARAMETER", payload.get("message") or "Không tạo được thao tác chờ xác nhận.")), None
        return None, payload["action_reference"]

    def pick_material(self, ctx, name):
        """Một tài liệu học đã index: khớp theo tên nếu người dùng nêu, tự chọn khi chỉ có một."""
        data = self.proc.step(ctx, "list_learning_materials",
                              {"limit": 20, "before_created_at": None, "before_material_id": None})["data"]
        ready = [m for m in data["materials"] if m["status"] == "READY"]  # shortcut: first 20 materials only, paginate when users exceed it
        if isinstance(name, str) and name.strip():
            wanted = name.strip().lower()
            matching = [m for m in ready if wanted in m["filename"].lower()]
            if not matching and ready:
                raise Terminal("ENTITY_NOT_FOUND", f"Không thấy tài liệu \"{name.strip()}\" trong các tài liệu sẵn sàng của bạn.")
            ready = matching
        if not ready:
            raise Terminal("ENTITY_NOT_FOUND", "Bạn chưa có tài liệu học nào sẵn sàng. Hãy tải tài liệu lên ở trang Học.")
        if len(ready) > 1:
            names = ", ".join(m["filename"] for m in ready[:5])
            raise Terminal("INVALID_PARAMETER", f"Bạn có nhiều tài liệu ({names}). Hãy nêu tên tài liệu muốn dùng.")
        return ready[0]

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
        if kind == "SET_BUSY_INTERVAL":
            operation = INTENT_TO_OPERATION[kind]
            window = dict(slots["window"]) if isinstance(slots.get("window"), dict) else slots.get("window")
            if isinstance(window, dict):
                # Contract requires every window key (nullable); the model only returns the ones it has a value for.
                window = {key: None for key in WINDOW_KEYS} | window
                if window.get("timezone") is None:
                    window["timezone"] = PRODUCT_TIMEZONE
                if window.get("recurrence") == "NONE" and window.get("start_at") and window.get("end_at"):
                    try:
                        reversed_window = datetime.fromisoformat(window["start_at"].replace("Z", "+00:00")) >= datetime.fromisoformat(window["end_at"].replace("Z", "+00:00"))
                    except ValueError:
                        reversed_window = False
                    if reversed_window:
                        raise Terminal("INVALID_PARAMETER", "Giờ kết thúc phải sau giờ bắt đầu.")
                if window.get("recurrence") == "WEEKLY" and window.get("start_time") and window.get("end_time") and window["start_time"] >= window["end_time"]:
                    raise Terminal("INVALID_PARAMETER", "Giờ kết thúc phải sau giờ bắt đầu.")
            arguments = {"change_type": slots.get("change_type", "ADD"), "window_id": None,
                         "expected_window_version": None, "window": window}
            return operation, arguments if arguments["change_type"] == "ADD" and contract.is_valid(f"{operation}Arguments", arguments) else None
        if kind == "SET_SCHEDULING_PREFERENCES":
            profile = self.proc.step(ctx, "ensure_user_context", {})["data"]
            arguments = {"policy_patch": slots.get("policy_patch"), "expected_schedule_revision": profile["schedule_revision"]}
            return "set_scheduling_preferences", arguments if contract.is_valid("set_scheduling_preferencesArguments", arguments) else None
        current = self.clock()
        now = current.replace(second=0, microsecond=0) + timedelta(minutes=1)
        proposed_start = minute_instant(slots.get("start_at"), ceiling=True)
        start = max(now, datetime.fromisoformat(proposed_start.replace("Z", "+00:00"))) if proposed_start else now
        proposed_end = minute_instant(slots.get("end_at"))
        end = datetime.fromisoformat(proposed_end.replace("Z", "+00:00")) if proposed_end else now + timedelta(days=7)
        if end <= start:
            end = start + timedelta(days=7)
        scope = {"start_at": iso(start),
                 "end_at": iso(end),
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
        self.proc.validate_task_slots(merged, now=self.proc.clock())
        if not contract.is_valid("CandidateTaskFields", merged):
            raise Terminal("INVALID_PARAMETER", "Mình chưa hiểu thông tin vừa nhập.")
        last = (action["last_presentation"] or {}).get("presentation") or {}
        if last.get("revision_recommendation") is not None:
            # Task nháp do đề xuất ôn tập tạo ra được bổ sung bằng đường review có sẵn (cùng đường với /v1/actions/{id}/review).
            stored = self.proc.step(ctx, "review_pending_action", {
                "action_id": pending["action_id"], "expected_action_version": pending["version"], "presentation": last,
                "candidate_patch": merged, "expected_candidate_version": candidate["version"]},
                conversation_id=conversation, idempotency_key=child_key(key, "review"), message_id=message_id)["data"]
            return self.proc.candidate_review_reply(ctx, stored)
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
                        "normalized_command": command, "effective_policy": None, "schedule_confirmation": None}
        stored = self.proc.step(ctx, "prepare_pending_action", {"presentation": presentation, "expected_action_version": pending["version"]},
                                conversation_id=conversation, idempotency_key=child_key(key, "reprepare"),
                                message_id=message_id)["data"]
        if missing:
            return 200, reply(ctx.request_id, "NEEDS_CLARIFICATION", "Mình cần thêm thông tin.",
                              reference=self.reference_for({"pending_action": stored["pending_action"], "candidate": updated, "proposal": None}),
                              questions=self.proc.questions(merged), result=_ok(ctx.request_id, "DRAFTED", stored))
        return 200, self.proc.awaiting_reply(ctx, stored, ("TASK_CANDIDATE", updated["candidate_id"], updated["version"]))

    # ------------------------------------------------------------ tiếp tục sau quyết định
    def resume(self, ctx, receipt, key, conversation, reference, operation, result, rejected, cancelled_reply=None):
        """Được gọi sau khi /v1/decisions xử lý xong thao tác đang chờ. Trả phản hồi tổng hợp, hoặc None nếu
        thao tác đó không thuộc hàng đợi tin nhắn (ví dụ: được tạo từ biểu mẫu)."""
        queue = self.continuation(ctx, conversation, None)
        if queue is None or queue["awaiting_reference"] is None or queue["awaiting_reference"]["action_id"] != reference["action_id"]:
            return None
        index = queue["cursor"]
        follow = None if rejected or operation != "decide_revision_recommendation" else self.follow_up(result)
        if follow is not None:
            # Đề xuất ôn tập vừa tạo task nháp: bước này tiếp tục chờ người dùng bổ sung/xác nhận task đó.
            queue = self.checkpoint(ctx, key, queue, self.binding(receipt, "submit_decision", key), "WAIT", reference=follow)
            return self.compose(ctx, queue, conversation, cancelled_reply)
        if rejected:
            outcome = self.outcome(queue, index, None, "REJECTED")
        else:
            outcome = self.outcome(queue, index, operation, "SUCCEEDED", result={**result, "request_id": ctx.request_id})
        queue = self.checkpoint(ctx, key, queue, self.binding(receipt, "submit_decision", key), "ADVANCE", outcome=outcome)
        # Các bước sau dùng ID tin nhắn gốc của hàng đợi; chỉ receipt và khóa con lấy từ yêu cầu này.
        return self.advance(ctx, receipt, key, queue, "submit_decision", fallback=cancelled_reply)

    def follow_up(self, result):
        data = (result or {}).get("data") or {}
        pending = data.get("pending_action") if isinstance(data, dict) else None
        if pending is None or pending.get("state") not in AWAITING or data.get("candidate") is None:
            return None
        return self.reference_for({"pending_action": pending, "candidate": data["candidate"], "proposal": None})

    # ------------------------------------------------------------ ghép phản hồi từ trạng thái đã lưu
    def _window_query_line(self, ctx, cont, step, conversation):
        intent_item = cont["extraction"]["intents"][step["intent_index"]]
        slots = intent_item.get("slots") or {}
        raw_start = slots.get("start_at")
        if not isinstance(raw_start, str) or not raw_start.strip():
            return None
        try:
            q_start = datetime.fromisoformat(raw_start.replace("Z", "+00:00"))
        except ValueError:
            return None
        raw_end = slots.get("end_at")
        try:
            q_end = datetime.fromisoformat(raw_end.replace("Z", "+00:00")) if isinstance(raw_end, str) and raw_end.strip() else q_start + timedelta(minutes=1)
        except ValueError:
            q_end = q_start + timedelta(minutes=1)
        if q_end <= q_start:
            q_end = q_start + timedelta(minutes=1)
        zone = ZoneInfo(self.timezone)
        q_start_local = q_start.astimezone(zone)
        q_end_local = q_end.astimezone(zone)

        try:
            windows_resp = self.proc.step(ctx, "list_time_windows", {"kind": None, "include_archived": False, "page_size": 100, "cursor": None},
                                          conversation_id=conversation, message_id=cont["source_message_id"])
            windows = windows_resp["data"].get("items", [])
        except Exception:
            windows = []

        busy_hits = []
        for w in windows:
            if w.get("archived_at") or w.get("kind") != "BUSY":
                continue
            label = (w.get("label") or "").strip()
            if w.get("recurrence") == "WEEKLY":
                if w.get("weekday") != q_start_local.isoweekday():
                    continue
                day_str = q_start_local.date().isoformat()
                if w.get("valid_from") and day_str < w["valid_from"]:
                    continue
                if w.get("valid_until") and day_str >= w["valid_until"]:
                    continue
                st, et = w.get("start_time"), w.get("end_time")
                if not (st and et):
                    continue
                w_start = datetime.fromisoformat(f"{day_str}T{st}:00").replace(tzinfo=zone)
                w_end = datetime.fromisoformat(f"{day_str}T{et}:00").replace(tzinfo=zone)
            else:
                sa, ea = w.get("start_at"), w.get("end_at")
                if not (sa and ea):
                    continue
                w_start = datetime.fromisoformat(sa.replace("Z", "+00:00")).astimezone(zone)
                w_end = datetime.fromisoformat(ea.replace("Z", "+00:00")).astimezone(zone)
            if w_start < q_end_local and w_end > q_start_local:
                span = f"{w_start:%H:%M}–{w_end:%H:%M}"
                desc = f"{label} ({span})" if label else span
                busy_hits.append(desc)

        plan_data = (step.get("result") or {}).get("data") or {}
        plan = plan_data.get("plan")
        block_hits = []
        for b in (plan.get("blocks", []) if isinstance(plan, dict) else []):
            bsa, bea = b.get("start_at"), b.get("end_at")
            if not (bsa and bea):
                continue
            b_start = datetime.fromisoformat(bsa.replace("Z", "+00:00")).astimezone(zone)
            b_end = datetime.fromisoformat(bea.replace("Z", "+00:00")).astimezone(zone)
            if b_start < q_end_local and b_end > q_start_local:
                block_hits.append(f"{b.get('task_title') or 'Buổi học'} ({b_start:%H:%M}–{b_end:%H:%M})")

        parts = []
        if busy_hits:
            parts.append(f"Bạn có lịch bận: {', '.join(busy_hits)}.")
        if block_hits:
            parts.append(f"Bạn có lịch học đã xếp: {', '.join(block_hits)}.")
        if not busy_hits and not block_hits:
            if not any(not w.get("archived_at") and w.get("kind") == "BUSY" for w in windows):
                return None
            parts.append("Bạn chưa có lịch bận hay buổi học nào vào thời gian này.")
        return " ".join(parts)

    def compose(self, ctx, cont, conversation, fallback=None):
        lines, last_ok = [], None
        for step in cont["completed_steps"]:
            line, result = self.describe(step)
            if step["disposition"] == "SUCCEEDED" and step["operation"] == "get_study_plan":
                custom = self._window_query_line(ctx, cont, step, conversation)
                if custom:
                    line = custom
            if line not in lines:
                lines.append(line)
            if result is not None:
                last_ok = result
        reference = cont["awaiting_reference"]
        if reference is not None:
            lines = [self.describe(step)[0] for step in cont["completed_steps"]
                     if step["disposition"] != "FAILED"]
            lines = list(dict.fromkeys(lines))
            if any(step["disposition"] == "FAILED" for step in cont["completed_steps"]):
                lines.append("Một phần yêu cầu trước chưa xử lý được.")
            action = self.proc.workflow_context(ctx, conversation, reference["action_id"], "", False)["selected_action"]
            stored = (action["last_presentation"] or {})["presentation"]
            pending = action["pending_action"]
            if pending["state"] == "AWAITING_CLARIFICATION":
                return reply(ctx.request_id, "NEEDS_CLARIFICATION", " ".join(lines + ["Mình cần thêm thông tin."]),
                             reference=reference, questions=self.proc.questions(action["candidate"]["slots"]),
                             result=_ok(ctx.request_id, "DRAFTED", stored))
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


WINDOW_KEYS = ("kind", "label", "recurrence", "timezone", "start_at", "end_at", "weekday",
               "start_time", "end_time", "valid_from", "valid_until")
INTENT_TO_OPERATION = {"SET_BUSY_INTERVAL": "set_busy_interval"}
_ = (APPROVAL_OPERATIONS, INTENT)
