"""Scalar copy/move contracts and definite availability across control flow."""
import json
import shutil
import subprocess
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower, dump
from liza.types import SCALAR_TYPES
import test_loops


def compile_body(body):
    return lower(Parser('fn main()->u32{' + body + '}').parse())


class OwnershipTests(unittest.TestCase):
    def test_use_after_move_and_expression_order(self):
        invalid = [
            'x=1; y=move x; return x',
            'x=1; y=move x; z=copy x; return z',
            'x=1; y=move x; z=move x; return z',
            'x=1; return (move x)+x',
            'x=1; return (move x)+(move x)',
            'var x=1; y=move x; x=x+1; return x',
            'x=true; y=false && move x; if x {return 1} return 0',
            'x=true; y=true || move x; if x {return 1} return 0',
            'x=true; y=(move x) && x; return 0',
            'x=1; y=copy (move x); return x',
        ]
        for body in invalid:
            with self.subTest(body=body), self.assertRaisesRegex(CompileError, 'use after move'):
                compile_body(body)
        compile_body('x=1; return x+(move x)')
        compile_body('var x=1; x=move x; return x')
        compile_body('var x=1; y=move x; x=2; return x+y')
        for body in ('return move 1', 'return move (1+2)', 'var move=1; return 0',
                     'x=1; y=move x; x=2; return x',
                     'var x:u8=1; y=move x; x=u16(2); return 0',
                     'x=1; y=move x; var x=2; return x'):
            with self.subTest(body=body), self.assertRaises(CompileError):
                compile_body(body)

    def test_branches_scopes_and_returns(self):
        for body in (
            'x=1; if false {y=move x} return x',
            'var x=1; if true {y=move x} else {x=2} return x',
            'var x=1; if true {y=move x} else {y=move x} return x',
        ):
            with self.subTest(body=body), self.assertRaisesRegex(CompileError, 'use after move'):
                compile_body(body)
        for body in (
            'x=1; if true {return move x} return x',
            'var x=1; if true {y=move x} x=2; return x',
            'var x=1; if true {y=move x; x=2} else {x=3} return x',
            'if true {x=1; y=move x} x=2; return x',
            'x=1; if true {y=move x; while true {}} return x',
        ):
            with self.subTest(body=body):
                compile_body(body)

    def test_loop_fixed_points_and_exits(self):
        for body in (
            'x=1; while true {y=move x}',
            'x=1; while true {y=move x; continue}',
            'var x=true; while move x {} return 0',
            'x=1; while true {y=move x; break} return x',
            'x=1; while false {y=move x} return 0',
            'var x=1; while true {y=move x; if true {continue} x=2}',
            'x=1; while true {while true {y=move x; break}}',
            'x=1; while true {if false {y=move x; break} break} return x',
        ):
            with self.subTest(body=body), self.assertRaisesRegex(CompileError, 'use after move'):
                compile_body(body)
        for body in (
            'var x=1; while true {y=move x; x=2; continue}',
            'while true {x=1; y=move x; continue}',
            'x=1; while true {return move x}',
            'var x=1; while true {y=move x; break} x=2; return x',
            'var x=true; while move x {x=true} return 0',
            'var x=1; while true {while true {y=move x; break} x=2}',
        ):
            with self.subTest(body=body):
                compile_body(body)

    def test_calls_and_explicit_ir(self):
        prefix = 'fn f(a:u32,b:u32)->u32{return a+b} '
        with self.assertRaisesRegex(CompileError, 'use after move'):
            lower(Parser(prefix+'fn main()->u32{x=1; return f(move x,x)}').parse())
        lower(Parser(prefix+'fn main()->u32{x=1; return f(x,move x)}').parse())
        with self.assertRaisesRegex(CompileError, 'use after move'):
            lower(Parser('fn f(x:u32)->u32{y=move x; return x} fn main()->u32{return 0}').parse())
        module = compile_body('x:u8=copy 7; y=copy x; z=move x; return u32(y+z)')
        data = json.loads(dump(module))
        self.assertEqual(data['version'], 10)
        self.assertEqual(set(data['type_properties']), set(SCALAR_TYPES))
        for properties in data['type_properties'].values():
            self.assertEqual(properties, {'copyable': True, 'implicit_copy': True})
        ops = [op for block in module[0].blocks for op in block.operations]
        self.assertEqual([op.op for op in ops if op.op in ('copy','move')], ['copy','copy','move'])


@unittest.skipUnless(shutil.which('clang'), 'native tests require clang')
class OwnershipNativeTests(unittest.TestCase):
    build = test_loops.LoopNativeTests.build

    def test_runtime_values_and_reinitialization(self):
        source = '''fn compute(n:u32)->u32 {
            var x=n
            snapshot=copy x
            var sum=0
            var i=0
            while i<5 {
                value=move x
                x=value+1
                i=i+1
                if i%2==0 {continue}
                sum=sum+copy x
            }
            if n%2==0 {old=move x; x=old+1}
            return snapshot+sum+(move x)
        }
        fn main()->u32{return 0}'''
        harness = '''#include <stdint.h>
        #include <stdlib.h>
        extern uint32_t liza_compute(uint32_t);
        int main(int argc,char **argv){if(argc!=3)return 2;
        return liza_compute(strtoul(argv[1],0,10))==strtoul(argv[2],0,10)?0:1;}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe = self.build(directory, source, opt, harness)
                for n in (0,1,2,7,1000,100000):
                    self.assertEqual(subprocess.run([str(exe),str(n),str(5*n+14+(n%2==0))], timeout=5).returncode,0)

    def test_all_scalar_snapshots(self):
        bodies = []
        for i,t in enumerate(SCALAR_TYPES):
            value = 'true' if t=='bool' else '-1' if t.startswith('i') else '42'
            other = 'false' if t=='bool' else '0'
            bodies.append(f'var x{i}:{t}={value}; a{i}=x{i}; b{i}=copy x{i}; c{i}=move x{i}; x{i}={other}; if a{i}!=b{i} || b{i}!=c{i} || x{i}==c{i} {{return 1}}')
        source = 'fn main()->u32{'+'\n'.join(bodies)+'\nreturn 0}'
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe=self.build(directory,source,opt)
                self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)

    def test_copy_preserves_argument_traps(self):
        for opt in ('-O0','-O2'):
            for body in ('x:u8=255; unused=copy (x+1); return 0',
                         'var x:u8=255; y=move x; x=0; unused=copy (y+1); return 0'):
                with tempfile.TemporaryDirectory() as directory:
                    exe=self.build(directory,'fn main()->u32{'+body+'}',opt)
                    self.assertLess(subprocess.run([str(exe)],timeout=5,capture_output=True).returncode,0)
