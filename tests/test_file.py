"""Bounded file input: language contract and native end-to-end acceptance."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from test_io import compile_source, program
import test_io
from liza.frontend import CompileError
from liza.stdlib import link_flags

CAPACITY = 2048


class FileTypes(unittest.TestCase):
    def test_effects_signatures_and_lifetimes(self):
        for source in [
            'fn main()->u32{x=file.read("x");return 0}',
            program('x=file.read(1);return 0'),
            program('x=__liza_read_file("x");return 0'),
            program('match file.read("x"){Ok(b)=>{a=b.data;v=view a[0..b.len];c=move a;return 0} Err(e)=>{return 1}}'),
        ]:
            with self.subTest(source=source), self.assertRaises(CompileError):
                compile_source(source)
        m=compile_source(program('match file.read("x"){Ok(b)=>{a=b.data;v=view a[0..b.len];return v.len} Err(e)=>{return e.read}}'))
        self.assertEqual([f.name.text for f in m.externals],['__liza_read_file'])
        self.assertTrue(any('file_' in f for f in link_flags(m)))
        m=compile_source('fn main()->u32{e=FileError.Other;return 0}')
        self.assertEqual(link_flags(m),[])


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class FileNative(unittest.TestCase):
    build=test_io.ConsoleNative.build

    def test_runtime_files_bounds_and_errors(self):
        source=program('''
            match file.read("input.bin") {
                Ok(b)=>{
                    a=b.data
                    v=view a[0..b.len]
                    match console.write_bytes(v) {Ok(n)=>{return 0} Err(e)=>{return 10}}
                }
                Err(e)=>{
                    match e.kind {
                        FileError.TooLarge=>{if e.read==CAPACITY {return 3} return 30}
                        FileError.NotFound=>{return 1}
                        FileError.PermissionDenied=>{return 2}
                        FileError.InvalidPath=>{return 4}
                        FileError.PathTooLong=>{return 5}
                        FileError.WouldBlock=>{return 6}
                        FileError.Other=>{return 7}
                    }
                }
            }'''.replace('CAPACITY',str(CAPACITY)))
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=10)
                self.assertEqual(r.returncode,1,r.stderr)
                for n in (0,1,12,CAPACITY-1,CAPACITY,CAPACITY+1):
                    with self.subTest(opt=opt,length=n):
                        data=bytes(i%256 for i in range(n))
                        (Path(d)/'input.bin').write_bytes(data)
                        r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=10)
                        self.assertEqual(r.returncode,3 if n>CAPACITY else 0,r.stderr)
                        self.assertEqual(r.stdout,b'' if n>CAPACITY else data)

    def test_paths_and_zero_tail(self):
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                (Path(d)/'Лиза.bin').write_bytes(b'\xff')
                source=program('''
                    match file.read("Лиза.bin") {
                        Ok(b)=>{if b.len!=1 || b.data[0]!=255 || b.data[1]!=0 || b.data[CAPACITY-1]!=0 {return 1}}
                        Err(e)=>{return 2}
                    }
                    match file.read("bad\\u0000path") {Ok(b)=>{return 3} Err(e)=>{match e.kind {FileError.InvalidPath=>{} FileError.NotFound=>{return 4} FileError.PermissionDenied=>{return 4} FileError.TooLarge=>{return 4} FileError.PathTooLong=>{return 4} FileError.WouldBlock=>{return 4} FileError.Other=>{return 4}}}}
                    return 0
                '''.replace('CAPACITY',str(CAPACITY)))
                exe=self.build(d,source,opt)
                r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=10)
                self.assertEqual(r.returncode,0,r.stderr)

    def test_rtp_file_example(self):
        source=Path('examples/rtp_file.liza').read_text(encoding='utf-8')
        # Keep the parser example synchronized until Liza has source modules.
        parser=Path('examples/rtp_result.liza').read_text().split('// Scalar inspection boundary')[0]
        self.assertTrue(source.startswith(parser))
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                data_dir=Path(d)/'examples/data';data_dir.mkdir(parents=True)
                path=data_dir/'rtp.bin'
                for data,code,out in [(bytes([128,96,18,52,0,0,0,1,0,0,0,2]),0,b'RTP sequence: 4660\n'),
                                      (b'',2,b'Invalid RTP packet\n'),
                                      (bytes(12),2,b'Invalid RTP packet\n'),
                                      (bytes(CAPACITY+1),1,b'Cannot read RTP file\n')]:
                    path.write_bytes(data)
                    r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=10)
                    self.assertEqual((r.returncode,r.stdout),(code,out),r.stderr)

    def test_large_value_calling_convention(self):
        values=','.join(str(i) for i in range(128))
        source='''struct S {a:[u8;128]}
        fn identity(s:S)->S{return s}
        fn choose(a:S,b:S,c:bool)->S{var x=a;if c{x=b}return x}
        fn main()->u32{
            a=S([VALUES])
            b=identity(a)
            var c=choose(a,b,true)
            var i:u32=0
            while i<3 {c=identity(c);i=i+1}
            return u32(a.a[127])+u32(b.a[0])+u32(c.a[63])-190
        }'''.replace('VALUES',values)
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                r=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(r.returncode,0,r.stderr)

    @unittest.skipUnless(sys.platform in ('linux','darwin'),'POSIX runtime fault injection')
    def test_partial_reads_interruption_and_close_failure(self):
        runtime=(Path(__file__).resolve().parents[1]/'liza/runtime/file_posix.c').as_posix()
        harness=r"""
        #include <stdint.h>
        #include <string.h>
        #include <errno.h>
        #include <fcntl.h>
        #include <unistd.h>
        static int scenario, reads, closes;
        static int mock_open(const char *p,int flags,...) {return 42;}
        static int mock_close(int fd) {
            closes++;
            if(scenario==4 || scenario==5){errno=EIO;return -1;}
            return 0;
        }
        static ssize_t mock_read(int fd,void *out,size_t size) {
            reads++;
            if(reads==1){errno=EINTR;return -1;}
            if(scenario==1 || scenario==2){
                if(reads==2){memset(out,42,size);return (ssize_t)size;}
                if(scenario==1)return 0;
                *(uint8_t*)out=99;return 1;
            }
            if(reads==2){*(uint8_t*)out=42;return 1;}
            if(scenario==3 || scenario==5){errno=EAGAIN;return -1;}
            return 0;
        }
        #define open mock_open
        #define read mock_read
        #define close mock_close
        #include "RUNTIME"
        int main(void) {
            uint8_t out[CAPACITY];
            for(scenario=0;scenario<6;scenario++){
                reads=closes=0;
                uint64_t result=liza_rt_read_file((const uint8_t*)"x",1,out);
                uint32_t count=scenario==1 || scenario==2 ? CAPACITY : 1;
                uint32_t error=scenario==2?3:scenario==3 || scenario==5?6:scenario==4?7:0;
                if(result!=((uint64_t)error<<32|count)||closes!=1||reads!=3||out[0]!=42)return 1+scenario;
                if(count==1 && out[1]!=0)return 10;
            }
            closes=reads=0;
            if(liza_rt_read_file((const uint8_t*)"",0,out)!=((uint64_t)4<<32))return 11;
            if(closes||reads)return 12;
            return 0;
        }
        """.replace('RUNTIME',runtime)
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                c=Path(d)/'test.c';exe=Path(d)/'test'
                c.write_text(harness)
                r=subprocess.run(['clang',opt,str(c),'-o',str(exe)],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)
                r=subprocess.run([str(exe)],capture_output=True,timeout=10)
                self.assertEqual(r.returncode,0,r.stderr)
