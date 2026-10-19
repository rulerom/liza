from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm


def compile_source(s):
    return lower(Parser(s).parse())


def program(body):
    return 'fn main()->u32{'+body+'}'


class ArrayTypes(unittest.TestCase):
    def test_types_literals_and_rejections(self):
        good = ['a:[u8;0]=[]; return 0', 'a=[[1,2],[3,4]]; return a[1][0]',
                'x:u8=[1,2][0]; return u32(x)', 'a=[u8(1),2]; return u32(a[0])']
        for body in good:
            compile_source(program(body))
        bad = ['a=[]; return 0', 'a:[u8;2]=[1]; return 0', 'a=[1,true]; return 0',
               'a:[u8;1]=[256]; return 0', 'a:[u8;4294967296]=[]; return 0',
               'a:[u8;-1]=[]; return 0', 'a:[u8;1+1]=[1,2]; return 0',
               'a=[1]; return a[i32(0)]', 'a=[1]; return a[u64(0)]',
               'a=[1]; a[0]=2; return 0', 'a=[1]; x=move a[0]; return 0',
               'a=[1]; v=view a[0..1]; w=view v[0..1]; return 0',
               'v=view [1][0..1]; return 0', 'a=[1]; v=view a[0..1]; b=[v]; return 0']
        for body in bad:
            with self.subTest(body=body), self.assertRaises(CompileError):
                compile_source(program(body))
        for s in ['struct S {v:View<u8>} ', 'struct S {v:[View<u8>;0]} ',
                  'struct S {v:[S;0]} ', 'fn f(v:View<u8>)->View<u8>{return v} ']:
            with self.assertRaises(CompileError):
                compile_source(s+program('return 0'))

    def test_borrow_prohibitions_and_aliases(self):
        bad = [
            'var a=[1,2]; v=view a[0..1]; x=move a; return 0',
            'var a=[1,2]; v=view a[0..1]; a=[3,4]; return 0',
            'var a=[1,2]; v=view a[0..1]; w=move v; a=[3,4]; return 0',
            'var a=[1,2]; var b=[3,4]; var v=view a[0..1]; v=view b[0..1]; a=[0,0]; return 0',
            'a=[1]; var v=view a[0..1]; if true {b=[2]; v=view b[0..1]} return v[0]',
            'a=[1]; var v=view a[0..1]; if true {b=[2]; w=view b[0..1]; v=copy w} return v[0]',
            'var a=[1]; v=view a[0..1]; while true {a=[2]; break} return 0',
            'var a=[1]; v=view a[0..1]; if false {x=move a} return 0',
        ]
        for body in bad:
            with self.subTest(body=body),self.assertRaises(CompileError):
                compile_source(program(body))
        # A range endpoint cannot move the reserved owner.
        with self.assertRaisesRegex(CompileError,'readonly'):
            compile_source('fn consume(a:[u32;1])->u32{return 0} '+program('a=[1]; v=view a[consume(move a)..1]; return 0'))

    def test_scope_release_cfg_and_independent_copies(self):
        good = [
            'var a=[1,2]; if true {v=view a[0..1]; x=v[0]} b=move a; return b[0]',
            'var a=[1,2]; v=view a[0..1]; var b=copy a; b=[3,4]; c=move b; return v[0]+c[0]',
            'var a=[1]; while false {v=view a[0..1]; continue} b=move a; return b[0]',
            'var a=[1]; while true {v=view a[0..1]; break} a=[2]; return a[0]',
            'var a=[1]; while true {if true {v=view a[0..1]} a=[2]; break} return a[0]',
            'a=[1]; v=view a[0..1]; w=copy v; return w[0]',
            'a=[1]; var v=view a[0..1]; if true {v=copy v} return v[0]',
        ]
        for body in good:
            with self.subTest(body=body):
                compile_source(program(body))

    def test_ir_bounds_and_owner_links(self):
        m=compile_source('fn first(v:View<u8>)->u8{return v[0]} '+program('a:[u8;2]=[1,2]; v=view a[0..2]; return u32(first(v))+u32(a[1])'))
        ops=[op for f in m for b in f.blocks for op in b.operations]
        accesses=[op for op in ops if op.op in ('array.read','view.read','view.create')]
        self.assertEqual(len(accesses),3)
        self.assertTrue(all(op.may_trap and op.bounds_policy=='trap' for op in accesses))
        create=next(op for op in accesses if op.op=='view.create')
        self.assertEqual(create.owner_binding,'a')
        self.assertEqual(create.source_type,'[u8;2]')
        self.assertTrue(all(f.may_trap for f in m))
        self.assertNotRegex(llvm(m),r'\b(nsw|nuw|inbounds|exact|ptrtoint)\b')


