from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from liza.frontend import Parser, CompileError
from liza.ir import lower, dump
from liza.backend import llvm
from liza.stdlib import link_flags


def compile_source(source):
    return lower(Parser(source).parse())


def program(body):
    return 'fn main()->u32:io{'+body+'}'


class Effects(unittest.TestCase):
    def test_effect_contracts_and_trusted_calls(self):
        bad=[
            'fn main()->u32{x=console.write("x");return 0}',
            'fn main()->u32:pure{if false {x=console.write("x")}return 0}',
            'fn f()->u32:io{return 0} fn main()->u32{return f()}',
            'fn f()->u32{return g()} fn g()->u32:io{return f()} fn main()->u32:io{return g()}',
            'fn main()->u32:io{return __liza_print_u64(1)}',
            'fn __liza_secret()->u32{return 0} fn main()->u32{return 0}',
            'fn main()->u32:io{x=console.unknown("x");return 0}',
            'fn main()->u32:io{x=console.write(42);return 0}',
        ]
        for source in bad:
            with self.subTest(source=source), self.assertRaises(CompileError):
                compile_source(source)
        m=compile_source('fn f()->u32:io{x=console.write("x");return 0} fn main()->u32:io{return f()}')
        data=json.loads(dump(m))
        self.assertEqual(data['version'],17)
        self.assertTrue(data['externals'])
        calls=[op for f in m for b in f.blocks for op in b.operations if op.op=='call']
        self.assertTrue(any(op.callee=='console.write' and op.effect_contract=='io' for op in calls))
        self.assertTrue(all(op.op not in ('print','println') for f in m for b in f.blocks for op in b.operations))
        compile_source('fn f()->u32:io{return g()} fn g()->u32:io{return f()} fn main()->u32{return 0}')

    def test_text_and_ownership(self):
        compile_source('struct S {t:Text} fn f()->Text{return "test"} fn main()->u32{x=S(f());return x.t.len}')
        for body in ['a="x";b=move a;return a.len', 'a="x";return a[0]',
                     'a="x";if a=="x" {return 0} return 1', 'a="\\q";return 0',
                     'a="\\ud800";return 0']:
            with self.subTest(body=body),self.assertRaises(CompileError):
                compile_source(program(body))
        m=compile_source('fn main()->u32{return "Привет\\u0000".len}')
        self.assertFalse(m.externals)
        self.assertEqual(link_flags(m),[])
        m=compile_source('fn main()->u32{e=IoError.Other;return 0}')
        self.assertEqual(link_flags(m),[])
        self.assertNotIn('liza_rt_',llvm(m))


