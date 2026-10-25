"""Whole-value resource structures: ownership, per-field origins and lowering."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower, dump
from liza.backend import llvm
from liza.stdlib import link_flags
from liza.modules import load_program

HEADER='''struct Owner {buffer:memory.Buffer<u8>;length:u32}
fn wrap(b:memory.Buffer<u8>)->Owner {return Owner(move b,1)}
fn pass<T>(x:T)->T {return move x}
fn dispose(s:Owner)->u32 {(b,n)=move s;return memory.release(move b)}
'''

def body(text):
    return HEADER+'''fn main()->u32:alloc {
    match memory.create(128) {Err(e)=>{return 1} Ok(region)=>{
        match memory.alloc<u8>(region,4,65) {Err(e)=>{} Ok(b)=>{
        '''+text+'''
        }}
        c=memory.close(move region);return 0
    }}
}'''

class ResourceStructureTypes(unittest.TestCase):
    def reject(self,source,pattern):
        with self.assertRaisesRegex(CompileError,pattern):lower(Parser(source).parse())

    def test_whole_owner_and_nested_origins(self):
        source=HEADER+'''struct Nested<T> {item:T;tag:u32}
fn nested(b:memory.Buffer<u8>)->Nested<Owner> {return Nested<Owner>(wrap(move b),7)}
fn release(n:Nested<Owner>)->u32 {(s,tag)=move n;return dispose(move s)}
fn main()->u32{return 0}'''
        m=lower(Parser(source).parse())
        f=next(f for f in m if f.name=='nested')
        self.assertEqual(f.storage_contract['returns']['components'][0]['components'][0]['depends_on'],["('parameter', '0')"])
        self.assertTrue(any(op.op=='unpack.consume' for f in m for b in f.blocks for op in b.operations))

    def test_no_copy_drop_overwrite_or_partial_field(self):
        cases=[('s=wrap(move b);return 0','closed or transferred'),
               ('s=wrap(move b);t=copy s;x=dispose(move s);y=dispose(move t)','cannot be copied'),
               ('s=wrap(move b);t=s;x=dispose(move s);y=dispose(move t)','explicit move'),
               ('s=wrap(move b);x=s.length;y=dispose(move s)','whole-value unpack'),
               ('n=wrap(move b).length','whole-value unpack'),
               ('s=wrap(move b);(x,n)=s;y=memory.release(move x)','explicit move'),
               ('s=wrap(move b);(x,n)=move s;y=dispose(move s);z=memory.release(move x)','use after move'),
               ('s=wrap(move b);(x,)=move s;y=memory.release(move x)','every component'),
               ('s=wrap(move b);(_,n)=move s','distinct new'),
               ('s=wrap(move b);(x,x)=move s','distinct new')]
        for text,pattern in cases:
            with self.subTest(text=text):self.reject(body(text),pattern)
        self.reject(HEADER+'fn bad(s:Owner,t:Owner)->Owner {var x=move s;x=move t;return move x} fn main()->u32{return 0}', 'overwrite a live resource')

    def test_region_protected_by_whole_temporary_and_variant(self):
        for text in ('s=wrap(move b);c=memory.close(move region);x=dispose(move s)',
                     's=pass(wrap(move b));c=memory.close(move region);x=dispose(move s)',
                     's:Option<Owner> =Some(wrap(move b));c=memory.close(move region);match move s {Some(o)=>{x=dispose(move o)} None=>{}}'):
            with self.subTest(text=text):self.reject(body(text).replace('Err(e)=>{} Ok(b)', 'Err(e)=>{c=memory.close(move region);return 2} Ok(b)').replace('c=memory.close(move region);return 0','return 0'),'dependent buffer or Result')
        source=body('s=keep(wrap(move b),memory.close(move region));x=dispose(move s)').replace('Err(e)=>{} Ok(b)', 'Err(e)=>{c=memory.close(move region);return 2} Ok(b)').replace('c=memory.close(move region);return 0','return 0')
        self.reject('fn keep(s:Owner,n:u32)->Owner:alloc{return move s}\n'+source,'dependent buffer or Result')

    def test_distinct_origins_survive_unpack_and_call(self):
        src='''struct Two {a:memory.Buffer<u8>;b:memory.Buffer<u8>}
fn swap(x:Two)->Two {(a,b)=move x;return Two(move b,move a)}
fn main()->u32:alloc {
 match memory.create(8) {Err(e)=>{return 1} Ok(r1)=>{
 match memory.create(8) {Err(e)=>{c=memory.close(move r1);return 2} Ok(r2)=>{
 match memory.alloc<u8>(r1,1,1) {Err(e)=>{c1=memory.close(move r1);c2=memory.close(move r2);return 3} Ok(a)=>{
 match memory.alloc<u8>(r2,1,2) {Err(e)=>{x=memory.release(move a);c1=memory.close(move r1);c2=memory.close(move r2);return 4} Ok(b)=>{
 s=swap(Two(move a,move b));(first,second)=move s
 x=memory.release(move first)
 BAD
 y=memory.release(move second)
 }}}}
 c2=memory.close(move r2);c1=memory.close(move r1);return 0
 }}}} }'''
        lower(Parser(src.replace('BAD','')).parse())
        self.reject(src.replace('BAD','early=memory.close(move r1)').replace('c1=memory.close(move r1);return 0','return 0'), 'dependent buffer or Result')
        # Closing the released buffer's region is allowed (remove later duplicate close).
        lower(Parser(src.replace('BAD','early=memory.close(move r2)').replace('c2=memory.close(move r2);c1=memory.close(move r1);return 0','c1=memory.close(move r1);return 0')).parse())

    def test_unpacked_loan_and_escape(self):
        self.reject(body('v=memory.view(b);s=wrap(move b);x=dispose(move s)'), 'readonly view')
        self.reject(body('s=wrap(move b);(x,n)=move s;v=memory.view(x);s2=Owner(move x,n);y=dispose(move s2)'), 'readonly view')
        source=HEADER+'''fn make()->Owner:alloc {
          match memory.create(16) {Err(e)=>{while true {}} Ok(r)=>{
            match memory.alloc<u8>(r,1,0) {Err(e)=>{c=memory.close(move r);while true {}}
              Ok(b)=>{return Owner(move b,0)}}
          }}
        } fn main()->u32{return 0}'''
        self.reject(source,'resource must be closed|locally owned region')

    def test_loop_carries_owner_and_no_drop_on_break(self):
        lower(Parser(body('''var s=wrap(move b);var i:u32=0
        while i<3 {(x,n)=move s;s=Owner(move x,n+1);i=i+1}
        y=dispose(move s)''')).parse())
        self.reject(body('s=wrap(move b);while true {(x,n)=move s;break}'),'closed or transferred')

    def test_private_fields_block_construction_and_unpack(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'owned.liza').write_text('''pub struct Owner {buffer:memory.Buffer<u8>;length:u32}
            pub fn wrap(b:memory.Buffer<u8>)->Owner {return Owner(move b,0)}
            pub fn release(s:Owner)->u32 {(b,n)=move s;return memory.release(move b)}''')
            for text in ('fn bad(x:owned.Owner)->u32 {(b,n)=move x;return memory.release(move b)}',
                         'fn bad(b:memory.Buffer<u8>)->owned.Owner {return owned.Owner(move b,0)}'):
                (root/'main.liza').write_text('import owned\n'+text+'\nfn main()->u32{return 0}')
                with self.assertRaisesRegex(CompileError,'private'):lower(load_program(root/'main.liza'))

    def test_singleton_and_arity_three(self):
        lower(Parser('''struct One {f:File} struct Three {a:One;b:u32;c:u64}
        fn f(x:Three)->File {(one,b,c)=move x;(file,)=move one;return move file}
        fn main()->u32{return 0}''').parse())

@unittest.skipUnless(shutil.which('clang'),'requires clang')
class ResourceStructureNative(unittest.TestCase):
    def test_nested_large_fields_and_reconstruction(self):
        source=HEADER+'''struct Large {prefix:[u32;64];owner:Owner;suffix:[u32;64]}
        fn step(x:Large)->Large {
          (a,s,z)=move x;(b,n)=move s
          next=memory.set(move b,0,66)
          return Large(a,Owner(move next,n+1),z)
        }
        '''+body('''s=wrap(move b);var x=Large([7;64],move s,[9;64]);var i:u32=0
        while i<3 {x=step(move x);i=i+1}
        (a,s2,z)=move x;(buf,n)=move s2
        var status:u32=0
        {v=memory.view(buf);if v[0]!=66 || n!=4 || a[63]!=7 || z[0]!=9 {status=3}}
        done=memory.release(move buf)
        if status!=0 {c=memory.close(move region);return status}
        ''').replace(HEADER,'')
        module=lower(Parser(source).parse())
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);ir=root/'test.ll';ir.write_text(llvm(module))
            for opt in ('-O0','-O2'):
                exe=root/('test'+opt[1:]+('.exe' if sys.platform=='win32' else ''))
                r=subprocess.run(['clang','-Wno-override-module',opt,str(ir),*link_flags(module),'-o',str(exe)],capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=10).returncode,0)

if __name__=='__main__':unittest.main()
