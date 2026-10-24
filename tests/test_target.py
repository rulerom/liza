from dataclasses import replace
import shutil
import subprocess
import tempfile
from pathlib import Path
import unittest

from liza.target import resolve
from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm


@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class TargetTests(unittest.TestCase):
    def test_generated_and_optimized_environment(self):
        target = resolve()
        self.assertEqual(target.pointer_bits, 64)
        self.assertEqual(target.pointer_align, 8)
        self.assertEqual(target.i32_align, 4)
        self.assertTrue(target.little_endian)
        module = lower(Parser('fn main()->u32 { return 0 }').parse())
        source = llvm(module, target)
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)/'module.ll'
            raw.write_text(source)
            for level in ('0', '2'):
                path = Path(tmp)/f'O{level}.ll'
                subprocess.run(['clang', *target.flags, '-Werror=override-module',
                                '-S', '-emit-llvm', '-O'+level, str(raw), '-o', str(path)],
                               check=True, capture_output=True)
                for directive in (f'target triple = "{target.triple}"',
                                  f'target datalayout = "{target.data_layout}"'):
                    self.assertIn(directive, source)
                    self.assertIn(directive, path.read_text())

    def test_invalid_target_rejected(self):
        with self.assertRaises(ValueError):
            resolve('clang', 'not-a-real-architecture')
        with self.assertRaises(ValueError):
            replace(resolve(), triple='bad"\ninjected')
        with self.assertRaises(ValueError):
            replace(resolve(), pointer_bits=32)

    def test_legacy_target_neutral_api(self):
        module = lower(Parser('fn main()->u32 { return 0 }').parse())
        self.assertNotIn('target triple', llvm(module))


class ProbeFailureTests(unittest.TestCase):
    """Exercise Clang-wrapper failures without depending on a system compiler."""
    def output(self, triple='x86_64-unknown-linux-gnu', bits=64, endian=1):
        return (f'target triple = "{triple}"\n'
                'target datalayout = "e-p:64:64-i64:64"\n'
                f'@liza_pointer_bits = constant i32 {bits}\n'
                '@liza_pointer_align = constant i32 8\n'
                '@liza_i64_align = constant i32 8\n'
                '@liza_i32_align = constant i32 4\n'
                f'@liza_little_endian = constant i32 {endian}\n')

    def process(self, output=None, code=0, error=''):
        return subprocess.CompletedProcess([], code, self.output() if output is None else output, error)

    def test_clang_failure_preserves_diagnostic(self):
        from unittest.mock import patch
        with patch('liza.target.subprocess.run', return_value=self.process(code=1, error='invalid SDK')):
            with self.assertRaisesRegex(ValueError, 'invalid SDK'):
                resolve('custom-clang')

    def test_missing_executable(self):
        from unittest.mock import patch
        with patch('liza.target.subprocess.run', side_effect=FileNotFoundError('missing clang')):
            with self.assertRaises(FileNotFoundError):
                resolve('absent-clang')

    def test_incomplete_probe_is_rejected(self):
        from unittest.mock import patch
        for missing in ('target triple', 'target datalayout', '@liza_pointer_align'):
            output='\n'.join(line for line in self.output().splitlines() if not line.startswith(missing))
            with self.subTest(missing=missing), patch('liza.target.subprocess.run', return_value=self.process(output)):
                with self.assertRaisesRegex(ValueError, 'Clang omitted'):
                    resolve()

    def test_unsupported_abis(self):
        from unittest.mock import patch
        for output in (self.output(bits=32), self.output(endian=0),
                       self.output(triple='riscv64-unknown-linux-gnu')):
            with self.subTest(output=output), patch('liza.target.subprocess.run', return_value=self.process(output)):
                with self.assertRaises(ValueError):
                    resolve()

    def test_environment_drift_between_probes(self):
        from unittest.mock import patch
        for changed in (self.output(triple='x86_64-pc-windows-msvc'),
                        self.output().replace('e-p:64:64', 'e-p:64:32'),
                        self.output().replace('pointer_align = constant i32 8', 'pointer_align = constant i32 4')):
            with self.subTest(changed=changed), patch('liza.target.subprocess.run', side_effect=[
                    self.process(), self.process(), self.process(changed)]):
                with self.assertRaisesRegex(ValueError, 'not stable'):
                    resolve()

    def test_wrapper_path_and_canonical_target(self):
        from unittest.mock import patch
        canonical='x86_64-pc-windows-msvc19.51.0'
        with patch('liza.target.subprocess.run', return_value=self.process(self.output(triple=canonical))) as run:
            target=resolve('/custom directory/clang-wrapper', 'x86_64-pc-windows-msvc')
        self.assertEqual(target.triple, canonical)
        self.assertEqual(target.flags, ('--target='+canonical, '-march=x86-64'))
        self.assertEqual(run.call_args_list[0].args[0][0], '/custom directory/clang-wrapper')
        self.assertIn('--target=x86_64-pc-windows-msvc', run.call_args_list[0].args[0])
        self.assertIn('--target='+canonical, run.call_args_list[-1].args[0])
        self.assertNotIn('shell', run.call_args.kwargs)
