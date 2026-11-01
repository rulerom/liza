import unittest
from model import explore


class NotificationModel(unittest.TestCase):
    def test_reachable_states(self):
        for capacity in (1, 2):
            count, trace, bad = explore(capacity)
            print('capacity', capacity, 'reachable', count)
            self.assertGreater(count, 10)
            self.assertIsNone(bad, (trace, bad))

    def test_negative_controls(self):
        for mutation in ('lost_wake', 'early_arm', 'reset_race', 'hidden_fault'):
            with self.subTest(mutation=mutation):
                _, trace, bad = explore(2, mutation)
                print(mutation, trace, bad)
                self.assertIsNotNone(bad)


if __name__ == '__main__':
    unittest.main()
