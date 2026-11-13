"""Acceptance coverage for the complete schedule confirmation DTO (BE-03)."""

import unittest
from datetime import datetime, timezone
from uuid import UUID

from backend.app.f1.planning.generate import generate


OWNER = "00000000-0000-4000-8000-000000000001"
TASK = "00000000-0000-4000-8000-000000000002"
BLOCK_A = "00000000-0000-4000-8000-000000000010"
BLOCK_B = "00000000-0000-4000-8000-000000000011"
FRESH_BLOCK = UUID("00000000-0000-4000-8000-000000000012")


def task(remaining=60):
    return {
        "task_id": TASK,
        "user_id": OWNER,
        "title": "Ôn xác suất",
        "description": "Chương 2",
        "start_at": "2026-11-05T12:00:00Z",
        "available_from_at": "2026-11-05T12:00:00Z",
        "deadline_at": "2026-11-05T16:00:00Z",
        "deadline_timezone": "Asia/Ho_Chi_Minh",
        "estimated_minutes": 120,
        "remaining_minutes": remaining,
        "priority": 1,
        "color": "#FF5733",
        "status": "TODO",
    }


def availability(start="2026-11-05T12:00:00Z", end="2026-11-05T13:00:00Z"):
    return {
        "window_id": "00000000-0000-4000-8000-000000000020",
        "user_id": OWNER,
        "version": 1,
        "kind": "AVAILABILITY",
        "label": "Buổi tối",
        "recurrence": "NONE",
        "timezone": "Asia/Ho_Chi_Minh",
        "start_at": start,
        "end_at": end,
        "weekday": None,
        "start_time": None,
        "end_time": None,
        "valid_from": None,
        "valid_until": None,
        "archived_at": None,
        "created_at": "2026-11-01T00:00:00Z",
        "updated_at": "2026-11-01T00:00:00Z",
    }


def block(block_id, start, end):
    return {
        "block_id": block_id,
        "user_id": OWNER,
        "task_id": TASK,
        "start_at": start,
        "end_at": end,
        "is_locked": False,
    }


def snapshot(*, remaining=60, windows=None, blocks=()):
    return {
        "user": {
            "user_id": OWNER,
            "timezone": "Asia/Ho_Chi_Minh",
            "scheduling_policy": {
                "min_block_minutes": 25,
                "max_block_minutes": 90,
                "allow_short_final_block": True,
                "max_daily_minutes": 240,
                "break_minutes": 10,
            },
        },
        "schedule_revision": 7,
        "tasks": [task(remaining)],
        "time_windows": windows or [availability()],
        "base_plan": {
            "plan": {"plan_id": "00000000-0000-4000-8000-000000000030", "version": 3} if blocks else None,
            "study_blocks": list(blocks),
        },
    }


COMMAND = {
    "generation_scope": {
        "start_at": "2026-11-05T00:00:00Z",
        "end_at": "2026-11-06T00:00:00Z",
        "selection_mode": "SELECTED_TASKS",
        "task_ids": [TASK],
    },
    "policy_overrides": {},
}


class CompleteScheduleConfirmationAcceptance(unittest.TestCase):
    def test_confirmation_expands_changed_and_removed_entries(self):
        outcome = generate(
            snapshot(blocks=(
                block(BLOCK_A, "2026-11-05T08:00:00Z", "2026-11-05T09:00:00Z"),
                block(BLOCK_B, "2026-11-05T10:00:00Z", "2026-11-05T11:00:00Z"),
            )),
            COMMAND,
            now=datetime(2026, 11, 5, 7, tzinfo=timezone.utc),
            block_id_factory=lambda: FRESH_BLOCK,
        )

        self.assertIsNotNone(outcome.proposal)
        proposal = outcome.proposal
        confirmation = proposal["payload"]["schedule_confirmation"]
        self.assertEqual(
            (confirmation["proposal_id"], confirmation["proposal_version"], confirmation["base_schedule_revision"]),
            (proposal["proposal_id"], proposal["version"], 7),
        )
        self.assertEqual((len(confirmation["entries"]), len(confirmation["changed"]), len(confirmation["removed"])), (1, 1, 1))
        entry = confirmation["entries"][0]
        self.assertEqual(
            (entry["task_id"], entry["task_name"], entry["date"], entry["start_at"], entry["end_at"],
             entry["duration_minutes"], entry["color"]),
            (TASK, "Ôn xác suất", "2026-11-05", "2026-11-05T12:00:00.000000Z",
             "2026-11-05T13:00:00.000000Z", 60, "#FF5733"),
        )
        changed = confirmation["changed"][0]
        self.assertEqual(changed["before"]["block_id"], changed["after"]["block_id"])
        self.assertNotEqual(changed["before"]["start_at"], changed["after"]["start_at"])
        self.assertEqual(confirmation["warnings"], proposal["payload"]["warnings"])
        self.assertEqual(confirmation["unscheduled_work"], [])

    def test_partial_proposal_exposes_unscheduled_work(self):
        outcome = generate(
            snapshot(
                remaining=90,
                windows=[availability("2026-11-05T12:00:00Z", "2026-11-05T12:30:00Z")],
            ),
            COMMAND,
            now=datetime(2026, 11, 5, 7, tzinfo=timezone.utc),
            block_id_factory=lambda: FRESH_BLOCK,
        )

        confirmation = outcome.proposal["payload"]["schedule_confirmation"]
        self.assertEqual(len(confirmation["added"]), 1)
        self.assertEqual(confirmation["added"][0], confirmation["entries"][0])
        self.assertEqual(confirmation["unscheduled_work"], [{
            "task_id": TASK,
            "task_name": "Ôn xác suất",
            "color": "#FF5733",
            "unscheduled_minutes": 60,
            "reason_codes": ["INSUFFICIENT_CAPACITY"],
        }])


if __name__ == "__main__":
    unittest.main()
