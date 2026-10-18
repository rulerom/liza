from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm


def compile_source(source):
    return lower(Parser(source).parse())


class FrontendTests(unittest.TestCase):
    def test_value_graph(self):
        module = compile_source('fn main() -> u32 { a = 2; b = a; return b +% 3 * 4 }')
        operations = module[0].operations
        self.assertEqual([o.op for o in operations], ['constant', 'constant', 'constant', 'mul', 'add'])
        self.assertEqual(operations[-1].overflow, 'wrap')
        self.assertEqual(operations[-2].overflow, 'trap')
        self.assertEqual(operations[-1].args[0], 'v0')

    def test_rejected_programs(self):
        cases = [
            ('fn main() -> u32 { a=1; a=2; return a }', 'immutable'),
            ('fn main() -> u32 { return absent }', 'unknown value'),
            ('fn main() -> u32 { return missing() }', 'unknown function'),
            ('fn f(a:u32)->u32{return a} fn main()->u32{return f()}', 'number of arguments'),
            ('fn main()->u32{return 4294967296}', 'outside u32'),
            ('fn main()->u32{}', 'must return'),
            ('fn main()->u32{return 1; a=2}', 'unreachable'),
            ('fn main(a:u32)->u32{return a}', 'no parameters'),
            ('fn f()->u32{return 1}', 'missing fn main'),
            ('fn main()->u32{return 1} fn main()->u32{return 2}', 'duplicate function'),
            ('fn f(a:u32,a:u32)->u32{return a} fn main()->u32{return 0}', 'duplicate parameter'),
            ('fn main()->u32{return 1 / 0}', 'unexpected character'),
            ('fn main()->u32{return 1', 'expected newline'),
            ('fn main()->u32{return 1 2}', 'expected newline'),
            ('fn main()->u32:realtime{return 0}', "expected 'pure'"),
            ('fn main()->i32{return 0}', "expected 'u32'"),
        ]
        for source, message in cases:
            with self.subTest(source=source), self.assertRaisesRegex(CompileError, message):
                compile_source(source)

    def test_source_location(self):
        with self.assertRaisesRegex(CompileError, '2:12: unknown value'):
            compile_source('fn main()->u32 {\n    return missing\n}')

    def test_comments_and_hex(self):
        module = compile_source('// heading\nfn main()->u32 {\nreturn 0xff // value\n}\n')
        self.assertEqual(module[0].operations[0].args, [255])


@unittest.skipUnless(shutil.which('clang'), 'native tests require clang')
class NativeTests(unittest.TestCase):
    def run_source(self, source, optimization):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            ir = path / 'program.ll'
            exe = path / 'program'
            ir.write_text(llvm(compile_source(source)))
            result = subprocess.run(['clang', '-Wno-override-module', optimization, str(ir), '-o', str(exe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return subprocess.run([str(exe)], capture_output=True, timeout=5).returncode

    def test_native_semantics(self):
        cases = [
            ('fn main()->u32{return 2 + 3 * 4}', 14),
            ('fn main()->u32{return (2 + 3) * 4}', 20),
            ('fn main()->u32{return 9 - 3 - 2}', 4),
            ('fn main()->u32{return f(21)} fn f(x:u32)->u32{return x * 2}', 42),
            ('fn main()->u32{return 0xffffffff +% 1}', 0),
            ('fn main()->u32{return (0 -% 1) - 0xffffff00}', 255),
            ('fn main()->u32{return 65536 *% 65536}', 0),
        ]
        for optimization in ('-O0', '-O2'):
            for source, expected in cases:
                with self.subTest(source=source, optimization=optimization):
                    self.assertEqual(self.run_source(source, optimization), expected)

    def test_overflow_traps_even_if_result_unused(self):
        for optimization in ('-O0', '-O2'):
            for expression in ('0xffffffff + 1', '0 - 1', '65536 * 65536'):
                with self.subTest(expression=expression, optimization=optimization):
                    source = f'fn main()->u32{{ unused = {expression}; return 0 }}'
                    self.assertLess(self.run_source(source, optimization), 0)

    def test_cli_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source.liza'
            output = Path(directory) / 'program'
            source.write_text('fn main()->u32{return 42}')
            def cli(*args):
                return subprocess.run([sys.executable, '-m', 'liza', *args], capture_output=True, text=True)
            self.assertEqual(cli('check', str(source)).returncode, 0)
            self.assertEqual(cli('build', str(source), '-o', str(output)).returncode, 0)
            self.assertEqual(subprocess.run([str(output)]).returncode, 42)
            self.assertEqual(cli('run', str(source)).returncode, 42)
            self.assertEqual(cli('build', str(source), '-o', str(source)).returncode, 1)
            self.assertEqual(source.read_text(), 'fn main()->u32{return 42}')
            self.assertEqual(cli('build', str(source), '--clang', '/nonexistent/liza-clang').returncode, 1)


if __name__ == '__main__':
    unittest.main()
