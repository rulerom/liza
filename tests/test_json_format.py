"""Streaming format: native O0/O2, exact lexemes, bounded storage and I/O errors."""
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from liza.modules import load_program
from liza.ir import lower
from liza.frontend import CompileError

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'examples/apps/liza_json.liza'

@unittest.skipUnless(shutil.which('clang'),'requires clang')
class JsonFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
        cls.executables=[]
        for opt in ('0','2'):
            exe=cls.root/('format'+opt+('.exe' if sys.platform=='win32' else ''))
            subprocess.run([sys.executable,'-m','liza','build',str(ENTRY),'--project-root',str(ROOT/'examples'),'-O',opt,'-o',str(exe)],check=True,capture_output=True)
            cls.executables.append(exe)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def run_json(self,exe,data,command='format'):
        path=self.root/'данные.json';path.write_bytes(data)
        return subprocess.run([str(exe),command,str(path)],capture_output=True,timeout=60)

    def test_exact_layout_lexemes_and_empty_containers(self):
        cases=[
            (b' { } ',b'{}\n'),(b' [ ] ',b'[]\n'),
            (b'1.2300E+009',b'1.2300E+009\n'),
            (b'{"x":-0,"x":[true,{},[],false,null]}',
             b'{\n  "x": -0,\n  "x": [\n    true,\n    {},\n    [],\n    false,\n    null\n  ]\n}\n'),
            (b'{"s":"a\\n\\t\\/\\\\\\\"\\u0000\\uD83D\\uDE80"}',
             b'{\n  "s": "a\\n\\t\\/\\\\\\\"\\u0000\\uD83D\\uDE80"\n}\n'),
            ('["🚀","Привет","é"]'.encode(),'[\n  "🚀",\n  "Привет",\n  "é"\n]\n'.encode()),
        ]
        for exe in self.executables:
            for data,expected in cases:
                with self.subTest(opt=exe.name,data=data):
                    r=self.run_json(exe,data)
                    self.assertEqual((r.returncode,r.stdout,r.stderr),(0,expected,b''))
                    again=self.run_json(exe,r.stdout)
                    self.assertEqual((again.returncode,again.stdout),(0,expected))

    def test_generated_documents_independent_pretty_print(self):
        rng=random.Random(1984)
        def value(depth):
            if depth==0:return rng.choice([None,True,False,rng.randrange(-10000,10000),'a🚀\n"\\é'])
            return rng.choice([value(0),[value(depth-1) for _ in range(rng.randrange(4))],
                               {str(i):value(depth-1) for i in range(rng.randrange(4))}])
        for _ in range(40):
            obj=value(3);ascii=bool(rng.randrange(2))
            data=json.dumps(obj,ensure_ascii=ascii,separators=(',',':')).encode()
            expected=(json.dumps(obj,ensure_ascii=ascii,indent=2)+'\n').encode()
            for exe in self.executables:
                r=self.run_json(exe,data)
                self.assertEqual((r.returncode,r.stdout,r.stderr),(0,expected,b''))

    def test_chunk_boundaries_unicode_escapes_and_numbers(self):
        suffixes=['🚀'.encode(),b'\\uD83D\\uDE80',b'\\\"',b'\\\\']
        for suffix in suffixes:
            for offset in range(2044,2050):
                data=b'["'+b'a'*offset+suffix+b'"]'
                expected=b'[\n  "'+b'a'*offset+suffix+b'"\n]\n'
                for exe in self.executables:
                    r=self.run_json(exe,data)
                    self.assertEqual((r.returncode,r.stdout),(0,expected))
        for exe in self.executables:
            data=b'1'+b'0'*10000+b'.12345e-999'
            r=self.run_json(exe,data)
            self.assertEqual((r.returncode,r.stdout),(0,data+b'\n'))

    def test_depth_limit_and_error_offsets(self):
        bad=[b'',b'[',b'{"x":1,}',b'01',b'1 2',b'[]true',b'"\\uD800"',b'"\\uDC00"',
             b'"\\uD800\\u0000"',b'"\\x"',b'"\xff"',b'"\xf0\x9f"',b'['*65,b'\xef\xbb\xbf0']
        for exe in self.executables:
            for data in bad:
                r=self.run_json(exe,data)
                original=self.run_json(exe,data,'check')
                self.assertIn(r.returncode,(1,4))
                self.assertEqual((r.returncode,r.stderr),(original.returncode,original.stderr))
            data=b'['*64+b'0'+b']'*64
            r=self.run_json(exe,data)
            self.assertEqual(r.returncode,0)
            self.assertEqual(json.loads(r.stdout),json.loads(data))

    def test_large_tokens_and_late_failure(self):
        for exe in self.executables:
            data=b'["'+b'a'*2_000_000+b'"]'
            r=self.run_json(exe,data)
            self.assertEqual((r.returncode,r.stdout),(0,b'[\n  "'+b'a'*2_000_000+b'"\n]\n'))
            bad=b'"'+b'a'*10000+b'\xff"'
            r=self.run_json(exe,bad)
            self.assertEqual((r.returncode,r.stderr),(1,b'InvalidUtf8 at byte 10001\n'))
            self.assertGreater(len(r.stdout),0) # streaming, not transactional
            self.assertTrue(bad.startswith(r.stdout))

    def test_fixed_allocations_and_private_state(self):
        module=lower(load_program(ENTRY,ROOT/'examples'))
        allocations=[(f.name,o.op) for f in module for b in f.blocks for o in b.operations if o.op in ('region.create','region.alloc','vec.create','vec.reserve')]
        self.assertEqual(len(allocations),2)
        self.assertTrue(all(name=='apps.liza_json.format' for name,op in allocations))
        for f in module:
            if f.name.startswith('text.json_format.'):
                self.assertEqual(f.effect_contract,'pure')

    def test_private_state_and_utf8_snapshot(self):
        source="""import text.json_format
        fn main()->u32{
            var s=text.json_format.create()
            a:[u8;2]=[34,240];var i:u32=0
            while i<2 {match text.json_format.feed_byte(borrow mut s,a[i]){
                Err(e)=>{return 1}Ok(piece)=>{if i==1 && piece.length!=0{return 2}}
            }i=i+1}
            snapshot=copy s
            b:[u8;3]=[159,154,128];i=0
            while i<3 {match text.json_format.feed_byte(borrow mut s,b[i]){
                Err(e)=>{return 3}Ok(piece)=>{
                    if i<2 && piece.length!=0{return 4}
                    if i==2 {
                        if piece.length!=4 || piece.data[0]!=240 || piece.data[3]!=128{return 5}
                    }
                }
            }i=i+1}
            match text.json_format.feed_byte(borrow mut s,34){Err(e)=>{return 6}Ok(p)=>{}}
            match text.json_format.finish(s){Err(e)=>{return 7}Ok(n)=>{if n!=6{return 8}}}
            match text.json_format.finish(snapshot){Ok(n)=>{return 9}Err(e)=>{if e.offset!=1{return 10}}}
            return 0
        }"""
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);shutil.copytree(ROOT/'examples/text',root/'text')
            entry=root/'probe.liza';entry.write_text(source)
            for opt in ('0','2'):
                exe=root/('probe'+('.exe' if sys.platform=='win32' else ''))
                subprocess.run([sys.executable,'-m','liza','build',str(entry),'-O',opt,'-o',str(exe)],check=True,capture_output=True)
                self.assertEqual(subprocess.run([str(exe)],timeout=10).returncode,0)
            entry.write_text('import text.json_format\nfn main()->u32{s=text.json_format.create();return s.depth}')
            with self.assertRaisesRegex(CompileError,'private'):
                lower(load_program(entry))

    def test_usage_and_missing_file(self):
        for exe in self.executables:
            r=subprocess.run([str(exe),'format',str(self.root/'missing')],capture_output=True,timeout=10)
            self.assertEqual((r.returncode,r.stderr),(3,b'Cannot open file\n'))
            r=subprocess.run([str(exe),'format'],capture_output=True,timeout=10)
            self.assertEqual(r.returncode,2)
            self.assertIn(b'errors may leave partial output',r.stderr)
            self.assertIn(b'Do not redirect to the input file',r.stderr)

    @unittest.skipUnless(os.name=='posix','closed POSIX pipe')
    def test_output_failure_is_error_not_trap(self):
        path=self.root/'pipe.json';path.write_bytes(b'"'+b'a'*10000+b'"')
        for exe in self.executables:
            reader,writer=os.pipe();os.close(reader)
            try:
                r=subprocess.run([str(exe),'format',str(path)],stdout=writer,stderr=subprocess.PIPE,timeout=30)
            finally:os.close(writer)
            self.assertEqual((r.returncode,r.stderr),(3,b'Cannot read or write JSON\n'))

if __name__=='__main__':unittest.main()
