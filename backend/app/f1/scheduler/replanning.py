from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .intervals import contains
from .models import (
    BlockIdFactory,
    EngineBlock,
    GenerationScope,
    Interval,
    Issue,
    PlanDiff,
    ProposedStudyBlock,
    StudyBlock,
)


@dataclass(frozen=True, slots=True)
class BlockPartition:
    retained_blocks: tuple[StudyBlock, ...]
    replaceable_blocks: tuple[StudyBlock, ...]
    issues: tuple[Issue, ...]


def partition_blocks_for_replan(
    blocks: tuple[StudyBlock, ...],
    *,
    now,
    generation_scope: GenerationScope,
    selected_task_ids: tuple[object, ...],
) -> BlockPartition:
    """Apply schema 1.1 replan scope rules to a current-plan snapshot."""
    retained: list[StudyBlock] = []
    replaceable: list[StudyBlock] = []
    issues: list[Issue] = []
    scope = Interval(generation_scope.start_at, generation_scope.end_at)
    selected = set(selected_task_ids)

    for block in sorted(blocks, key=lambda item: (item.start_at, item.end_at, str(item.block_id))):
        interval = Interval(block.start_at, block.end_at)
        if block.end_at <= now:
            retained.append(block)
        elif block.start_at < now < block.end_at:
            retained.append(block)
            if block.task_id in selected:
                issues.append(Issue(
                    code="ACTIVE_BLOCK_REQUIRES_REVIEW",
                    message="An active block for a selected task must be reviewed before replanning.",
                    details={"block_id": str(block.block_id), "task_id": str(block.task_id)},
                ))
        elif block.is_locked or block.task_id not in selected or not contains(scope, interval):
            retained.append(block)
        else:
            replaceable.append(block)
    return BlockPartition(tuple(retained), tuple(replaceable), tuple(issues))


def materialize_snapshot(
    *,
    retained_blocks: tuple[StudyBlock, ...],
    replaceable_blocks: tuple[StudyBlock, ...],
    generated_blocks: tuple[EngineBlock, ...],
    user_id,
    block_id_factory: BlockIdFactory,
) -> tuple[tuple[ProposedStudyBlock, ...], PlanDiff]:
    """Assign IDs, preserve logical IDs across snapshots, and compute a stable plan diff."""
    snapshot: list[ProposedStudyBlock] = []
    added: list[object] = []
    moved: list[object] = []
    removed: list[object] = []
    unchanged: list[object] = []

    for block in retained_blocks:
        snapshot.append(ProposedStudyBlock(
            block_id=block.block_id,
            user_id=block.user_id,
            task_id=block.task_id,
            start_at=block.start_at,
            end_at=block.end_at,
            is_locked=block.is_locked,
        ))
        unchanged.append(block.block_id)

    old_by_task: dict[object, list[StudyBlock]] = defaultdict(list)
    new_by_task: dict[object, list[EngineBlock]] = defaultdict(list)
    for block in replaceable_blocks:
        old_by_task[block.task_id].append(block)
    for block in generated_blocks:
        new_by_task[block.task_id].append(block)

    for task_id in sorted(set(old_by_task) | set(new_by_task), key=str):
        old_blocks = sorted(old_by_task[task_id], key=lambda item: (item.start_at, item.end_at, str(item.block_id)))
        new_blocks = sorted(new_by_task[task_id], key=lambda item: (item.start_at, item.end_at))
        paired = min(len(old_blocks), len(new_blocks))
        for index in range(paired):
            old = old_blocks[index]
            new = new_blocks[index]
            snapshot.append(ProposedStudyBlock(
                block_id=old.block_id,
                user_id=user_id,
                task_id=task_id,
                start_at=new.start_at,
                end_at=new.end_at,
                is_locked=False,
            ))
            if old.start_at == new.start_at and old.end_at == new.end_at:
                unchanged.append(old.block_id)
            else:
                moved.append(old.block_id)
        for new in new_blocks[paired:]:
            block_id = block_id_factory()
            snapshot.append(ProposedStudyBlock(
                block_id=block_id,
                user_id=user_id,
                task_id=task_id,
                start_at=new.start_at,
                end_at=new.end_at,
                is_locked=False,
            ))
            added.append(block_id)
        removed.extend(block.block_id for block in old_blocks[paired:])

    snapshot.sort(key=lambda item: (item.start_at, item.end_at, str(item.task_id), str(item.block_id)))
    diff = PlanDiff(
        added=tuple(sorted(added, key=str)),
        moved=tuple(sorted(moved, key=str)),
        removed=tuple(sorted(removed, key=str)),
        unchanged=tuple(sorted(unchanged, key=str)),
    )
    return tuple(snapshot), diff

