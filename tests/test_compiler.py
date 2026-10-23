from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import json

from liza.frontend import Parser, CompileError
from liza.ir import lower, dump
from liza.backend import llvm


def compile_source(source):
    return lower(Parser(source).parse())


class FrontendTests(unittest.TestCase):
    def test_value_graph(self):
        module = compile_source('fn main() -> u32 { a = 2; b = a; return b +% 3 * 4 }')
        operations = module[0].blocks[0].operations
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
            ('fn main()->u32{return 1 @ 0}', 'unexpected character'),
            ('fn main()->u32{return 1', 'expected newline'),
            ('fn main()->u32{return 1 2}', 'expected newline'),
            ('fn main()->u32:realtime{return 0}', "expected 'pure'"),
            ('fn main()->i128{return 0}', "unknown type"),
        ]
        for source, message in cases:
            with self.subTest(source=source), self.assertRaisesRegex(CompileError, message):
                compile_source(source)

    def test_source_location(self):
        with self.assertRaisesRegex(CompileError, '2:12: unknown value'):
            compile_source('fn main()->u32 {\n    return missing\n}')

    def test_comments_and_hex(self):
        module = compile_source('// heading\nfn main()->u32 {\nreturn 0xff // value\n}\n')
        self.assertEqual(module[0].blocks[0].operations[0].args, [255])

    def test_type_and_branch_errors(self):
        cases = [
            ('fn main()->bool{return true}', 'main must return u32'),
            ('fn main()->u32{return false}', 'expected u32, got bool'),
            ('fn main()->u32{x:bool=1; return 0}', 'expected integer, got bool'),
            ('fn main()->u32{x:u32=true; return 0}', 'expected u32, got bool'),
            ('fn main()->u32{if 1 {return 0} return 1}', 'expected integer, got bool'),
            ('fn main()->u32{if true {return 0}}', 'every path'),
            ('fn main()->u32{if true {x=1} return x}', 'unknown value'),
            ('fn main()->u32{if true {x=1} else {return x} return 0}', 'unknown value'),
            ('fn main()->u32{x=1; if true {x=2} return x}', 'immutable'),
            ('fn main()->u32{if true {return 1} else {return 2} return 3}', 'unreachable'),
            ('fn main()->u32{if false {return true} return 0}', 'expected u32, got bool'),
            ('fn main()->u32{x=true + false; return 0}', 'expected integer, got bool'),
            ('fn main()->u32{x=true < false; return 0}', 'expected integer, got bool'),
            ('fn main()->u32{x=true == 1; return 0}', 'expected integer, got bool'),
            ('fn main()->u32{x=!1; return 0}', 'expected integer, got bool'),
            ('fn f(x:bool)->u32{return 0} fn main()->u32{return f(1)}', 'expected integer, got bool'),
            ('fn main()->u32{true=1; return 0}', 'identifier'),
            ('fn main()->u32{if true {return 0} else}', "expected"),
        ]
        for source, message in cases:
            with self.subTest(source=source), self.assertRaisesRegex(CompileError, message):
                compile_source(source)

    def test_ir_control_flow(self):
        module = compile_source('fn main()->u32{if 1 < 2 {return 3} else {return 4}}')
        blocks = module[0].blocks
        self.assertEqual(blocks[0].terminator.op, 'branch')
        self.assertEqual(blocks[0].operations[-1].type, 'bool')
        self.assertTrue(all(block.terminator is not None for block in blocks))

    def test_ir_transitive_trap_summary(self):
        source = '''fn main()->u32{return first(1)}
        fn first(x:u32)->u32{return second(x)}
        fn second(x:u32)->u32{if x == 0 {return first(x)} return x + 1}
        fn wrapping(x:u32)->u32{return x +% 1}
        fn safe()->u32{return wrapping(1)}
        fn recursive()->u32{return recursive()}
        fn dead()->u32{if false {unused=0-1} return 0}'''
        module = {fn.name: fn for fn in compile_source(source)}
        for name in ('main', 'first', 'second', 'dead'):
            self.assertTrue(module[name].may_trap, name)
        for name in ('wrapping', 'safe', 'recursive'):
            self.assertFalse(module[name].may_trap, name)
        for fn in module.values():
            for block in fn.blocks:
                for op in block.operations:
                    if op.op == 'call':
                        self.assertEqual(op.may_trap, module[op.callee].may_trap)
                    else:
                        self.assertEqual(op.may_trap, op.overflow == 'trap')
        serialized = json.loads(dump(list(module.values())))
        self.assertEqual(serialized['version'], 15)
        self.assertTrue(serialized['functions'][0]['may_trap'])

    def test_arithmetic_lowering_has_no_unproven_flags(self):
        source = '''fn check(x:u32)->u32{return (x + 1) - 1}
        fn wrap(x:u32)->u32{return (x +% 1) -% 1}
        fn main()->u32{return check(wrap(1))}'''
        generated = llvm(compile_source(source))
        self.assertNotRegex(generated, r'\b(nsw|nuw|inbounds|exact)\b')
        self.assertIn('@llvm.uadd.with.overflow.i32', generated)


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

    def test_native_branches(self):
        cases = [
            ('fn main()->u32{if true {return 42} else {return 7}}', 42),
            ('fn main()->u32{if false {return 42} else {return 7}}', 7),
            ('fn main()->u32{if false {return 0 - 1} return 42}', 42),
            ('fn main()->u32{if true {return 42} else {return 0 - 1}}', 42),
            ('fn main()->u32{x=40; if false {a=x+1} else {b=x+2} return x}', 40),
            ('fn main()->u32{if false {return 1}\nelse if true {if false {return 2} return 42}\nelse{return 3}}', 42),
            ('fn main()->u32{if true {x=1} x=42; return x}', 42),
            ('fn main()->u32{if true {} return 42}', 42),
            ('fn decide(x:bool)->bool{return !x} fn main()->u32{if decide(false)==true {return 42} return 0}', 42),
            ('fn main()->u32{if 2 + 3 * 4 == 14 {return 42} return 0}', 42),
        ]
        for optimization in ('-O0', '-O2'):
            for source, expected in cases:
                with self.subTest(source=source, optimization=optimization):
                    self.assertEqual(self.run_source(source, optimization), expected)

    def test_unsigned_comparisons(self):
        # Exercise both outcomes, especially across the signed i32 boundary.
        pairs = [(0, 0), (0, 1), (1, 0), (0xffffffff, 1), (1, 0xffffffff)]
        operators = {'==': lambda a,b:a==b, '!=': lambda a,b:a!=b,
                     '<': lambda a,b:a<b, '<=': lambda a,b:a<=b,
                     '>': lambda a,b:a>b, '>=': lambda a,b:a>=b}
        # One native program per optimization level, so all comparisons execute.
        functions, calls = [], []
        for i, (op, compare) in enumerate(operators.items()):
            functions.append(f'fn c{i}(a:u32,b:u32)->bool{{return a {op} b}}')
            for a, b in pairs:
                expected = 'true' if compare(a, b) else 'false'
                calls.append(f'if c{i}({a},{b}) != {expected} {{return 1}}')
        source = '\n'.join(functions) + '\nfn main()->u32{\n' + '\n'.join(calls) + '\nreturn 0\n}'
        for optimization in ('-O0', '-O2'):
            self.assertEqual(self.run_source(source, optimization), 0)

    def test_taken_branch_preserves_trap(self):
        for optimization in ('-O0', '-O2'):
            source = 'fn main()->u32{if true {unused=0-1} return 0}'
            self.assertLess(self.run_source(source, optimization), 0)

    def test_checked_reassociation_and_dead_branch(self):
        function = 'fn test(x:u32)->u32{return (x + 1) - 1}\n'
        cases = [
            ('return test(0xffffffff)', True),
            ('unused=test(0xffffffff); return 0', True),
            ('x:u32=0xffffffff; y=x+1-1; return 0', True),
            ('if test(0xfffffffe) == 0xfffffffe {return 0} return 1', False),
            ('if false {x:u32=0xffffffff; y=x+1} return 0', False),
            ('if false {unused=test(0xffffffff)} return 0', False),
        ]
        for optimization in ('-O0', '-O2'):
            for body, traps in cases:
                with self.subTest(body=body, optimization=optimization):
                    code = self.run_source(function + 'fn main()->u32{' + body + '}', optimization)
                    if traps:
                        self.assertLess(code, 0)
                    else:
                        self.assertEqual(code, 0)

    def test_checked_reassociation_with_runtime_input(self):
        # Separate translation units and no LTO keep the input unknown to codegen.
        source = 'fn test(x:u32)->u32{return (x+1)-1} fn main()->u32{return 0}'
        harness = '''#include <stdint.h>
        #include <stdlib.h>
        extern uint32_t liza_test(uint32_t);
        int main(int argc, char **argv) {
            if (argc != 2) return 2;
            uint32_t x = (uint32_t)strtoul(argv[1], 0, 10);
            return liza_test(x) == x ? 0 : 1;
        }'''
        for optimization in ('-O0', '-O2'):
            with self.subTest(optimization=optimization), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                ir, c, exe = path / 'module.ll', path / 'harness.c', path / 'program'
                ir.write_text(llvm(compile_source(source)).replace('define i32 @main()', 'define i32 @test_entry()'))
                c.write_text(harness)
                result = subprocess.run(['clang', '-Wno-override-module', optimization, str(ir), str(c), '-o', str(exe)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                for value in ('0', '1', '4294967294'):
                    result = subprocess.run([str(exe), value], capture_output=True, timeout=5)
                    self.assertEqual(result.returncode, 0)
                result = subprocess.run([str(exe), '4294967295'], capture_output=True, timeout=5)
                self.assertLess(result.returncode, 0)

    def test_recursive_boolean_function(self):
        source = '''fn even(n:u32)->bool {
            if n == 0 {return true}
            return !even(n - 1)
        }
        fn main()->u32 {if even(10) {return 42} return 1}'''
        for optimization in ('-O0', '-O2'):
            self.assertEqual(self.run_source(source, optimization), 42)

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
