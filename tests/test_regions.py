"""Region provenance, normal-exit obligations and bounded storage semantics."""
import json
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

ROOT=Path(__file__).resolve().parents[1]


def compile_source(source): return lower(Parser(source).parse())


def in_region(body,capacity=64):
    return '''fn main()->u32:alloc {
    match memory.create(CAPACITY) {Err(e)=>{return 1} Ok(region)=>{
    BODY
    closed=memory.close(move region)
    return 0
    }}}'''.replace('CAPACITY',str(capacity)).replace('BODY',body)


def with_buffer(body):
    return in_region('''match memory.alloc<u32>(region,4,7) {
    Err(e)=>{} Ok(buffer)=>{BODY}}
    '''.replace('BODY',body))


class RegionTypes(unittest.TestCase):
    def reject(self,source,pattern):
        with self.assertRaisesRegex(CompileError,pattern):compile_source(source)

    def test_unresolved_result_and_region_identity(self):
        self.reject(in_region('''a=memory.alloc<u8>(region,4,0)
        other=move region
        match move a {Err(e)=>{} Ok(b)=>{r=memory.release(move b)}}
        region=move other'''),'immutable|dependent')
        self.reject('''fn main()->u32:alloc {
        match memory.create(64) {Err(e)=>{return 1} Ok(r)=>{
        a=memory.alloc<u8>(r,4,0)
        c=memory.close(move r)
        match move a {Err(e)=>{} Ok(b)=>{x=memory.release(move b)}}
        return 0 }}}''','dependent buffer or Result')

    def test_copy_release_borrow_and_double_close(self):
        self.reject(with_buffer('copy_b=copy buffer\nx=memory.release(move buffer)'), 'cannot be copied|copyable')
        self.reject(with_buffer('v=memory.view(buffer)\nx=memory.release(move buffer)'), 'readonly view')
        self.reject(with_buffer('v=memory.view(buffer)\nb=memory.set(move buffer,0,1)\nx=memory.release(move b)'), 'readonly view')
        self.reject(in_region('first_close=memory.close(move region)'), 'use after move|available')
        self.reject(with_buffer('x=memory.len(buffer)'), 'resource must be closed')

    def test_function_transfer_and_argument_temporaries(self):
        prefix='''fn pass<T>(b:T)->T{return move b}
        fn consume(b:memory.Buffer<u32>,r:memory.Region)->u32:alloc {
        x=memory.release(move b)\ny=memory.close(move r)\nreturn 0}
        '''
        source=prefix+with_buffer('b=pass(move buffer)\nx=memory.release(move b)')
        module=compile_source(source)
        self.assertTrue(any(f.storage_contract['returns']['depends_on'] for f in module))
        result_helper='''fn finish(a:Result<memory.Buffer<u32>,MemoryError>)->u32 {
        match move a {Err(e)=>{return 0} Ok(b)=>{x=memory.release(move b)\nreturn 0}}}
        '''
        compile_source(result_helper+in_region('a=memory.alloc<u32>(region,4,0)\nx=finish(move a)'))
        self.reject(prefix+'''fn main()->u32:alloc {
        match memory.create(64){Err(e)=>{return 1} Ok(r)=>{
        a=memory.alloc<u32>(r,4,0)
        b=pass(move a)
        c=memory.close(move r)
        match move b {Err(e)=>{} Ok(buffer)=>{x=memory.release(move buffer)}}
        return 0}}}''','dependent buffer or Result')

        self.reject(prefix+'''fn main()->u32:alloc {
        match memory.create(64) {Err(e)=>{return 1} Ok(r)=>{
        match memory.alloc<u32>(r,4,0) {Err(e)=>{c=memory.close(move r)} Ok(b)=>{
        x=consume(move b,move r)}}
        return 0 }}}''','dependent buffer')

    def test_region_borrow_spans_later_argument_evaluation(self):
        self.reject('''fn main()->u32:alloc {
        match memory.create(64){Err(e)=>{return 1} Ok(r)=>{
          a=memory.alloc<u8>(r,memory.close(move r),0)
          match move a {Err(e)=>{} Ok(b)=>{x=memory.release(move b)}}
          return 0
        }}}''','borrowed by an earlier argument')

    def test_effects_and_ir_relations(self):
        self.reject('fn main()->u32 {a=memory.create(0)\nreturn 0}','alloc function')
        self.reject('fn f(b:memory.Buffer<[[u64;4294967295];4294967295]>)->u32 {x=memory.release(move b)\nreturn 0} fn main()->u32{return 0}', 'element layout exceeds')
        module=compile_source(with_buffer('{v=memory.view(buffer)\nx=v[0]}\nx=memory.release(move buffer)'))
        ops=[o for f in module for b in f.blocks for o in b.operations]
        self.assertEqual(next(o.storage_relation for o in ops if o.op=='region.alloc'),'depends_on_argument_0')
        self.assertTrue(next(o for o in ops if o.op=='view.read').may_trap)
        self.assertIn('storage_contract',json.loads(dump(module))['functions'][0])

    def test_scopes_loop_origins_and_cfg(self):
        source='''fn make()->Result<memory.Region,MemoryError>:alloc{return memory.create(64)}
        fn main()->u32:alloc {
        var i=0
        while i<3 {
          match make() {Err(e)=>{return 1} Ok(r)=>{
            match memory.alloc<u8>(r,4,0) {Err(e)=>{} Ok(b)=>{
              {v=memory.view(b)\nx=v[0]}
              x=memory.release(move b)
            }}
            c=memory.close(move r)
          }}
          i=i+1
          if i==2 {continue}
          if i==3 {break}
        }
        return 0}'''
        compile_source(source)
        self.reject(source.replace('x=memory.release(move b)','if i==2 {continue}\nx=memory.release(move b)'), 'resource must be closed')

    def test_loop_carried_origins_and_deterministic_ir(self):
        self.reject('''fn swap(a:memory.Region,b:memory.Region,n:u32)->u32:alloc {
        var current=move a
        var spare=move b
        var i=0
        while i<n {temporary=move current
          current=move spare
          spare=move temporary
          i=i+1}
        x=memory.close(move current)
        y=memory.close(move spare)
        return 0}
        fn main()->u32{return 0}''','loop backedge must preserve storage origins')
        source=with_buffer('x=memory.release(move buffer)')
        self.assertEqual(dump(compile_source(source)),dump(compile_source(source)))



