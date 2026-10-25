"""Fail-closed result comparison, independently of compiler availability."""
import unittest
from run import assert_results

class AgreementTests(unittest.TestCase):
    def test_wrong_error_kind_is_not_agreement(self):
        with self.assertRaises(AssertionError):assert_results([(5,1)],[(4,1)],'mutant')

    def test_wrong_offset_is_not_agreement(self):
        with self.assertRaises(AssertionError):assert_results([(4,2)],[(4,1)],'mutant')

    def test_missing_or_extra_result_is_not_agreement(self):
        for actual in ([],[(0,2),(0,2)]):
            with self.subTest(actual=actual):
                with self.assertRaises(AssertionError):assert_results(actual,[(0,2)],'mutant')

    def test_failure_is_not_success_with_same_offset(self):
        with self.assertRaises(AssertionError):assert_results([(0,1)],[(1,1)],'mutant')
