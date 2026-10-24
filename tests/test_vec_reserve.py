"""Explicit growth: provenance, failure atomicity, initialized-prefix preservation."""
import json
import unittest
import shutil
import test_vectors as vectors
from test_vectors import compile_source, with_vec, ROOT
from liza.frontend import CompileError
from liza.ir import dump


class ReserveTypes(unittest.TestCase):
    def test_borrow_and_transfer_rejections(self):
        bodies = [
            ('v=vec.view(initial)\n(next,status)=vec.reserve(move initial,region,0)\nx=vec.release(move next)', 'readonly view'),
            ('(next,status)=vec.reserve(initial,region,4)\nx=vec.release(move next)', 'explicit move'),
            ('(next,status)=vec.reserve(move initial,move region,4)\nx=vec.release(move next)', 'borrowed resource argument'),
            ('(next,status)=vec.reserve(move initial,region,memory.close(move region))\nx=vec.release(move next)', 'borrowed by an earlier argument'),
            ('(next,status)=vec.reserve(move initial,region,u64(4))\nx=vec.release(move next)', 'expected'),
            ('pending=vec.reserve(move initial,region,4)', 'resource must be closed'),
        ]
        for body, pattern in bodies:
            with self.subTest(body=body), self.assertRaisesRegex(CompileError,pattern):
                compile_source(with_vec(body))

    def test_wrong_origin_rejected_even_for_noop(self):
        for capacity in (0,4):
            source=with_vec('''match memory.create(8192){
              Err(e)=>{x=vec.release(move initial)}
              Ok(other)=>{
                (next,status)=vec.reserve(move initial,other,CAPACITY)
                x=vec.release(move next)
                c=memory.close(move other)
              }}'''.replace('CAPACITY',str(capacity)))
            with self.subTest(capacity=capacity), self.assertRaisesRegex(CompileError,'original region'):
                compile_source(source)

    def test_alloc_effect_required(self):
        source='''fn grow(v:vec.Vec<u32>,r:memory.Region)->u32 {
          (next,status)=vec.reserve(move v,r,4)
          x=vec.release(move next)
          c=memory.close(move r)
          return 0
        }
        fn main()->u32{return 0}'''
        with self.assertRaisesRegex(CompileError,'alloc function'): compile_source(source)

    def test_pending_product_retains_region_dependency(self):
        source='fn pass<T>(value:T)->T{return move value}\n'+with_vec('''
          pending=pass(vec.reserve(move initial,region,4))
          c=memory.close(move region)
          (next,status)=move pending
          x=vec.release(move next)''')
        source=source.replace('closed=memory.close(move region)','closed=0').replace('Err(e)=>{error=2}','Err(e)=>{c=memory.close(move region)\nreturn 2}')
        with self.assertRaisesRegex(CompileError,'dependent buffer or Result'): compile_source(source)

    def test_ir_summary_tracks_relocation_transitively(self):
        source=(ROOT/'examples/vec_reserve.liza').read_text().replace('fn main()', 'fn run()')+'\nfn main()->u32:alloc{return run()}'
        module=compile_source(source)
        operations=[o for f in module for b in f.blocks for o in b.operations]
        reserve=next(o for o in operations if o.op=='vec.reserve')
        self.assertEqual(reserve.parameter_modes,['value','borrow','value'])
        self.assertEqual(reserve.effect_contract,'alloc')
        self.assertEqual(reserve.storage_relation,'preserve_origin_0_may_relocate_component_0')
        self.assertFalse(reserve.may_trap)
        for name in ('run','main'):
            fn=next(f for f in module if f.name==name)
            self.assertIn('vec.reserve',fn.storage_contract['effects'])
            self.assertEqual(fn.storage_contract['returned_buffer_storage'],'may_relocate_within_origin')
        self.assertEqual(json.loads(dump(module))['version'],20)


