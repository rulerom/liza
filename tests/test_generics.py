"""Monomorphization preserves ordinary typing, ownership and execution."""
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
from liza.modules import load_program


def compile_source(source):
    return lower(Parser(source).parse())


class GenericTests(unittest.TestCase):
    def test_inference_cache_and_capacity(self):
        module=compile_source('''
struct Pair<T,U> { a:T, b:U }
struct Buffer<T,N:u32> { data:[T;N] }
fn identity<T>(x:T)->T { return move x }
fn length<T,N:u32>(x:[T;N])->u32 { return N }
fn main()->u32 {
    p=Pair<u32,u64>(1,2)
    b:Buffer<u8,4> = Buffer([3;4])
    a=identity(p.a)
    c=identity<u32>(a)
    return length(b.data) + c
}''')
        instances=module.specializations
        self.assertEqual(sum(i['declaration']=='identity' for i in instances),1)
        self.assertTrue(any(i['arguments']==['u8','4'] for i in instances))
        self.assertEqual(json.loads(dump(module))['specializations'],instances)

    def test_same_specialization_recursion(self):
        module=compile_source('''fn down<T>(x:T)->T {
if x == 0 { return x }
return down<T>(x-1)
}
fn main()->u32 { return down(5) }''')
        self.assertEqual(len(module.specializations),1)

    def test_failures_have_specialization_chain(self):
        for source,pattern in [
            ('fn bad<T>(x:T)->T{return copy x}\nfn main()->u32 { return bad<bool>(true) }','expected bool'),
            ('fn bad<T>(x:T)->T{return x+1}\nfn main()->u32 { x=bad<bool>(true)\nreturn 0 }','specialization: bad<bool>'),
            ('fn bad<T>(x:T)->T{return bad<[T;1]>([x])}\nfn main()->u32{return bad(1)}','expanding/polymorphic'),
            ('struct B<T,N:u32>{a:[T;N]}\nfn main()->u32{x:B<u8,4294967296>=B([1])\nreturn 0}','u32'),
        ]:
            with self.subTest(pattern=pattern),self.assertRaisesRegex((CompileError,ValueError),pattern):
                compile_source(source)

    def test_declaration_site_privacy(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'lib.liza').write_text('pub fn extract<T>(x:T)->u32{return x.secret}')
            (root/'main.liza').write_text('import lib\nstruct Secret {secret:u32}\nfn main()->u32{return lib.extract(Secret(1))}')
            with self.assertRaisesRegex(CompileError,'private field'):
                lower(load_program(root/'main.liza'))

    def test_resource_specializations_and_bounds(self):
        source="""fn identity<T>(x:T)->T{return move x}
fn transfer(x:File)->File{return identity(move x)}
fn main()->u32{return 0}"""
        compile_source(source)
        for body in ('return copy x', 'return x'):
            with self.assertRaisesRegex(CompileError,'specialization: identity<File>'):
                compile_source(source.replace('return move x',body))
        with self.assertRaisesRegex(CompileError,'File is not copyable'):
            compile_source(source.replace('identity<T>','identity<T:copyable>'))
        with self.assertRaisesRegex(CompileError,'non-generic'):
            compile_source('fn f(x:u32)->u32{return x} fn main()->u32{return f<u32>(0)}')

    def test_effects_and_nominal_instances(self):
        with self.assertRaisesRegex(CompileError,'pure function cannot call io'):
            compile_source('fn output<T>(x:T)->T : io {return move x} fn main()->u32{return output(0)}')
        with self.assertRaisesRegex(CompileError,'expected'):
            compile_source('struct B<T,N:u32>{a:[T;N]} fn main()->u32 {a:B<u8,1>=B<u8,2>([0;2])\nreturn 0}')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            files={
              'common.liza':'pub struct Box<T>{pub value:T}',
              'a.liza':'import common\npub fn make()->common.Box<u32>{return common.Box(7)}',
              'b.liza':'import common\npub fn read(x:common.Box<u32>)->u32{return x.value}',
              'main.liza':'import a\nimport b\nfn main()->u32{return b.read(a.make())}' }
            for name,text in files.items():(root/name).write_text(text)
            module=lower(load_program(root/'main.liza'))
            self.assertEqual(sum(i['declaration']=='common.Box' for i in module.specializations),1)

    @unittest.skipUnless(shutil.which('clang'),'clang required')
    def test_repeat_evaluates_once_and_preserves_phi_edges(self):
        source='''fn emit<T>(x:T)->T:io {
            match console.write("x") {Ok(n)=>{} Err(e)=>{}}
            return move x
        }
        fn main()->u32:io {
            empty:[u32;0]=[emit(9);0]
            var values:[u32;128]=[0;128]
            var i=0
            while i<3 {
                values=[emit(i);128]
                i=i+1
            }
            return values[127]-2
        }'''
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);module=compile_source(source)
            ir=root/'test.ll';ir.write_text(llvm(module))
            exe=root/('test.exe' if sys.platform=='win32' else 'test')
            for opt in ('0','2'):
                subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*link_flags(module),'-o',str(exe)],check=True,capture_output=True)
                result=subprocess.run([str(exe)],capture_output=True,timeout=5)
                self.assertEqual((result.returncode,result.stdout),(0,b'xxxx'))

    @unittest.skipUnless(shutil.which('clang'),'clang required')
    def test_generic_table_values_snapshots_and_ids(self):
        library=(Path(__file__).resolve().parents[1]/'examples/tables/value_table.liza').read_text()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'table.liza').write_text(library)
            for record,zero,one,two,read in [
                ('u32','0','1','2','v'),
                ('Record','Record(0,0)','Record(1,10)','Record(2,20)','v.a')]:
                source="""import table
struct Record { a:u32,b:u64 }
fn main()->u32 {
 var t=table.empty<RECORD,4>(ZERO)
 a=table.add(move t,ONE)
 t=a.table
 match a.result {
  Err(e)=>{return 1}
  Ok(id)=>{
   snapshot=copy t
   changed=table.edit(move t,id,TWO)
   t=changed.table
   match table.get(snapshot,id) {None=>{return 2} Some(v)=>{if READ != 1 {return 3}}}
   removed=table.del(move t,id)
   t=removed.table
   added=table.add(move t,TWO)
   t=added.table
   match table.get(t,id) {Some(v)=>{return 4} None=>{}}
   match added.result {Err(e)=>{return 5} Ok(next)=>{
    if next.slot != id.slot || next.generation == id.generation {return 6}
    match table.get(t,next) {None=>{return 7} Some(v)=>{return READ-2}}
   }}
  }
 }
}
""".replace('RECORD',record).replace('ZERO',zero).replace('ONE',one).replace('TWO',two).replace('READ',read)
                entry=root/'main.liza';entry.write_text(source)
                (root/'test.ll').write_text(llvm(lower(load_program(entry))))
                exe=root/('test.exe' if sys.platform=='win32' else 'test')
                for opt in ('0','2'):
                    subprocess.run(['clang','-Wno-override-module','-O'+opt,str(root/'test.ll'),'-o',str(exe)],check=True,capture_output=True)
                    result=subprocess.run([str(exe)],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,0,result.stderr)

    @unittest.skipUnless(shutil.which('clang'),'clang required')
    def test_native_values_traps_and_repeat(self):
        cases=[('''struct B<T,N:u32>{data:[T;N]}
fn fill<T,N:u32>(x:T)->B<T,N>{return B<T,N>([x;N])}
fn identity<T>(x:T)->T{return move x}
fn main()->u32{b=fill<u32,4096>(42)\nreturn identity(b.data[3000])-42}''',False),
        ('''fn increment<T>(x:T)->T{return x+1}
fn main()->u32{x=increment<u8>(255)\nreturn 0}''',True),
        ('''fn increment<T>(x:T)->T{return x+1}
fn main()->u32{x:[u8;0]=[increment<u8>(255);0]\nreturn 0}''',True)]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            executable=root/('test.exe' if sys.platform=='win32' else 'test')
            for source,trap in cases:
                (root/'test.ll').write_text(llvm(compile_source(source)))
                for opt in ('0','2'):
                    subprocess.run(['clang','-Wno-override-module','-O'+opt,str(root/'test.ll'),'-o',str(executable)],check=True,capture_output=True)
                    result=subprocess.run([str(executable)],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode!=0,trap)
