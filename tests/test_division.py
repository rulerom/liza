"""Division contracts checked against integer mathematics with runtime inputs."""
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm
from liza.types import INTEGER_TYPES, bounds, signed, width


def compile_source(source):
    return lower(Parser(source).parse())


class DivisionTypeTests(unittest.TestCase):
    def test_context_and_trap_metadata(self):
        module = compile_source('''fn quotient(a:i16)->i16{return 7/a}
        fn remainder(a:i16)->i16{return a%3}
        fn main()->u32{x=quotient(2); y=remainder(2); return 0}''')
        for fn, instruction in zip(module, ('div', 'rem')):
            op = fn.blocks[0].operations[-1]
            self.assertEqual((op.op, op.type, op.division_policy), (instruction, 'i16', 'trap'))
            self.assertEqual(op.overflow, 'none')
            self.assertTrue(op.may_trap)
        self.assertTrue(all(fn.may_trap for fn in module))

    def test_reject_mixed_types_and_bool(self):
        for operator in ('/', '%'):
            for body in ('x:u8=7; y:u16=2; z=x OP y',
                         'x:i8=7; y:u8=2; z=x OP y',
                         'x=true OP false', 'x:u8=7 OP 256'):
                with self.subTest(operator=operator, body=body), self.assertRaisesRegex(CompileError, 'expected|range'):
                    compile_source('fn main()->u32{' + body.replace('OP', operator) + '; return 0}')


@unittest.skipUnless(shutil.which('clang'), 'native tests require clang')
class DivisionNativeTests(unittest.TestCase):
    def build(self, directory, source, optimization, harness=None):
        path = Path(directory)
        ir, exe = path / 'module.ll', path / 'program'
        output = llvm(compile_source(source))
        self.assertNotRegex(output, r'\b(nsw|nuw|inbounds|exact)\b')
        if harness:
            output = output.replace('define i32 @main()', 'define i32 @test_entry()')
        ir.write_text(output)
        files = [str(ir)]
        if harness:
            c = path / 'harness.c'
            c.write_text(harness)
            files.append(str(c))
        result = subprocess.run(['clang', '-Wno-override-module', optimization, *files, '-o', str(exe)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return exe

    def test_all_widths_with_opaque_runtime_inputs(self):
        functions, declarations, dispatch = [], [], []
        for index, t in enumerate(INTEGER_TYPES):
            ctype = ('int' if signed(t) else 'uint') + str(width(t)) + '_t'
            parse = 'strtoll' if signed(t) else 'strtoull'
            for name, operator in (('div', '/'), ('rem', '%')):
                functions.append(f'fn {name}_{t}(a:{t},b:{t})->{t}{{return a{operator}b}}')
                declarations.append(f'extern {ctype} liza_{name}_{t}({ctype}, {ctype});')
            dispatch.append(f'''case {index}: {{
                {ctype} a=({ctype}){parse}(argv[3],0,10), b=({ctype}){parse}(argv[4],0,10);
                {ctype} expected=({ctype}){parse}(argv[5],0,10);
                {ctype} actual=argv[2][0]=='d' ? liza_div_{t}(a,b) : liza_rem_{t}(a,b);
                return actual==expected ? 0 : 1;
            }}''')
        source = '\n'.join(functions) + '\nfn main()->u32{return 0}'
        harness = '#include <stdint.h>\n#include <stdlib.h>\n' + '\n'.join(declarations) + '''
        int main(int argc, char **argv) {
            if (argc!=6) return 2;
            switch (atoi(argv[1])) {''' + '\n'.join(dispatch) + '''}
            return 3;
        }'''
        rng = random.Random(20261018)
        cases = []
        for index, t in enumerate(INTEGER_TYPES):
            low, high = bounds(t)
            values = {low, low+1, 0, 1, 2, 7, high-1, high}
            if signed(t):
                values.update((-7, -2, -1))
            pairs = [(a,b) for a in sorted(values) for b in sorted(values)]
            pairs += [(rng.randint(low, high), rng.randint(low, high)) for _ in range(16)]
            for a, b in pairs:
                for op in ('div', 'rem'):
                    traps = b == 0 or (op == 'div' and signed(t) and a == low and b == -1)
                    result = 0
                    if not traps:
                        q = abs(a) // abs(b)
                        if (a < 0) != (b < 0):
                            q = -q
                        result = q if op == 'div' else a - q*b
                    cases.append(([str(index), op, str(a), str(b), str(result)], traps, t))
        for optimization in ('-O0', '-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe = self.build(directory, source, optimization, harness)
                for args, traps, t in cases:
                    with self.subTest(optimization=optimization, type=t, args=args[1:]):
                        code = subprocess.run([str(exe), *args], capture_output=True, timeout=5).returncode
                        if traps:
                            self.assertLess(code, 0)
                        else:
                            self.assertEqual(code, 0)

    def test_constants_control_flow_and_unused_results(self):
        safe = '''fn main()->u32 {
            a:i8=-128
            if a % -1 != 0 {return 1}
            if 24 / 3 * 2 != 16 {return 2}
            if 20 % 6 * 2 != 4 {return 3}
            if 20 / 2 / 2 != 5 {return 4}
            if 20 % 6 % 3 != 2 {return 5}
            if false {unused=1/0}
            if false && (1%0==0) {return 6}
            if !(true || (1/0==0)) {return 7}
            if !(true && (a % -1 == 0)) {return 8}
            if !(false || (12/3==4 && 12%5==2)) {return 9}
            // Slash comments coexist with division and wrapping tokens.
            if (255+%1)%3 != 1 {return 10}
            return 0
        }'''
        failures = ['unused=1/0', 'unused=1%0', 'a:i64=-9223372036854775808; unused=a/-1',
                    'unused=true && (1/0==0)', 'unused=false || (1%0==0)',
                    'x:u8=255; unused=(x+1)/2', 'unused=(1/0)*0']
        for optimization in ('-O0', '-O2'):
            for body in [None, *failures]:
                source = safe if body is None else 'fn main()->u32{' + body + '; return 0}'
                with self.subTest(optimization=optimization, body=body), tempfile.TemporaryDirectory() as directory:
                    exe = self.build(directory, source, optimization)
                    code = subprocess.run([str(exe)], capture_output=True, timeout=5).returncode
                    if body is None:
                        self.assertEqual(code, 0)
                    else:
                        self.assertLess(code, 0)
