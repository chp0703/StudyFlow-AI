from __future__ import annotations

import unittest

from backend.app.f1.scheduler.models import EngineBlock, GenerationScope, SelectionMode
from backend.app.f1.scheduler.replanning import materialize_snapshot, partition_blocks_for_replan

from .helpers import USER_ID, block, dt, task, uid


class ReplanningTests(unittest.TestCase):
    def test_partition_preserves_history_locked_outside_and_unselected(self) -> None:
        selected_task = task(201)
        other_task = task(202)
        blocks = (
            block(1, selected_task.task_id, dt(4, 6), dt(4, 7)),
            block(2, selected_task.task_id, dt(4, 9), dt(4, 10), True),
            block(3, selected_task.task_id, dt(4, 10), dt(4, 11)),
            block(4, selected_task.task_id, dt(6, 10), dt(6, 11)),
            block(5, other_task.task_id, dt(4, 12), dt(4, 13)),
        )
        scope = GenerationScope(dt(4, 8), dt(5, 23), SelectionMode.SELECTED_TASKS, (selected_task.task_id,))
        partition = partition_blocks_for_replan(
            blocks,
            now=dt(4, 8),
            generation_scope=scope,
            selected_task_ids=(selected_task.task_id,),
        )
        self.assertEqual({uid(1), uid(2), uid(4), uid(5)}, {item.block_id for item in partition.retained_blocks})
        self.assertEqual((uid(3),), tuple(item.block_id for item in partition.replaceable_blocks))

    def test_active_selected_block_requires_review(self) -> None:
        item = task(210)
        active = block(11, item.task_id, dt(4, 8), dt(4, 9))
        scope = GenerationScope(dt(4, 8), dt(5, 23), SelectionMode.SELECTED_TASKS, (item.task_id,))
        partition = partition_blocks_for_replan(
            (active,), now=dt(4, 8, 30), generation_scope=scope, selected_task_ids=(item.task_id,)
        )
        self.assertEqual("ACTIVE_BLOCK_REQUIRES_REVIEW", partition.issues[0].code)
        self.assertEqual((active,), partition.retained_blocks)

    def test_materialize_snapshot_reuses_ids_and_reports_diff(self) -> None:
        item = task(220)
        retained = (block(20, item.task_id, dt(4, 7), dt(4, 8), True),)
        replaceable = (
            block(21, item.task_id, dt(4, 9), dt(4, 10)),
            block(22, item.task_id, dt(4, 11), dt(4, 12)),
        )
        generated = (
            EngineBlock(item.task_id, dt(4, 9), dt(4, 10)),
            EngineBlock(item.task_id, dt(4, 12), dt(4, 13)),
            EngineBlock(item.task_id, dt(4, 14), dt(4, 15)),
        )
        values = iter((uid(23),))
        snapshot, diff = materialize_snapshot(
            retained_blocks=retained,
            replaceable_blocks=replaceable,
            generated_blocks=generated,
            user_id=USER_ID,
            block_id_factory=lambda: next(values),
        )
        self.assertEqual((uid(23),), diff.added)
        self.assertEqual((uid(22),), diff.moved)
        self.assertFalse(diff.removed)
        self.assertEqual({uid(20), uid(21)}, set(diff.unchanged))
        self.assertEqual({uid(20), uid(21), uid(22), uid(23)}, {item.block_id for item in snapshot})


if __name__ == "__main__":
    unittest.main()

