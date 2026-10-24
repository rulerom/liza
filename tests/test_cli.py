"""Native arguments/paths and the exact liza-text command contract."""
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

APP=Path(__file__).resolve().parents[1]/'examples/apps/liza_text.liza'
USAGE=b'Usage: liza-text <check|count|info> <file>\n'


class CliTypes(unittest.TestCase):
    def test_opaque_tokens_and_aggregate_restrictions(self):
        bad=['struct S {a:Arg}','enum E {A(Path)}','struct S {a:Option<Arg>}',
             'struct Box<T>{a:T}\nfn x(a:Box<Path>)->u32{return 0}',
             'fn x(a:[Arg;0])->u32{return 0}',
             'fn x(a:View<Path>)->u32{return 0}',
             'fn x(a:memory.Buffer<Arg>)->u32{return 0}',
             'fn x(a:vec.Vec<Option<Path>>)->u32{return 0}',
             'fn x(a:Arg)->u32{return u32(a)}',
             'fn x(a:Arg)->u32{return a.len}',
             'fn x()->Arg{return Arg(0)}',
             'fn x(a:Path)->Text{return a}',
             'fn x()->u32{return cli.count()}',
             'fn x()->Option<Arg>{return cli.arg(1)}',
             'fn x()->u32{return __liza_cli_count()}']
        for source in bad:
            with self.subTest(source=source),self.assertRaises((CompileError,ValueError)):
                test_io.compile_source(source+'\nfn main()->u32{return 0}')

    def test_function_return_generics_options_and_copy(self):
        m=test_io.compile_source('''fn identity<T>(x:T)->T{return move x}
fn argument()->Option<Arg>:io{return cli.arg(1)}
fn main()->u32:io{match argument(){None=>{return 0} Some(a)=>{
b=copy a;c=identity(move b);if cli.equals(c,"x"){return 1}return 0}}}''')
        self.assertTrue(any('cli_' in f for f in link_flags(m)))
        self.assertFalse(any('file_' in f or 'console_' in f for f in link_flags(m)))


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class CliNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='liza cli ')
        cls.executables=[]
        m=lower(load_program(APP))
        for opt in ('-O0','-O2'):
            folder=Path(cls.temp.name)/opt[1:];folder.mkdir()
            ir=folder/'app.ll';ir.write_text(llvm(m))
            exe=folder/('liza-text.exe' if sys.platform=='win32' else 'liza-text')
            subprocess.run(['clang','-Wno-override-module',opt,str(ir),*link_flags(m),'-o',str(exe)],check=True,capture_output=True)
            cls.executables.append(exe)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def check(self,args,code,out,err):
        for exe in self.executables:
            r=subprocess.run([str(exe),*args],capture_output=True,timeout=15)
            self.assertEqual((r.returncode,r.stdout,r.stderr),(code,out,err),args)

    def test_commands_exact_output_and_input_sizes(self):
        path=Path(self.temp.name)/'Лиза 😀 text.txt'
        for data,count in [(b'',0),('Лиза 😀\n'.encode(),7),
                           (b'x'*2047+'😀'.encode()+b'y'*6000,8048),
                           (b'\0\xef\xbb\xbf',2)]:
            path.write_bytes(data)
            self.check(['check',str(path)],0,b'OK\n',b'')
            self.check(['count',str(path)],0,f'{count}\n'.encode(),b'')
            self.check(['info',str(path)],0,f'Bytes: {len(data)}\nCode points: {count}\n'.encode(),b'')

    def test_invalid_utf8_never_prints_success(self):
        path=Path(self.temp.name)/'bad.txt'
        for data,offset in [(b'a'*2047+b'\xed\xa0\x80',2047),(b'a'*4095+b'\xf0\x90',4095),(b'\xff',0)]:
            path.write_bytes(data)
            for command in ('check','count','info'):
                self.check([command,str(path)],1,b'',f'Invalid UTF-8 at byte {offset}\n'.encode())

    def test_usage_and_open_failures(self):
        for args in ([],['check'],['check','x','extra'],['wrong','x'],['CHECK','x']):
            self.check(args,2,b'',USAGE)
        self.check(['check',str(Path(self.temp.name)/'absent')],3,b'',b'Cannot open file\n')
        self.check(['check',''],3,b'',b'Cannot open file\n')

    @unittest.skipUnless(sys.platform=='linux','Linux filesystem accepts arbitrary non-NUL path bytes')
    def test_non_utf8_path_and_command(self):
        path=os.fsencode(self.temp.name)+b'/file-\xff-\xfe'
        with open(path,'wb') as f:f.write(b'ok')
        self.check([b'count',path],0,b'2\n',b'')
        self.check([b'\xff',path],2,b'',USAGE)

    @unittest.skipUnless(os.name=='posix','POSIX open adapter')
    def test_native_path_passed_verbatim_to_open(self):
        runtime=APP.parents[2]/'liza/runtime'
        source=r'''
#include <stdint.h>
#include <fcntl.h>
#include <errno.h>
static char raw[]={'x',(char)255,0};
static int mock_open(const char *path,int flags,...){return path==raw?17:-1;}
#define open mock_open
#include "FILE_RUNTIME"
#undef open
#include "CLI_RUNTIME"
int main(void){char *argv[]={raw};uint64_t handle=0;
liza_rt_cli_init(1,argv);
if(liza_rt_cli_path(0)!=raw)return 1;
if(liza_rt_file_open_native(liza_rt_cli_path(0),&handle)!=0||handle!=17)return 2;
if(liza_rt_cli_equals(0,(const uint8_t*)"x",1))return 3;
return 0;}
'''.replace('FILE_RUNTIME',(runtime/'file_posix.c').as_posix()).replace('CLI_RUNTIME',(runtime/'cli_posix.c').as_posix())
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d);c=p/'test.c';c.write_text(source);exe=p/'test'
                subprocess.run(['clang',opt,str(c),'-o',str(exe)],check=True,capture_output=True)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True).returncode,0)

    @unittest.skipUnless(sys.platform=='win32','Windows native UTF-16')
    def test_unpaired_utf16_path(self):
        path=Path(self.temp.name)/'unpaired-\ud800.txt'
        path.write_bytes(b'ok')
        self.check(['count',str(path)],0,b'2\n',b'')

    def test_arguments_lifetime_bounds_and_literal_comparison(self):
        source='''fn arg()->Option<Arg>:io{return cli.arg(1)}
fn main()->u32:io {
if cli.count()!=4{return 1}
match cli.arg(0){None=>{return 2} Some(name)=>{}}
match cli.arg(4294967295){Some(a)=>{return 3} None=>{}}
match cli.path_arg(4){Some(p)=>{return 4} None=>{}}
match arg(){None=>{return 5} Some(a)=>{
if !cli.equals(a,"Лиза 😀"){return 6}
if cli.equals(a,"Лиза") || cli.equals(a,"Лиза 😀x") || cli.equals(a,"Лиза 😀\\u0000"){return 7}
}}
match cli.arg(2){None=>{return 8} Some(a)=>{if !cli.equals(a,""){return 9}}}
match cli.arg(3){None=>{return 10} Some(a)=>{if !cli.equals(a,"a\\\"b\\\\"){return 11}}}
return 0
}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=test_io.ConsoleNative.build(self,d,source,opt)
                r=subprocess.run([str(exe),'Лиза 😀','','a"b\\'],capture_output=True)
                self.assertEqual(r.returncode,0,r.stderr)

    def test_broken_stdout_and_stderr(self):
        path=Path(self.temp.name)/'output.txt';path.write_bytes(b'ok')
        for exe in self.executables:
            for stream,args in [('stdout',['check',str(path)]),('stderr',[])]:
                read,write=os.pipe();os.close(read)
                try:
                    kwargs={'stdout':subprocess.PIPE,'stderr':subprocess.PIPE};kwargs[stream]=write
                    r=subprocess.run([str(exe),*args],timeout=15,**kwargs)
                    self.assertEqual(r.returncode,3)
                finally:os.close(write)

    def test_stderr_text_numbers_bytes_and_file_redirection(self):
        source='''fn main()->u32:io {
a=console.err("Лиза 😀 ");b=console.err_u64(18446744073709551615)
c=console.err(" ");d=console.err_i64(-9223372036854775808);e=console.errln("")
raw:[u8;2]=[0,255];v=view raw[0..2];f=console.err_bytes(v)
g=console.println("stdout");return 0}'''
        expected='Лиза 😀 18446744073709551615 -9223372036854775808\n'.encode()+b'\0\xff'
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=test_io.ConsoleNative.build(self,d,source,opt)
                r=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual((r.returncode,r.stdout,r.stderr),(0,b'stdout\n',expected))
                with open(Path(d)/'err','wb') as f:r=subprocess.run([str(exe)],stdout=subprocess.PIPE,stderr=f)
                self.assertEqual((r.returncode,r.stdout),(0,b'stdout\n'))
                self.assertEqual((Path(d)/'err').read_bytes(),expected)

    def test_read_and_close_failures_still_close_resource(self):
        module=lower(load_program(APP));text=llvm(module)
        for opt in ('-O0','-O2'):
            for read_error,close_error,message in [(7,0,b'Cannot read file\n'),(0,7,b'Cannot close file\n'),(7,7,b'Cannot read file\n')]:
                with tempfile.TemporaryDirectory() as d:
                    p=Path(d);ir=p/'app.ll';ir.write_text(text)
                    shim=p/'mock.c';shim.write_text('''#include <stdint.h>
