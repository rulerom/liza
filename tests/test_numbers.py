"""Numeric semantics: compile-time rejection and full-width native comparisons."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm
from liza.types import INTEGER_TYPES, bounds, width, signed


def compile_source(source):
    return lower(Parser(source).parse())


class NumericTypeTests(unittest.TestCase):
    def test_literal_boundaries(self):
        for type_name in INTEGER_TYPES:
            low, high = bounds(type_name)
            for value in (low, high, 0):
                with self.subTest(type=type_name, value=value):
                    compile_source(f'fn f()->{type_name}{{return {value}}} fn main()->u32{{return 0}}')
            for value in (low - 1, high + 1):
                with self.subTest(type=type_name, value=value), self.assertRaisesRegex(CompileError, 'range'):
                    compile_source(f'fn f()->{type_name}{{return {value}}} fn main()->u32{{return 0}}')

    def test_context_flows_in_both_directions(self):
        source = '''fn id(x:i16)->i16{return x}
        fn f()->i16 {a:i16=-100; b=(1+2)+a; c=a+(1+2); return id(b+c)}
        fn main()->u32{return 0}'''
        module = compile_source(source)
        for block in module[1].blocks:
            self.assertTrue(all(op.type == 'i16' for op in block.operations))

    def test_rejections(self):
        cases = [
            'x:u8=1; y:u16=x',
            'x:u8=1; y:u16=2; z=x+y',
            'x:u8=1; y:i8=1; z=x==y',
            'x:u64=1; y:u8=2; z=x<<y',
            'x:u8=1; z=x<<-1',
            'x:i32=1; z=1<<x',
            'x=true; y=~x',
            'x=true & false',
            'x=1 && true',
            'x=false || 1',
            'x:u8=1; y=-x',
            'x=-1',
            'x=4294967296',
            'x:u8=(255+256)-256',
            'x:bool=256==1; y:u8=256',
        ]
        for body in cases:
            with self.subTest(body=body), self.assertRaises(CompileError):
                compile_source('fn main()->u32{' + body + '; return 0}')

    def test_ir_shift_policy_and_traps(self):
        module = compile_source('fn f(x:i8,n:u32)->i8{return x>>n} fn main()->u32{return 0}')
        op = module[0].blocks[0].operations[-1]
        self.assertEqual(op.op, 'shr')
        self.assertEqual(op.type, 'i8')
        self.assertTrue(op.may_trap)
        self.assertEqual(op.overflow, 'none')
        self.assertEqual(op.shift_policy, 'trap')


@unittest.skipUnless(shutil.which('clang'), 'native tests require clang')
class NumericNativeTests(unittest.TestCase):
    def execute(self, source, optimization):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            ir, exe = path / 'program.ll', path / 'program'
            ir.write_text(llvm(compile_source(source)))
            result = subprocess.run(['clang', '-Wno-override-module', optimization, str(ir), '-o', str(exe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return subprocess.run([str(exe)], capture_output=True, timeout=5).returncode

    def test_values_all_widths(self):
        functions, checks = [], []
        for t in INTEGER_TYPES:
            low, high = bounds(t)
            bits = width(t)
            functions.extend([
                f'fn add_{t}(a:{t},b:{t})->{t}{{return a+b}}',
                f'fn wrap_{t}(a:{t})->{t}{{return a+%1}}',
                f'fn sub_{t}(a:{t})->{t}{{return a-%1}}',
                f'fn shl_{t}(a:{t},n:u32)->{t}{{return a<<n}}',
                f'fn shr_{t}(a:{t},n:u32)->{t}{{return a>>n}}',
            ])
            checks.extend([
                f'if add_{t}({high-1},1)!={high} {{return 1}}',
                f'if wrap_{t}({high})!={low} {{return 2}}',
                f'if sub_{t}({low})!={high} {{return 3}}',
                f'if shl_{t}(1,{bits-1})!={low if signed(t) else 1 << (bits-1)} {{return 4}}',
                f'if shl_{t}({low if signed(t) else 1 << (bits-1)},1)!=0 {{return 5}}',
                f'if shr_{t}({low if signed(t) else high},{bits-1})!={-1 if signed(t) else 1} {{return 6}}',
                f'if shr_{t}({high},0)!={high} {{return 7}}',
                f'x_{t}:{t}=5; if (x_{t}&3)!=1 {{return 8}}',
                f'if (x_{t}|2)!=7 {{return 9}}',
                f'if (x_{t}^3)!=6 {{return 10}}',
                f'if (~x_{t})!={-6 if signed(t) else high-5} {{return 11}}',
                f'if (x_{t}*%3)!=15 {{return 12}}',
                f'if (x_{t}*3)!=15 {{return 13}}',
                f'if (x_{t}-3)!=2 {{return 14}}',
            ])
            if signed(t):
                checks.append(f'if -x_{t} != -5 {{return 15}}')
                checks.append(f'if x_{t} < -1 {{return 16}}')
        source = '\n'.join(functions) + '\nfn main()->u32{\n' + '\n'.join(checks) + '\nreturn 0}'
        for optimization in ('-O0', '-O2'):
            with self.subTest(optimization=optimization):
                self.assertEqual(self.execute(source, optimization), 0)

    def test_runtime_traps_all_widths(self):
        for t in INTEGER_TYPES:
            low, high = bounds(t)
            expressions = [f'{high}+1', f'{low}-1', f'{high}*2', f'1<<{width(t)}', f'1>>4294967295']
            if signed(t):
                expressions.append('-x')
            for optimization in ('-O0', '-O2'):
                for expr in expressions:
                    with self.subTest(type=t, expr=expr, optimization=optimization):
                        source = f'fn f(x:{t})->{t}{{return {expr}}} fn main()->u32{{unused=f({low}); return 0}}'
                        self.assertLess(self.execute(source, optimization), 0)

    def test_short_circuit(self):
        prefix = 'fn boom()->bool{x:u8=255; unused=x+1; return true}\n'
        safe = [('false && boom()', 'false'), ('true || boom()', 'true'),
                ('(false && boom()) || true', 'true'), ('(true || boom()) && false', 'false'),
                ('true && (1+1==2)', 'true'), ('false || (1<<2==4)', 'true'),
                ('(1+1==2) && (false || (2*2==4))', 'true')]
        for optimization in ('-O0', '-O2'):
            for expression, expected in safe:
                source = prefix + f'fn main()->u32{{if ({expression})=={expected} {{return 0}} return 1}}'
                self.assertEqual(self.execute(source, optimization), 0)
            for expression in ('true && boom()', 'false || boom()'):
                source = prefix + f'fn main()->u32{{unused={expression}; return 0}}'
                self.assertLess(self.execute(source, optimization), 0)

    def test_u8_reassociation_and_dead_branch(self):
        prefix = 'fn f(x:u8)->u8{return (x+1)-1}\n'
        for optimization in ('-O0', '-O2'):
            self.assertLess(self.execute(prefix+'fn main()->u32{unused=f(255); return 0}', optimization), 0)
            self.assertEqual(self.execute(prefix+'fn main()->u32{if f(254)!=254{return 1} if false {unused=f(255)} return 0}', optimization), 0)

    def test_runtime_inputs_for_64_bit_arithmetic_and_shifts(self):
        source = '''fn left(x:u64,n:u32)->u64{return x<<n}
        fn right(x:i64,n:u32)->i64{return x>>n}
        fn checked(x:i64)->i64{return (x+1)-1}
        fn main()->u32{return 0}'''
        harness = '''#include <stdint.h>
        #include <stdlib.h>
        extern uint64_t liza_left(uint64_t, uint32_t);
        extern int64_t liza_right(int64_t, uint32_t);
        extern int64_t liza_checked(int64_t);
        int main(int argc, char **argv) {
            if (argc != 5) return 2;
            uint32_t n = (uint32_t)strtoul(argv[3], 0, 10);
            if (argv[1][0] == 'l')
                return liza_left(strtoull(argv[2],0,10), n) == strtoull(argv[4],0,10) ? 0 : 1;
            int64_t x = strtoll(argv[2],0,10);
            int64_t actual = argv[1][0] == 'r' ? liza_right(x,n) : liza_checked(x);
            return actual == strtoll(argv[4],0,10) ? 0 : 1;
        }'''
        cases = [
            (['l', '1', '63', str(1 << 63)], False),
            (['l', str(1 << 63), '1', '0'], False),
            (['l', '1', '64', '0'], True),
            (['l', '1', '4294967295', '0'], True),
            (['r', str(-(1 << 63)), '63', '-1'], False),
            (['r', '-1', '64', '0'], True),
            (['c', str((1 << 63) - 2), '0', str((1 << 63) - 2)], False),
            (['c', str((1 << 63) - 1), '0', '0'], True),
        ]
        for optimization in ('-O0', '-O2'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)
                ir, c, exe = path / 'module.ll', path / 'harness.c', path / 'program'
                ir.write_text(llvm(compile_source(source)).replace('define i32 @main()', 'define i32 @test_entry()'))
                c.write_text(harness)
                result = subprocess.run(['clang', '-Wno-override-module', optimization, str(ir), str(c), '-o', str(exe)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                for args, traps in cases:
                    with self.subTest(optimization=optimization, args=args):
                        code = subprocess.run([str(exe), *args], capture_output=True, timeout=5).returncode
                        self.assertLess(code, 0) if traps else self.assertEqual(code, 0)
