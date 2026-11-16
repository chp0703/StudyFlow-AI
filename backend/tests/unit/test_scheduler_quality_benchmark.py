import importlib.util
import unittest

from backend.app.f1.scheduler.engine import generate_schedule
from backend.scripts.benchmark_scheduler_quality import make_context, optimal_solution


@unittest.skipUnless(importlib.util.find_spec("ortools"), "install backend/requirements-evaluation.txt")
class SchedulerQualityBenchmarkTests(unittest.TestCase):
    def test_oracle_is_deterministic_and_bounds_greedy(self):
        context = make_context(20261116)
        greedy = sum(item.unallocated_minutes == 0 for item in generate_schedule(context).task_summaries)
        first = optimal_solution(context)
        second = optimal_solution(context)
        self.assertEqual((first["completed"], first["priority_score"]),
                         (second["completed"], second["priority_score"]))
        self.assertEqual(first["status"], "OPTIMAL")
        self.assertLessEqual(greedy, first["completed"])


if __name__ == "__main__":
    unittest.main()
