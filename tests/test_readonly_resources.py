"""T2-A permissions, not merely non-consuming argument passing."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm
from liza.modules import load_program
from liza.stdlib import link_flags

HEADER='''struct Holder {buffer:memory.Buffer<u8>;length:u32}
fn length(borrow h:Holder)->u32 {return h.length}
fn capacity(borrow h:Holder)->u32 {return memory.len(h.buffer)}
fn release(h:Holder)->u32 {(b,n)=move h;return memory.release(move b)}
'''

def program(body,extra=''):
    return HEADER+extra+'''fn main()->u32:alloc {
    match memory.create(64) {Err(e)=>{return 1} Ok(r)=>{
      match memory.alloc<u8>(r,4,65) {
        Err(e)=>{c=memory.close(move r);return 2}
        Ok(b)=>{
          h=Holder(move b,4)
          '''+body+'''
        }
      }
    }}
}'''

class ReadonlyTypes(unittest.TestCase):
    def reject(self,source,pattern):
        with self.assertRaisesRegex(CompileError,pattern):lower(Parser(source).parse())

    def test_signature_projection_and_ir_origin(self):
        source=HEADER+'''struct Outer {inner:Holder;tag:u32}
        fn nested(borrow o:Outer)->u32 {return capacity(o.inner)}
        fn read(borrow h:Holder)->u8 {v=memory.view(h.buffer);return v[0]}
        fn main()->u32{return 0}'''
        module=lower(Parser(source).parse())
        for name in ('length','capacity','nested','read'):
            fn=next(f for f in module if f.name==name)
            self.assertEqual(fn.params[0]['mode'],'readonly')
            self.assertEqual(fn.storage_contract['consumes'],[])
            self.assertEqual(len(fn.storage_contract['readonly_parameters']),1)
            for block in fn.blocks:
                for op in block.operations:
                    if op.op=='struct.field':
                        self.assertEqual(op.storage_relation,'readonly_projection')
                        self.assertEqual(op.owner_binding,'p0')
                    if op.op in ('call','buffer.view','buffer.length'):
                        self.assertEqual(op.parameter_modes[0],'readonly')
                        if op.op in ('buffer.view','buffer.length'):self.assertEqual(op.owner_binding,'p0')
        self.assertTrue(next(f for f in module if f.name=='read').storage_contract['parameters']['h']['components'][0]['depends_on'])

    def test_no_owned_extraction_copy_or_drop_obligation(self):
        for body in ('x=h.buffer;return 0','x=copy h;return 0','x=move h;return 0',
                     '(b,n)=move h;return memory.release(move b)',
                     'return release(move h)',
                     'return release(h)',
                     'x:Option<memory.Buffer<u8>> = Some(h.buffer);return 0'):
            with self.subTest(body=body):self.reject(HEADER+'fn bad(borrow h:Holder)->u32{'+body+'} fn main()->u32{return 0}', 'readonly')
        self.reject(HEADER+'fn bad(borrow h:Holder)->Holder{return move h} fn main()->u32{return 0}', 'independent copyable')
        self.reject(HEADER+'fn drop(h:Holder)->u32{return length(h)} fn main()->u32{return 0}', 'closed or transferred')
        # A non-consuming observer has no obligation to release its parameter.
        lower(Parser(HEADER+'fn ignore(borrow h:Holder)->u32{return 0} fn main()->u32{return 0}').parse())

    def test_no_update_or_view_escape(self):
        self.reject(HEADER+'fn bad(borrow h:Holder)->u32{h.length=0;return 0} fn main()->u32{return 0}','immutable|readonly')
        self.reject(HEADER+'fn bad(borrow h:Holder)->View<u8>{return memory.view(h.buffer)} fn main()->u32{return 0}','views cannot')
        self.reject('struct Saved {v:View<u8>} fn main()->u32{return 0}','views cannot')

    def test_legacy_borrowed_operations_are_not_readonly(self):
        cases=[
            ('struct R {r:memory.Region}', 'r:R', 'x=memory.alloc<u8>(r.r,1,0);match move x {Err(e)=>{} Ok(b)=>{z=memory.release(move b)}}', 'alloc'),
            ('struct F {f:File}', 'f:F','x=file.read_chunk(f.f)', 'io'),
            ('struct N {r:net.Reactor}', 'n:N','x=net.reactor_poll(n.r,0)', 'io'),
        ]
        for decl,param,body,effect in cases:
            with self.subTest(param=param):self.reject(decl+' fn bad(borrow '+param+')->u32:'+effect+'{'+body+';return 0} fn main()->u32{return 0}','no readonly permission')
        for op in ('memory.set(h.buffer,0,1)','memory.release(h.buffer)'):
            self.reject(HEADER+'fn bad(borrow h:Holder)->u32{x='+op+';return 0} fn main()->u32{return 0}','readonly')
        self.reject('struct V {v:vec.Vec<u8>} fn bad(borrow x:V)->u32{(n,s)=vec.push(x.v,1);z=vec.release(move n);return 0} fn main()->u32{return 0}', 'readonly')

    def test_argument_order_nested_calls_and_generics(self):
        extra='''fn use(borrow first:Holder,second:Holder)->u32{return release(move second)}
        fn consume(first:Holder,borrow second:Holder)->u32{return release(move first)}
        fn count(borrow first:Holder,n:u32)->u32{return n}
        fn pass<T>(value:T)->T{return move value}
        fn observe<T>(borrow value:T)->u32{return capacity(value)}
        '''
        for text in ('x=use(h,move h)','x=consume(move h,h)',
                     'x=count(h,release(move h))',
                     'x=use(h,pass(move h))'):
            self.reject(program(text+';c=memory.close(move r);return 0',extra),'earlier argument|after move')
        lower(Parser(program('''n=observe<Holder>(h);m=length(h)
          x=release(move h);c=memory.close(move r);return n-m''',extra)).parse())
        self.reject(HEADER+'''fn pass<T>(value:T)->T{return move value}
          fn bad(borrow h:Holder)->u32{x=pass(h);return release(move x)} fn main()->u32{return 0}''','readonly')

    def test_same_owner_readers_and_borrow_ends_on_return(self):
        extra='fn two(borrow a:Holder,borrow b:Holder)->u32{return length(a)+capacity(b)}'
        lower(Parser(program('n=two(h,h);x=release(move h);c=memory.close(move r);return n-8',extra)).parse())

    def test_region_dependency_in_later_argument(self):
        extra='fn keep(borrow h:Holder,n:u32)->u32:alloc{return n}'
        self.reject(program('n=keep(h,memory.close(move r));x=release(move h);return n',extra),'dependent buffer or Result')

    def test_nested_generic_reborrow_keeps_region_origin(self):
        extra = """struct Box<T> {value:T}
        fn leaf(borrow h:Holder,n:u32)->u32{return capacity(h)+n}
        fn middle<T>(borrow x:Box<T>,n:u32)->u32{return leaf(x.value,n)}
        fn outer<T>(borrow x:Box<Box<T>>,n:u32)->u32{return middle(x.value,n)}
        fn discard<T>(x:Box<Box<T>>)->u32 {
          (inner,)=move x;(h,)=move inner;return release(move h)
        }
        """
        # The same generic projection chain is well typed before the bad argument
        # is introduced. Closing an unrelated region is allowed while x is lent.
        body = """x=Box<Box<Holder>>(Box<Holder>(move h))
        match memory.create(8) {Err(e)=>{
          d=discard(move x);c=memory.close(move r);return 1
        } Ok(other)=>{
          n=outer(x,memory.close(move other))
          d=discard(move x);c=memory.close(move r);return n
        }}"""
        lower(Parser(program(body,extra)).parse())
        self.reject(program(body.replace('outer(x,memory.close(move other))',
            'outer(x,memory.close(move r))').replace(
            'd=discard(move x);c=memory.close(move r);return n',
            'd=discard(move x);c=memory.close(move other);return n'),extra),
            'dependent buffer or Result')

    def test_generic_reborrow_cannot_mutate_nested_region(self):
        source = """struct RegionOwner {region:memory.Region}
        struct Box<T> {value:T}
        fn observe(borrow r:RegionOwner,n:u32)->u32{return n}
        fn bad<T>(borrow x:Box<T>)->u32:alloc {
          return observe(x.value,close_region(x.value.region))
        }
        fn close_region(r:memory.Region)->u32:alloc {
          c=memory.close(move r);return c
        }
        fn main()->u32:alloc {
          match memory.create(8) {Err(e)=>{return 1} Ok(r)=>{
            x=Box<RegionOwner>(RegionOwner(move r))
            n=bad(x);(owner,)=move x;(region,)=move owner
            c=memory.close(move region);return n
          }}
        }"""
        self.reject(source,'readonly')
        # Legacy non-consuming alloc also cannot acquire mutation permission.
        self.reject(source.replace('return observe(x.value,close_region(x.value.region))',
            'match memory.alloc<u8>(x.value.region,1,0) {'
            'Err(e)=>{return 1} Ok(b)=>{return memory.release(move b)}}'),
            'no readonly permission')

    def test_privacy_and_generic_projection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'owner.liza').write_text('''pub struct Box<T> {value:T}
            pub fn inspect<T>(borrow box:Box<T>)->u32 {return memory.len(box.value)}''')
            (root/'main.liza').write_text('''import owner
            fn bad(borrow box:owner.Box<memory.Buffer<u8>>)->u32 {return memory.len(box.value)}
            fn main()->u32{return 0}''')
            with self.assertRaisesRegex(CompileError,'private'):lower(load_program(root/'main.liza'))

    def test_only_resource_structures_and_named_arguments(self):
        for t in ('u32','memory.Buffer<u8>','memory.Region'):
            self.reject('fn bad(borrow x:'+t+')->u32{return 0} fn main()->u32{return 0}', 'concrete resource structure')
        self.reject(program('x=length(Holder(move b,4));c=memory.close(move r);return x').replace('h=Holder(move b,4)',''), 'available binding')
        self.reject(program('n=length(move h);c=memory.close(move r);return n'), 'available binding')

    def test_builtin_read_permissions_do_not_change_owned_call_modes(self):
        source='fn size(b:memory.Buffer<u8>)->u32{n=memory.len(b);x=memory.release(move b);return n} fn main()->u32{return 0}'
        m=lower(Parser(source).parse());ops=[o for f in m for b in f.blocks for o in b.operations if o.op=='buffer.length']
        self.assertEqual(ops[0].parameter_modes,['borrow'])

@unittest.skipUnless(shutil.which('clang'),'requires clang')
class ReadonlyNative(unittest.TestCase):
    def run_source(self,source):
        m=lower(Parser(source).parse())
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);ir=root/'test.ll';ir.write_text(llvm(m))
            for opt in ('-O0','-O2'):
                exe=root/('test'+opt[1:]+('.exe' if sys.platform=='win32' else ''))
                r=subprocess.run(['clang','-Wno-override-module',opt,str(ir),*link_flags(m),'-o',str(exe)],capture_output=True,text=True)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=10).returncode,0)

    def test_string_observer_cost(self):
        from tools.check_readonly_cost import inspect
        with tempfile.TemporaryDirectory() as folder:
            self.assertIn('O0/O2',inspect(folder))

    def test_nested_reborrow_loops_and_independent_large_snapshot(self):
        source=HEADER+'''struct Outer {inner:Holder;data:[u32;64]}
        fn inner(borrow o:Outer)->u32{return capacity(o.inner)}
        fn snapshot(borrow o:Outer)->[u32;64] {var a=o.data;a[0]=99;return a}
        fn read(borrow o:Outer)->u32 {
          var sum:u32=0;var i:u32=0
          while i<4 {
            if i<2 {v=memory.view(o.inner.buffer);sum=sum+u32(v[i])}
            else {sum=sum+inner(o)}
            i=i+1
          }
          return sum
        }
        fn main()->u32:alloc {
          match memory.create(4) {Err(e)=>{return 1} Ok(r)=>{
            match memory.alloc<u8>(r,4,65) {Err(e)=>{c=memory.close(move r);return 2} Ok(b)=>{
              o=Outer(Holder(move b,4),[7;64])
              a=snapshot(o);n=read(o)
              (h,original)=move o
              x=release(move h);c=memory.close(move r)
              if a[0]!=99 || original[0]!=7 || n!=138 {return 3}
              return 0
            }}
          }}
        }'''
        self.run_source(source)

    def test_readonly_io_is_independent_of_effects(self):
        self.run_source(program('''n=output(h);x=release(move h);c=memory.close(move r);return n''',
            'fn output(borrow h:Holder)->u32:io {v=memory.view(h.buffer);match console.write_bytes(v) {Ok(n)=>{return 0} Err(e)=>{return 3}}}').replace('main()->u32:alloc','main()->u32:io,alloc'))

if __name__=='__main__':unittest.main()