@unittest.skipUnless(shutil.which('clang'),'clang required')
class RegionNative(unittest.TestCase):
    def run_source(self,source,stdout=b'',trap=False):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);module=compile_source(source)
            ir=root/'test.ll';ir.write_text(llvm(module))
            exe=root/('test.exe' if sys.platform=='win32' else 'test')
            for opt in ('0','2'):
                build=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*link_flags(module),'-o',str(exe)],capture_output=True,text=True)
                self.assertEqual(build.returncode,0,build.stderr)
                result=subprocess.run([str(exe)],capture_output=True,timeout=5)
                self.assertEqual(result.returncode!=0,trap,result.stderr)
                self.assertEqual(result.stdout,stdout)

    def test_example_and_scope_phi(self):
        self.run_source((ROOT/'examples/region_buffer.liza').read_text())
        self.run_source(with_buffer('''var b=move buffer
        var i=0
        while i<4 {
          { b=memory.set(move b,i,i+1) }
          i=i+1
        }
        var result=0
        {v=memory.view(b)\nif v[3]!=4 {result=1}}
        x=memory.release(move b)
        if result!=0 {c=memory.close(move region)\nreturn result}'''))

    def test_failure_atomicity_alignment_and_no_reclaim(self):
        self.run_source(in_region('''
        match memory.alloc<u8>(region,1,3) {Err(e)=>{} Ok(b)=>{x=memory.release(move b)}}
        match memory.alloc<u64>(region,4,9) {Err(e)=>{} Ok(b)=>{x=memory.release(move b)\nc=memory.close(move region)\nreturn 2}}
        match memory.alloc<u64>(region,3,11) {
          Err(e)=>{c=memory.close(move region)\nreturn 3}
          Ok(b)=>{
            var result=0
            {v=memory.view(b)\nif v[2]!=11 {result=4}}
            x=memory.release(move b)
            if result!=0 {c=memory.close(move region)\nreturn result}
          }
        }
        match memory.alloc<u8>(region,1,0) {Err(e)=>{} Ok(b)=>{x=memory.release(move b)\nc=memory.close(move region)\nreturn 5}}
        ''',32))

    def test_large_element_snapshot_survives_update_and_close(self):
        self.run_source('''fn main()->u32:alloc {
        match memory.create(4096){Err(e)=>{return 1} Ok(r)=>{
          match memory.alloc<[u8;128]>(r,2,[7;128]){
            Err(e)=>{c=memory.close(move r)\nreturn 2}
            Ok(initial)=>{
              var snapshot:[u8;128]=[0;128]
              {v=memory.view(initial)\nsnapshot=v[0]}
              updated=memory.set(move initial,0,[9;128])
              x=memory.release(move updated)
              c=memory.close(move r)
              if snapshot[0]!=7 || snapshot[127]!=7 {return 3}
              return 0
            }
          }
        }}}''')

    def test_struct_and_array_elements(self):
        self.run_source('struct P {a:u8,b:u64}\n'+in_region('''
        match memory.alloc<P>(region,2,P(3,99)) {Err(e)=>{} Ok(initial)=>{
          b=memory.set(move initial,1,P(7,42))
          var error=0
          {v=memory.view(b)\nif v[0].b!=99 || v[1].a!=7 {error=2}}
          x=memory.release(move b)
          if error!=0 {c=memory.close(move region)\nreturn error}
        }}
        match memory.alloc<[u8;3]>(region,2,[1,2,3]) {Err(e)=>{} Ok(b)=>{
          var error=0
          {v=memory.view(b)\nif v[1][2]!=3 {error=3}}
          x=memory.release(move b)
          if error!=0 {c=memory.close(move region)\nreturn error}
        }}'''))

    def test_live_view_survives_further_allocation(self):
        self.run_source(with_buffer('''var error=0
        {
          v=memory.view(buffer)
          match memory.alloc<u64>(region,2,99){Err(e)=>{} Ok(other)=>{x=memory.release(move other)}}
          if v[0]!=7 {error=2}
        }
        x=memory.release(move buffer)
        if error!=0 {c=memory.close(move region)\nreturn error}'''))

    def test_initialization_effect_on_empty_and_failed_allocation(self):
        source='''fn initial()->u64:io {
        match console.write("I"){Ok(n)=>{} Err(e)=>{}}
        return 7}
        '''+in_region('''match memory.alloc<u64>(region,0,initial()) {
        Err(e)=>{} Ok(b)=>{x=memory.release(move b)}}
        match memory.alloc<u64>(region,1,initial()) {
        Err(e)=>{} Ok(b)=>{x=memory.release(move b)}}''',0).replace('main()->u32:alloc','main()->u32:io,alloc')
        self.run_source(source,stdout=b'II')

    def test_set_arguments_precede_bounds_trap(self):
        source='''fn effect()->u32:io {
        match console.write("RHS") {Ok(n)=>{} Err(e)=>{}}
        return 9}
        '''+with_buffer('b=memory.set(move buffer,4,effect())\nx=memory.release(move b)').replace('main()->u32:alloc','main()->u32:io,alloc')
        self.run_source(source,stdout=b'RHS',trap=True)

    def test_zero_capacity_and_different_factory_instances(self):
        self.run_source(in_region('''match memory.alloc<u64>(region,0,1) {
        Err(e)=>{c=memory.close(move region)\nreturn 2}
        Ok(b)=>{n=memory.len(b)\nx=memory.release(move b)}}''',0))
        self.run_source('''fn make()->Result<memory.Region,MemoryError>:alloc{return memory.create(16)}
        fn main()->u32:alloc {
          match make(){Err(e)=>{return 1} Ok(a)=>{
            match make(){Err(e)=>{c=memory.close(move a)\nreturn 2} Ok(b)=>{
              match memory.alloc<u64>(b,1,5){Err(e)=>{c=memory.close(move a)} Ok(buffer)=>{
                c=memory.close(move a)
                x=memory.release(move buffer)
              }}
              c=memory.close(move b)\nreturn 0
            }}
          }}
        }''')
