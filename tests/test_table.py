"""Table source fixtures and storage-backend snapshot regressions."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from liza.frontend import Parser
from liza.ir import lower
from liza.backend import llvm
from tools.check_table_cost import source_for
import test_io


class TableTypes(unittest.TestCase):
    def test_both_capacities_use_existing_ir(self):
        for n in (64,4096):
            module=lower(Parser(source_for(n)).parse())
            self.assertEqual(dict(module.structs['ConnectionTable'].fields)['slots'],f'[ConnectionSlot;{n}]')
            self.assertTrue(all(fn.effect_contract=='pure' for fn in module))
            self.assertTrue(any(op.op=='array.update' for fn in module for b in fn.blocks for op in b.operations))
            output=llvm(module)
            self.assertNotIn('byval(',output)
            self.assertNotRegex(output,r'\b(nsw|nuw|inbounds)\b')


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class TableStorageNative(unittest.TestCase):
    build=test_io.ConsoleNative.build

    def test_parallel_phi_snapshots_and_nested_large_elements(self):
        source='''struct Big { values:[u32;128] }
        fn identity(b:Big)->Big{return b}
        fn main()->u32 {
            var a=Big([VALUES])
            var b=a
            b.values[0]=100
            original=copy a
            var previous=b
            var i=0
            while i<7 {
                previous=a
                old=a
                a=identity(b)
                b=old
                a.values[1]=i
                if previous.values[0]!=b.values[0] {return 1}
                i=i+1
                if i<3 {continue}
                if i==7 {break}
            }
            if a.values[0]!=100 || b.values[0]!=0 || previous.values[0]!=0 {return 2}
            if original.values[1]!=1 || a.values[1]!=6 || b.values[1]!=5 {return 3}
            var nested=[a,b]
            snapshot=copy nested
            if true {
                v=view nested[0..2]
                var piece=v[0]
                piece.values[0]=99
                if v[0].values[0]!=100 {return 4}
            }
            nested[0].values[0]=7
            if snapshot[0].values[0]!=100 || nested[0].values[0]!=7 {return 5}
            var result:Option<Big> = Some(a)
            var count=0
            while count<2 {
                match result {
                    None=>{return 6}
                    Some(value)=>{
                        var changed=value
                        changed.values[2]=count
                        result=Some(move changed)
                    }
                }
                count=count+1
            }
            match result {None=>{return 7} Some(value)=>{if value.values[2]!=1 {return 8}}}
            if a.values[2]!=2 {return 9}
            return 0
        }'''.replace('VALUES',','.join(map(str,range(128))))
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                result=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr)

    def test_table_example(self):
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source_for(64),opt)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=10).returncode,0)


REUSE_LIBRARY='''
struct Big { values:[u32;128] }
struct Updated { value:Big, status:u32 }
fn change(input:Big, index:u32, value:u32)->Updated {
    var next=move input
    next.values[index]=value
    return Updated(move next,17)
}
fn competing(input:Big, flag:bool)->Updated {
    a=Updated(input,1)
    b=Updated(input,2)
    if flag {return a}
    return b
}
fn initial()->Big {return Big([VALUES])}
'''.replace('VALUES',','.join(map(str,range(128))))


class StorageProofs(unittest.TestCase):
    def test_owned_variant_and_live_observers(self):
        from tools.check_table_cost import function_body
        source=REUSE_LIBRARY+'''
        fn unique()->u32 {
            changed=change(initial(),3,99)
            return changed.value.values[3]
        }
        fn snapshot()->u32 {
            original=initial()
            retained=copy original
            changed=change(move original,3,99)
            return retained.values[3]+changed.value.values[3]
        }
        fn borrowed()->u32 {
            original=initial()
            v=view original.values[0..128]
            changed=change(original,3,99)
            return v[3]+changed.value.values[3]
        }
        fn main()->u32{return 0}
        '''
        # Views currently require an array binding, not a field projection.
        source=source.replace('v=view original.values[0..128]', 'array=original.values\n v=view array[0..128]')
        output=llvm(lower(Parser(source).parse()))
        self.assertIn('@liza___liza_owned_change',function_body(output,'unique'))
        for name in ('snapshot','borrowed'):
            self.assertNotIn('@liza___liza_owned_change',function_body(output,name))
        self.assertNotIn('define void @liza___liza_owned_competing',output)
        owned=function_body(output,'__liza_owned_change')
        self.assertNotRegex(owned,r'@llvm.mem(?:cpy|move)')
        self.assertIn('@llvm.trap()',owned)


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class StorageReuseNative(unittest.TestCase):
    build=test_io.ConsoleNative.build

    def test_snapshots_views_branches_and_repeated_calls(self):
        source=REUSE_LIBRARY+'''
        fn main()->u32 {
            original=initial()
            snapshot=copy original
            changed=change(move original,3,99)
            if snapshot.values[3]!=3 || changed.value.values[3]!=99 {return 1}
            var table=changed.value
            var i:u32=0
            while i<20 {
                old=copy table
                next=change(move table,i,i+100)
                table=next.value
                if old.values[i]==table.values[i] {return 2}
                i=i+1
            }
            i=0
            while i<20 {
                next=change(move table,i,i+200)
                table=next.value
                i=i+1
                if i<5 {continue}
                if i==20 {break}
            }
            if table.values[0]!=200 || table.values[19]!=219 || table.values[20]!=20 {return 3}
            array=[snapshot,table]
            v=view array[0..2]
            piece=v[0]
            changed_piece=change(move piece,0,777)
            if v[0].values[0]!=0 || changed_piece.value.values[0]!=777 {return 4}
            a=competing(snapshot,true)
            b=competing(snapshot,false)
            if a.status!=1 || b.status!=2 {return 5}
            return 0
        }
        '''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                r=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(r.returncode,0,r.stderr)

    def test_owned_update_keeps_runtime_bounds_trap(self):
        # Unique call chooses the owned implementation; index remains opaque
        # across the public scalar test-driver ABI.
        source=REUSE_LIBRARY+'''
        fn probe(index:u32)->u32 {
            changed=change(initial(),index,7)
            return changed.status
        }
        fn main()->u32{return 0}
        '''
        from tools.check_table_cost import function_body
        output=llvm(lower(Parser(source).parse()))
        self.assertIn('@liza___liza_owned_change',function_body(output,'probe'))
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as directory:
                d=Path(directory)
                (d/'test.ll').write_text(output.replace('define i32 @main()', 'define i32 @unused_main()'))
                (d/'test.c').write_text('#include <stdint.h>\n#include <stdlib.h>\nextern uint32_t liza_probe(uint32_t);\nint main(int argc,char **argv){return liza_probe((uint32_t)strtoul(argv[1],0,10))==17?0:1;}')
                exe=d/('test.exe' if __import__('sys').platform=='win32' else 'test')
                subprocess.run(['clang',opt,'-Wno-override-module',str(d/'test.ll'),str(d/'test.c'),'-o',str(exe)],check=True,capture_output=True)
                self.assertEqual(subprocess.run([str(exe),'127'],capture_output=True).returncode,0)
                self.assertNotEqual(subprocess.run([str(exe),'128'],capture_output=True).returncode,0)