@unittest.skipUnless(shutil.which('clang'),'clang required')
class ReserveNative(unittest.TestCase):
    run_source=vectors.VectorNative.run_source

    def test_example(self):
        self.run_source((ROOT/'examples/vec_reserve.liza').read_text())

    def test_failure_preserves_vector_and_region_capacity(self):
        self.run_source(with_vec('''
          (filled,pushed)=vec.push(move initial,42)
          (unchanged,failed)=vec.reserve(move filled,region,3)
          match failed {
            Ok(done)=>{error=3}
            Err(reason)=>{match reason {
              MemoryError.Exhausted=>{}
              MemoryError.OutOfMemory=>{error=4}
              MemoryError.SizeOverflow=>{error=5}
            }}
          }
          if vec.capacity(unchanged)!=1 || vec.len(unchanged)!=1 {error=6}
          {v=vec.view(unchanged)\nif v[0]!=42 {error=7}}
          (grown,status)=vec.reserve(move unchanged,region,2)
          match status {Ok(done)=>{} Err(reason)=>{error=8}}
          if vec.capacity(grown)!=2 {error=9}
          x=vec.release(move grown)
          match memory.alloc<u8>(region,1,0){
            Err(reason)=>{}
            Ok(b)=>{r=memory.release(move b)\nerror=10}
          }
        ''',capacity=1,region_capacity=12))

    def test_noop_with_full_region_and_zero_requested(self):
        self.run_source(with_vec('''
          (a,pushed)=vec.push(move initial,7)
          (b,status)=vec.reserve(move a,region,1)
          match status {Ok(done)=>{} Err(reason)=>{error=3}}
          (c,status2)=vec.reserve(move b,region,0)
          match status2 {Ok(done)=>{} Err(reason)=>{error=4}}
          if vec.capacity(c)!=1 || vec.len(c)!=1 {error=5}
          {v=vec.view(c)\nif v[0]!=7 {error=6}}
          x=vec.release(move c)
        ''',capacity=1,region_capacity=4))

    def test_zero_capacity_empty_growth_and_zero_sized_elements(self):
        self.run_source(with_vec('''
          (next,status)=vec.reserve(move initial,region,4)
          match status {Ok(done)=>{} Err(reason)=>{error=3}}
          if vec.len(next)!=0 || vec.capacity(next)!=4 {error=4}
          match vec.get(next,0) {Some(value)=>{error=5} None=>{}}
          (filled,pushed)=vec.push(move next,11)
          {v=vec.view(filled)\nif v[0]!=11 {error=6}}
          x=vec.release(move filled)
        ''',capacity=0,region_capacity=16))
        self.run_source('struct Empty {}\n'+with_vec('''
          (next,status)=vec.reserve(move initial,region,4294967295)
          match status {Ok(done)=>{} Err(reason)=>{error=3}}
          (filled,pushed)=vec.push(move next,Empty())
          if vec.len(filled)!=1 || vec.capacity(filled)!=4294967295 {error=4}
          x=vec.release(move filled)
        ''',capacity=0,element='Empty',region_capacity=0))

    def test_size_overflow_returns_original_empty_vector(self):
        self.run_source(with_vec('''
          (next,status)=vec.reserve(move initial,region,4294967295)
          match status {
            Ok(done)=>{error=3}
            Err(reason)=>{match reason {
              MemoryError.SizeOverflow=>{}
              MemoryError.Exhausted=>{error=4}
              MemoryError.OutOfMemory=>{error=5}
            }}
          }
          if vec.len(next)!=0 || vec.capacity(next)!=0 {error=6}
          x=vec.release(move next)
        ''',capacity=0,element='[u64;1073741824]',region_capacity=0))

    def test_snapshots_large_elements_and_new_view(self):
        source='''struct Record {tag:u64,data:[u8;128]}
        fn pass<T>(value:T)->T{return move value}
        '''+with_vec('''
          (filled,pushed)=vec.push(move initial,Record(42,[7;128]))
          snapshot=vec.get(filled,0)
          {old=vec.view(filled)\nif old[0].tag!=42 {error=3}}
          pending=pass(vec.reserve(move filled,region,4))
          (next,status)=move pending
          match status {Ok(done)=>{} Err(reason)=>{error=4}}
          (changed,updated)=vec.set(move next,0,Record(99,[9;128]))
          {fresh=vec.view(changed)\nif fresh.len!=1 || fresh[0].data[127]!=9 {error=5}}
          x=vec.release(move changed)
          c=memory.close(move region)
          match snapshot {Some(v)=>{if v.tag!=42 || v.data[127]!=7 {error=6}} None=>{error=7}}
          return error
        ''',capacity=1,element='Record')
        self.run_source(source)

    def test_loop_cfg_and_stable_origin(self):
        self.run_source(with_vec('''
          var current=move initial
          var i=0
          while i<4 {
            (next,status)=vec.reserve(move current,region,i+1)
            current=move next
            match status {Ok(done)=>{} Err(reason)=>{error=3}}
            (filled,pushed)=vec.push(move current,i)
            current=move filled
            i=i+1
            if i==2 {continue}
            if i==4 {break}
          }
          {v=vec.view(current)\nif v.len!=4 || v[0]!=0 || v[3]!=3 {error=4}}
          if vec.capacity(current)!=4 {error=5}
          x=vec.release(move current)
        ''',capacity=0))

    def test_arguments_run_before_noop_or_failure(self):
        source='''fn requested()->u32:io {
          match console.write("R"){Ok(n)=>{} Err(e)=>{}}
          return 1
        }
        '''+with_vec('''
          (a,status)=vec.reserve(move initial,region,requested())
          (b,status2)=vec.reserve(move a,region,requested()+1)
          match status2 {Ok(done)=>{error=3} Err(reason)=>{}}
          x=vec.release(move b)
        ''',capacity=1,region_capacity=4).replace('main()->u32:alloc','main()->u32:io,alloc')
        self.run_source(source,stdout=b'RR')

    def test_argument_trap_is_not_elided_for_noop(self):
        source='''fn requested()->u32:io {
          match console.write("before"){Ok(n)=>{} Err(e)=>{}}
          n:u8=255
          return u32(n+1)
        }
        '''+with_vec('''(next,status)=vec.reserve(move initial,region,requested())
        x=vec.release(move next)''').replace('main()->u32:alloc','main()->u32:io,alloc')
        self.run_source(source,stdout=b'before',trap=True)
