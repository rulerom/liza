"""Model-only proofs, byte-level controls and fail-closed report regressions."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import z3
from .check import check, solve
from .model import CAPACITY, OPERATIONS, queries
from .replay import confirm, eligible, execute, valid


def state(head=0, tail=0, eof=False, fin=False, written=None):
    buffer = [(i * 13) % 256 for i in range(CAPACITY)]
    W = [] if written is None else written[:]
    return {'B': buffer, 'W': W, 'R': W+buffer[head:tail], 'head': head, 'tail': tail, 'eof': eof, 'fin': fin}


class BufferModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.report = check(cls.root / 'run')

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_full_positive_matrix(self):
        self.assertEqual(self.report['status'], 'passed')
        rows = self.report['obligations']
        self.assertEqual(len(rows), 34)
        self.assertEqual(len({r['name'] for r in rows}), 34)
        self.assertTrue(all(r['status'] == 'proved_model_obligation' for r in rows))

    def test_eleven_controls_have_valid_concrete_witnesses(self):
        self.assertEqual(len(self.report['mutations']), 11)
        for control in self.report['mutations']:
            with self.subTest(control=control['name']):
                self.assertEqual(control['status'], 'detected_and_replayed')
                row = next(r for r in control['checks'] if r['status'] == 'counterexample_replayed')
                replay = row['replay']
                self.assertTrue(valid(replay['before']))
                result = confirm(replay['before'], control['operation'], replay['count'], replay['data'], control['name'])
                self.assertTrue(result['confirmed'])
                self.assertEqual(result['violations'], replay['violations'])

    def test_content_mutations_preserve_counts_but_not_bytes(self):
        for mutation in ('read_corrupts_byte', 'write_swaps_bytes', 'write_from_tail'):
            operation = 'read' if mutation.startswith('read') else 'write'
            replay = confirm(state(0, 4), operation, 2, [0, 255] if operation == 'read' else [], mutation)
            before, after = replay['before'], replay['after']
            self.assertIsNotNone(after, mutation)
            self.assertEqual(len(after['R']), len(after['W'])+after['tail']-after['head'])
            self.assertNotEqual(after['R'], after['W']+after['B'][after['head']:after['tail']])
            self.assertTrue(valid(before))

    def test_artifacts_and_standalone_smt(self):
        root = self.root / 'run'
        for name, digest in self.report['artifacts'].items():
            self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest)
        for path in (root / 'queries').glob('*.smt2'):
            solver = z3.Solver(); solver.set(timeout=10000); solver.from_file(str(path))
            self.assertEqual(solver.check(), z3.unsat, path.name)

    def test_all_program_claims_false(self):
        self.assertTrue(self.report['model_byte_conservation_verified'])
        for key in ('program_verified', 'semantic_ir_verified', 'runtime_verified', 'llvm_verified', 'end_to_end_verified', 'proof_certificate'):
            self.assertIs(self.report[key], False)

    def test_transition_preconditions_are_satisfiable(self):
        for op in OPERATIONS:
            *_, pre, posts = queries(op)
            solver = z3.Solver(); solver.add(pre)
            self.assertEqual(solver.check(), z3.sat, op)

    def test_unbounded_history_is_not_u32_or_bounded_exploration(self):
        for op in ('read', 'write'):
            s, _, _, _, pre, posts = queries(op)
            solver = z3.Solver(); solver.add(pre, s.wlen > 2**40)
            self.assertEqual(solver.check(), z3.sat)
            solver.add(z3.Not(posts['conservation']))
            self.assertEqual(solver.check(), z3.unsat)

    def test_read_updates_only_tail_range(self):
        before = state(3, 6, written=[77])
        after = execute(before, 'read', 3, [0, 255, 18])
        self.assertEqual(after['B'][:6], before['B'][:6])
        self.assertEqual(after['B'][6:9], [0, 255, 18])
        self.assertEqual(after['B'][9:], before['B'][9:])
        self.assertTrue(valid(after))

    def test_short_write_accepts_exact_prefix(self):
        before = state(3, 9)
        after = execute(before, 'write', 2, [])
        self.assertEqual(after['W'], before['B'][3:5])
        self.assertEqual((after['head'], after['tail']), (5, 9))
        self.assertEqual(after['B'], before['B'])
        self.assertTrue(valid(after))

    def test_full_buffer_backpressure_until_drained(self):
        s = state(0, CAPACITY)
        self.assertFalse(eligible(s, 'read', 1))
        self.assertFalse(eligible(s, 'eof', 0))
        s = execute(s, 'write', 1, [])
        self.assertFalse(eligible(s, 'read', 1))
        s = execute(s, 'write', CAPACITY-1, [])
        self.assertEqual((s['head'], s['tail']), (0, 0))
        self.assertTrue(eligible(s, 'read', 1)); self.assertTrue(valid(s))

    def test_eof_and_fin_preserve_pending_bytes(self):
        before = state(1, 4)
        s = execute(before, 'eof', 0, [])
        self.assertEqual(s['B'], before['B']); self.assertTrue(valid(s))
        self.assertFalse(eligible(s, 'fin', 0))
        s = execute(s, 'write', 3, [])
        self.assertTrue(eligible(s, 'fin', 0))
        s = execute(s, 'fin', 0, [])
        self.assertEqual(s['R'], s['W']); self.assertTrue(valid(s))
        self.assertFalse(eligible(s, 'fin', 0))

    def test_would_block_is_full_identity(self):
        s = state(4, 12, written=[0, 255])
        self.assertEqual(execute(s, 'would_block', 0, []), s)

    def test_multiple_interleaved_steps(self):
        s = state()
        for op, n, data in [('read', 4, [0, 255, 1, 200]), ('write', 2, []),
                            ('would_block', 0, []), ('read', 3, [7, 8, 9]),
                            ('write', 1, []), ('eof', 0, []), ('write', 4, []), ('fin', 0, [])]:
            self.assertTrue(eligible(s, op, n))
            s = execute(s, op, n, data)
            self.assertTrue(valid(s), op)
        self.assertEqual(s['W'], [0, 255, 1, 200, 7, 8, 9])

    def test_invalid_pre_state_not_confirmed(self):
        s = state(0, 1); s['R'] = [255]
        self.assertFalse(confirm(s, 'write', 1, [], 'write_from_tail')['confirmed'])

    def test_good_transition_not_a_counterexample(self):
        self.assertFalse(confirm(state(0, 2), 'write', 1, [], '')['confirmed'])

    def test_timeout_is_unknown(self):
        with patch('z3.Solver.check', return_value=z3.unknown), patch('z3.Solver.reason_unknown', return_value='test timeout'):
            row = solve('unknown', z3.BoolVal(True), z3.BoolVal(True), self.root / 'unknown', 1)
        self.assertEqual(row['status'], 'unknown')

    def test_unreproduced_sat_is_unknown(self):
        row = solve('sat', z3.BoolVal(True), z3.BoolVal(False), self.root / 'sat', 10000,
                    lambda m: {'confirmed': False})
        self.assertEqual(row['status'], 'unknown')

    def test_unknown_never_passes_run(self):
        with patch('verification.relay_r2a.check.solve', return_value={'status': 'unknown'}):
            report = check(self.root / 'all-unknown')
        self.assertEqual(report['status'], 'incomplete')
        self.assertFalse(report['model_byte_conservation_verified'])

    def test_bad_timeout_rejected(self):
        with self.assertRaisesRegex(ValueError, 'positive'): check(self.root / 'timeout', 0)

    def test_output_cannot_mix_runs(self):
        with self.assertRaisesRegex(ValueError, 'empty'): check(self.root / 'run')


if __name__ == '__main__': unittest.main()
