"""Nominal aggregate values, independent copies and value-only lowering."""
import json
import shutil
import subprocess
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower, dump
from liza.backend import llvm
import test_loops


def compile_source(source):
    return lower(Parser(source).parse())


class StructureTests(unittest.TestCase):
    def test_invalid_definitions(self):
        cases = [
            ('struct A {x:u8; x:u16}', 'duplicate field'),
            ('struct A {} struct A {}', 'duplicate structure'),
            ('struct A {x:Missing}', 'unknown type'),
            ('struct A {x:A}', 'recursive'),
            ('struct A {x:B} struct B {x:A}', 'recursive'),
            ('struct A {} fn A()->u32{return 0}', 'distinct'),
            ('struct u32 {}', 'identifier'),
            ('struct A {x:u8 y:u8}', 'separator'),
            ('fn f(x:Missing)->u32{return 0}', 'unknown type'),
        ]
        for prefix, message in cases:
            with self.subTest(prefix=prefix), self.assertRaisesRegex(CompileError,message):
                compile_source(prefix+' fn main()->u32{return 0}')

    def test_nominal_types_fields_and_operations(self):
        prefix='struct A {x:u8} struct B {x:u8} '
        cases=[
            ('x:A=B(1); return 0','expected A'),
            ('x=A(); return 0','constructor arguments'),
            ('x=A(1,2); return 0','constructor arguments'),
            ('x=A(256); return 0','outside u8'),
            ('x=A(u16(1)); return 0','expected u8'),
            ('x=A(true); return 0','expected u8'),
            ('x=A(1); return u32(x.missing)','unknown field'),
            ('x=1; return x.missing','requires a structure'),
            ('x=A(1); y=move x.x; return 0','binding name'),
            ('x=A(1); y=x==x; return 0','scalar'),
            ('x=A(1); y=x+x; return 0','integer'),
            ('x=A(1); y=u32(x); return 0','integer'),
            ('x:Missing=1; return 0','unknown type'),
            ('var x=A(1); x=B(1); return 0','expected A'),
        ]
        for body,message in cases:
            with self.subTest(body=body),self.assertRaisesRegex(CompileError,message):
                compile_source(prefix+'fn main()->u32{'+body+'}')

    def test_forward_nested_types_and_semantic_ir(self):
        module=compile_source('''struct Box {point:Point, valid:bool,}
            fn wrap(p:Point)->Box{return Box(move p,true)}
            struct Point {x:i16; y:u64}
            fn main()->u32 {
                var box=wrap(Point(-32768,18446744073709551615))
                before=copy box
                box=Box(Point(0,0),false)
                if before.point.x == -32768 && before.valid {return 0}
                return 1
            }''')
        data=json.loads(dump(module))
        self.assertEqual(data['version'],16)
        self.assertEqual(data['type_properties']['Box'],{'copyable':True,'implicit_copy':True})
        self.assertEqual(module.structs['Box'].fields,[('point','Point'),('valid','bool')])
        ops=[op for fn in module for block in fn.blocks for op in block.operations]
        self.assertTrue(any(op.op=='struct.construct' and op.type=='Box' for op in ops))
        self.assertTrue(any(op.op=='struct.field' and op.field_name=='point' and op.type=='Point' for op in ops))
        output=llvm(module)
        self.assertIn('insertvalue',output)
        self.assertIn('extractvalue',output)
        self.assertNotRegex(output,r'\b(alloca|load|store|getelementptr|ptr|poison|undef)\b')

    def test_ownership_across_fields_calls_and_loops(self):
        prefix='struct A {x:u32} struct Pair {a:A; b:A} '
        for body in (
            'x=A(1); y=move x; return x.x',
            'x=A(1); y=Pair(move x,copy x); return 0',
            'var x=A(1); if false {y=move x} return x.x',
            'x=A(1); while true {y=move x}',
            'var x=A(1); while true {y=move x; continue} ',
        ):
            with self.subTest(body=body),self.assertRaisesRegex(CompileError,'use after move'):
                compile_source(prefix+'fn main()->u32{'+body+'}')
        for body in (
            'x=A(1); y=Pair(copy x,move x); return y.a.x',
            'x=A(1); y=(move x).x; return y',
            'var x=A(1); y=move x; x=A(2); return x.x+y.x',
            'var x=A(1); while true {y=move x; x=A(y.x+%1)}',
        ):
            with self.subTest(body=body):
                compile_source(prefix+'fn main()->u32{'+body+'}')


