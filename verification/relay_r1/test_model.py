"""Positive proofs, compiled controls, replay and fail-closed verifier tests."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import z3
from .check import SOURCE, PREFIX, analyze, check
from .replay import run
from .specification import SUBJECTS, concrete


class DirectionValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.report = check(cls.root / 'bundle')
        cls.module = json.loads((cls.root / 'bundle/original/semantic.json').read_text())

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def function(self, module, name):
        return next(f for f in module['functions'] if f['name'] == PREFIX + name)

    def query(self, module, name='valid'):
        return analyze(module, name, self.root / self.id().split('.')[-1])

    def test_full_domain_proofs(self):
        self.assertEqual(self.report['status'], 'passed')
        self.assertEqual(len(self.report['obligations']), 16)
        self.assertEqual({r['function'] for r in self.report['obligations']}, set(SUBJECTS))
        self.assertTrue(all(r['status'] == 'proved' for r in self.report['obligations']))

    def test_eight_source_mutants_compile_and_replay(self):
        self.assertEqual(len(self.report['mutations']), 8)
        for control in self.report['mutations']:
            with self.subTest(control=control['name']):
                self.assertEqual(control['status'], 'detected_and_replayed')
                witness = next(r for r in control['checks'] if r['status'] == 'counterexample')
                self.assertTrue(witness['replay']['trace'])
                path = self.root / 'bundle/mutations' / control['name']
                self.assertNotEqual((path / 'source/relay/direction.liza').read_bytes(), SOURCE.read_bytes())
                mutant = json.loads((path / 'semantic.json').read_text())
                d = tuple(witness['inputs']['direction']); n = witness['inputs']['count']
                args = [d, n] if control['function'] in ('read', 'write') else [d]
                actual = run(mutant, PREFIX + control['function'], args)
                self.assertTrue(actual['outcome'] == 'Trap' or actual['value'] != concrete(control['function'], d, n))

    def test_artifacts_exact_source_ir_and_queries(self):
        root = self.root / 'bundle'
        self.assertEqual((root / 'original/source/relay/direction.liza').read_bytes(), SOURCE.read_bytes())
        for path, digest in self.report['artifacts'].items():
            self.assertEqual(hashlib.sha256((root / path).read_bytes()).hexdigest(), digest)
        for subject in SUBJECTS:
            for obligation in ('no_trap', 'exact_outcome'):
                solver = z3.Solver()
                solver.from_file(str(root / 'original' / subject / (obligation + '.smt2')))
                self.assertEqual(solver.check(), z3.unsat)

    def test_claim_boundaries(self):
        for key in ('byte_conservation_verified', 'runtime_verified', 'llvm_verified', 'end_to_end_verified', 'proof_certificate'):
            self.assertIs(self.report[key], False)

    def test_concrete_boundary_inputs(self):
        states = [(0, 0, False, False), (0, 2048, False, False), (2048, 2048, True, False),
                  (0, 4294967295, False, False), (4294967295, 0, True, True),
                  (0, 0, False, True), (0, 0, True, True), (1, 2, True, False)]
        for d in states:
            for n in (0, 1, 2048, 4294967295):
                for name in SUBJECTS:
                    args = [] if name == 'empty' else [d, n] if name in ('read', 'write') else [d]
                    result = run(self.module, PREFIX + name, args)
                    self.assertEqual(result['outcome'], 'Return', (name, d, n))
                    self.assertEqual(result['value'], concrete(name, d, n), (name, d, n))

    def test_invalid_state_short_circuits_checked_subtraction(self):
        result = run(self.module, PREFIX + 'readable', [(0, 4294967295, False, False)])
        self.assertEqual(result['value'], 0)
        self.assertTrue(all(step.get('outcome') != 'Trap' for step in result['trace']))

    def test_compiler_summaries_are_not_axioms(self):
        module = copy.deepcopy(self.module)
        for f in module['functions']:
            f['may_trap'] = False; f['storage_contract'] = {'false': 'summary'}
        self.assertTrue(all(r['status'] == 'proved' for r in self.query(module, 'read')))
        # The same annotation cannot hide an actual checked arithmetic trap.
        path = self.root / 'bundle/mutations/unchecked_read_count/semantic.json'
        mutant = json.loads(path.read_text())
        for f in mutant['functions']: f['may_trap'] = False
        self.assertEqual(self.query(mutant, 'read')[0]['status'], 'counterexample')

    def test_unsupported_instruction_unknown(self):
        module = copy.deepcopy(self.module)
        self.function(module, 'valid')['blocks'][0]['operations'][0]['op'] = 'unmodelled.load'
        self.assertEqual(self.query(module)[0]['status'], 'unknown')

    def test_effects_unknown(self):
        module = copy.deepcopy(self.module)
        self.function(module, 'valid')['effect_contract'] = 'io'
        self.assertEqual(self.query(module)[0]['status'], 'unknown')

    def test_cyclic_cfg_unknown(self):
        module = copy.deepcopy(self.module)
        f = self.function(module, 'valid')
        f['blocks'][0]['terminator'] = {'op': 'jump', 'args': [f['blocks'][0]['name']]}
        self.assertEqual(self.query(module)[0]['status'], 'unknown')

    def test_recursion_unknown(self):
        module = copy.deepcopy(self.module)
        f = self.function(module, 'readable')
        o = next(o for b in f['blocks'] for o in b['operations'] if o['op'] == 'call')
        o['callee'] = f['name']
        self.assertEqual(self.query(module, 'readable')[0]['status'], 'unknown')

    def test_missing_function_unknown(self):
        module = copy.deepcopy(self.module)
        module['functions'] = [f for f in module['functions'] if f['name'] != PREFIX + 'valid']
        self.assertEqual(self.query(module, 'readable')[0]['status'], 'unknown')

    def test_bad_phi_unknown(self):
        module = copy.deepcopy(self.module)
        f = self.function(module, 'valid')
        o = next(o for b in f['blocks'] for o in b['operations'] if o['op'] == 'phi')
        o['incoming_blocks'] = ['absent'] * len(o['args'])
        self.assertEqual(self.query(module)[0]['status'], 'unknown')

    def test_wrong_declaration_unknown(self):
        module = copy.deepcopy(self.module)
        module['structures'][0]['fields'][0][1] = 'u64'
        self.assertEqual(self.query(module)[0]['status'], 'unknown')

    def test_unchecked_arithmetic_unknown(self):
        module = copy.deepcopy(self.module)
        f = self.function(module, 'queued')
        next(o for b in f['blocks'] for o in b['operations'] if o['op'] == 'sub')['overflow'] = 'wrap'
        self.assertEqual(self.query(module, 'queued')[0]['status'], 'unknown')

    def test_unsupported_terminator_unknown(self):
        module = copy.deepcopy(self.module)
        self.function(module, 'valid')['blocks'][0]['terminator'] = {'op': 'unreachable', 'args': []}
        self.assertEqual(self.query(module)[0]['status'], 'unknown')

    def test_solver_unknown_is_not_proof(self):
        with patch('z3.Solver.check', return_value=z3.unknown), patch('z3.Solver.reason_unknown', return_value='test timeout'):
            rows = self.query(self.module)
        self.assertTrue(all(r['status'] == 'unknown' for r in rows))

    def test_unconfirmed_witness_is_unknown(self):
        path = self.root / 'bundle/mutations/missing_capacity_bound/semantic.json'
        module = json.loads(path.read_text())
        with patch('verification.relay_r1.check.run', return_value={'outcome': 'Return', 'value': False, 'trace': []}):
            rows = self.query(module)
        self.assertEqual(rows[1]['status'], 'unknown')
        self.assertIn('not confirmed', rows[1]['reason'])

    def test_replay_budget_is_not_success(self):
        with self.assertRaisesRegex(ValueError, 'budget'):
            run(self.module, PREFIX + 'valid', [(0, 0, False, False)], budget=0)

    def test_new_ir_version_unknown(self):
        module = copy.deepcopy(self.module)
        module['version'] = 999
        self.assertEqual(self.query(module)[0]['status'], 'unknown')

    def test_existing_artifacts_cannot_be_mixed(self):
        with self.assertRaisesRegex(ValueError, 'empty directory'):
            check(self.root / 'bundle')

    def test_unbounded_solver_timeout_rejected(self):
        with self.assertRaisesRegex(ValueError, 'positive'):
            check(self.root / 'bad-timeout', timeout=0)


if __name__ == '__main__': unittest.main()
