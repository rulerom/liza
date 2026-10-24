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
