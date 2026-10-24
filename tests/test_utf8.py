"""Strict UTF-8 semantics against Python's independent decoder, at O0/O2."""
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from liza.frontend import CompileError
from liza.modules import load_program
from liza.ir import lower
from liza.stdlib import link_flags
import test_io
from tools.check_utf8_cost import build, probe


def error(kind, offset):
    return (1<<63) | (kind<<32) | offset


def oracle(case):
    op,data,start,end = case
    if op in (2,3):
        if start>len(data): return error(2,start)
        if start==len(data): return 1<<62
        # Only the selected scalar is decoded; invalid suffixes are irrelevant.
        for width in range(1,5):
            try:
                text=data[start:start+width].decode('utf-8')
            except UnicodeDecodeError:
                continue
            if len(text)==1:
                return ord(text) if op==2 else start+width
        return error(1,start)
    if op==4 and start>len(data): return error(2,start)
    if op==5:
        if start>end:return error(4,start)
        if end>len(data):return error(2,end)
    try:
        text=data.decode('utf-8')
    except UnicodeDecodeError as e:
        return error(1,e.start)
    if op==0:return 0
    if op==1:return len(text)
    boundaries={0}; index=0
    for c in text:
        index+=len(c.encode('utf-8'));boundaries.add(index)
    if op==4:return int(start in boundaries)
    if start not in boundaries:return error(3,start)
    if end not in boundaries:return error(3,end)
    return (start<<32)|end


