"""Partition invariance, independent oracle, private state and EOF snapshots."""
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm
from liza.modules import load_program
import test_io
from tools.check_utf8_stream_cost import build,probe


def expected(chunks):
    try:return (0,len(b''.join(chunks).decode('utf-8')))
    except UnicodeDecodeError as e:return (1,e.start)


class StreamTypes(unittest.TestCase):
    def test_private_state_and_signature_errors(self):
        for body in ('s.position=1','x=s.remaining','x=Utf8StreamState(0,0,0,0,128,191,0,0)',
                     'x=utf8_stream.feed(s,1)','x=utf8_stream.finish(0)',
                     'x=utf8_stream.create(1)'):
            with self.subTest(body=body),self.assertRaises(CompileError):
                test_io.compile_source('fn main()->u32{var s=utf8_stream.create();'+body+';return 0}')

    def test_module_generic_and_borrow_scope(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/'reader.liza').write_text('pub fn pass<T>(x:T)->T{return move x}\npub fn start()->Utf8StreamState{return utf8_stream.create()}')
            (p/'main.liza').write_text('''import reader
fn main()->u32 {var s=reader.pass(reader.start());var a:[u8;1]=[65]
{v=view a[0..1];s=utf8_stream.feed(s,v)}
a[0]=66;match utf8_stream.finish(s){Ok(n)=>{return u32(n)-1} Err(e)=>{return 2}}}''')
            lower(load_program(p/'main.liza'))
            (p/'main.liza').write_text('fn main()->u32{var s=utf8_stream.create();s.position=1;return 0}')
            with self.assertRaisesRegex(CompileError,'private'):lower(load_program(p/'main.liza'))


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class StreamNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.executables=[build(Path(cls.temp.name)/opt[1:],opt)[0] for opt in ('-O0','-O2')]

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def check(self,cases):
        answers=[expected(c) for c in cases]
        for exe in self.executables:
            actual=probe(exe,cases)
            for c,a,e in zip(cases,actual,answers):
                if a!=e:self.fail(f'{exe}: {c!r}: {a} != {e}')

    def test_every_split_of_boundary_sequences(self):
        samples=[b'',b'\0',b'abc', 'Лиза 😀'.encode(),b'e\xcc\x81',b'\xef\xbb\xbf',
                 b'\xc0\x80',b'\xe0\x9f\xbf',b'\xed\xa0\x80',b'\xf0\x8f\xbf\xbf',
                 b'\xf4\x90\x80\x80',b'\xf5\x80\x80\x80',b'\xe2A\x80',b'\xff',
                 b'\xc2',b'\xe2\x80',b'\xf0\x90\x80']
        samples += [chr(n).encode() for n in (0x7f,0x80,0x7ff,0x800,0xd7ff,0xe000,0xffff,0x10000,0x10ffff)]
        cases=[]
        for s in samples:
            for data in (s,b'abc'+s):
                for i in range(len(data)+1):
                    for j in range(i,len(data)+1):
                        cases.append([data[:i],b'',data[i:j],b'',data[j:]])
        self.check(cases)

    def test_all_byte_pairs_split_and_unsplit(self):
        cases=[]
        for a in range(256):
            for b in range(256):
                cases.extend([[bytes([a,b])],[bytes([a]),b'',bytes([b])]])
        self.check(cases)

    def test_random_partitions_and_valid_unicode(self):
        rng=random.Random(23);cases=[]
        for _ in range(1000):
            data=bytes(rng.randrange(256) for _ in range(rng.randrange(40)))
            points=[rng.randrange(0x110000) for _ in range(12)]
            valid=''.join(chr(n) for n in points if not 0xd800<=n<=0xdfff).encode()
            for s in (data,valid):
                cases.append([s]);cases.append([s[i:i+1] for i in range(len(s))])
                cuts=sorted([0,len(s)]+[rng.randrange(len(s)+1) for _ in range(7)])
                cases.append([s[a:b] for a,b in zip(cuts,cuts[1:])])
        self.check(cases)

    def test_all_scalars_with_fixed_chunk_sizes(self):
        data=''.join(chr(n) for n in range(0x110000) if not 0xd800<=n<=0xdfff).encode()
        self.check([[data[i:i+size] for i in range(0,len(data),size)] for size in (2047,2048,2049)])

    def test_snapshot_copy_finish_and_chunk_lifetime(self):
        source='''fn main()->u32 {
            var state=utf8_stream.create()
            {a:[u8;1]=[240];v=view a[0..1];state=utf8_stream.feed(state,v)}
            snapshot=copy state
            match utf8_stream.finish(state){Ok(n)=>{return 1} Err(e)=>{if e.offset!=0{return 2}}}
            {b:[u8;3]=[159,152,128];v=view b[0..3];state=utf8_stream.feed(state,v)}
            match utf8_stream.finish(state){Ok(n)=>{if n!=1{return 3}} Err(e)=>{return 4}}
            match utf8_stream.finish(snapshot){Ok(n)=>{return 5} Err(e)=>{if e.offset!=0{return 6}}}
            return 0
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=test_io.ConsoleNative.build(self,d,source,opt)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=10).returncode,0)

    def test_u64_limits_without_exabyte_input(self):
        # Test-only trusted construction. Public programs cannot forge state.
        source='''fn main()->u32 {
            var s=Utf8StreamState(18446744073709551614,0,0,0,128,191,0,0)
            a:[u8;1]=[65];v=view a[0..1]
            s=utf8_stream.feed(s,v)
            match utf8_stream.finish(s){Ok(n)=>{if n!=1{return 1}} Err(e)=>{return 2}}
            s=utf8_stream.feed(s,v)
            match utf8_stream.finish(s){Ok(n)=>{return 3} Err(e)=>{
                if e.offset!=18446744073709551615{return 4}
                match e.kind {Utf8StreamErrorKind.SizeOverflow=>{} Utf8StreamErrorKind.InvalidEncoding=>{return 5}}
            }}
            s=Utf8StreamState(99,18446744073709551615,0,0,128,191,0,0)
            s=utf8_stream.feed(s,v)
            match utf8_stream.finish(s){Ok(n)=>{return 6} Err(e)=>{if e.offset!=99{return 7}}}
            s=Utf8StreamState(18446744073709551615,0,18446744073709551614,1,128,191,0,0)
            match utf8_stream.finish(s){Ok(n)=>{return 8} Err(e)=>{if e.offset!=18446744073709551614{return 9}}}
            return 0
        }'''
        p=Parser(source).parse();p[0].module='__liza_utf8_stream'
        text=llvm(lower(p))
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                ir=Path(d)/'test.ll';ir.write_text(text);exe=Path(d)/'test.exe'
                r=subprocess.run(['clang','-Wno-override-module',opt,str(ir),'-o',str(exe)],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=10).returncode,0)

    def test_large_file_and_eof_example(self):
        source=Path('examples/utf8_stream_file.liza').read_text(encoding='utf-8')
        samples=[b'',b'A'*2047+'😀'.encode()+b'B'*4096,b'a'*2047+b'\xe2',
                 b'a'*4095+b'\xed\xa0\x80',b'x'*16384]
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=test_io.ConsoleNative.build(self,d,source,opt)
                path=Path(d)/'examples/data';path.mkdir(parents=True)
                self.assertEqual(subprocess.run([str(exe)],cwd=d,capture_output=True).returncode,1)
                for data in samples:
                    (path/'utf8.txt').write_bytes(data)
                    code,value=expected([data]);out=f'Invalid UTF-8 at byte: {value}\n' if code else f'Code points: {value}\n'
                    r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=10)
                    self.assertEqual((r.returncode,r.stdout),(5 if code else 0,out.encode()),r.stderr)
