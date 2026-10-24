"""Linear products and initialized-prefix vectors, including native O0/O2."""
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

ROOT = Path(__file__).resolve().parents[1]


def compile_source(source, internal=False):
    program = Parser(source, internal=internal).parse()
    for fn in program: fn.trusted_library = False
    return lower(program)


def with_vec(body, capacity=2, element='u32', region_capacity=8192):
    return f'''fn main()->u32:alloc {{
    match memory.create({region_capacity}) {{Err(e)=>{{return 1}} Ok(region)=>{{
      var error:u32=0
      match vec.with_capacity<{element}>(region,{capacity}) {{
        Err(e)=>{{error=2}}
        Ok(initial)=>{{{body}}}
      }}
      closed=memory.close(move region)
      return error
    }}}}}}'''


class VectorTypes(unittest.TestCase):
    def reject(self, body, pattern):
        with self.assertRaisesRegex(CompileError, pattern): compile_source(with_vec(body))

    def test_product_requires_whole_explicit_consumption(self):
        for body, pattern in [
            ('result=vec.pop(move initial)', 'resource must be closed'),
            ('result=vec.pop(move initial)\n(a,b)=result\nx=vec.release(move a)', 'explicit move'),
            ('result=vec.pop(move initial)\n(a,b)=copy result\nx=vec.release(move a)', 'cannot be copied|copyable'),
            ('result=vec.pop(move initial)\n(a,b)=move result\n(c,d)=move result\nx=vec.release(move a)\ny=vec.release(move c)', 'use after move|available'),
            ('result=vec.pop(move initial)\na=move result.first', 'partial|binding|move'),
            ('(a,b)=vec.pop(move initial)', 'resource must be closed'),
            ('(a,a)=vec.pop(move initial)', 'distinct new'),
            ('(initial,b)=vec.pop(move initial)', 'distinct new'),
            ('(_,b)=vec.pop(move initial)', 'distinct new'),
            ('(a,b)=42\nx=vec.release(move initial)', 'linear product'),
        ]:
            with self.subTest(body=body): self.reject(body, pattern)

    def test_live_views_block_all_consuming_operations(self):
        for operation in ('vec.push(move initial,1)', 'vec.pop(move initial)', 'vec.set(move initial,0,1)'):
            self.reject('v=vec.view(initial)\n(next,status)='+operation+'\nx=vec.release(move next)', 'readonly view')
        self.reject('v=vec.view(initial)\nx=vec.release(move initial)', 'readonly view')
        self.reject('x=copy initial\na=vec.release(move initial)\nb=vec.release(move x)', 'copyable|cannot be copied')

    def test_region_dependency_survives_pending_product_and_generic_call(self):
        source='fn pass<T>(x:T)->T{return move x}\n'+with_vec('''
        pending=pass(vec.pop(move initial))
        c=memory.close(move region)
        (next,item)=move pending
        x=vec.release(move next)''')
        source=source.replace('closed=memory.close(move region)','closed=0').replace('Err(e)=>{error=2}', 'Err(e)=>{c=memory.close(move region)\nreturn 2}')
        with self.assertRaisesRegex(CompileError,'dependent buffer or Result'): compile_source(source)

    def test_temporary_product_keeps_region_dependency(self):
        source='fn keep<T>(x:T,n:u32)->T:alloc{return move x}\n'+with_vec('''
          (next,item)=keep(vec.pop(move initial),memory.close(move region))
          x=vec.release(move next)''')
        source=source.replace('closed=memory.close(move region)','closed=0').replace('Err(e)=>{error=2}', 'Err(e)=>{c=memory.close(move region)\nreturn 2}')
        with self.assertRaisesRegex(CompileError,'dependent buffer or Result'): compile_source(source)

    def test_borrow_of_vec_spans_later_arguments(self):
        self.reject('x=vec.get(initial,vec.release(move initial))', 'borrowed by an earlier argument')

    def test_effects_and_element_constraints(self):
        source=with_vec('x=vec.release(move initial)').replace('main()->u32:alloc','main()->u32')
        with self.assertRaisesRegex(CompileError,'alloc function'): compile_source(source)
        with self.assertRaisesRegex(CompileError,'copyable'): compile_source(with_vec('x=vec.release(move initial)', element='File'))
        self.reject('(next,status)=vec.push(move initial,true)\nx=vec.release(move next)', 'expected')
        self.reject('x=vec.get(initial,u64(0))\nr=vec.release(move initial)', 'expected')
        self.reject('v=vec.view(vec.push(move initial,1))', 'expected vec.Vec')

    def test_product_ir_and_provenance(self):
        module=compile_source((ROOT/'examples/bounded_vec.liza').read_text())
        ops=[o for f in module for b in f.blocks for o in b.operations]
        consumes=[o for o in ops if o.op=='unpack.consume']
        self.assertEqual(len(consumes),2)
        for op in consumes:
            components=[o for o in ops if o.op=='unpack.component' and o.args==[op.result]]
            self.assertEqual({o.field_name for o in components},{'0','1'})
        identity=next(f for f in module if f.name.startswith('liza$function$'))
        self.assertTrue(identity.storage_contract['returns']['components'][0]['depends_on'])
        self.assertFalse(identity.storage_contract['returns']['components'][1]['depends_on'])
        self.assertEqual(json.loads(dump(module))['version'],20)
        self.assertEqual(dump(module),dump(compile_source((ROOT/'examples/bounded_vec.liza').read_text())))

    def test_universal_product_components_and_conditional_resource(self):
        # Internal fixture: no public syntax can name or construct Product.
        source='''fn dispose(value:__liza_Product<Result<memory.Buffer<u32>,MemoryError>,File>)->u32:io {
          (allocation,file_handle)=move value
          match move allocation {Ok(b)=>{r=memory.release(move b)} Err(e)=>{}}
          match file.close(move file_handle) {Ok(done)=>{} Err(error)=>{}}
          return 0
        }
        fn identity<T>(value:T)->T{return move value}
        fn forward(value:__liza_Product<Result<memory.Buffer<u32>,MemoryError>,File>)->__liza_Product<Result<memory.Buffer<u32>,MemoryError>,File> {
          return identity(move value)
        }
        fn main()->u32{return 0}'''
        module=compile_source(source,internal=True)
        forward=next(f for f in module if f.name=='forward')
        self.assertTrue(forward.storage_contract['returns']['components'][0]['variants']['Ok']['depends_on'])
        self.assertFalse(forward.storage_contract['returns']['components'][1]['depends_on'])
        with self.assertRaisesRegex(CompileError,'resource must be closed'):
            compile_source(source.replace('match file.close(move file_handle) {Ok(done)=>{} Err(error)=>{}}',''),internal=True)
        with self.assertRaisesRegex(CompileError,'reserved implementation name'):
            compile_source(source)

    def test_product_cannot_hide_in_aggregate(self):
        source='''struct Hidden<T>{value:T}
        fn wrap<T>(value:T)->Hidden<T>{return Hidden<T>(move value)}
        '''+with_vec('result=wrap(vec.pop(move initial))')
        with self.assertRaisesRegex(CompileError,'linear products cannot be stored'): compile_source(source)

    def test_module_generic_transfer_and_namespace(self):
        from liza.modules import load_program
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'helper.liza').write_text('pub fn pass<T>(x:T)->T{return move x}')
            source='import helper\n'+with_vec('(next,item)=helper.pass(vec.pop(move initial))\nx=vec.release(move next)')
            path=root/'main.liza';path.write_text(source)
            module=lower(load_program(path))
            self.assertTrue(any(f.storage_contract['returns']['components'] for f in module))
            path.write_text(source.replace('(next,item)', '(vec,item)'))
            with self.assertRaisesRegex(CompileError,'module namespace'): lower(load_program(path))

    def test_copyable_components_do_not_make_product_copyable(self):
        for body in ('return 0', 'other=copy value\nreturn 0'):
            source='fn f(value:__liza_Product<u32,bool>)->u32{'+body+'} fn main()->u32{return 0}'
            with self.assertRaisesRegex(CompileError,'resource must be closed|copyable|cannot be copied'):
                compile_source(source,internal=True)
        source='fn f(value:__liza_Product<u32,bool>)->u32{(a,b)=move value\nreturn a} fn main()->u32{return 0}'
        compile_source(source,internal=True)

    def test_loop_obligations_and_scope_cleanup(self):
        self.reject('''var current=move initial
          while true {(next,item)=vec.pop(move current)\nbreak}
          x=vec.release(move current)''','use after move|resource must be closed|available')
        self.reject('''var current=move initial
          while true {(next,item)=vec.pop(move current)\ncontinue}''','resource must be closed')


