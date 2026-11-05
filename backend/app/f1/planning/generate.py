"""Turns the database scheduling snapshot into a PlanProposal (or a read-only report) using the real engine.

The engine never commits anything: the result is persisted as a proposal and only an approved decision
makes it the current plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID, uuid4

from ..scheduler.constraints import validate_context
from ..scheduler.models import (
    AcademicTask, GenerationScope, Issue, Priority, SchedulingContext, SchedulingPolicy, SelectionMode, StudyBlock,
    TaskStatus,
)
from ..scheduler.normalization import normalize_time_windows
from ..scheduler.replanning import partition_blocks_for_replan
from ..scheduler.service import PlanningService

DEFAULT_POLICY = {"min_block_minutes": 25, "max_block_minutes": 90, "allow_short_final_block": True,
                  "max_daily_minutes": 240, "break_minutes": 10}


@dataclass(frozen=True)
class Generated:
    proposal: dict | None  # a complete PlanProposal, ready for persist_plan_proposal
    report: dict | None  # SchedulingReadData when there is nothing to propose
    conflicts: tuple[Issue, ...] = ()


def _when(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _issue(issue: Issue) -> dict:
    return {"code": issue.code, "message": issue.message, "field": issue.field, "details": dict(issue.details)}


def _task(raw: dict) -> AcademicTask:
    return AcademicTask(
        task_id=UUID(raw["task_id"]), user_id=UUID(raw["user_id"]), title=raw["title"], deadline_at=_when(raw["deadline_at"]),
        estimated_minutes=raw["estimated_minutes"], remaining_minutes=raw["remaining_minutes"],
        priority=Priority(raw["priority"]), status=TaskStatus(raw["status"]),
        available_from_at=_when(raw["available_from_at"]) if raw.get("available_from_at") else None)


def _block(raw: dict) -> StudyBlock:
    return StudyBlock(block_id=UUID(raw["block_id"]), user_id=UUID(raw["user_id"]), task_id=UUID(raw["task_id"]),
                      start_at=_when(raw["start_at"]), end_at=_when(raw["end_at"]), is_locked=raw["is_locked"])


def generate(snapshot: dict, command: dict, *, now: datetime, block_id_factory: Callable[[], UUID] = uuid4) -> Generated:
    """snapshot: SchedulingInputSnapshot; command: generate_study_planArguments (already validated)."""
    user = snapshot["user"]
    scope_raw = command["generation_scope"]
    start, end = _when(scope_raw["start_at"]), _when(scope_raw["end_at"])
    policy_raw = {**DEFAULT_POLICY, **user["scheduling_policy"], **command["policy_overrides"]}
    user_id = UUID(user["user_id"])
    tasks = tuple(sorted((_task(t) for t in snapshot["tasks"]), key=lambda t: str(t.task_id)))
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
    proposal = {
        "proposal_id": str(uuid4()), "user_id": user["user_id"], "version": 1, "status": "PROPOSED",
        "base_plan_id": base["plan_id"] if base else None, "base_plan_version": base["version"] if base else None,
        "base_schedule_revision": snapshot["schedule_revision"], "generation_scope": scope_raw,
        "payload": {
            "study_blocks": [{"block_id": str(b.block_id), "user_id": str(b.user_id), "task_id": str(b.task_id),
                              "start_at": _iso(b.start_at), "end_at": _iso(b.end_at), "is_locked": b.is_locked}
                             for b in payload.study_blocks],
            "task_summaries": summaries, "coverage": payload.coverage.value, "warnings": [_issue(w) for w in payload.warnings],
            "plan_diff": {name: [str(i) for i in getattr(diff, name)] for name in ("added", "moved", "removed", "unchanged")}},
        "algorithm_version": result.algorithm_version, "policy_snapshot": policy_raw, "generated_at": stamp,
        "committed_plan_id": None, "created_at": stamp, "updated_at": stamp}
    return Generated(proposal, None)