#include <stdlib.h>
static int closed;
static void verify(void){if(closed!=1)_Exit(90);}
uint32_t liza_rt_file_open_native(const void *p,uint64_t *h){*h=7;atexit(verify);return 0;}
uint64_t liza_rt_read_chunk(uint64_t h,uint8_t *out){return (uint64_t)READ<<32;}
uint32_t liza_rt_file_close(uint64_t h){if(h!=7)_Exit(91);closed++;return CLOSE;}
'''.replace('READ',str(read_error)).replace('CLOSE',str(close_error)))
                    exe=p/'test.exe'
                    subprocess.run(['clang','-Wno-override-module',opt,str(ir),*[f for f in link_flags(module) if 'file_' not in f],str(shim),'-o',str(exe)],check=True,capture_output=True)
                    r=subprocess.run([str(exe),'info','ignored'],capture_output=True)
                    self.assertEqual((r.returncode,r.stdout,r.stderr),(3,b'',message))

    def test_size_limit_and_error_reporting_without_huge_file(self):
        source=APP.read_text(encoding='utf-8').split('fn main()')[0]+'''fn main()->u32:io {
match add_bytes(18446744073709551615,1){Some(n)=>{return 99} None=>{}}
return report(2,0,Err(Utf8StreamError(Utf8StreamErrorKind.SizeOverflow,18446744073709551615)))
}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=test_io.ConsoleNative.build(self,d,source,opt)
                r=subprocess.run([str(exe)],capture_output=True)
                self.assertEqual((r.returncode,r.stdout,r.stderr),(4,b'',b'Input exceeds supported size\n'))

    def test_run_separator_forwards_program_arguments(self):
        r=subprocess.run([sys.executable,'-B','-m','liza','run',str(APP),'--','count','examples/data/utf8.txt'],capture_output=True,timeout=60)
        self.assertEqual((r.returncode,r.stdout,r.stderr),(0,b'7\n',b''))
