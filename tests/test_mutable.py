"""Local rebinding, lexical scopes and value-based branch joins."""
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


class MutableTypeTests(unittest.TestCase):
    def test_rejections(self):
        cases = [
            ('x=1; x=2', 'immutable'),
            ('var x=1; var x=2', 'duplicate'),
            ('var x=1; if true {var x=2}', 'duplicate'),
            ('x=1; if true {var x=2}', 'duplicate'),
            ('var x=1; x:u32=2', 'duplicate'),
            ('var x:u8=1; x=u16(2)', 'expected'),
            ('var x:u8=1; x=256', 'range'),
            ('var x:u8=1; x=true', 'expected'),
            ('var x=1; x=-1', 'range'),
            ('var x=x+1', 'unknown'),
            ('if true {var x=1} y=x', 'unknown'),
            ('if true {var x=1} else {y=x}', 'unknown'),
            ('if false {x=1; x=2}', 'immutable'),
            ('var x:u32', 'expected'),
            ('var x=1; x+=1', 'expected'),
            ('var x=1; x.field=2', 'expected'),
            ('var x=1; return x; x=2', 'unreachable'),
        ]
        for body, message in cases:
            with self.subTest(body=body), self.assertRaisesRegex(CompileError, message):
                compile_source('fn main()->u32{'+body+'; return 0}')
        for body in ('x=2; return x', 'var x=2; return x'):
            with self.subTest(body=body), self.assertRaises(CompileError):
                compile_source('fn f(x:u32)->u32{'+body+'} fn main()->u32{return 0}')

    def test_mutable_type_is_fixed_and_alias_is_snapshot(self):
        module = compile_source('fn main()->u32{var x:u8=1; old=x; x=2; return u32(old+x)}')
        operations = module[0].blocks[0].operations
        add = next(op for op in operations if op.op == 'add')
        self.assertEqual(add.type, 'u8')
        self.assertNotEqual(add.args[0], add.args[1])
        compile_source('fn main()->u32{if true {var a=1} else {var a=2} var a=3; return a}')

    def test_ssa_joins_use_only_continuing_predecessors(self):
        module = compile_source('''fn f(flag:bool)->u32 {
            var x=1
            if flag {x=2} else {x=3}
            return x
        }
        fn g(flag:bool)->u32 {
            var x=1
            if flag {x=2; return x} else {x=3}
            return x
        }
        fn h(flag:bool)->u32 {var x=1; if flag {x=x} return x}
        fn main()->u32{return 0}''')
        phis = [op for b in module[0].blocks for op in b.operations if op.op=='phi']
        self.assertEqual(len(phis), 1)
        self.assertEqual(len(phis[0].args), 2)
        self.assertEqual(len(set(phis[0].incoming_blocks)), 2)
        for fn in module[1:3]:
            self.assertFalse(any(op.op=='phi' for b in fn.blocks for op in b.operations))
        self.assertNotRegex(llvm(module), r'\b(alloca|load|store|getelementptr)\b')


@unittest.skipUnless(shutil.which('clang'), 'native tests require clang')
class MutableNativeTests(unittest.TestCase):
    def build(self, directory, source, opt, harness=None):
        path = Path(directory)
        ir, exe = path / 'module.ll', path / 'program'
        output = llvm(compile_source(source))
        self.assertNotRegex(output, r'\b(alloca|load|store|getelementptr|nsw|nuw|inbounds|exact)\b')
        if harness:
            output = output.replace('define i32 @main()', 'define i32 @test_entry()')
        ir.write_text(output)
        files = [str(ir)]
        if harness:
            c = path / 'harness.c'
            c.write_text(harness)
            files.append(str(c))
        result = subprocess.run(['clang','-Wno-override-module',opt,*files,'-o',str(exe)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return exe

    def test_runtime_branches_nested_and_early_return(self):
        source = '''fn choose(flag:u32, n:u32)->u32 {
            var x=n
            var y=10
            old=x
            var good=true
            if flag==0 {
                x=x+1
                if n<5 {y=x*2} else {y=3}
                good=false || (x>old && y>0)
            } else if flag==1 {
                y=x+20
                x=y/2
                if n==7 {return x+y}
            } else {
                var local=3
                local=local+1
                x=local
                good=false
            }
            if good {y=y+1}
            return x+y+old
        }
        fn main()->u32{return 0}'''
        harness = '''#include <stdint.h>
        #include <stdlib.h>
        extern uint32_t liza_choose(uint32_t,uint32_t);
        int main(int argc,char **argv) {
            if(argc!=4)return 2;
            return liza_choose(strtoul(argv[1],0,10),strtoul(argv[2],0,10))==strtoul(argv[3],0,10)?0:1;
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe = self.build(directory,source,opt,harness)
                for flag in (0,1,2):
                    for n in (0,1,4,5,7,20):
                        if flag==0:
                            x=n+1
                            y=2*x if n<5 else 3
                            expected=x+y+1+n
                        elif flag==1:
                            y=n+20
                            x=y//2
                            expected=x+y if n==7 else x+y+1+n
                        else:
                            expected=4+10+n
                        with self.subTest(opt=opt,flag=flag,n=n):
                            self.assertEqual(subprocess.run([str(exe),str(flag),str(n),str(expected)],capture_output=True,timeout=5).returncode,0)

    def test_scalars_single_arm_and_value_snapshots(self):
        source = '''fn main()->u32 {
            var x:u8=10
            y=x
            var copy=x
            x=x+1
            copy=copy+2
            if y!=10 || x!=11 || copy!=12 {return 1}
            if true {x=13}
            if x!=13 {return 2}
            if false {x=14}
            if x!=13 {return 3}
            var flag=false
            if true {flag=true && (u8(u32(x))==13)}
            if !flag {return 4}
            var wide:u64=18446744073709551615
            if flag {wide=wide-%1} else {wide=0}
            if wide!=18446744073709551614 {return 5}
            var signed:i64=-9223372036854775808
            if flag {signed=signed+1}
            if signed != -9223372036854775807 {return 6}
            if true {var local=1; local=2} else {var local=3}
            var local=4
            if local!=4 {return 7}
            return 0
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                exe = self.build(directory,source,opt)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=5).returncode,0)

    def test_traps_survive_overwrite_and_unselected_branches(self):
        bodies = [
            'var x:u8=255; x=x+1; x=0',
            'var x:u8=254; if true {x=x+1} x=x+1',
            'var x:u8=1; if true {x=u8(u32(300))} x=0',
            'var x:u32=0; if true {x=1/0} x=0',
            'var x:u8=1; x=x<<8; x=0',
        ]
        safe = 'var x:u8=255; if false {x=x+1} x=1'
        for opt in ('-O0','-O2'):
            for body in [safe,*bodies]:
                with self.subTest(opt=opt,body=body), tempfile.TemporaryDirectory() as directory:
                    exe=self.build(directory,'fn main()->u32{'+body+'; return 0}',opt)
                    code=subprocess.run([str(exe)],capture_output=True,timeout=5).returncode
                    self.assertEqual(code,0) if body==safe else self.assertLess(code,0)
