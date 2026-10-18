"""Structured loops: SSA edges, runtime values, traps and nontermination."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm


def compile_source(source):
    return lower(Parser(source).parse())


class LoopTypeTests(unittest.TestCase):
    def test_invalid_control_and_scopes(self):
        cases = [
            ('break', 'outside'), ('continue', 'outside'),
            ('if false {break}', 'outside'),
            ('while 1 {}', 'bool'),
            ('var x=0; while false {var x=1}', 'duplicate'),
            ('while false {var x=1} return x', 'unknown'),
            ('while false {x=x+1}', 'unknown'),
            ('x=0; while false {x=1}', 'immutable'),
            ('var x:u8=0; while false {x=u16(1)}', 'expected'),
            ('while true {break; x=1}', 'unreachable'),
            ('while true {continue; x=1}', 'unreachable'),
            ('while true {} return 0', 'unreachable'),
            ('while true {while true {break}} return 0', 'unreachable'),
            ('while false {break 1}', 'expected'),
        ]
        for body, message in cases:
            with self.subTest(body=body), self.assertRaisesRegex(CompileError, message):
                compile_source('fn main()->u32{'+body+'; return 0}')
        for body in ('while false {}', 'while true {break}', 'while true {if false {break}}'):
            with self.subTest(body=body), self.assertRaisesRegex(CompileError, 'must return'):
                compile_source('fn main()->u32{'+body+'}')
        compile_source('fn main()->u32{while true {}}')
        compile_source('fn main()->u32{while true {return 0}}')

    def test_ssa_predecessors_and_divergence_contract(self):
        module = compile_source('''fn main()->u32 {
            var i=0
            var sum=0
            while i<10 && sum<100 {
                i=i+1
                if i==2 {continue}
                if i==8 {break}
                sum=sum+i
            }
            return sum
        }''')
        fn=module[0]
        self.assertEqual(fn.termination_contract,'may_diverge')
        predecessors={b.name:set() for b in fn.blocks}
        for block in fn.blocks:
            term=block.terminator
            targets=term.args[1:] if term.op=='branch' else term.args if term.op=='jump' else []
            for target in targets:
                predecessors[target].add(block.name)
        phis=[]
        for block in fn.blocks:
            for op in block.operations:
                if op.op=='phi':
                    phis.append(op)
                    self.assertEqual(set(op.incoming_blocks),predecessors[block.name])
                    self.assertEqual(len(op.args),len(op.incoming_blocks))
        self.assertGreaterEqual(len(phis),4)
        self.assertTrue(any(len(op.args)==3 for op in phis))
        self.assertNotRegex(llvm(module),r'\b(alloca|load|store|getelementptr|mustprogress|willreturn)\b')


@unittest.skipUnless(shutil.which('clang'),'native tests require clang')
class LoopNativeTests(unittest.TestCase):
    def build(self,directory,source,opt,harness=None):
        path=Path(directory)
        ir,exe=path/'module.ll',path/'program'
        output=llvm(compile_source(source))
        self.assertNotRegex(output,r'\b(alloca|load|store|getelementptr|mustprogress|willreturn|nsw|nuw|inbounds|exact)\b')
        if harness:
            output=output.replace('define i32 @main()','define i32 @test_entry()')
        ir.write_text(output)
        files=[str(ir)]
        if harness:
            c=path/'harness.c'; c.write_text(harness); files.append(str(c))
        result=subprocess.run(['clang','-Wno-override-module',opt,*files,'-o',str(exe)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return exe

    def test_runtime_nested_loops_break_continue_return(self):
        source='''fn compute(n:u32)->u32 {
            var i=0
            var total=0
            while i<n {
                i=i+1
                if i%2==0 {continue}
                var j=0
                while j<i {
                    j=j+1
                    if j==2 {continue}
                    if j==5 {break}
                    total=total+i+j
                    if total>120 {return total}
                }
                if i>8 {break}
            }
            return total+i
        }
        fn main()->u32{return 0}'''
        harness='''#include <stdint.h>
        #include <stdlib.h>
        extern uint32_t liza_compute(uint32_t);
        int main(int argc,char **argv){if(argc!=3)return 2;
        return liza_compute(strtoul(argv[1],0,10))==strtoul(argv[2],0,10)?0:1;}'''
        def expected(n):
            i,total=0,0
            while i<n:
                i+=1
                if i%2==0: continue
                j=0
                while j<i:
                    j+=1
                    if j==2: continue
                    if j==5: break
                    total+=i+j
                    if total>120: return total
                if i>8: break
            return total+i
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe=self.build(directory,source,opt,harness)
                for n in range(21):
                    with self.subTest(opt=opt,n=n):
                        self.assertEqual(subprocess.run([str(exe),str(n),str(expected(n))],capture_output=True,timeout=5).returncode,0)

    def test_zero_iterations_multiple_values_and_condition(self):
        source='''fn main()->u32 {
            var x:u8=254
            while x<255 {x=x+1}
            if x!=255 {return 1}
            while false {x=x+1}
            var a:u64=1
            var b:u64=1
            var n=0
            while n<10 {
                old=a
                a=b
                b=old+b
                n=n+1
            }
            if a!=89 || b!=144 {return 2}
            var flag=true
            while flag {flag=false; continue}
            if flag {return 3}
            var v:i8=-3
            while v<0 {v=v+1}
            if v!=0 {return 4}
            var count=0
            while count<3 && 10/(3-count)>0 {count=count+1; continue}
            if count!=3 {return 5}
            while true {x=42; break}
            if x!=42 {return 6}
            while false {}
            while true {if flag {continue} else {break}}
            return 0
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe=self.build(directory,source,opt)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=5).returncode,0)

    def test_traps_inside_condition_and_after_loops(self):
        cases=[
            'var x:u8=254; while x<255 {x=x+1} x=x+1',
            'var x:u8=254; while true {x=x+1}',
            'var n=0; while 1/(1-n)>0 {n=n+1; continue}',
            'var x:u8=255; while true {x=x+1; break}',
            'var x:u8=1; while true {x=u8(u32(300)); break}',
        ]
        for opt in ('-O0','-O2'):
            for body in cases:
                # An unconditional infinite loop needs no following return.
                end='' if body.endswith('while true {x=x+1}') else '; return 0'
                with self.subTest(opt=opt,body=body),tempfile.TemporaryDirectory() as directory:
                    exe=self.build(directory,'fn main()->u32{'+body+end+'}',opt)
                    self.assertLess(subprocess.run([str(exe)],capture_output=True,timeout=5).returncode,0)

    def test_infinite_execution_is_preserved(self):
        sources=[
            'fn main()->u32{while true {}}',
            'fn spin()->u32{while true {continue}} fn main()->u32{unused=spin(); return 0}',
            'fn main()->u32{var x:u8=0; while true {x=x+%1}}',
            'fn main()->u32{var b=true; while b {} return 1/0}',
        ]
        for opt in ('-O0','-O2'):
            for source in sources:
                with self.subTest(opt=opt,source=source),tempfile.TemporaryDirectory() as directory:
                    exe=self.build(directory,source,opt)
                    # A bounded regression check, not a proof of nontermination.
                    with self.assertRaises(subprocess.TimeoutExpired):
                        subprocess.run([str(exe)],capture_output=True,timeout=0.3)
