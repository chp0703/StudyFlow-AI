from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .intervals import contains, to_utc
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

    now_utc = to_utc(now)
    for block in sorted(blocks, key=lambda item: (to_utc(item.start_at), to_utc(item.end_at), str(item.block_id))):
        interval = Interval(block.start_at, block.end_at)
        start_utc = to_utc(block.start_at)
        end_utc = to_utc(block.end_at)
        if end_utc <= now_utc:
            retained.append(block)
        elif start_utc < now_utc < end_utc:
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
        old_blocks = sorted(old_by_task[task_id], key=lambda item: (to_utc(item.start_at), to_utc(item.end_at), str(item.block_id)))
        new_blocks = sorted(new_by_task[task_id], key=lambda item: (to_utc(item.start_at), to_utc(item.end_at)))
        matched_old_indices: set[int] = set()
        matched_new_indices: set[int] = set()

        for new_idx, new in enumerate(new_blocks):
            for old_idx, old in enumerate(old_blocks):
                if old_idx in matched_old_indices:
                    continue
                if (
                    old.task_id == new.task_id
                    and to_utc(old.start_at) == to_utc(new.start_at)
                    and to_utc(old.end_at) == to_utc(new.end_at)
                    and not old.is_locked
                ):
                    matched_old_indices.add(old_idx)
                    matched_new_indices.add(new_idx)
                    snapshot.append(ProposedStudyBlock(
                        block_id=old.block_id,
                        user_id=user_id,
                        task_id=task_id,
                        start_at=new.start_at,
                        end_at=new.end_at,
                        is_locked=False,
                    ))
                    unchanged.append(old.block_id)
                    break

        remaining_old = [
            old for idx, old in enumerate(old_blocks)
            if idx not in matched_old_indices
        ]
        remaining_new = [
            new for idx, new in enumerate(new_blocks)
            if idx not in matched_new_indices
        ]
        paired = min(len(remaining_old), len(remaining_new))
        for index in range(paired):
            old = remaining_old[index]
            new = remaining_new[index]
            snapshot.append(ProposedStudyBlock(
                block_id=old.block_id,
                user_id=user_id,
                task_id=task_id,
                start_at=new.start_at,
                end_at=new.end_at,
                is_locked=False,
            ))
            moved.append(old.block_id)
        for new in remaining_new[paired:]:
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
        removed.extend(block.block_id for block in remaining_old[paired:])

    snapshot.sort(key=lambda item: (to_utc(item.start_at), to_utc(item.end_at), str(item.task_id), str(item.block_id)))
    diff = PlanDiff(
        added=tuple(sorted(added, key=str)),
        moved=tuple(sorted(moved, key=str)),
        removed=tuple(sorted(removed, key=str)),
        unchanged=tuple(sorted(unchanged, key=str)),
    )
    return tuple(snapshot), diff
