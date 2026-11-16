import argparse
import unittest

from backend.app.f1.scheduler.evaluation import percentile
from backend.scripts.benchmark_f1 import non_negative_int, positive_int, run_scheduler


class BenchmarkF1Tests(unittest.TestCase):
    def test_percentile(self):
        self.assertEqual(percentile([5, 1, 3], 0.5), 3)
        self.assertEqual(percentile([1, 2, 3, 4], 0.5), 2)
        self.assertEqual(percentile([1, 2, 3, 4], 0.95), 4)
        with self.assertRaises(ValueError):
            percentile([], 0.5)
        with self.assertRaises(ValueError):
            percentile([1], 0)
        with self.assertRaises(ValueError):
            percentile([1], 1.01)

    def test_run_counts_must_be_positive(self):
        self.assertEqual(positive_int("1"), 1)
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_int("0")
        self.assertEqual(non_negative_int("0"), 0)
        with self.assertRaises(argparse.ArgumentTypeError):
            non_negative_int("-1")

    def test_scheduler_scales_are_deterministic_and_valid(self):
        report = run_scheduler(repetitions=2, warmups=1)
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["warmups"], 1)


if __name__ == "__main__":
    unittest.main()