@unittest.skipUnless(shutil.which('clang') and sys.platform in ('darwin','linux'),'POSIX native tests')
class ConsoleNative(unittest.TestCase):
    def build(self,root,source,opt,shim=None):
        root=Path(root); m=compile_source(source); ir=root/'module.ll'; exe=root/('program.exe' if sys.platform == 'win32' else 'program')
        ir.write_text(llvm(m))
        files=[str(ir),*link_flags(m)]
        if shim:
            c=root/'shim.c';c.write_text(shim);files.append(str(c))
        result=subprocess.run(['clang','-Wno-override-module',opt,*files,'-o',str(exe)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        return exe

    def test_utf8_nul_bytes_numbers_and_text_lifetime(self):
        source='''fn text()->Text{return "Привет\\u0000"}
        fn main()->u32:io {
            var t:Text=text()
            if true {t="Привет\\u0000"}
            match console.println(t) {Ok(n)=>{if n!=14 {return 1}} Err(e)=>{return 2}}
            a:[u8;3]=[0,255,10]; v=view a[0..3]
            match console.write_bytes(v) {Ok(n)=>{if n!=3{return 3}} Err(e)=>{return 4}}
            x=console.print_u64(18446744073709551615)
            y=console.write(" ")
            z=console.print_i64(-9223372036854775808)
            zero=console.print_u64(0)
            empty=console.write("")
            return 0
        }'''
        expected='Привет\0\n'.encode()+b'\0\xff\n18446744073709551615 -92233720368547758080'
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                result=subprocess.run([str(exe)],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stdout,expected)

    def test_effects_order_traps_and_dead_branches(self):
        cases=[('a=console.write("A"); if false {b=console.write("B")} c=console.write("C"); return 0',b'AC',False),
               ('a=console.write("A"); bad:u8=255; unused=bad+1; b=console.write("B"); return 0',b'A',True),
               ('bad:u8=255; unused=bad+1; a=console.write("A"); return 0',b'',True)]
        for opt in ('-O0','-O2'):
            for body,expected,trap in cases:
                with tempfile.TemporaryDirectory() as d:
                    exe=self.build(d,program(body),opt)
                    result=subprocess.run([str(exe)],capture_output=True,timeout=5)
                    self.assertEqual(result.stdout,expected)
                    self.assertLess(result.returncode,0) if trap else self.assertEqual(result.returncode,0)

    def test_effectful_arguments_run_left_to_right(self):
        source='''fn first()->u32:io {x=console.write("A");return 1}
        fn second()->u32:io {x=console.write("B");return 2}
        fn add(a:u32,b:u32)->u32{return a+b}
        fn main()->u32:io{return add(first(),second())-3}'''
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                result=subprocess.run([str(exe)],capture_output=True,timeout=5)
                self.assertEqual(result.returncode,0)
                self.assertEqual(result.stdout,b'AB')

    def test_closed_stdout_and_broken_pipe_are_results(self):
        source=program('''match console.println("hello") {
            Ok(n)=>{return 9}
            Err(e)=>{if e.written!=0 {return 8} match e.kind {
                IoError.Closed=>{return 41} IoError.BrokenPipe=>{return 42}
                IoError.PermissionDenied=>{return 3} IoError.WouldBlock=>{return 4}
                IoError.NoSpace=>{return 5} IoError.Other=>{return 6}
            }}
        }''')
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                exe=self.build(d,source,opt)
                result=subprocess.run([str(exe)],preexec_fn=lambda:os.close(1),stderr=subprocess.PIPE,timeout=5)
                self.assertEqual(result.returncode,41,result.stderr)
                read,write=os.pipe();os.close(read)
                try:
                    result=subprocess.run([str(exe)],stdout=write,stderr=subprocess.PIPE,timeout=5)
                    self.assertEqual(result.returncode,42,result.stderr)
                finally:os.close(write)

    def test_partial_write_eintr_and_newline_failure(self):
        shims=[('''static int count;
        ssize_t write(int fd,const void *p,size_t n){count++;if(count==1){errno=EINTR;return -1;}if(count==2)return 2;errno=ENOSPC;return -1;}''',2),
        ('''static int count;
        ssize_t write(int fd,const void *p,size_t n){if(count++==0)return n;errno=ENOSPC;return -1;}''',5)]
        for opt in ('-O0','-O2'):
            for shim,expected in shims:
                body='''match console.println("hello") {Ok(n)=>{return 1} Err(e)=>{
                    if e.written!='''+str(expected)+''' {return 2}
                    match e.kind {IoError.NoSpace=>{return 0} IoError.Closed=>{return 3}
                    IoError.PermissionDenied=>{return 4} IoError.BrokenPipe=>{return 5}
                    IoError.WouldBlock=>{return 6} IoError.Other=>{return 7}}
                }}'''
                with tempfile.TemporaryDirectory() as d:
                    exe=self.build(d,program(body),opt,'#include <unistd.h>\n#include <errno.h>\n'+shim)
                    self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=5).returncode,0)

    def test_signal_state_is_restored_and_pending_signal_preserved(self):
        harness=r"""
        #define _POSIX_C_SOURCE 200809L
        #include <stdint.h>
        #include <signal.h>
        #include <pthread.h>
        #include <unistd.h>
        extern uint64_t liza_rt_write(const uint8_t*,uint32_t);
        int main(void){
            int fds[2]; if(pipe(fds))return 1;
            close(fds[0]);if(dup2(fds[1],1)<0)return 2;close(fds[1]);
            signal(SIGPIPE,SIG_DFL);
            sigset_t set,old,now;sigemptyset(&set);sigaddset(&set,SIGPIPE);
            pthread_sigmask(SIG_UNBLOCK,&set,0);
            if(liza_rt_write((const uint8_t*)"x",1)!=((uint64_t)3<<32))return 3;
            pthread_sigmask(SIG_BLOCK,0,&now);if(sigismember(&now,SIGPIPE))return 4;
            pthread_sigmask(SIG_BLOCK,&set,&old);raise(SIGPIPE);
            if(liza_rt_write((const uint8_t*)"x",1)!=((uint64_t)3<<32))return 5;
            sigpending(&now);if(!sigismember(&now,SIGPIPE))return 6;
            int caught;sigwait(&set,&caught);pthread_sigmask(SIG_SETMASK,&old,0);
            signal(SIGPIPE,SIG_IGN);
            if(liza_rt_write((const uint8_t*)"x",1)!=((uint64_t)3<<32))return 7;
            return 0;
        }
        """
        for opt in ('-O0','-O2'):
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);c=root/'test.c';exe=root/('program.exe' if sys.platform == 'win32' else 'program');c.write_text(harness)
                subprocess.run(['clang',opt,str(c),'liza/runtime/console_posix.c','-pthread','-o',str(exe)],check=True,capture_output=True)
                self.assertEqual(subprocess.run([str(exe)],capture_output=True,timeout=5).returncode,0)

    def test_cli_hello_and_runtime_cost(self):
        from tools.check_console_cost import inspect
        # First invocation includes Python/Clang/linker startup on a fresh
        # Windows runner. This build+run smoke check is not a latency budget.
        startup_timeout = 60 if sys.platform == 'win32' else 15
        for opt in ('0','2'):
            result=subprocess.run([sys.executable,'-B','-m','liza','run','examples/hello.liza','-O',opt],capture_output=True,timeout=startup_timeout)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,b'Hello, Liza!\n')
        with tempfile.TemporaryDirectory() as d:
            report=inspect(d)
            self.assertIn('no heap calls',report)
