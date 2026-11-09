from __future__ import annotations

import unittest

from backend.app.f1.scheduler.models import Coverage, Interval
from backend.app.f1.scheduler.service import PlanningService

from .helpers import USER_ID, context, dt, task, uid


class PlanningServiceTests(unittest.TestCase):
    def test_full_result_becomes_proposal_payload(self) -> None:
        item = task(401, remaining=60, deadline=dt(4, 12))
        service = PlanningService(block_id_factory=lambda: uid(999))
        outcome = service.generate_proposal_payload(
            context((item,), available=(Interval(dt(4, 8), dt(4, 10)),)),
            user_id=USER_ID,
        )
        self.assertIsNotNone(outcome.proposal_payload)
        self.assertEqual(Coverage.FULL, outcome.proposal_payload.coverage)
        self.assertEqual((uid(999),), outcome.proposal_payload.plan_diff.added)

    def test_none_result_does_not_create_proposal(self) -> None:
        item = task(402, remaining=60)
        outcome = PlanningService().generate_proposal_payload(
            context((item,), available=()), user_id=USER_ID
        )
        self.assertEqual(Coverage.NONE, outcome.scheduling_result.coverage)
        self.assertIsNone(outcome.proposal_payload)

    def test_owner_mismatch_is_rejected_at_service_boundary(self) -> None:
        item = task(403, remaining=60)
        with self.assertRaises(ValueError):
            PlanningService().generate_proposal_payload(context((item,)), user_id=uid(404))


if __name__ == "__main__":
    unittest.main()

