"""Hằng số, lỗi nghiệp vụ và hàm dựng dữ liệu workflow dùng chung."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import zlib
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..clients.rpc import iso

PRODUCT_TIMEZONE = "Asia/Ho_Chi_Minh"
DEFAULT_TASK_COLOR = "#596CF0"
TASK_COLOR_PALETTE = (
    "#6C5CE7",
    "#0EA5E9",
    "#10B981",
    "#F59E0B",
    "#EF4444",
    "#EC4899",
    "#C69214",
    "#0D9488",
    "#6366F1",
)


def default_task_color(slots: dict) -> str:
    """Chọn màu mặc định xoay vòng ổn định theo công việc khi người dùng không chỉ định màu."""
    seed = "|".join(str(slots.get(k) or "").strip().lower() for k in ("title", "start_at", "deadline_date", "deadline_at"))
    if not seed.strip("|"):
        return TASK_COLOR_PALETTE[0]
    return TASK_COLOR_PALETTE[zlib.crc32(seed.encode("utf-8")) % len(TASK_COLOR_PALETTE)]
DEFAULT_TASK_PRIORITY = 0.5
POLICY_DEFAULT = {"min_block_minutes": 25, "max_block_minutes": 90, "allow_short_final_block": True,
                  "max_daily_minutes": 240, "break_minutes": 10}
INTENT = {"create_task_candidate": "CREATE_TASK",
          "set_busy_interval": "SET_BUSY_INTERVAL", "set_scheduling_preferences": "SET_SCHEDULING_PREFERENCES"}
FORM_TEXT = {"create_task_candidate": "Thêm công việc bằng biểu mẫu",
             "set_busy_interval": "Cập nhật giờ bận bằng biểu mẫu", "set_scheduling_preferences": "Cập nhật tùy chọn lập lịch bằng biểu mẫu",
             "generate_study_plan": "Tạo kế hoạch học bằng biểu mẫu"}
DONE_TEXT = {"confirm_task": "Đã lưu công việc.",
             "set_busy_interval": "Đã cập nhật giờ bận.", "set_scheduling_preferences": "Đã cập nhật tùy chọn lập lịch.",
             "approve_study_plan": "Đã duyệt kế hoạch học.", "reject_study_plan": "Đã từ chối kế hoạch.",
             "verify_question_drafts": "Đã xác nhận bộ câu hỏi.", "decide_revision_recommendation": "Đã áp dụng đề xuất ôn tập.",
             "decide_learning_session_outcome": "Đã lưu kết quả phiên học."}
AWAITING = ("AWAITING_CLARIFICATION", "AWAITING_CONFIRMATION", "AWAITING_APPROVAL")


class Terminal(Exception):
    """Kết quả lỗi nghiệp vụ cuối cùng, được lưu trong receipt để phát lại khi gửi lại yêu cầu."""

    def __init__(self, code: str, message: str, field: str | None = None):
        super().__init__(code)
        self.error = {"code": code, "message": message, "field": field, "details": {}, "retryable": False}


def _ok(request_id: str, outcome: str, data) -> dict:
    return {"schema_version": "1.1", "request_id": request_id, "outcome": outcome, "data": data, "error": None, "warnings": []}


def reply(request_id: str, state: str, message: str, *, reference=None, questions=None, result=None) -> dict:
    return {"schema_version": "1.1", "request_id": request_id, "state": state, "message": message,
            "action_reference": reference, "questions": questions or [], "result": result, "error": None}


def deadline_instant(slots: dict) -> str | None:
    """Deadline chỉ có ngày kết thúc ở đầu ngày kế tiếp theo giờ Việt Nam (Asia/Ho_Chi_Minh)."""
    try:
        tz_name = slots.get("deadline_timezone") or PRODUCT_TIMEZONE
        if tz_name != PRODUCT_TIMEZONE:
            return None
        zone = ZoneInfo(tz_name)
        local = datetime.combine(date.fromisoformat(slots["deadline_date"]) + timedelta(days=1), time.min, zone)
    except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError):
        return None
    return iso(local.astimezone(timezone.utc))


def end_instant_from_start(start_at: object, estimated_minutes: object) -> str | None:
    """Mặc định cuối ngày địa phương, đủ chỗ cho các quãng nghỉ giữa block."""
    if not isinstance(start_at, str) or type(estimated_minutes) is not int or estimated_minutes <= 0:
        return None
    try:
        parsed = datetime.fromisoformat(start_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    breaks = max(0, (estimated_minutes - 1) // POLICY_DEFAULT["max_block_minutes"]) * POLICY_DEFAULT["break_minutes"]
    local = parsed.astimezone(ZoneInfo(PRODUCT_TIMEZONE))
    end_of_day = local.replace(hour=23, minute=59, second=0, microsecond=0)
    return iso(max(end_of_day, parsed + timedelta(minutes=estimated_minutes + breaks)).astimezone(timezone.utc))


def minute_instant(value: object, *, ceiling: bool = False) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    rounded = parsed.replace(second=0, microsecond=0)
    if ceiling and rounded < parsed:
        rounded += timedelta(minutes=1)
    return iso(rounded.astimezone(timezone.utc))
