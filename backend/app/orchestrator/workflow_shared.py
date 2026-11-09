"""Hằng số, lỗi nghiệp vụ và hàm dựng dữ liệu workflow dùng chung."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..clients.rpc import iso

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
    """Deadline chỉ có ngày kết thúc ở đầu ngày kế tiếp theo giờ địa phương (contract mục 2)."""
    try:
        zone = ZoneInfo(slots["deadline_timezone"])
        local = datetime.combine(date.fromisoformat(slots["deadline_date"]) + timedelta(days=1), time.min, zone)
    except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError):
        return None
    return iso(local.astimezone(timezone.utc))