@unittest.skipUnless(shutil.which('clang'),'clang required')
class VectorNative(unittest.TestCase):
    def run_source(self, source, stdout=b'', trap=False):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);module=compile_source(source)
            ir=root/'test.ll';ir.write_text(llvm(module))
            exe=root/('test.exe' if sys.platform=='win32' else 'test')
            for opt in ('0','2'):
                build=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*link_flags(module),'-o',str(exe)],capture_output=True,text=True)
                self.assertEqual(build.returncode,0,build.stderr)
                result=subprocess.run([str(exe)],capture_output=True,timeout=5)
                self.assertEqual(result.returncode!=0,trap,(opt,result.returncode,result.stderr))
                self.assertEqual(result.stdout,stdout)

    def test_example_generic_transfer(self):
        self.run_source((ROOT/'examples/bounded_vec.liza').read_text())

    def test_full_empty_failure_atomicity_and_slot_reuse(self):
        self.run_source(with_vec('''
        (a,status)=vec.push(move initial,10)
        (b,status2)=vec.push(move a,20)
        (full,failure)=vec.push(move b,30)
        match failure {Ok(done)=>{error=3} Err(e)=>{
          match e {vec.Error.Full=>{} vec.Error.OutOfBounds=>{error=4}}
        }}
        if vec.len(full)!=2 {error=5}
        (unchanged,bad)=vec.set(move full,2,99)
        match bad {Ok(done)=>{error=6} Err(e)=>{
          match e {vec.Error.Full=>{error=7} vec.Error.OutOfBounds=>{}}
        }}
        (one,last)=vec.pop(move unchanged)
        match last {Some(n)=>{if n!=20 {error=8}} None=>{error=9}}
        match vec.get(one,1) {Some(n)=>{error=10} None=>{}}
        (again,status3)=vec.push(move one,77)
        {v=vec.view(again)\nif v.len!=2 || v[0]!=10 || v[1]!=77 {error=11}}
        (changed,status4)=vec.set(move again,0,42)
        (single,last2)=vec.pop(move changed)
        (empty,first)=vec.pop(move single)
        match first {Some(n)=>{if n!=42 {error=12}} None=>{error=13}}
        (still_empty,missing)=vec.pop(move empty)
        match missing {Some(n)=>{error=14} None=>{}}
        if vec.len(still_empty)!=0 {error=15}
        x=vec.release(move still_empty)'''))

    def test_zero_capacity_and_empty_view(self):
        self.run_source(with_vec('''
        (a,status)=vec.push(move initial,9)
        match status {Ok(done)=>{error=3} Err(e)=>{}}
        (b,item)=vec.pop(move a)
        match item {Some(n)=>{error=4} None=>{}}
        match vec.get(b,0) {Some(n)=>{error=5} None=>{}}
        {v=vec.view(b)\nif v.len!=0 {error=6}}
        x=vec.release(move b)''',capacity=0,region_capacity=0))
        self.run_source(with_vec('{v=vec.view(initial)\nx=v[0]}\nr=vec.release(move initial)',capacity=0),trap=True)

    def test_loops_phi_scopes_break_continue(self):
        self.run_source(with_vec('''var current=move initial
        var i=0
        while i<10 {
          (next,status)=vec.push(move current,i)
          (empty,item)=vec.pop(move next)
          current=move empty
          match item {Some(n)=>{if n!=i {error=3}} None=>{error=4}}
          {v=vec.view(current)\nif v.len!=0 {error=5}}
          i=i+1
          if i==3 {continue}
          if i==9 {break}
        }
        x=vec.release(move current)'''))

    def test_large_element_get_pop_snapshot_survives_close(self):
        source='''fn main()->u32:alloc {
        match memory.create(4096){Err(e)=>{return 1} Ok(region)=>{
          match vec.with_capacity<[u8;128]>(region,2){
            Err(e)=>{c=memory.close(move region)\nreturn 2}
            Ok(initial)=>{
              (a,status)=vec.push(move initial,[7;128])
              snapshot=vec.get(a,0)
              pending=vec.pop(move a)
              (empty,item)=move pending
              (reused,status2)=vec.push(move empty,[9;128])
              x=vec.release(move reused)
              c=memory.close(move region)
              match snapshot {Some(data)=>{if data[0]!=7 || data[127]!=7 {return 3}} None=>{return 4}}
              match item {Some(data)=>{if data[0]!=7 || data[127]!=7 {return 5}} None=>{return 6}}
              return 0
            }
          }
        }}}'''
        self.run_source(source)

    def test_linear_product_phi_and_loop_backedge(self):
        self.run_source(with_vec('''var pending=vec.pop(move initial)
          var i=0
          while i<3 {
            if i==1 {
              (current,item)=move pending
              (filled,status)=vec.push(move current,i)
              pending=vec.pop(move filled)
            } else {
              (current,item)=move pending
              pending=vec.pop(move current)
            }
            i=i+1
          }
          (empty,item)=move pending
          x=vec.release(move empty)'''))

    def test_zero_sized_elements_and_large_invalid_index(self):
        self.run_source('struct Empty {}\n'+with_vec('''
          (filled,status)=vec.push(move initial,Empty())
          match vec.get(filled,4294967295) {Some(v)=>{error=3} None=>{}}
          (empty,item)=vec.pop(move filled)
          match item {Some(v)=>{} None=>{error=4}}
          x=vec.release(move empty)''',element='Empty',region_capacity=0))

    def test_nested_struct_elements_and_large_product_generic_abi(self):
        source='''struct Record {tag:u32,data:[u8;128]}
        fn pass<T>(value:T)->T{return move value}
        '''+with_vec('''
        (a,status)=vec.push(move initial,Record(42,[7;128]))
        result=pass(vec.pop(move a))
        (empty,item)=move result
        match item {Some(record)=>{if record.tag!=42 || record.data[127]!=7 {error=3}} None=>{error=4}}
        x=vec.release(move empty)''',element='Record')
        self.run_source(source)

    def test_argument_effects_before_full_and_out_of_bounds(self):
        source='''fn effect()->u32:io {
        match console.write("E"){Ok(n)=>{} Err(e)=>{}}
        return 7}
        '''+with_vec('''
        (a,status)=vec.push(move initial,effect())
        (b,updated)=vec.set(move a,0,effect())
        x=vec.release(move b)''',capacity=0).replace('main()->u32:alloc','main()->u32:io,alloc')
        self.run_source(source,stdout=b'EE')

    def test_argument_trap_remains_observable_even_when_full(self):
        source='''fn fail()->u32:io {
          match console.write("before"){Ok(n)=>{} Err(e)=>{}}
          n:u8=255
          return u32(n+1)
        }
        '''+with_vec('(next,status)=vec.push(move initial,fail())\nx=vec.release(move next)',capacity=0).replace('main()->u32:alloc','main()->u32:io,alloc')
        self.run_source(source,stdout=b'before',trap=True)

    def test_allocation_failure_atomicity_and_release_does_not_reclaim(self):
        self.run_source('''fn main()->u32:alloc {
        match memory.create(8){Err(e)=>{return 1} Ok(region)=>{
          match vec.with_capacity<u64>(region,2){Err(e)=>{} Ok(v)=>{x=vec.release(move v)\nc=memory.close(move region)\nreturn 2}}
          match vec.with_capacity<u64>(region,1){Err(e)=>{c=memory.close(move region)\nreturn 3} Ok(v)=>{x=vec.release(move v)}}
          match vec.with_capacity<u8>(region,1){Err(e)=>{} Ok(v)=>{x=vec.release(move v)\nc=memory.close(move region)\nreturn 4}}
          c=memory.close(move region)\nreturn 0
        }}}''')
