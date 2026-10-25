"""Keep the relay experiment separate from V0--V4 and ordinary builds."""
import unittest
from .check import check


class RelayModel(unittest.TestCase):
    def test_independent_transition_obligations_and_mutations(self):
        report=check()
        self.assertEqual(report['status'],'passed',report)
        self.assertFalse(report['program_verified'])
        self.assertFalse(report['runtime_verified'])
        self.assertFalse(report['end_to_end_verified'])
        self.assertEqual(len([r for r in report['obligations'] if not r['mutation']]),9)
        self.assertEqual(len([r for r in report['obligations'] if r['mutation']]),6)
