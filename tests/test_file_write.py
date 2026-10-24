"""File output contracts: partial external effects, exclusive create and cleanup."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from liza.frontend import CompileError
from liza.modules import load_program
from liza.ir import lower
from liza.backend import llvm
from liza.stdlib import link_flags
import test_io

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'examples/apps/liza_copy.liza'
PARTIAL=b'Destination may be incomplete; it has not been removed\n'


class FileWriteTypes(unittest.TestCase):
    def test_borrowed_operations_and_resource_obligations(self):
        source='''fn main()->u32:io {
match cli.path_arg(1){None=>{return 1} Some(p)=>{
match file.create_path(p){Err(e)=>{return 2} Ok(f)=>{
a:[u8;1]=[42];v=view a[0..1];x=file.write_chunk(f,v);y=file.flush(f)
z=file.close(move f);return 0
}}}}}'''
        m=test_io.compile_source(source)
        for name in ('file.write_chunk','file.flush'):
            fn=next(f for f in m if f.name==name)
            self.assertEqual(fn.params[0]['mode'],'borrow')
        for changed in [source.replace('z=file.close(move f);',''),
                        source.replace('file.flush(f)','file.flush(move f)'),
                        source.replace('file.write_chunk(f,v)','file.write_chunk(f,a)'),
                        source.replace('file.flush(f)','file.flush(0)'),
                        source.replace('file.create_path(p)','file.create_path("x")'),
                        source.replace(':io','')]:
            with self.subTest(changed=changed),self.assertRaises(CompileError):test_io.compile_source(changed)

    def test_existing_error_matches_remain_exhaustive(self):
        test_io.compile_source('''fn error(e:FileError)->u32 {match e {
FileError.NotFound=>{return 1} FileError.PermissionDenied=>{return 2}
FileError.TooLarge=>{return 3} FileError.InvalidPath=>{return 4}
FileError.PathTooLong=>{return 5} FileError.WouldBlock=>{return 6} FileError.Other=>{return 7}}}
fn main()->u32{return 0}''')


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class CopyNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='liza copy ')
        cls.module=lower(load_program(APP));cls.text=llvm(cls.module);cls.executables=[]
        for opt in ('-O0','-O2'):
            p=Path(cls.temp.name)/opt[1:];p.mkdir();ir=p/'copy.ll';ir.write_text(cls.text)
            exe=p/'liza-copy.exe'
            subprocess.run(['clang','-Wno-override-module',opt,str(ir),*link_flags(cls.module),'-o',str(exe)],check=True,capture_output=True)
            cls.executables.append(exe)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def test_exact_binary_copy_empty_large_and_native_paths(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'Исходник 😀.bin';dst=Path(d)/'Копия 😀.bin'
            for data in (b'',b'\0\xff\xfe\r\n',bytes(range(256))*8193):
                src.write_bytes(data)
                for exe in self.executables:
                    r=subprocess.run([str(exe),str(src),str(dst)],capture_output=True,timeout=30)
                    self.assertEqual((r.returncode,r.stdout,r.stderr),(0,b'',b''))
                    self.assertEqual(dst.read_bytes(),data);dst.unlink()

    def test_existing_destination_same_file_and_hardlink_are_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);src=p/'src';src.write_bytes(b'source');dst=p/'dst';dst.write_bytes(b'keep')
            alias=p/'alias';os.link(src,alias)
            for exe in self.executables:
                for target in (src,dst,alias):
                    r=subprocess.run([str(exe),str(src),str(target)],capture_output=True)
                    self.assertEqual((r.returncode,r.stdout,r.stderr),(3,b'',b'Destination already exists\n'))
                    self.assertEqual(src.read_bytes(),b'source');self.assertEqual(dst.read_bytes(),b'keep')

    @unittest.skipUnless(os.name=='posix','POSIX symlinks')
    def test_symlinks_including_dangling_are_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);src=p/'src';src.write_bytes(b'source');target=p/'target';target.write_bytes(b'keep')
            link=p/'link';link.symlink_to(target);dangling=p/'dangling';dangling.symlink_to(p/'absent')
            for exe in self.executables:
                for dest in (link,dangling):
                    r=subprocess.run([str(exe),str(src),str(dest)],capture_output=True)
                    self.assertEqual(r.returncode,3)
                    self.assertEqual(target.read_bytes(),b'keep');self.assertFalse((p/'absent').exists())

    def test_usage_source_and_creation_errors(self):
        for exe in self.executables:
            r=subprocess.run([str(exe)],capture_output=True)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(2,b'',b'Usage: liza-copy <source> <destination>\n'))
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);src=p/'src';dst=p/'dst'
                r=subprocess.run([str(exe),str(src),str(dst)],capture_output=True)
                self.assertEqual((r.returncode,r.stderr),(3,b'Cannot open source\n'));self.assertFalse(dst.exists())
                src.write_bytes(b'x')
                r=subprocess.run([str(exe),str(src),str(p/'missing'/'dst')],capture_output=True)
                self.assertEqual((r.returncode,r.stderr),(3,b'Cannot create destination\n'))

    @unittest.skipUnless(sys.platform=='linux','Linux raw byte paths')
    def test_non_utf8_paths(self):
        with tempfile.TemporaryDirectory() as d:
            src=os.fsencode(d)+b'/src-\xff';dst=os.fsencode(d)+b'/dst-\xfe'
            with open(src,'wb') as f:f.write(b'\0\xff')
            for exe in self.executables:
                r=subprocess.run([os.fsencode(exe),src,dst],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)
                with open(dst,'rb') as f:self.assertEqual(f.read(),b'\0\xff')
                os.unlink(dst)

    def test_fault_order_partial_write_flush_and_close_cleanup(self):
        # Replacement OS boundary verifies both handles close once and in order.
        base=r'''
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
static int reads,closes,flushed,writes;
static void verify(void){if(closes!=2 || flushed!=FLUSHED || writes!=WRITES)_Exit(90);}
uint32_t liza_rt_file_open_native(const void*p,uint64_t*h){*h=10;atexit(verify);return 0;}
uint32_t liza_rt_file_create_native(const void*p,uint64_t*h){*h=11;return 0;}
uint64_t liza_rt_read_chunk(uint64_t h,uint8_t*out){
if(h!=10)_Exit(91);memset(out,0,2048);
if(READERR)return (uint64_t)7<<32;
return reads++==0?4:0;}
uint64_t liza_rt_file_write(uint64_t h,const uint8_t*p,uint32_t n){
if(h!=11||n!=4)_Exit(92);writes++;return WRITEERR?((uint64_t)3<<32)|2:4;}
uint32_t liza_rt_file_flush(uint64_t h){if(h!=11)_Exit(93);flushed++;return FLUSHERR?3:0;}
uint32_t liza_rt_file_close(uint64_t h){if(h!=(closes?10:11))_Exit(94);closes++;return CLOSEERR?7:0;}
'''
        cases=[(1,0,0,1,0,0,b'Cannot read source\nAlso failed to close destination\nAlso failed to close source\n'),
               (0,1,0,1,0,1,b'Cannot write destination; bytes written in current chunk: 2\nAlso failed to close destination\nAlso failed to close source\n'),
               (0,0,1,1,1,1,b'Cannot flush destination\nAlso failed to close destination\nAlso failed to close source\n'),
               (0,0,0,1,1,1,b'Cannot close destination\nAlso failed to close source\n')]
        for opt in ('-O0','-O2'):
            for read,write,flush,close,flushed,writes,out in cases:
                with tempfile.TemporaryDirectory() as d:
                    p=Path(d);ir=p/'app.ll';ir.write_text(self.text);shim=p/'shim.c';code=base
                    for key,value in [('READERR',read),('WRITEERR',write),('FLUSHERR',flush),('CLOSEERR',close),('FLUSHED',flushed),('WRITES',writes)]:code=code.replace(key,str(value))
                    shim.write_text(code);exe=p/'test.exe'
                    subprocess.run(['clang','-Wno-override-module',opt,str(ir),*[f for f in link_flags(self.module) if 'file_' not in f],str(shim),'-o',str(exe)],check=True,capture_output=True)
                    r=subprocess.run([str(exe),'source','destination'],capture_output=True)
                    self.assertEqual((r.returncode,r.stdout,r.stderr),(3,b'',out+PARTIAL))
                    read_fd,write_fd=os.pipe();os.close(read_fd)
                    try:
                        r=subprocess.run([str(exe),'source','destination'],stdout=subprocess.PIPE,stderr=write_fd)
                        self.assertEqual(r.returncode,3) # verify() still checked cleanup.
                    finally:os.close(write_fd)

    def test_borrowed_write_and_flush_return_result_and_preserve_file(self):
        source='''fn main()->u32:io {
match cli.path_arg(1){None=>{return 1} Some(path)=>{
match file.create_path(path){Err(e)=>{return 2} Ok(f)=>{
var status:u32=0
a:[u8;3]=[0,128,255];v=view a[0..3]
match file.write_chunk(f,v){Ok(n)=>{if n!=3{status=3}} Err(e)=>{status=4}}
match file.write_chunk(f,v){Ok(n)=>{if n!=3{status=5}} Err(e)=>{status=6}}
match file.flush(f){Ok(n)=>{} Err(e)=>{status=7}}
match file.close(move f){Ok(n)=>{} Err(e)=>{status=8}}
return status
}}}}}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=test_io.ConsoleNative.build(self,d,source,opt);p=Path(d)/'out'
                r=subprocess.run([str(exe),str(p)],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(p.read_bytes(),b'\0\x80\xff'*2)

    @unittest.skipUnless(os.name=='posix','POSIX file limits and signals')
    def test_file_limit_is_result_and_pending_signal_is_preserved(self):
        code=r'''
#include <stdint.h>
#include <signal.h>
#include <pthread.h>
#include <sys/resource.h>
#include <unistd.h>
extern uint32_t liza_rt_file_create_native(const char*,uint64_t*);
extern uint64_t liza_rt_file_write(uint64_t,const uint8_t*,uint32_t);
extern uint32_t liza_rt_file_close(uint64_t);
int main(void){
    uint64_t handle;uint8_t data[64]={0};struct rlimit old,limit;
    if(getrlimit(RLIMIT_FSIZE,&old))return 1;
    limit=old;limit.rlim_cur=32;if(setrlimit(RLIMIT_FSIZE,&limit))return 2;
    signal(SIGXFSZ,SIG_DFL);
    sigset_t one,previous,now;sigemptyset(&one);sigaddset(&one,SIGXFSZ);
    pthread_sigmask(SIG_UNBLOCK,&one,&previous);
    if(liza_rt_file_create_native("limited",&handle))return 3;
    uint64_t result=liza_rt_file_write(handle,data,64);
    if(result!=(((uint64_t)6<<32)|32))return 4;
    pthread_sigmask(SIG_BLOCK,0,&now);if(sigismember(&now,SIGXFSZ))return 5;
    pthread_sigmask(SIG_BLOCK,&one,0);raise(SIGXFSZ);
    if(liza_rt_file_write(handle,data,1)!=((uint64_t)6<<32))return 6;
    sigpending(&now);if(!sigismember(&now,SIGXFSZ))return 7;
    int caught;sigwait(&one,&caught);pthread_sigmask(SIG_SETMASK,&previous,0);
    if(setrlimit(RLIMIT_FSIZE,&old))return 8;
    return liza_rt_file_close(handle)?9:0;
}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);c=p/'test.c';c.write_text(code);exe=p/'test'
                subprocess.run(['clang',opt,str(c),str(ROOT/'liza/runtime/file_posix.c'),'-pthread','-o',str(exe)],check=True,capture_output=True)
                r=subprocess.run([str(exe)],cwd=d,capture_output=True,timeout=10)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertEqual((p/'limited').stat().st_size,32)

    @unittest.skipUnless(os.name=='posix','POSIX resource limits')
    def test_copy_failure_keeps_real_partial_destination(self):
        import resource
        def limit():resource.setrlimit(resource.RLIMIT_FSIZE,(32,32))
        for exe in self.executables:
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);src=p/'src';dst=p/'dst';data=bytes(range(128));src.write_bytes(data)
                r=subprocess.run([str(exe),str(src),str(dst)],preexec_fn=limit,capture_output=True,timeout=10)
                self.assertEqual((r.returncode,r.stdout,r.stderr),(3,b'',b'Cannot write destination; bytes written in current chunk: 32\n'+PARTIAL))
                self.assertEqual(dst.read_bytes(),data[:32]);self.assertEqual(src.read_bytes(),data)
                r=subprocess.run([str(exe),str(src),str(dst)],capture_output=True)
                self.assertEqual(r.returncode,3);self.assertEqual(dst.read_bytes(),data[:32])
