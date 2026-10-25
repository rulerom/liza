"""M0 storage identity, call-scoped exclusivity and observable writes."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm
from tools.check_table_cost import function_body


def compile_ir(source):
    return lower(Parser(source).parse())


BASE = '''
struct Small {n:u32}
struct Large {a:[u32;128];n:u32}
fn inc(borrow mut s:Small)->u32 {s.n=s.n+1;return s.n}
fn get(borrow s:Small)->u32 {return s.n}
fn capacity(borrow s:Large)->u32 {return s.a.len}
fn take(s:Small)->u32 {return s.n}
fn set(borrow mut s:Large,i:u32)->u32 {s.a[i]=s.a[i]+1;s.n=s.n+1;return 0}
fn twice(borrow mut s:Small)->u32 {
 before=get(s);x=inc(borrow mut s);after=get(s)
 if after!=before+1 {return 1}
 y=inc(borrow mut s);return 0
}
fn pair(borrow mut a:Small,borrow mut b:Small)->u32 {a.n=a.n+1;b.n=b.n+2;return 0}
fn mixed(borrow a:Small,borrow mut b:Small)->u32 {b.n=a.n;return 0}
fn later(borrow mut a:Small,b:u32)->u32 {a.n=b;return 0}
'''


class MutableBorrowChecking(unittest.TestCase):
    def reject(self, source, message):
        with self.assertRaisesRegex(CompileError, message): compile_ir(BASE+source)

    def test_explicit_mutable_argument_and_named_var(self):
        for body in ('var s=Small(1);x=inc(s)', 's=Small(1);x=inc(borrow mut s)'):
            self.reject('fn main()->u32 {'+body+';return 0}', 'mutable')
        self.reject('fn main()->u32 {var s=Small(1);x=borrow mut s;return 0}', 'only allowed')
        self.reject('fn main()->u32 {var s=Small(1);x=take(borrow mut s);return 0}', 'only allowed')

    def test_conflicting_arguments_and_evaluation_order(self):
        for call in ('pair(borrow mut s,borrow mut s)', 'mixed(s,borrow mut s)',
                     'later(borrow mut s,s.n)', 'later(borrow mut s,inc(borrow mut s))',
                     'later(borrow mut s,get(s))', 'later(borrow mut s,take(move s))'):
            with self.subTest(call=call):
                self.reject('fn main()->u32 {var s=Small(1);x='+call+';return 0}', 'borrow')

    def test_readonly_cannot_be_upgraded_or_rebound(self):
        self.reject('fn bad(borrow s:Small)->u32 {return inc(borrow mut s)} fn main()->u32{return 0}', 'mutable')
        self.reject('fn bad(borrow s:Small)->u32 {s.n=2;return 0} fn main()->u32{return 0}', 'immutable|readonly')
        self.reject('fn bad(borrow mut s:Small)->Small {return move s} fn main()->u32{return 0}', 'cannot move')

    def test_types_and_no_escape(self):
        for declaration in ('fn bad(borrow mut x:u32)->u32{return 0}',
                            'struct V {v:View<u8>} fn bad(borrow mut x:V)->u32{return 0}'):
            self.reject(declaration+' fn main()->u32{return 0}', 'structure|View|view')
        self.reject('fn bad(borrow mut s:Small)->Small{return borrow mut s} fn main()->u32{return 0}', 'only allowed')

    def test_mutable_mode_and_direct_storage_ir(self):
        module=compile_ir(BASE+'fn main()->u32{var s=Small(0);x=twice(borrow mut s);return s.n-2}')
        inc=next(f for f in module if f.name=='inc')
        self.assertEqual(inc.params[0]['mode'],'mutable')
        self.assertEqual(inc.effect_contract,'pure')
        self.assertIn('storage.write',inc.storage_contract['effects'])
        self.assertEqual(inc.storage_contract['mutable_parameters'],['s'])
        self.assertIn('storage.write',[o.op for b in inc.blocks for o in b.operations])
        ir=llvm(module)
        self.assertIn('define i32 @liza_inc(ptr %p0)',ir)
        self.assertNotRegex(function_body(ir,'inc'),r'alloca|memcpy|memmove|insertvalue')
        self.assertIn('store i32',function_body(ir,'inc'))
        self.assertNotIn('__liza_owned_inc',ir)
        for name in ('set', 'capacity'):
            self.assertNotRegex(function_body(ir,name),r'alloca|memcpy|memmove|insertvalue')

    def test_readonly_generic_reborrow(self):
        src='''struct Box<T> {value:T}
fn observe<T>(borrow s:Box<T>)->T {return s.value}
fn update<T>(borrow mut s:Box<T>,value:T)->T {old=observe(s);s.value=value;return old}
fn main()->u32 {var s=Box<u32>(7);old=update(borrow mut s,9);return old-7+s.value-9}'''
        llvm(compile_ir(src))


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class MutableBorrowNative(unittest.TestCase):
    def run_source(self, source, expect_trap=False, mutate=None, expected_exit=0):
        text=llvm(compile_ir(source))
        if mutate: text=mutate(text)
        for opt in ('-O0','-O2'):
            with self.subTest(opt=opt), tempfile.TemporaryDirectory() as folder:
                ll=Path(folder)/'test.ll';ll.write_text(text)
                exe=Path(folder)/'test.exe'
                r=subprocess.run(['clang','-Wno-override-module',opt,str(ll),'-o',str(exe)],capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr)
                r=subprocess.run([str(exe)],capture_output=True,timeout=10)
                if expect_trap:
                    if sys.platform=='win32':self.assertIn(r.returncode & 0xffffffff,(0x80000003,0xc000001d))
                    else:self.assertLess(r.returncode,0)
                else:self.assertEqual(r.returncode,expected_exit,r.stderr)

    def test_snapshots_small_large_nested_calls_and_loops(self):
        self.run_source(BASE+'''fn main()->u32 {
 var s=Small(1);first=copy s;second=copy s;x=twice(borrow mut s)
 if first.n!=1 || second.n!=1 || s.n!=3 {return 1}
 var big=Large([7;128],0);old=copy big;var i:u32=0
 while i<128 {step=set(borrow mut big,i);i=i+1}
 if old.a[127]!=7 || big.a[127]!=8 || big.n!=128 {return 2}
 var other=Small(10);done=pair(borrow mut s,borrow mut other)
 if s.n!=4 || other.n!=12 {return 3}
 // Rebinding preserves address identity for subsequent calls.
 s=Small(20);again=inc(borrow mut s)
 if s.n!=21 {return 4}
 return 0
}''')

    def test_branch_continue_break_and_snapshot_at_join(self):
        self.run_source(BASE+'''fn main()->u32 {
 var s=Small(0);var i:u32=0
 while i<5 {
  i=i+1
  if i==2 {continue}
  if i==5 {break}
  x=inc(borrow mut s)
 }
 old=copy s
 if s.n==3 {a=inc(borrow mut s)} else {return 1}
 if old.n!=3 || s.n!=4 {return 2}
 return 0
}''')

    def test_argument_snapshot_precedes_mutable_call(self):
        self.run_source(BASE+'''fn compare(old:Small,n:u32)->u32{return n-old.n}
fn main()->u32 {var s=Small(0);delta=compare(s,inc(borrow mut s));return delta-1}''')

    def test_err_preserves_prior_writes(self):
        self.run_source(BASE+'''fn fail(borrow mut s:Small)->Result<u32,u32>{s.n=9;return Err(1)}
fn main()->u32 {var s=Small(0);match fail(borrow mut s){Ok(v)=>{return 1} Err(e)=>{}}
 return s.n-9}''')

    def test_order_checked_traps_and_short_circuit(self):
        self.run_source(BASE+'fn main()->u32{var s=Small(4294967295);x=inc(borrow mut s);return 0}',True)
        self.run_source(BASE+'fn main()->u32{var s=Large([0;128],0);x=set(borrow mut s,128);return 0}',True)
        self.run_source(BASE+'fn main()->u32{var s=Small(4294967295);if false && inc(borrow mut s)==0{return 1} return 0}')

    def test_mutant_deleted_overflow_trap(self):
        source=BASE+'fn main()->u32{var s=Small(4294967295);x=inc(borrow mut s);return 0}'
        self.run_source(source,True)
        self.run_source(source,mutate=lambda text:re.sub(r'br i1 %v\d+_overflow,','br i1 false,',text))

    def test_mutant_snapshot_alias(self):
        source=BASE+'''fn main()->u32{var s=Large([7;128],0);old=copy s;
 x=set(borrow mut s,0);if old.a[0]!=7 {return 1} return 0}'''
        self.run_source(source)
        # Replace the actual snapshot operation, not the expected result.
        module=compile_ir(source)
        main=next(f for f in module if f.name=='main')
        snapshot=next(o for b in main.blocks for o in b.operations if o.op=='storage.read' and o.type=='Large')
        snapshot.op='loan.begin'
        with patch.object(sys.modules[__name__], 'compile_ir', return_value=module):
            self.run_source(source,expected_exit=1)

    def test_mutant_disabled_exclusivity_replays_alias_violation(self):
        source=BASE+'''fn conflict(borrow mut a:Small,borrow b:Small)->u32 {
 old=b.n;a.n=a.n+1;if b.n!=old {return 1} return 0
}
fn main()->u32 {var s=Small(1);return conflict(borrow mut s,s)}'''
        with self.assertRaisesRegex(CompileError,'borrow'):
            compile_ir(source)
        with patch('liza.ir.check_borrows',return_value=None):
            self.run_source(source,expected_exit=1)

    def test_mutable_json_entire_partitioned_corpus_at_o0_o2(self):
        import json
        import os
        import struct
        from benchmarks.json.corpus import cases, partitions
        root=Path(__file__).resolve().parents[1]
        payload=bytearray();expected=[]
        for data,status,offset in cases():
            for chunks in partitions(data):
                expected.append((status,offset));payload.extend(struct.pack('<I',len(chunks)))
                for chunk in chunks:
                    payload.extend(struct.pack('<I',len(chunk)));payload.extend(chunk)
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);ir=folder/'module.ll'
            r=subprocess.run([sys.executable,str(root/'benchmarks/mutable/emit.py'),str(ir),shutil.which('clang')],
                             cwd=root,env={**os.environ,'PYTHONPATH':str(root)},capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            flags=json.loads(ir.with_suffix('.target.json').read_text())['flags']
            for opt in ('-O0','-O2'):
                with self.subTest(opt=opt):
                    exe=folder/'probe.exe'
                    r=subprocess.run(['clang',*flags,opt,str(ir),str(root/'benchmarks/json/driver.c'),'-o',str(exe)],capture_output=True,text=True)
                    self.assertEqual(r.returncode,0,r.stderr)
                    r=subprocess.run([str(exe),'probe'],input=payload,capture_output=True,timeout=120)
                    self.assertEqual(r.returncode,0,r.stderr)
                    self.assertEqual(list(struct.iter_unpack('<IQ',r.stdout)),expected)