class Utf8Types(unittest.TestCase):
    def test_pure_library_and_invalid_calls(self):
        source='fn main()->u32 {a:[u8;0]=[];v=view a[0..0];r=utf8.count(v);return 0}'
        module=test_io.compile_source(source)
        self.assertEqual(link_flags(module),[])
        self.assertFalse(module.externals)
        for expr in ('utf8.count(1)','utf8.count("text")','utf8.unknown(v)',
                     'utf8.next(v,-1)','utf8.next(v,u64(0))','utf8.range(v,0)',
                     '__liza_utf8_boundary(v,0)'):
            with self.subTest(expr=expr),self.assertRaises(CompileError):
                test_io.compile_source(source.replace('utf8.count(v)',expr))

    def test_modules_and_public_result_types(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'reader.liza').write_text('pub fn count(data:View<u8>)->Result<u32,Utf8Error>{return utf8.count(data)}')
            (root/'main.liza').write_text('import reader\nfn main()->u32{a:[u8;0]=[];v=view a[0..0];match reader.count(v){Ok(n)=>{return n} Err(e)=>{return e.offset}}}')
            self.assertEqual(link_flags(lower(load_program(root/'main.liza'))),[])
            (root/'main.liza').write_text('import utf8\nfn main()->u32{return 0}')
            with self.assertRaisesRegex(CompileError,'reserved'):
                load_program(root/'main.liza')

    def test_borrow_is_not_consumed_or_extended(self):
        test_io.compile_source('''fn main()->u32 {
            var a:[u8;2]=[65,66]
            {v=view a[0..2];r=utf8.validate(v);s=utf8.count(v)}
            a[0]=67
            b=move a
            return 0
        }''')
        with self.assertRaises(CompileError):
            test_io.compile_source('''fn main()->u32 {
                var a:[u8;2]=[65,66];v=view a[0..2]
                r=utf8.count(v);a[0]=67;return 0
            }''')


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class Utf8Native(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.executables=[build(Path(cls.temp.name)/opt[1:],opt)[0] for opt in ('-O0','-O2')]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check(self,cases):
        expected=[oracle(c) for c in cases]
        for exe in self.executables:
            actual=probe(exe,cases)
            for i,(got,want) in enumerate(zip(actual,expected)):
                if got!=want:self.fail(f'{exe}: {cases[i]!r}: {got} != {want}')

    def test_all_one_and_two_byte_inputs(self):
        cases=[(1,bytes([a]),0,0) for a in range(256)]
        cases.extend((1,bytes([a,b]),0,0) for a in range(256) for b in range(256))
        self.check(cases)

    def test_every_unicode_scalar_in_one_runtime_stream(self):
        text=''.join(chr(n) for n in range(0x110000) if not 0xd800<=n<=0xdfff)
        data=text.encode('utf-8')
        for exe in self.executables:
            self.assertEqual(probe(exe,[(0,data,0,0),(1,data,0,0)]),[0,len(text)])

    def test_decode_boundary_scalars_and_invalid_sequences(self):
        samples=[b'',b'\0',b'\xef\xbb\xbf',b'e\xcc\x81', 'Лиза 😀'.encode(),
                 b'\x80',b'\xc0\x80',b'\xc1\xbf',b'\xe0\x9f\xbf',b'\xed\xa0\x80',
                 b'\xf0\x8f\xbf\xbf',b'\xf4\x90\x80\x80',b'\xf5\x80\x80\x80',b'\xff',
                 b'\xc2',b'\xe1\x80',b'\xf1\x80\x80',b'\xe1A\x80',b'\xe1\x80A']
        for n in (0x7f,0x80,0x7ff,0x800,0xd7ff,0xe000,0xffff,0x10000,0x10ffff):
            samples.append(chr(n).encode())
        cases=[]
        for data in samples:
            for op in range(5):
                for start in range(len(data)+2):cases.append((op,data,start,0))
            cases.append((2,data,0xffffffff,0))
            cases.append((4,data,0xffffffff,0))
            # A malformed sequence after a valid prefix reports its own start.
            cases.append((1,b'abc'+data,0,0))
        self.check(cases)

    def test_ranges_validate_whole_input_and_prioritize_errors(self):
        cases=[]
        for data in (b'',b'abc','aЛ😀z'.encode(),b'a\xff',b'\xc2\x80\xff'):
            for start in range(len(data)+2):
                for end in range(len(data)+2):cases.append((5,data,start,end))
        cases.extend([(5,b'',0xffffffff,0),(5,b'',0,0xffffffff)])
        self.check(cases)

    def test_random_runtime_inputs(self):
        rng=random.Random(22);cases=[]
        for _ in range(2000):
            data=bytes(rng.randrange(256) for _ in range(rng.randrange(16)))
            for op in range(6):cases.append((op,data,rng.randrange(len(data)+2),rng.randrange(len(data)+2)))
        self.check(cases)

    def test_file_example_success_error_and_size_limit(self):
        source=Path('examples/utf8_file.liza').read_text(encoding='utf-8')
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=test_io.ConsoleNative.build(self,d,source,opt)
                path=Path(d)/'examples/data';path.mkdir(parents=True)
                for data,code,out in [(b'',0,b'Code points: 0\n'),
                                      ('Лиза 😀\n'.encode(),0,b'Code points: 7\n'),
                                      (b'abc\xed\xa0\x80',2,b'Invalid UTF-8 at byte: 3\n'),
                                      (b'a'*2049,1,b'Cannot read text file\n')]:
                    (path/'utf8.txt').write_bytes(data)
                    r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=10)
                    self.assertEqual((r.returncode,r.stdout),(code,out),r.stderr)

    def test_region_vec_input_and_independent_scalar_result(self):
        source='''fn main()->u32:alloc {
            var count:u32=0
            match memory.create(128) {
                Err(e)=>{return 1}
                Ok(region)=>{
                    match vec.with_capacity<u8>(region,2) {
                        Err(e)=>{closed=memory.close(move region);return 2}
                        Ok(current)=>{
                            (a,s)=vec.push(move current,194)
                            (b,t)=vec.push(move a,128)
                            {v=vec.view(b);match utf8.count(v){Ok(n)=>{count=n} Err(e)=>{count=99}}}
                            released=vec.release(move b)
                        }
                    }
                    closed=memory.close(move region)
                }
            }
            return count-1
        }'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=test_io.ConsoleNative.build(self,d,source,opt)
                r=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(r.returncode,0,r.stderr)

    def test_argument_effects_and_traps_are_preserved(self):
        prefix='''fn index()->u32:io {
            printed=console.write("before")
            VALUE
        }
        fn main()->u32:io {
            a:[u8;0]=[];v=view a[0..0]
            result=utf8.next(v,index())
            printed=console.write("after")
            return 0
        }'''
        for opt in ('-O0','-O2'):
            for value,traps in [('return 0',False),('x:u8=255;y=x+1;return u32(y)',True)]:
                with tempfile.TemporaryDirectory() as d:
                    exe=test_io.ConsoleNative.build(self,d,prefix.replace('VALUE',value),opt)
                    r=subprocess.run([str(exe)],capture_output=True,timeout=10)
                    self.assertEqual(r.stdout,b'before' if traps else b'beforeafter')
                    self.assertNotEqual(r.returncode,0) if traps else self.assertEqual(r.returncode,0)
