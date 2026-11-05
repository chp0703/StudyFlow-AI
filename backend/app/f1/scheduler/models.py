from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Callable, Mapping
from uuid import UUID


class Priority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"


class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SelectionMode(str, Enum):
    ALL_ELIGIBLE = "ALL_ELIGIBLE"
    SELECTED_TASKS = "SELECTED_TASKS"


class Coverage(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    NONE = "NONE"
    NO_CHANGE = "NO_CHANGE"


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    message: str
    field: str | None = None
    details: Mapping[str, object] = dc_field(
        default_factory=lambda: MappingProxyType({})
    )


@dataclass(frozen=True, slots=True, order=True)
class Interval:
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True, slots=True)
class GenerationScope:
    start_at: datetime
    end_at: datetime
    selection_mode: SelectionMode
    task_ids: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class SchedulingPolicy:
    min_block_minutes: int = 25
    max_block_minutes: int = 90
    allow_short_final_block: bool = True
    max_daily_minutes: int = 240
    break_minutes: int = 10


@dataclass(frozen=True, slots=True)
class AcademicTask:
    task_id: UUID
    user_id: UUID
    title: str
    deadline_at: datetime
    estimated_minutes: int
    remaining_minutes: int
    priority: Priority = Priority.NORMAL
    status: TaskStatus = TaskStatus.TODO
    available_from_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class StudyBlock:
    block_id: UUID
    user_id: UUID
    task_id: UUID
    start_at: datetime
    end_at: datetime
    is_locked: bool = False


@dataclass(frozen=True, slots=True)
class EngineBlock:
    task_id: UUID
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True, slots=True)
class TaskSchedulingSummary:
    task_id: UUID
    remaining_minutes: int
    retained_future_minutes: int
    newly_scheduled_minutes: int
    unallocated_minutes: int
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SchedulingContext:
    now: datetime
    timezone: str
    generation_scope: GenerationScope
    selected_task_ids: tuple[UUID, ...]
    tasks: tuple[AcademicTask, ...]
    available_intervals: tuple[Interval, ...]
    busy_intervals: tuple[Interval, ...] = ()
    retained_blocks: tuple[StudyBlock, ...] = ()
    replaceable_blocks: tuple[StudyBlock, ...] = ()
    policy: SchedulingPolicy = dc_field(default_factory=SchedulingPolicy)


@dataclass(frozen=True, slots=True)
class SchedulingResult:
    generated_blocks: tuple[EngineBlock, ...]
    task_summaries: tuple[TaskSchedulingSummary, ...]
    coverage: Coverage
    conflicts: tuple[Issue, ...]
    warnings: tuple[Issue, ...]
    algorithm_version: str


@dataclass(frozen=True, slots=True)
class ProposedStudyBlock:
    block_id: UUID
    user_id: UUID
    task_id: UUID
    start_at: datetime
    end_at: datetime
    is_locked: bool


@dataclass(frozen=True, slots=True)
class PlanDiff:
    added: tuple[UUID, ...]
    moved: tuple[UUID, ...]
    removed: tuple[UUID, ...]
    unchanged: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ProposalPayload:
    study_blocks: tuple[ProposedStudyBlock, ...]
    task_summaries: tuple[TaskSchedulingSummary, ...]
    coverage: Coverage
    warnings: tuple[Issue, ...]
    plan_diff: PlanDiff


@dataclass(frozen=True, slots=True)
class PlanningOutcome:
    scheduling_result: SchedulingResult
    proposal_payload: ProposalPayload | None


BlockIdFactory = Callable[[], UUID]

