"""Fail-closed tests of the V3 harness (no external solver required)."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verification.v3.check import classify, normalize, gate, command, module_metadata


def summary(correct=0, incorrect=0, failed=0, errors=0):
    return (f'{correct} correct transformations\n'
            f'{incorrect} incorrect transformations\n'
            f'{failed} failed-to-prove transformations\n'
            f'{errors} Alive2 errors\n')


class HarnessTests(unittest.TestCase):
    def test_refinement(self):
        self.assertEqual(classify(summary(correct=1), 0), 'refinement_verified')

    def test_counterexample(self):
        self.assertEqual(classify(summary(incorrect=1), 0), 'counterexample')

    def test_exit_zero_is_not_proof(self):
        self.assertEqual(classify('', 0), 'unknown')
        self.assertEqual(classify('Transformation seems to be correct!', 0), 'unknown')

    def test_missing_or_partial_coverage(self):
        for text in (summary(), summary(correct=2), summary(correct=1, failed=1),
                     summary(correct=1)+summary(correct=1)):
            self.assertEqual(classify(text, 0), 'unknown')

    def test_errors_and_failures(self):
        for text, code in ((summary(failed=1), 0), (summary(errors=1), 0),
                           (summary(correct=1), 1)):
            self.assertEqual(classify(text, code), 'unknown')

    def test_missed_control_is_unsuitable(self):
        self.assertEqual(normalize('refinement_verified', True), 'unsuitable')
        self.assertEqual(normalize('unknown', True), 'unknown')

    def test_gate(self):
        good = [{'negative': False, 'status': 'verified'},
                {'negative': True, 'status': 'counterexample'}]
        self.assertEqual(gate(good), 'verified')
        self.assertEqual(gate([]), 'unknown')
        self.assertEqual(gate(good+[{'negative': True, 'status': 'unknown'}]), 'unknown')
        self.assertEqual(gate(good+[{'negative': True, 'status': 'unsuitable'}]), 'unsuitable')

    def test_missing_executable(self):
        code, output = command(['/liza/nonexistent/alive-tv'])
        self.assertNotEqual(code, 0)
        self.assertEqual(classify(output, code), 'unknown')

    def test_timeout(self):
        import subprocess
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('alive', 1, b'partial')):
            code, output = command(['alive'])
        self.assertEqual(classify(output, code), 'unknown')
        self.assertIn('timeout', output)

    def test_manifest(self):
        root = Path(__file__).parent/'fixtures'
        cases = json.loads((root/'manifest.json').read_text())
        self.assertEqual(len(cases), 10)
        self.assertEqual(len({c['name'] for c in cases}), 10)
        for case in cases:
            for key in ('source', 'target'):
                self.assertIn('@subject(', (root/case[key]).read_text())

    def test_frozen_baseline(self):
        from verification.v3.check import ROOT, HERE, sha
        baseline = json.loads((HERE/'baseline.json').read_text())
        self.assertTrue(baseline)
        for path, digest in baseline.items():
            self.assertEqual(sha(ROOT/path), digest, path)

    def test_target_mismatch_never_calls_alive(self):
        from types import SimpleNamespace
        from verification.v3.check import compare
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, tgt = root/'src.ll', root/'tgt.ll'
            src.write_text('target triple = "x86_64-unknown-linux-gnu"\n')
            tgt.write_text('target triple = "x86_64-pc-windows-msvc"\n')
            args = SimpleNamespace(alive_tv='alive-tv', timeout=1)
            with patch('verification.v3.check.command') as execute:
                row = compare(args, root/'out', 'mismatch', src, tgt, 'subject')
                execute.assert_not_called()
            self.assertEqual(row['status'], 'unknown')

    def test_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'test.ll'
            path.write_text('target triple = "aarch64-apple-darwin"\ntarget datalayout = "e-p:64:64"\n')
            meta = module_metadata(path)
            self.assertEqual(meta['data_layout'], 'e-p:64:64')
            self.assertEqual(meta['triple'], 'aarch64-apple-darwin')
            self.assertEqual(len(meta['sha256']), 64)


if __name__ == '__main__':
    unittest.main()