@unittest.skipUnless(shutil.which('clang'),'native tests require clang')
class ArrayNative(unittest.TestCase):
    def build(self,directory,source,opt,harness=None):
        root=Path(directory); ir=root/'module.ll'; exe=root/'program'
        output=llvm(compile_source(source))
        self.assertNotRegex(output,r'\b(nsw|nuw|inbounds|exact|ptrtoint)\b')
        if harness:
            output=output.replace('define i32 @main()', 'define i32 @test_entry()')
        ir.write_text(output)
        files=[str(ir)]
        if harness:
            c=root/'harness.c'; c.write_text(harness); files.append(str(c))
        result=subprocess.run(['clang','-Wno-override-module',opt,*files,'-o',str(exe)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return exe

    def test_dynamic_array_and_view_indices(self):
        source='''fn read(v:View<u32>, i:u32)->u32{return v[i]}
        fn compute(n:u32,i:u32)->u32 {
            a=[n,n+1,n+2,n+3]
            v=view a[1..4]
            return a[i]+read(v,i)
        }
        fn main()->u32{return 0}'''
        harness='''#include <stdint.h>
        #include <stdlib.h>
        extern uint32_t liza_compute(uint32_t,uint32_t);
        int main(int c,char**v){if(c!=3)return 2;uint32_t n=strtoul(v[1],0,10),i=strtoul(v[2],0,10);
        return liza_compute(n,i)==2*n+2*i+1?0:1;}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt,harness)
                for n in (0,7,100000):
                    for i in (0,1,2,3,4,4294967295):
                        r=subprocess.run([str(exe),str(n),str(i)],capture_output=True,timeout=5).returncode
                        self.assertEqual(r,0) if i<3 else self.assertLess(r,0)

    def test_dynamic_ranges_empty_and_boundaries(self):
        source='''fn compute(start:u32,end:u32,i:u32)->u32 {
            a=[10,20,30,40]
            v=view a[start..end]
            return v[i]
        } fn main()->u32{return 0}'''
        harness='''#include <stdint.h>
        #include <stdlib.h>
        extern uint32_t liza_compute(uint32_t,uint32_t,uint32_t);
        int main(int c,char**v){if(c!=5)return 2;
        return liza_compute(strtoul(v[1],0,10),strtoul(v[2],0,10),strtoul(v[3],0,10))==strtoul(v[4],0,10)?0:1;}'''
        cases=[(0,4,3,40),(1,3,0,20),(1,3,1,30),(4,4,0,None),(0,0,0,None),
               (2,1,0,None),(0,5,0,None),(1,3,2,None),(4294967295,0,0,None)]
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt,harness)
                for start,end,i,expected in cases:
                    r=subprocess.run([str(exe),str(start),str(end),str(i),str(expected or 0)],capture_output=True,timeout=5).returncode
                    self.assertEqual(r,0) if expected is not None else self.assertLess(r,0)

    def test_nested_values_phi_views_and_copy(self):
        source='''struct Row {data:[u8;2]}
        fn identity(a:[Row;2])->[Row;2]{return move a}
        fn read(v:View<Row>)->u8{return v[1].data[0]}
        fn main()->u32 {
            var a=[Row([1,2]),Row([3,4])]
            snapshot=copy a
            var n=0
            while n<4 {
                if n==2 {a=[Row([5,6]),Row([7,8])]}
                if true {v=view a[0..2]; x=read(v); if x==0 {return 1}}
                a=identity(move a)
                n=n+1
                if n==2 {continue}
            }
            v=view a[0..2]
            var b=copy a
            b=[Row([9,10]),Row([11,12])]
            if read(v)!=7 || snapshot[1].data[0]!=3 || b[1].data[0]!=11 {return 2}
            e:[u8;0]=[]
            empty=view e[0..0]
            return 0
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)

    def test_traps_unused_reads_and_dead_branches(self):
        bad=['a=[1]; unused=a[1]; return 0', 'a:[u8;0]=[]; unused=a[0]; return 0',
             'a=[1]; unused=view a[1..0]; return 0',
             'a=[1]; v=view a[1..1]; unused=v[0]; return 0',
             'a=[1]; return [a[1],2][1]']
        for opt in ('-O0','-O2'):
            for body in bad:
                with tempfile.TemporaryDirectory() as d:
                    exe=self.build(d,program(body),opt)
                    self.assertLess(subprocess.run([str(exe)],capture_output=True,timeout=5).returncode,0)
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,program('a:[u8;0]=[]; if false {unused=a[0]} return 0'),opt)
                self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)

    def test_view_reassignment_phi_and_lexical_release(self):
        body='''a=[1,2]; b=[3,4]; var v=view a[0..2]
        var n=0
        while n<3 {v=view b[0..2]; n=n+1; continue}
        if v[0]!=3 {return 1}
        var c=[5,6]
        while true {w=view c[0..2]; break}
        c=[7,8]
        return c[0]-7'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,program(body),opt)
                self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)

    def test_rtp_runtime_and_no_copy_cost(self):
        from tools.check_view_cost import inspect, HARNESS
        with tempfile.TemporaryDirectory() as directory:
            ir, report = inspect(directory)
            self.assertIn('runtime loads',report)
            root=Path(directory); c=root/'runtime.c'; c.write_text(HARNESS)
            for opt in ('-O0','-O2'):
                exe=root/'runtime'
                subprocess.run(['clang','-Wno-override-module',opt,str(ir),str(c),'-o',str(exe)],check=True,capture_output=True)
                for data in ((128,96,18,52),(255,255,255,255),(0,0,0,0),(64,127,1,2)):
                    for length in (0,1,2,3,4):
                        result=subprocess.run([str(exe),*map(str,data),str(length)],capture_output=True,timeout=5)
                        self.assertEqual(result.returncode,0) if length==4 else self.assertLess(result.returncode,0)
