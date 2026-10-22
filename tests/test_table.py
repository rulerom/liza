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
