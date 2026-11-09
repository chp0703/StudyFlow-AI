"""Bộ lập lịch thuần, cho kết quả xác định, theo schema F1 1.1 của StudyFlow AI."""

from .engine import ALGORITHM_VERSION, generate_schedule
from .models import (
    AcademicTask,
    Coverage,
    EngineBlock,
    GenerationScope,
    Interval,
    Priority,
    SchedulingContext,
    SchedulingPolicy,
    SchedulingResult,
    StudyBlock,
    TaskStatus,
)
from .normalization import normalize_time_windows

__all__ = [
    "ALGORITHM_VERSION",
    "AcademicTask",
    "Coverage",
    "EngineBlock",
    "GenerationScope",
    "Interval",
    "Priority",
    "SchedulingContext",
    "SchedulingPolicy",
    "SchedulingResult",
    "StudyBlock",
    "TaskStatus",
    "generate_schedule",
    "normalize_time_windows",
]
