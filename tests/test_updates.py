"""Whole-value updates: sequencing, ownership, aggregate SSA and native traps."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm
import test_io


def compile_source(source):
    return lower(Parser(source).parse())


class UpdateTypes(unittest.TestCase):
    def test_rejected_updates(self):
        prefix = 'struct P {x:u32; data:[u8;2]} '
        cases = [
            ('p=P(1,[2,3]); p.x=2', 'requires var'),
            ('var p=P(1,[2,3]); p.x=true', 'expected u32'),
            ('var p=P(1,[2,3]); p.missing=1', 'unknown field'),
            ('var a=[1]; a.len=2', 'structure fields'),
            ('var a=[1]; a[true]=2', 'u32'),
            ('var a=[1]; a[i32(0)]=2', 'u32'),
            ('var a=[1]; var v=view a[0..1]; v[0]=2', 'owned array'),
            ('var a=[1]; v=view a[0..1]; a[0]=2', 'readonly view'),
            ('var a=[1]; if true {v=move a} a[0]=2', 'use after move'),
            ('var a=[1]; b=move a; a[0]=2', 'use after move'),
            ('var p=P(1,[2,3]); b=move p.x', 'binding name'),
            ('var p=P(1,[2,3]); p.x=take(move p)', 'owner during'),
            ('var a=[1]; a[index(move a)]=2', 'owner during'),
            ('var a=[1]; a[0]=first(view a[0..1])', 'readonly view'),
            ('var p.x=1', 'var declares'),
        ]
        helpers = ('fn take(p:P)->u32{return p.x} '
                   'fn index(a:[u32;1])->u32{return 0} '
                   'fn first(v:View<u32>)->u32{return v[0]} ')
        for body, message in cases:
            with self.subTest(body=body), self.assertRaisesRegex(CompileError, message):
                compile_source(prefix+helpers+'fn main()->u32{'+body+'; return 0}')

    def test_loans_end_at_scope_and_loop_move_availability(self):
        compile_source('''fn main()->u32{
            var a=[1]; var i=0
            while i<3 {
                if true {v=view a[0..1]; x=v[0]}
                a[0]=i
                i=i+1
                if i==1 {continue}
                if i==2 {break}
            }
            b=move a; a=[3]; a[0]=4
            return a[0]
        }''')
        with self.assertRaisesRegex(CompileError, 'use after move'):
            compile_source('fn main()->u32{var a=[1]; while true {a[0]=2; b=move a; continue}}')

    def test_resource_effects_in_update_operands(self):
        prefix = 'fn finish(f:File)->u32:io{r=file.close(move f); return 0} '
        compile_source(prefix+"""fn use(f:File)->u32:io {
            var a=[1]; a[finish(move f)]=2; return a[0]
        } fn main()->u32{return 0}""")
        with self.assertRaisesRegex(CompileError, 'resource must be closed'):
            compile_source(prefix+"""fn use(f:File)->u32:io {
                var a=[1]; a[0]=2; return a[0]
            } fn main()->u32{return 0}""")
        compile_source(prefix+"""fn use(f:File)->u32:io {
            var a=[1]; a[0]=finish(move f); return a[0]
        } fn main()->u32{return 0}""")

    def test_semantic_updates_and_phi(self):
        m=compile_source('''struct P{x:u32}
            fn f(i:u32)->u32 {var a=[P(1),P(2)]
                if i==0 {a[i].x=7} else {a[i].x=8}
                return a[i].x}
            fn main()->u32{return f(1)}''')
        ops=[op for f in m for b in f.blocks for op in b.operations]
        self.assertTrue(any(op.op=='struct.update' for op in ops))
        self.assertTrue(any(op.op=='array.update' and op.may_trap for op in ops))
        self.assertTrue(any(op.op=='phi' and op.type=='[P;2]' for op in ops))
        self.assertNotRegex(llvm(m),r'\b(nsw|nuw|inbounds)\b')


@unittest.skipUnless(shutil.which('clang'),'native tests require clang')
class UpdateNative(unittest.TestCase):
    build = test_io.ConsoleNative.build

    def test_nested_updates_copies_loops_and_views(self):
        source='''struct P {x:u32; bytes:[u8;2]}
            struct Box {items:[P;2]}
            fn run(n:u32)->u32 {
                var box=Box([P(1,[2,3]),P(4,[5,6])])
                snapshot=copy box
                var i=0
                while i<n {
                    box.items[i].bytes[1]=u8(i+10)
                    box.items[i].x=box.items[i].x+1
                    i=i+1
                    if i==1 {continue}
                    break
                }
                if snapshot.items[0].bytes[1]!=3 || snapshot.items[1].x!=4 {return 1}
                if box.items[0].bytes[1]!=10 || box.items[1].bytes[1]!=11 {return 2}
                var a=box.items
                if true {v=view a[0..2]; if v[1].x!=5 {return 3}}
                a[1]=P(99,[8,9])
                if box.items[1].x!=5 || a[1].x!=99 {return 4}
                if true {
                    v=view a[0..2]
                    var independent=copy a
                    independent[1].x=77
                    if v[1].x!=99 || independent[1].x!=77 {return 6}
                }
                old=move a; a=[P(0,[0,0]),P(0,[0,0])]; a[0].x=7
                if old[1].x!=99 || a[0].x!=7 {return 5}
                var matrix=[[1,2],[3,4]]
                matrix[1][0]=8
                return matrix[0][0]+matrix[1][0]-9
            }
            fn main()->u32{return run(2)}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=5).returncode,0)

    def test_evaluation_order_and_traps(self):
        helpers='''fn index()->u32:io {r=console.write("I"); return 0}
            fn rhs()->u32:io {r=console.write("R"); return 9}
            fn inner()->u32:io {r=console.write("J"); return 0}
            fn flag()->bool:io {r=console.write("B"); return true}'''
        cases=[
            ('var a=[false]; a[index()]=true && flag(); if a[0] {return 0} return 1',b'IB',False),
            ('var a=[true]; a[index()]=false && flag(); if a[0] {return 1} return 0',b'I',False),
            ('var a=[[1]]; a[index()][inner()]=rhs(); return a[0][0]-9',b'IJR',False),
            ('var a:[u32;0]=[]; a[index()]=rhs(); return 0',b'I',True),
            ('var a=[[1]]; a[1][inner()]=rhs(); return 0',b'',True),
            ('var a=[1]; a[4294967295]=rhs(); return 0',b'',True),
            ('var a=[1]; if false {a[1]=rhs()} return 0',b'',False),
            ('var a:[u8;1]=[255]; a[0]=a[0]+1; return 0',b'',True),
        ]
        for opt in ('-O0','-O2'):
            for body, output, trap in cases:
                with self.subTest(opt=opt,body=body), tempfile.TemporaryDirectory() as d:
                    exe=self.build(d,helpers+'fn main()->u32:io{'+body+'}',opt)
                    r=subprocess.run([str(exe)],capture_output=True,timeout=5)
                    self.assertEqual(r.stdout,output)
                    if trap:
                        if sys.platform=='win32':
                            self.assertIn(r.returncode & 0xffffffff,(0x80000003,0xc000001d))
                        else:
                            self.assertLess(r.returncode,0)
                    else:
                        self.assertEqual(r.returncode,0,r.stderr)

    def test_runtime_index_against_reference(self):
        source='''fn update(i:u32,v:u32)->u32 {
            var a=[10,20,30,40]; before=copy a
            a[i]=v
            if before[0]!=10 || before[1]!=20 || before[2]!=30 || before[3]!=40 {return 1}
            var j=0
            while j<4 {
                if j==i {if a[j]!=v {return 2}}
                else {if a[j]!=before[j] {return 3}}
                j=j+1
            }
            return 0
        } fn main()->u32{return 0}'''
        harness='''#include <stdint.h>
            #include <stdlib.h>
            extern uint32_t liza_update(uint32_t,uint32_t);
            int main(int argc,char **argv){return liza_update((uint32_t)strtoul(argv[1],0,10),(uint32_t)strtoul(argv[2],0,10));}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d); ir=root/'test.ll'; c=root/'test.c'; exe=root/('test.exe' if sys.platform=='win32' else 'test')
                ir.write_text(llvm(compile_source(source)).replace('define i32 @main()', 'define i32 @test_entry()'))
                c.write_text(harness)
                r=subprocess.run(['clang','-Wno-override-module',opt,str(ir),str(c),'-o',str(exe)],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)
                for i in range(4):
                    for v in (0,17,4294967295):
                        self.assertEqual(subprocess.run([str(exe),str(i),str(v)],capture_output=True,timeout=5).returncode,0)
