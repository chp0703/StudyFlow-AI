from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from .engine import generate_schedule
from .models import (
    BlockIdFactory,
    Coverage,
    PlanningOutcome,
    ProposalPayload,
    SchedulingContext,
)
from .replanning import materialize_snapshot


class PlanningService:
    """Application boundary that builds proposal payloads but never commits a plan."""

    def __init__(self, block_id_factory: BlockIdFactory = uuid4) -> None:
        self._block_id_factory = block_id_factory

    def generate_proposal_payload(
        self,
        context: SchedulingContext,
        *,
        user_id,
    ) -> PlanningOutcome:
        if any(task.user_id != user_id for task in context.tasks):
            raise ValueError("user_id must match the owner of every task in the context")
        if any(block.user_id != user_id for block in (*context.retained_blocks, *context.replaceable_blocks)):
            raise ValueError("user_id must match the owner of every block in the context")
        result = generate_schedule(context)
        if result.conflicts or result.coverage in (Coverage.NONE, Coverage.NO_CHANGE):
            return PlanningOutcome(result, None)

        snapshot, plan_diff = materialize_snapshot(
            retained_blocks=context.retained_blocks,
            replaceable_blocks=context.replaceable_blocks,
            generated_blocks=result.generated_blocks,
            user_id=user_id,
            block_id_factory=self._block_id_factory,
        )
        if not (plan_diff.added or plan_diff.moved or plan_diff.removed):
            unchanged_result = (
                replace(result, coverage=Coverage.NO_CHANGE)
                if result.coverage is Coverage.FULL
                else result
            )
            return PlanningOutcome(unchanged_result, None)

        payload = ProposalPayload(
            study_blocks=snapshot,
            task_summaries=result.task_summaries,
            coverage=result.coverage,
            warnings=result.warnings,
            plan_diff=plan_diff,
        )
        return PlanningOutcome(result, payload)
