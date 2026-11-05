import copy
import unittest

from backend.app.services.scheduling_policy import merge_scheduling_policy


class SchedulingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = {'min_block_minutes': 25, 'max_block_minutes': 90,
                       'allow_short_final_block': True, 'max_daily_minutes': 240,
                       'break_minutes': 10}

    def test_custom_120_and_no_hardcoded_limits(self):
        result = merge_scheduling_policy(self.policy, {'min_block_minutes': 120,
                                         'max_block_minutes': 120,
                                         'max_daily_minutes': 480, 'break_minutes': 0})
        self.assertEqual((result['min_block_minutes'], result['max_block_minutes'],
                          result['max_daily_minutes'], result['break_minutes']), (120, 120, 480, 0))

    def test_merge_one_field_and_empty_override_do_not_mutate_input(self):
        before = copy.deepcopy(self.policy)
        result = merge_scheduling_policy(self.policy, {'break_minutes': 3})
        self.assertEqual(result, {**before, 'break_minutes': 3})
        self.assertEqual(self.policy, before)
        empty = merge_scheduling_policy(self.policy, {})
        self.assertEqual(empty, before)
        self.assertIsNot(empty, self.policy)

    def test_rejects_invalid_merged_policy(self):
        for patch in ({'min_block_minutes': 100}, {'max_block_minutes': 0},
                      {'max_daily_minutes': 0}, {'break_minutes': -1},
                      {'allow_short_final_block': 1}, {'break_minutes': None}, {'unknown': 1}):
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    merge_scheduling_policy(self.policy, patch)

    def test_requires_complete_valid_baseline(self):
        invalid = dict(self.policy)
        del invalid['max_daily_minutes']
        with self.assertRaises(ValueError):
            merge_scheduling_policy(invalid, {})
        invalid = {**self.policy, 'min_block_minutes': 100}
        with self.assertRaises(ValueError):
            merge_scheduling_policy(invalid, {'max_block_minutes': 120})


if __name__ == '__main__':
    unittest.main()
