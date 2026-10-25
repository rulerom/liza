"""Exclusive whole-value callee variants: snapshots and mandatory traps."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm
from liza import storage
from tools.check_table_cost import function_body

LIBRARY='''
struct State {data:[u32;128];marker:u32}
fn initial()->State {return State([7;128],0)}
fn leaf(s:State,i:u32,value:u32)->State {
 var n=s;n.data[i]=value;n.marker=value;return n
}
fn chain(s:State,i:u32,value:u32)->State {
 first=leaf(s,i,value);return leaf(first,i,value+1)
}
fn observed(s:State)->State {
 old=copy s;var n=s;n.marker=1
 if old.marker==0 {return n}
 return old
}
fn checked(s:State,value:u8)->State {
 var n=s;n.marker=u32(value+1);n.marker=0;return n
}
fn recur(s:State,n:u32)->State {
 if n==0 {return s}
 return recur(s,n-1)
}
fn unique(i:u32)->u32 {n=chain(initial(),i,9);return n.data[i]-10}
fn snapshot(i:u32)->u32 {
 original=initial();old=copy original;n=chain(original,i,9)
 if old.marker!=0 || old.data[i]!=7 || n.marker!=10 || n.data[i]!=10 {return 1}
 return 0
}
fn view_observer(i:u32)->u32 {
 original=initial();array=original.data;v=view array[0..128]
 n=chain(original,i,9)
 if v[i]!=7 || n.data[i]!=10 {return 2}
 return 0
}
fn retained_inside()->u32 {n=observed(initial());return n.marker-1}
fn trap(value:u8)->u32 {n=checked(initial(),value);return n.marker}
fn main()->u32 {return 0}
'''


def emit(source=LIBRARY):return llvm(lower(Parser(source).parse()))


class DirectStorageProofs(unittest.TestCase):
    def test_only_proven_dead_local_values_select_owned_calls(self):
        ir=emit()
        self.assertIn('@liza___liza_owned_chain',function_body(ir,'unique'))
        for name in ('snapshot','view_observer'):
            self.assertNotIn('@liza___liza_owned_chain',function_body(ir,name))
        self.assertNotIn('define void @liza___liza_owned_observed',ir)
        self.assertNotIn('define void @liza___liza_owned_recur',ir)
        self.assertIn('@liza___liza_owned_leaf',function_body(ir,'__liza_owned_chain'))
        self.assertNotRegex(function_body(ir,'__liza_owned_leaf'),r'@llvm.mem(?:cpy|move)')
        self.assertIn('@llvm.trap()',function_body(ir,'__liza_owned_leaf'))

    def test_discovery_does_not_depend_on_function_order(self):
        module=lower(Parser(LIBRARY).parse())
        module.reverse()
        ir=llvm(module)
        self.assertIn('@liza___liza_owned_chain',function_body(ir,'unique'))

    def test_public_parameter_is_never_exclusive(self):
        source=LIBRARY+'fn public_call(s:State,i:u32)->State{return leaf(s,i,4)}'
        ir=emit(source)
        self.assertNotIn('@liza___liza_owned_leaf',function_body(ir,'public_call'))
        self.assertIn('@liza___liza_owned_leaf',function_body(ir,'__liza_owned_public_call'))


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class DirectStorageNative(unittest.TestCase):
    def build(self,root,ir,opt,entry,ctype='uint32_t'):
        root=Path(root);source=root/'test.ll';source.write_text(ir.replace('define i32 @main()', 'define i32 @unused_main()'))
        argument='' if entry=='retained_inside' else '('+ctype+')strtoul(argv[1],0,10)'
        declaration='void' if entry=='retained_inside' else ctype
        driver=root/'driver.c';driver.write_text('#include <stdint.h>\n#include <stdlib.h>\nextern uint32_t liza_'+entry+'('+declaration+');\nint main(int argc,char**argv){return liza_'+entry+'('+argument+');}')
        exe=root/('test.exe' if sys.platform=='win32' else 'test')
        r=subprocess.run(['clang','-Wno-override-module',opt,str(source),str(driver),'-o',str(exe)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        return exe

    def test_native_snapshots_views_and_unique_updates(self):
        ir=emit()
        for opt in ('-O0','-O2'):
            for name in ('unique','snapshot','view_observer','retained_inside'):
                with self.subTest(opt=opt,name=name),tempfile.TemporaryDirectory() as folder:
                    exe=self.build(folder,ir,opt,name)
                    for i in (0,64,127):
                        self.assertEqual(subprocess.run([str(exe),str(i)],capture_output=True,timeout=10).returncode,0)

    def test_bounds_and_overflow_are_still_traps(self):
        ir=emit()
        for opt in ('-O0','-O2'):
            for name,value,ctype in (('unique',128,'uint32_t'),('unique',4294967295,'uint32_t'),('trap',255,'uint8_t')):
                with self.subTest(opt=opt,name=name,value=value),tempfile.TemporaryDirectory() as folder:
                    exe=self.build(folder,ir,opt,name,ctype)
                    r=subprocess.run([str(exe),str(value)],capture_output=True,timeout=10)
                    if sys.platform=='win32':self.assertIn(r.returncode & 0xffffffff,(0x80000003,0xc000001d))
                    else:self.assertLess(r.returncode,0)

    def test_mutant_liveness_replays_snapshot_corruption(self):
        real=storage.liveness
        with patch.object(storage,'liveness',side_effect=lambda fn:{k:set() for k in real(fn)}):
            mutant=emit()
        self.assertIn('@liza___liza_owned_chain',function_body(mutant,'snapshot'))
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as folder:
                exe=self.build(folder,mutant,opt,'snapshot')
                self.assertEqual(subprocess.run([str(exe),'3'],capture_output=True,timeout=10).returncode,1,
                                 'mutant must corrupt snapshot at input i=3')

    def test_mutant_overflow_guard_replays_missing_trap(self):
        original=emit()
        mutant,count=re.subn(r'br i1 %v[0-9]+_overflow,', 'br i1 false,', original)
        self.assertGreater(count,0)
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as folder:
                exe=self.build(folder,mutant,opt,'trap','uint8_t')
                self.assertEqual(subprocess.run([str(exe),'255'],capture_output=True,timeout=10).returncode,0,
                                 'mutant must return normally despite u8 overflow')
