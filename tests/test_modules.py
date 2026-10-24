"""Module paths/identity/privacy and unchanged whole-program value semantics."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
from liza.frontend import CompileError
from liza.modules import load_program
from liza.ir import lower, dump
from liza.backend import llvm
from liza.stdlib import link_flags


class ModuleTests(unittest.TestCase):
    def program(self, files, entry='main.liza'):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)
        for name,text in files.items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text,encoding='utf-8')
        return root,root/entry

    def compile(self, files):
        root,entry=self.program(files)
        return lower(load_program(entry,root))

    def reject(self,files,pattern):
        with self.assertRaisesRegex((CompileError,ValueError),pattern):self.compile(files)

    def test_diamond_identity_and_stable_declaration_ids(self):
        module=self.compile({
            'common.liza':'pub struct Id { pub value:u32 }',
            'a.liza':'import common\npub fn make()->common.Id{return common.Id(42)}',
            'b.liza':'import common\npub fn read(x:common.Id)->u32{return x.value}',
            'main.liza':'import a\nimport b\nfn main()->u32{return b.read(a.make())}'})
        self.assertEqual(list(module.structs),['common.Id'])
        data=json.loads(dump(module));self.assertEqual(data['version'],19)
        self.assertEqual(data['modules'],['a','b','common','main'])
        self.assertEqual(sum(d['id']=='common.Id' for d in data['declarations']),1)
        self.assertIn('a.make',llvm(module))

    def test_nominal_types_and_explicit_imports(self):
        files={'a.liza':'pub struct Id {pub value:u32}',
               'b.liza':'pub struct Id {pub value:u32}\npub fn take(x:Id)->u32{return x.value}',
               'main.liza':'import a\nimport b\nfn main()->u32{return b.take(a.Id(1))}'}
        self.reject(files,'expected b.Id, got a.Id')
        files['main.liza']='import b\nfn main()->u32{return b.take(a.Id(1))}'
        self.reject(files,'unknown or unimported')

    def test_private_declarations_fields_and_constructors(self):
        library='''pub struct Box {hidden:u32, pub shown:u32}
        struct Secret {x:u32}
        fn secret()->u32{return 1}
        pub fn make()->Box{return Box(1,2)}'''
        for body,error in [
            ('return a.secret()','private'),
            ('x:a.Secret=a.Secret(1);return 0','private'),
            ('x=a.make();return x.hidden','private field'),
            ('var x=a.make();x.hidden=3;return 0','private field'),
            ('x=a.Box(1,2);return 0','private fields')]:
            with self.subTest(body=body):
                self.reject({'a.liza':library,'main.liza':'import a\nfn main()->u32{'+body+'}'},error)
        self.compile({'a.liza':library,'main.liza':'import a\nfn main()->u32{var x=a.make();x.shown=3;return x.shown}'})
        for exported in ['pub fn leak()->Hidden{return Hidden(1)}',
                         'pub struct Open {pub value:Hidden}', 'pub enum Open {Value(Hidden)}']:
            self.reject({'a.liza':'struct Hidden {x:u32}\n'+exported,
                         'main.liza':'import a\nfn main()->u32{return 0}'},'public interface exposes private type')

    def test_import_cycles_paths_and_namespaces(self):
        self.reject({'a.liza':'import b','b.liza':'import a','main.liza':'import a\nfn main()->u32{return 0}'},'main -> a -> b -> a')
        self.reject({'main.liza':'import missing\nfn main()->u32{return 0}'},'not found')
        self.reject({'main.liza':'import file\nfn main()->u32{return 0}'},'reserved')
        self.reject({'a.liza':'','main.liza':'import a\nimport a\nfn main()->u32{return 0}'},'duplicate import')
        self.reject({'a.liza':'','main.liza':'import a\nfn main()->u32{a=1;return a}'},'namespace')
        self.reject({'A.liza':'','main.liza':'import a\nfn main()->u32{return 0}'},'not found')
        root,entry=self.program({'lib/value.liza':'pub fn get()->u32{return 42}',
                                 'app/main.liza':'import lib.value\nfn main()->u32{return lib.value.get()}'},'app/main.liza')
        lower(load_program(entry,root))
        with self.assertRaisesRegex(CompileError,'not found'):load_program(entry)
        with self.assertRaisesRegex(ValueError,'inside project root'):load_program(entry,root/'lib')
        if hasattr(__import__('os'),'symlink'):
            try:(root/'alias.liza').symlink_to(root/'lib/value.liza')
            except OSError:return  # Windows runner may lack symlink privileges.
            (root/'main.liza').write_text('import alias\nfn main()->u32{return 0}')
            with self.assertRaisesRegex(CompileError,'symlink'):load_program(root/'main.liza')

    def test_nested_import_order_and_namespace_collisions(self):
        files={'a.liza':'', 'a/b.liza':'pub enum E {Value(u32)}',
               'main.liza':''}
        for imports in ['import a\nimport a.b', 'import a.b\nimport a']:
            files['main.liza']=imports+'''
fn main()->u32 {
                x=a.b.E.Value(7)
                match x {a.b.E.Value(n)=>{return n}}
            }'''
            self.compile(files)
        files['a.liza']='pub enum b {Value(u32)}'
        self.reject(files,'namespace conflicts with declaration')

    def test_entry_identity_and_dependency_diagnostics(self):
        root,entry=self.program({'a.b.liza':'fn main()->u32{return 0}',
                                 'a/b.liza':'fn main()->u32{return 1}'},'a.b.liza')
        with self.assertRaisesRegex(ValueError,'module identifiers'):load_program(entry)
        (root/'console.liza').write_text('fn main()->u32{return 0}')
        with self.assertRaisesRegex(CompileError,'reserved'):load_program(root/'console.liza')
        (root/'main.liza').write_text('import bad\nfn main()->u32{return 0}')
        (root/'bad.liza').write_text('@')
        with self.assertRaises(CompileError) as caught:load_program(root/'main.liza')
        self.assertIn('bad.liza:1:1',str(caught.exception))

    def test_effects_moves_views_resources_and_qualified_enums(self):
        library='''pub enum E {Yes(u32), No}
        pub fn echo(x:u32)->u32{return x}
        pub fn first(x:View<u8>)->u8{return x[0]}
        pub fn output()->u32:io {r=console.println("ok");return 0}
        pub fn close(f:File)->Result<u32,FileError>:io {return file.close(move f)}'''
        self.reject({'lib.liza':library,'main.liza':'import lib\nfn main()->u32{return lib.output()}'},'io')
        self.reject({'lib.liza':library,'main.liza':'import lib\nfn main()->u32{x=1;y=lib.echo(move x);return x}'},'move')
        self.compile({'lib.liza':library,'main.liza':'''import lib
        fn main()->u32 {
            data:[u8;2]=[1,2]; v=view data[0..2]; first=lib.first(v)
            x:lib.E=lib.E.Yes(u32(first))
            match x {lib.E.Yes(n)=>{return lib.echo(n)} lib.E.No=>{return 0}}
        }'''})


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class ModuleNativeTests(unittest.TestCase):
    program=ModuleTests.program

    def test_modular_update_and_cli(self):
        root,entry=self.program({'model.liza':'''pub struct Big {data:[u32;128]}
        pub struct Changed {pub value:Big, pub status:u32}
        pub fn empty()->Big {return Big(['''+','.join(['0']*128)+'''])}
        pub fn edit(input:Big,index:u32,value:u32)->Changed {
            var next=move input;next.data[index]=value;return Changed(move next,0)
        }
        pub fn get(input:Big,index:u32)->u32{return input.data[index]}''',
        'main.liza':'''import model
        fn main()->u32 {
            var table=model.empty();snapshot=copy table
            var i=0
            while i<100 {
                changed=model.edit(move table,i%128,i+1)
                table=changed.value;i=i+1
            }
            if model.get(snapshot,99)!=0 || model.get(table,99)!=100 {return 1}
            return 0
        }'''})
        module=lower(load_program(entry));output=llvm(module)
        self.assertIn('@liza___liza_owned_model.edit',output)
        from tools.check_table_cost import function_body
        self.assertNotRegex(function_body(output,'__liza_owned_model.edit'),r'@llvm.mem(?:cpy|move)')
        (root/'program.ll').write_text(output)
        for opt in ('0','2'):
            exe=root/('test.exe' if __import__('sys').platform=='win32' else 'test')
            subprocess.run(['clang','-Wno-override-module','-O'+opt,str(root/'program.ll'),*link_flags(module),'-o',str(exe)],check=True,capture_output=True)
            self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=10).returncode,0)
        import sys
        result=subprocess.run([sys.executable,'-m','liza','check',str(entry),'--project-root',str(root)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        original=(root/'model.liza').read_text()
        result=subprocess.run([sys.executable,'-m','liza','emit-ir',str(entry),'-o',str(root/'model.liza')],capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((root/'model.liza').read_text(),original)

    def test_resource_and_view_calls_across_modules(self):
        root,entry=self.program({'api.liza':'''pub fn first(data:View<u8>)->u8{return data[0]}
        pub fn close(f:File)->Result<u32,FileError>:io{return file.close(move f)}''',
        'main.liza':'''import api
        fn main()->u32:io {
            data:[u8;2]=[42,7];v=view data[0..2]
            if api.first(v)!=42 {return 1}
            match file.open("PATH") {
                Err(error)=>{return 2}
                Ok(handle)=>{
                    match api.close(move handle) {Ok(n)=>{return 0} Err(error)=>{return 3}}
                }
            }
        }'''})
        path=root/'bytes.bin';path.write_bytes(b'hello')
        entry.write_text(entry.read_text().replace('"PATH"',json.dumps(str(path))))
        module=lower(load_program(entry));ir=root/'native.ll';ir.write_text(llvm(module))
        for opt in ('0','2'):
            exe=root/('resource.exe' if __import__('sys').platform=='win32' else 'resource')
            subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*link_flags(module),'-o',str(exe)],check=True,capture_output=True)
            self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=10).returncode,0)
