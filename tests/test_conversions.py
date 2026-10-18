"""Conversions and saturation use a mathematical oracle and opaque C inputs."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm

TYPES = [(f'{sign}{bits}', bits, sign == 'i') for sign in ('u', 'i') for bits in (8, 16, 32, 64)]


def limits(bits, is_signed):
    return (-(2 ** (bits-1)), 2 ** (bits-1)-1) if is_signed else (0, 2 ** bits-1)


def compile_source(source):
    return lower(Parser(source).parse())


class ConversionTypeTests(unittest.TestCase):
    def test_explicit_ir_and_literal_context(self):
        module = compile_source('''fn f(x:i64)->u8{return u8(x)}
        fn g(x:i64)->u8{return u8.wrap(x)}
        fn h(x:i64)->u8{return u8.saturate(x)}
        fn main()->u32 {a=u8.wrap(-1); b=u8.saturate(999999999999999999999999999999); return 0}''')
        for fn, policy in zip(module, ('checked', 'wrap', 'saturate')):
            op = fn.blocks[0].operations[-1]
            self.assertEqual((op.op, op.source_type, op.type), ('convert.'+policy, 'i64', 'u8'))
            self.assertEqual(fn.may_trap, policy == 'checked')
        self.assertEqual(module[3].blocks[0].operations[0].type, 'integer')
        self.assertFalse(module[3].may_trap)
        saturated = compile_source('fn f(a:i8,b:i8)->i8{return a*|b} fn main()->u32{return 0}')
        op = saturated[0].blocks[0].operations[-1]
        self.assertEqual((op.op, op.overflow, op.type), ('mul', 'saturate', 'i8'))
        self.assertFalse(saturated[0].may_trap)

    def test_rejections(self):
        for expression in ('u8(300)', 'u8(-1)', 'i8(128)', 'u64(-1)',
                           'u8(true)', 'u8.wrap(false)', 'u8.saturate(true)',
                           'u8()', 'u8(1,2)', 'u8.unknown(1)', 'bool(1)',
                           'u8.wrap(-1+0)', 'u8(4294967296+0)',
                           'u8.wrap(1)+u16(1)', 'u8(1)+|u16(1)', 'true+|false'):
            with self.subTest(expression=expression), self.assertRaises(CompileError):
                compile_source(f'fn main()->u32{{unused={expression}; return 0}}')
        with self.assertRaises(CompileError):
            compile_source('fn main()->u32{if false {unused=u8(300)} return 0}')


@unittest.skipUnless(shutil.which('clang'), 'native tests require clang')
class ConversionNativeTests(unittest.TestCase):
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

    def test_all_64_pairs_runtime(self):
        # Compare at full logical width in Liza, return only a u32 status to C.
        # Narrow C return types require target ABI extensions not offered by
        # Liza's internal calling convention (public FFI is not implemented).
        functions, declarations, dispatch, cases = [], [], [], []
        for src, sbits, ssigned in TYPES:
            slo, shi = limits(sbits, ssigned)
            sc = ('int' if ssigned else 'uint')+str(sbits)+'_t'
            sp = 'strtoll' if ssigned else 'strtoull'
            for dst, dbits, dsigned in TYPES:
                dlo, dhi = limits(dbits, dsigned)
                dc = ('int' if dsigned else 'uint')+str(dbits)+'_t'
                dp = 'strtoll' if dsigned else 'strtoull'
                values = {slo, shi, 0, 1, -1, dlo-1, dlo, dlo+1, dhi-1, dhi, dhi+1}
                for mode in ('checked', 'wrap', 'saturate'):
                    index = len(dispatch)
                    name = f'c_{src}_{dst}_{mode}'
                    syntax = dst if mode == 'checked' else dst+'.'+mode
                    functions.append(f'fn {name}(x:{src},expected:{dst})->u32{{if {syntax}(x)==expected {{return 0}} return 1}}')
                    declarations.append(f'extern uint32_t liza_{name}({sc},{dc});')
                    dispatch.append(f'case {index}: return liza_{name}(({sc}){sp}(argv[2],0,10),({dc}){dp}(argv[3],0,10));')
                    for value in sorted(v for v in values if slo <= v <= shi):
                        trap = mode == 'checked' and not dlo <= value <= dhi
                        if mode == 'wrap':
                            expected = value % (2 ** dbits)
                            if dsigned and expected > dhi:
                                expected -= 2 ** dbits
                        elif mode == 'saturate':
                            expected = max(dlo, min(dhi, value))
                        else:
                            expected = value if not trap else 0
                        cases.append(([str(index), str(value), str(expected)], trap, name))
        source = '\n'.join(functions)+'\nfn main()->u32{return 0}'
        harness = '#include <stdint.h>\n#include <stdlib.h>\n'+'\n'.join(declarations)+'''
        int main(int argc,char **argv) {if(argc!=4)return 2; switch(atoi(argv[1])) {
        '''+'\n'.join(dispatch)+'} return 3;}'
        for opt in ('-O0', '-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe = self.build(directory, source, opt, harness)
                for args, trap, name in cases:
                    with self.subTest(opt=opt, name=name, value=args[1]):
                        code = subprocess.run([str(exe), *args], capture_output=True, timeout=5).returncode
                        self.assertLess(code, 0) if trap else self.assertEqual(code, 0)

    def test_saturating_arithmetic_runtime(self):
        functions, declarations, dispatch, cases = [], [], [], []
        for t, bits, sign in TYPES:
            lo, hi = limits(bits, sign)
            ct = ('int' if sign else 'uint')+str(bits)+'_t'
            parse = 'strtoll' if sign else 'strtoull'
            values = sorted(v for v in {lo, lo+1, -2, -1, 0, 1, 2, hi-1, hi} if lo <= v <= hi)
            for op, symbol in (('add','+|'), ('sub','-|'), ('mul','*|')):
                index = len(dispatch)
                name = f'{op}_{t}'
                functions.append(f'fn {name}(a:{t},b:{t},expected:{t})->u32{{if a{symbol}b==expected {{return 0}} return 1}}')
                declarations.append(f'extern uint32_t liza_{name}({ct},{ct},{ct});')
                dispatch.append(f'case {index}: return liza_{name}(({ct}){parse}(argv[2],0,10),({ct}){parse}(argv[3],0,10),({ct}){parse}(argv[4],0,10));')
                for a in values:
                    for b in values:
                        math = a+b if op=='add' else a-b if op=='sub' else a*b
                        cases.append(([str(index), str(a), str(b), str(max(lo,min(hi,math)))], name))
        source = '\n'.join(functions)+'\nfn main()->u32{return 0}'
        harness = '#include <stdint.h>\n#include <stdlib.h>\n'+'\n'.join(declarations)+'''
        int main(int argc,char **argv) {if(argc!=5)return 2; switch(atoi(argv[1])) {
        '''+'\n'.join(dispatch)+'} return 3;}'
        for opt in ('-O0', '-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe = self.build(directory, source, opt, harness)
                for args, name in cases:
                    with self.subTest(opt=opt, name=name, args=args[1:]):
                        self.assertEqual(subprocess.run([str(exe), *args], capture_output=True, timeout=5).returncode, 0)

    def test_literals_evaluation_and_phi(self):
        safe = '''fn clipped(a:i8,b:i8)->i8{return a*|b}
        fn narrow(x:i64)->i8{return i8.wrap(x)}
        fn main()->u32 {
            if u8.wrap(-1)!=255 {return 1}
            if i8.wrap(-129)!=127 {return 2}
            if u8.wrap(340282366920938463463374607431768211457)!=1 {return 3}
            if u8.saturate(-10)!=0 || u8.saturate(300)!=255 {return 4}
            if u64(18446744073709551615)!=18446744073709551615 {return 5}
            x:i64=300
            if false {unused=u8(x)}
            if false && (u8(x)==0) {return 6}
            if !(true || (u8(x)==0)) {return 7}
            if !(true && (u8(i64(42))==42)) {return 8}
            if !(false || (u8.saturate(x)==255 && u8.wrap(x)==44)) {return 9}
            a:u8=250
            if (a+|10)-|10!=245 {return 10}
            if a+|10*|2!=255 {return 11}
            if u8.wrap(250+10)!=4 {return 12}
            if clipped(127,-2)!=-128 || narrow(255)!=-1 {return 13}
            return 0
        }'''
        failures = ['x:i64=300; unused=u8(x)', 'x:i32=-1; unused=u64(x)',
                    'unused=u8(250+10)', 'unused=u8(i16(300))',
                    'x:u64=18446744073709551615; unused=i64(x)',
                    'x:u8=255; unused=u8.wrap(x+1)', 'x:u8=255; unused=u8.saturate(x+1)',
                    'x:u8=255; unused=(x+1)+|0', 'x:u8=255; unused=u8(x+1)']
        for opt in ('-O0','-O2'):
            for body in [None, *failures]:
                with self.subTest(opt=opt,body=body), tempfile.TemporaryDirectory() as directory:
                    source = safe if body is None else 'fn main()->u32{'+body+'; return 0}'
                    exe = self.build(directory, source, opt)
                    code = subprocess.run([str(exe)], capture_output=True, timeout=5).returncode
                    self.assertEqual(code, 0) if body is None else self.assertLess(code, 0)
