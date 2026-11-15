"""Dùng engine thật chuyển snapshot lập lịch từ database thành PlanProposal hoặc báo cáo chỉ đọc.

Engine không commit dữ liệu: kết quả được lưu thành đề xuất và chỉ trở thành lịch hiện hành
khi có quyết định phê duyệt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from ..scheduler.constraints import validate_context
from ..scheduler.models import (
    DEFAULT_TASK_COLOR, PRODUCT_TIMEZONE, AcademicTask, GenerationScope, Issue, Priority,
    SchedulingContext, SchedulingPolicy, SelectionMode, StudyBlock, TaskStatus,
)
from ..scheduler.normalization import normalize_time_windows
from ..scheduler.replanning import partition_blocks_for_replan
from ..scheduler.service import PlanningService

DEFAULT_POLICY = {"min_block_minutes": 25, "max_block_minutes": 90, "allow_short_final_block": True,
                  "max_daily_minutes": 240, "break_minutes": 10}


@dataclass(frozen=True)
class Generated:
    proposal: dict | None  # PlanProposal đầy đủ, sẵn sàng cho persist_plan_proposal
    report: dict | None  # SchedulingReadData khi không có thay đổi để đề xuất
    conflicts: tuple[Issue, ...] = ()


def _when(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _issue(issue: Issue) -> dict:
    return {"code": issue.code, "message": issue.message, "field": issue.field, "details": dict(issue.details)}


def _task(raw: dict) -> AcademicTask:
    raw_priority = raw["priority"]
    priority = (
        Priority(float(raw_priority))
        if type(raw_priority) in (int, float) and float(raw_priority) in (0.1, 0.5, 1.0)
        else raw_priority
    )
    return AcademicTask(
        task_id=UUID(raw["task_id"]), user_id=UUID(raw["user_id"]), title=raw["title"], deadline_at=_when(raw["deadline_at"]),
        estimated_minutes=raw["estimated_minutes"], remaining_minutes=raw["remaining_minutes"],
        priority=priority, status=TaskStatus(raw["status"]),
        available_from_at=_when(raw["available_from_at"]) if raw.get("available_from_at") else None,
        start_at=_when(raw["start_at"]) if raw.get("start_at") else None,
        color=raw.get("color", DEFAULT_TASK_COLOR),
        description=raw.get("description"),
        deadline_timezone=raw.get("deadline_timezone", PRODUCT_TIMEZONE))


def _block(raw: dict) -> StudyBlock:
    return StudyBlock(block_id=UUID(raw["block_id"]), user_id=UUID(raw["user_id"]), task_id=UUID(raw["task_id"]),
                      start_at=_when(raw["start_at"]), end_at=_when(raw["end_at"]), is_locked=raw["is_locked"])


def _confirmation_entry(block: StudyBlock, tasks: dict[UUID, AcademicTask]) -> dict:
    task = tasks[block.task_id]
    start = block.start_at.astimezone(timezone.utc)
    end = block.end_at.astimezone(timezone.utc)
    return {
        "block_id": str(block.block_id),
        "task_id": str(task.task_id),
        "task_name": task.title,
        "date": block.start_at.astimezone(ZoneInfo(PRODUCT_TIMEZONE)).date().isoformat(),
        "start_at": _iso(block.start_at),
        "end_at": _iso(block.end_at),
        "duration_minutes": int((end - start).total_seconds() // 60),
        "color": task.color,
    }


def generate(snapshot: dict, command: dict, *, now: datetime, block_id_factory: Callable[[], UUID] = uuid4) -> Generated:
    """snapshot: SchedulingInputSnapshot; command: generate_study_planArguments đã được kiểm tra."""
    user = snapshot["user"]
    scope_raw = command["generation_scope"]
    start, end = _when(scope_raw["start_at"]), _when(scope_raw["end_at"])
    policy_raw = {**DEFAULT_POLICY, **user["scheduling_policy"], **command["policy_overrides"]}
    user_id = UUID(user["user_id"])
    tasks = tuple(sorted((_task(t) for t in snapshot["tasks"]), key=lambda t: str(t.task_id)))
    tasks_by_id = {task.task_id: task for task in tasks}
    if scope_raw["selection_mode"] == "SELECTED_TASKS":
        selected = tuple(UUID(i) for i in scope_raw["task_ids"])
    else:
        selected = tuple(t.task_id for t in tasks if t.status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS) and t.remaining_minutes > 0)
    if not selected:
        return Generated(None, {"kind": "SCHEDULING_REPORT", "coverage": "NONE", "task_summaries": [],
                                "plan_diff": {"added": [], "moved": [], "removed": [], "unchanged": []}})
    windows = [w for w in snapshot["time_windows"] if w.get("archived_at") is None]
    available = normalize_time_windows([w for w in windows if w["kind"] == "AVAILABILITY"], start_at=start, end_at=end)
    busy = normalize_time_windows([w for w in windows if w["kind"] == "BUSY"], start_at=start, end_at=end)
    scope = GenerationScope(start, end, SelectionMode(scope_raw["selection_mode"]), tuple(UUID(i) for i in scope_raw["task_ids"]))
    blocks = tuple(_block(b) for b in snapshot["base_plan"]["study_blocks"])
    partition = partition_blocks_for_replan(blocks, now=now, generation_scope=scope, selected_task_ids=selected)
    if partition.issues:
        return Generated(None, None, partition.issues)
    context = SchedulingContext(
        now=now, timezone=user["timezone"], generation_scope=scope, selected_task_ids=selected, tasks=tasks,
        available_intervals=available, busy_intervals=busy, retained_blocks=partition.retained_blocks,
        replaceable_blocks=partition.replaceable_blocks, policy=SchedulingPolicy(**policy_raw))
    problems = validate_context(context)
    if problems:
        return Generated(None, None, problems)
    outcome = PlanningService(block_id_factory).generate_proposal_payload(context, user_id=user_id)
    result, payload = outcome.scheduling_result, outcome.proposal_payload
    summaries = [{"task_id": str(s.task_id), "remaining_minutes": s.remaining_minutes,
                  "retained_future_minutes": s.retained_future_minutes, "newly_scheduled_minutes": s.newly_scheduled_minutes,
                  "unallocated_minutes": s.unallocated_minutes, "reason_codes": list(s.reason_codes)}
                 for s in result.task_summaries]
    if result.conflicts:
        return Generated(None, None, result.conflicts)
    if payload is None:
        return Generated(None, {"kind": "SCHEDULING_REPORT", "coverage": result.coverage.value, "task_summaries": summaries,
                                "plan_diff": {"added": [], "moved": [], "removed": [], "unchanged": []}})
    base = snapshot["base_plan"]["plan"]
    stamp = _iso(now)
    diff = payload.plan_diff
    proposal_id = str(uuid4())
    proposed_by_id = {block.block_id: block for block in payload.study_blocks}
    base_by_id = {block.block_id: block for block in blocks}
    warnings = [_issue(warning) for warning in payload.warnings]
    confirmation = {
        "proposal_id": proposal_id,
        "proposal_version": 1,
        "base_schedule_revision": snapshot["schedule_revision"],
        "entries": [_confirmation_entry(block, tasks_by_id) for block in payload.study_blocks],
        "added": [_confirmation_entry(proposed_by_id[block_id], tasks_by_id) for block_id in diff.added],
        "changed": [{
            "before": _confirmation_entry(base_by_id[block_id], tasks_by_id),
            "after": _confirmation_entry(proposed_by_id[block_id], tasks_by_id),
        } for block_id in diff.moved],
        "removed": [_confirmation_entry(base_by_id[block_id], tasks_by_id) for block_id in diff.removed],
        "warnings": warnings,
        "unscheduled_work": [{
            "task_id": str(summary.task_id),
            "task_name": tasks_by_id[summary.task_id].title,
            "color": tasks_by_id[summary.task_id].color,
            "unscheduled_minutes": summary.unallocated_minutes,
            "reason_codes": list(summary.reason_codes),
        } for summary in result.task_summaries if summary.unallocated_minutes > 0],
    }
    proposal = {
        "proposal_id": proposal_id, "user_id": user["user_id"], "version": 1, "status": "PROPOSED",
        "base_plan_id": base["plan_id"] if base else None, "base_plan_version": base["version"] if base else None,
        "base_schedule_revision": snapshot["schedule_revision"], "generation_scope": scope_raw,
        "payload": {
            "study_blocks": [{"block_id": str(b.block_id), "user_id": str(b.user_id), "task_id": str(b.task_id),
                              "start_at": _iso(b.start_at), "end_at": _iso(b.end_at), "is_locked": b.is_locked}
                             for b in payload.study_blocks],
            "task_summaries": summaries, "coverage": payload.coverage.value, "warnings": warnings,
            "plan_diff": {name: [str(i) for i in getattr(diff, name)] for name in ("added", "moved", "removed", "unchanged")},
            "schedule_confirmation": confirmation},
        "algorithm_version": result.algorithm_version, "policy_snapshot": policy_raw, "generated_at": stamp,
        "committed_plan_id": None, "created_at": stamp, "updated_at": stamp}
    return Generated(proposal, None)