@unittest.skipUnless(shutil.which('clang'),'native tests require clang')
class StructureNativeTests(unittest.TestCase):
    build=test_loops.LoopNativeTests.build

    def test_runtime_aggregate_arguments_returns_and_loop_phis(self):
        source='''struct Point {x:u32; y:u32}
        struct State {point:Point; count:u32}
        fn advance(s:State)->State {
            return State(Point(s.point.x+1,s.point.y+2),s.count+1)
        }
        fn compute(n:u32)->u32 {
            var s=State(Point(n,n),0)
            snapshot=copy s
            while s.count<7 {
                s=advance(move s)
                if s.count==2 {continue}
                if s.count==5 {break}
            }
            if n%2==0 {s=State(Point(s.point.x+10,s.point.y),s.count)}
            return snapshot.point.x+s.point.x+s.point.y+s.count
        }
        fn main()->u32{return 0}'''
        harness='''#include <stdint.h>
        #include <stdlib.h>
        extern uint32_t liza_compute(uint32_t);
        int main(int argc,char **argv){if(argc!=3)return 2;
        return liza_compute(strtoul(argv[1],0,10))==strtoul(argv[2],0,10)?0:1;}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe=self.build(directory,source,opt,harness)
                for n in (0,1,2,7,1000,100000):
                    self.assertEqual(subprocess.run([str(exe),str(n),str(3*n+20+(10 if n%2==0 else 0))],timeout=5).returncode,0)

    def test_all_scalar_fields_and_nested_independence(self):
        source='''struct Scalars {a:i8; b:u8; c:i16; d:u16; e:i32; f:u32; g:i64; h:u64; flag:bool}
        struct Box {value:Scalars}
        fn identity(s:Box)->Box {return move s}
        fn main()->u32 {
            var a=Box(Scalars(-128,255,-32768,65535,-2147483648,4294967295,-9223372036854775808,18446744073709551615,true))
            var b=copy a
            c=b.value
            a=Box(Scalars(0,0,0,0,0,0,0,0,false))
            d=identity(move b)
            b=a
            if c.a != -128 || c.b != 255 || c.c != -32768 || c.d != 65535 {return 1}
            if c.e != -2147483648 || c.f != 4294967295 {return 2}
            if d.value.g != -9223372036854775808 || d.value.h != 18446744073709551615 {return 3}
            if !d.value.flag || a.value.flag || b.value.flag {return 4}
            return 0
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe=self.build(directory,source,opt)
                self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)

    def test_empty_values_recursion_and_projection_precedence(self):
        source='''struct Empty {}
        struct Counter {n:u32; marker:Empty}
        fn empty(e:Empty)->Empty{return copy e}
        fn count(c:Counter)->Counter {
            if c.n==0 {return move c}
            return count(Counter(c.n-1,empty(c.marker)))
        }
        fn main()->u32 {
            var c=Counter(3,Empty())
            before=copy c
            c=count(move c)
            if c.n!=0 || before.n!=3 {return 1}
            flag=~Counter(0,Empty()).n == 4294967295
            if !flag {return 2}
            return 0
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe=self.build(directory,source,opt)
                self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)

    def test_constructor_traps_and_unselected_branches(self):
        prefix='struct Pair {a:u8; b:u8} '
        cases=[
            'x:u8=255; unused=Pair(x+1,0); return 0',
            'x:u8=255; return u32(Pair(0,x+1).a)',
            'var p=Pair(255,0); q=move p; p=Pair(q.a+1,0); return 0',
        ]
        for opt in ('-O0','-O2'):
            for body in cases:
                with tempfile.TemporaryDirectory() as directory:
                    exe=self.build(directory,prefix+'fn main()->u32{'+body+'}',opt)
                    self.assertLess(subprocess.run([str(exe)],capture_output=True,timeout=5).returncode,0)
            with tempfile.TemporaryDirectory() as directory:
                source=prefix+'fn main()->u32{x:u8=255; if false {unused=Pair(x+1,0)} return 0}'
                exe=self.build(directory,source,opt)
                self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)

    def test_constructor_evaluates_left_to_right(self):
        source='''struct Pair {a:u32; b:u32}
        fn spin()->u32{while true {}}
        fn main()->u32{unused=Pair(spin(),1/0); return 0}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe=self.build(directory,source,opt)
                with self.assertRaises(subprocess.TimeoutExpired):
                    subprocess.run([str(exe)],capture_output=True,timeout=0.3)
