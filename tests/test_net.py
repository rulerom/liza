"""Blocking loopback TCP: ownership, region preservation, real bytes and faults."""
from pathlib import Path
import queue
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import unittest

from liza.frontend import CompileError
from liza.modules import load_program
from liza.ir import lower, dump
from liza.backend import llvm
from liza.stdlib import link_flags
import test_io

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'examples/apps/liza_echo.liza'


class NetTypes(unittest.TestCase):
    def test_resource_and_effect_contracts(self):
        source='''fn main()->u32:io {match net.listen(0){Err(e)=>{return 1} Ok(l)=>{
p=net.local_port(l);x=net.close_listener(move l);return 0}}}'''
        import json
        properties=json.loads(dump(test_io.compile_source(source)))['type_properties']
        self.assertFalse(properties['net.Listener']['copyable'])
        for bad in (source.replace('x=net.close_listener(move l);',''),
                    source.replace('move l','copy l'),
                    source.replace('move l','l'),
                    source.replace('return 0','x2=net.close_listener(move l);return 0'),
                    source.replace('net.close_listener','net.close_stream'),
                    source.replace(':io',''),
                    source.replace('net.listen(0)','net.listen(65536)')):
            with self.subTest(bad=bad),self.assertRaises(CompileError):test_io.compile_source(bad)

    def test_read_preserves_region_and_requires_exclusive_buffer(self):
        source='''fn read(s:net.Stream,b:memory.Buffer<u8>)->u32:io {
(next,result)=net.read(s,move b)
x=memory.release(move next);c=net.close_stream(move s);return 0
}
fn main()->u32:io,alloc {match net.listen(0){Err(e)=>{return 1} Ok(l)=>{
match net.accept(l){Err(e)=>{x=net.close_listener(move l);return 2} Ok(s)=>{
x=net.close_listener(move l)
match memory.create(32){Err(e)=>{c=net.close_stream(move s);return 3} Ok(r)=>{
match memory.alloc<u8>(r,32,0){Err(e)=>{c=net.close_stream(move s);z=memory.close(move r);return 4}
Ok(b)=>{(next,result)=net.read(s,move b);z=memory.release(move next);c=net.close_stream(move s);q=memory.close(move r);return 0}}
}}}}}}}'''
        test_io.compile_source(source)
        for bad in (source.replace('z=memory.release(move next);',''),
                    source.replace('(next,result)=net.read(s,move b);','q=memory.close(move r);(next,result)=net.read(s,move b);'),
                    source.replace('(next,result)=net.read(s,move b);','v=memory.view(b);(next,result)=net.read(s,move b);'),
                    source.replace('z=memory.release(move next);','q0=memory.close(move r);z=memory.release(move next);')):
            with self.subTest(bad=bad),self.assertRaises(CompileError):test_io.compile_source(bad)

    def test_read_lowering_has_no_payload_copy_or_allocation(self):
        text=llvm(lower(load_program(APP)))
        body=text.split('@liza_net.read(',1)[1].split('\n}',1)[0]
        self.assertIn('@liza_rt_net_read',body)
        for forbidden in ('memcpy','memmove','alloca','malloc','region_alloc'):
            self.assertNotIn(forbidden,body)
        self.assertIn('%buffer, 0',body)


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class NetNative(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='liza-net-')
        cls.module=lower(load_program(APP));cls.text=llvm(cls.module);cls.executables=[]
        for opt in ('0','2'):
            root=Path(cls.temp.name)/opt;root.mkdir();ir=root/'echo.ll';ir.write_text(cls.text)
            exe=root/'echo.exe'
            built=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*link_flags(cls.module),'-o',str(exe)],capture_output=True)
            if built.returncode:raise RuntimeError(built.stderr.decode(errors='replace'))
            cls.executables.append(exe)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def start(self,exe,mode="--once"):
        p=subprocess.Popen([str(exe),mode],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.addCleanup(lambda: self.stop(p))
        lines=queue.Queue()
        threading.Thread(target=lambda:lines.put(p.stdout.readline()),daemon=True).start()
        line=lines.get(timeout=10)
        self.assertTrue(line.strip().isdigit(),line)
        return p,int(line)

    @staticmethod
    def stop(p):
        if p.poll() is None:p.kill()
        p.wait(timeout=10)
        p.stdout.close();p.stderr.close()

    def test_empty_binary_multichunk_and_half_close(self):
        for exe in self.executables:
            for payload in (b'',b'\x00\xff\xfe\r\n',bytes(range(256))*1025):
                with self.subTest(exe=exe,payload=len(payload)):
                    p,port=self.start(exe)
                    with socket.create_connection(('127.0.0.1',port),timeout=10) as s:
                        # Send/read interleaved to avoid client/server backpressure deadlock.
                        received=bytearray()
                        for start in range(0,len(payload),997):
                            block=payload[start:start+997];s.sendall(block)
                            remaining=len(block)
                            while remaining:
                                part=s.recv(remaining);self.assertTrue(part)
                                received.extend(part);remaining-=len(part)
                        s.shutdown(socket.SHUT_WR)
                        self.assertEqual(s.recv(1),b'')
                    self.assertEqual(bytes(received),payload)
                    self.assertEqual(p.wait(timeout=10),0,p.stderr.read())
                    self.assertEqual(p.stderr.read(),b'')

    def test_multiple_sequential_clients_reuse_server(self):
        for exe in self.executables:
            p,port=self.start(exe,'--ephemeral')
            for i in range(12):
                with socket.create_connection(('127.0.0.1',port),timeout=10) as s:
                    payload=bytes([i,0,255])*80;s.sendall(payload);s.shutdown(socket.SHUT_WR)
                    actual=bytearray()
                    while True:
                        part=s.recv(4096)
                        if not part:break
                        actual.extend(part)
                    self.assertEqual(bytes(actual),payload)
            self.assertIsNone(p.poll())

    def test_reset_is_io_error_not_process_signal(self):
        for exe in self.executables:
            p,port=self.start(exe)
            with socket.create_connection(('127.0.0.1',port),timeout=10) as s:
                # Confirm accept completed before reset; otherwise the OS may
                # report an accept error rather than a stream read error.
                s.sendall(b"x")
                self.assertEqual(s.recv(1),b"x")
                # Abort the stream instead of sending EOF.
                import os
                linger=struct.pack('HH' if os.name=='nt' else 'ii',1,0)
                s.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,linger)
            self.assertEqual(p.wait(timeout=10),3)
            self.assertEqual(p.stderr.read(),b'Connection I/O failed\n')

    def test_partial_write_and_failure_cleanup(self):
        # Exercise the Liza application with deterministic OS-boundary outcomes.
        c=r'''
#include <stdint.h>
#include <stdlib.h>
static int reads,writes,closes;
static void verify(void){if(closes!=2 || writes!=EXPECTED)_Exit(90);}
uint32_t liza_rt_net_listen(uint16_t port,uint64_t*out){*out=10;atexit(verify);return 0;}
uint32_t liza_rt_net_accept(uint64_t h,uint64_t*out){if(h!=10)_Exit(91);*out=11;return 0;}
uint64_t liza_rt_net_port(uint64_t h){return 12345;}
uint64_t liza_rt_net_read(uint64_t h,uint8_t*p,uint32_t n){
if(h!=11||n!=2048)_Exit(92);
if(READERR)return (uint64_t)5<<32;
if(reads++)return 0;
p[0]=0;p[1]=255;p[2]=42;p[3]=7;return 4;}
uint64_t liza_rt_net_write(uint64_t h,const uint8_t*p,uint32_t n,uint32_t start,uint32_t count){
if(h!=11||n!=2048||start!=(uint32_t)(writes*2)||count!=4-start||p[1]!=255)_Exit(93);
writes++;if(WRITEERR&&writes==2)return (uint64_t)5<<32;return 2;}
uint32_t liza_rt_net_close(uint64_t h){if(h!=(closes?10:11))_Exit(94);closes++;return CLOSEERR?7:0;}
'''
        for opt in ('0','2'):
            for readerr,writeerr,closeerr,expected,exitcode in ((0,0,0,2,0),(1,0,0,0,3),(0,1,0,2,3),(0,0,1,2,3)):
                with self.subTest(opt=opt,readerr=readerr,writeerr=writeerr,closeerr=closeerr):
                    root=Path(self.temp.name);stub=root/'stub.c';stub.write_text(c)
                    exe=root/'stub.exe'
                    flags=[f'-DREADERR={readerr}',f'-DWRITEERR={writeerr}',f'-DCLOSEERR={closeerr}',f'-DEXPECTED={expected}']
                    runtime=[f for f in link_flags(self.module) if 'net_' not in f]
                    subprocess.run(['clang','-Wno-override-module','-O'+opt,*flags,str(root/opt/'echo.ll'),str(stub),*runtime,'-o',str(exe)],check=True,capture_output=True)
                    r=subprocess.run([str(exe),'--once'],capture_output=True,timeout=10)
                    self.assertEqual(r.returncode,exitcode,r.stderr)
                    self.assertEqual(r.stdout,b'12345\n')

    def test_nonempty_write_requires_progress_at_os_boundary(self):
        # Replace only send, keeping the real runtime's zero/progress handling.
        c=r'''#include <stdint.h>
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
static int calls, outcome;
static int fake_send(SOCKET s,const char *p,int n,int flags) {
#else
#include <sys/socket.h>
#include <netinet/in.h>
static int calls, outcome;
static ssize_t fake_send(int s,const void *p,size_t n,int flags) {
#endif
    (void)s;(void)p;(void)flags;
    if(n!=4)return -1;
    calls++;return outcome;
}
#define send fake_send
#include "net_common.h"
int main(void) {
    uint8_t data[8]={0};
    if(liza_rt_net_write(1,data,8,2,0)!=0 || calls!=0)return 1;
    outcome=0;
    if(liza_rt_net_write(1,data,8,2,4)!=((uint64_t)5<<32) || calls!=1)return 2;
    outcome=2;
    if(liza_rt_net_write(1,data,8,2,4)!=2 || calls!=2)return 3;
    outcome=4;
    if(liza_rt_net_write(1,data,8,2,4)!=4 || calls!=3)return 4;
    return 0;
}
'''
        root=Path(self.temp.name);source=root/'progress.c';source.write_text(c)
        libraries=[f for f in link_flags(self.module) if f=='-lws2_32']
        for opt in ('0','2'):
            exe=root/('progress-'+opt+'.exe')
            built=subprocess.run(['clang','-O'+opt,'-I',str(ROOT/'liza/runtime'),str(source),*libraries,'-o',str(exe)],capture_output=True)
            self.assertEqual(built.returncode,0,built.stderr)
            self.assertEqual(subprocess.run([str(exe)],timeout=10).returncode,0)

    def test_native_read_write_do_not_allocate_or_copy_payload(self):
        import re
        runtime=next(f for f in link_flags(self.module) if 'net_' in f)
        for opt in ('0','2'):
            target=Path(self.temp.name)/('runtime-'+opt+'.ll')
            subprocess.run(['clang','-O'+opt,'-S','-emit-llvm',runtime,'-o',str(target)],check=True,capture_output=True)
            text=target.read_text()
            for name in ('read','write'):
                body=re.search(r'define[^\n]*@liza_rt_net_'+name+r'\(.*?^}',text,re.S|re.M)
                self.assertIsNotNone(body)
                self.assertNotRegex(body.group(),r'@(?:malloc|calloc|realloc|memcpy|memmove|llvm\.memcpy|llvm\.memmove)')

    def test_runtime_ranges_and_listener_collision(self):
        # Native boundary checks avoid relying on error code interpretation alone.
        c=r'''
#include <stdint.h>
uint32_t liza_rt_net_listen(uint16_t,uint64_t*);
uint64_t liza_rt_net_port(uint64_t);
uint64_t liza_rt_net_read(uint64_t,uint8_t*,uint32_t);
uint64_t liza_rt_net_write(uint64_t,const uint8_t*,uint32_t,uint32_t,uint32_t);
uint32_t liza_rt_net_close(uint64_t);
int main(void){uint64_t a,b;uint8_t data[4]={0};
if(liza_rt_net_listen(0,&a))return 1;
uint64_t port=liza_rt_net_port(a);if(!port||port>65535)return 2;
if(!liza_rt_net_listen((uint16_t)port,&b))return 3;
if(liza_rt_net_read(a,data,0)!=((uint64_t)6<<32))return 4;
if(liza_rt_net_write(a,data,4,5,0)!=((uint64_t)6<<32))return 5;
if(liza_rt_net_write(a,data,4,1,UINT32_MAX)!=((uint64_t)6<<32))return 6;
if(liza_rt_net_write(a,data,4,4,0)!=0)return 7;
return liza_rt_net_close(a)?8:0;}
'''
        root=Path(self.temp.name);source=root/'ranges.c';source.write_text(c);exe=root/'ranges.exe'
        runtime=[f for f in link_flags(self.module) if 'net_' in f or f=='-lws2_32']
        subprocess.run(['clang',str(source),*runtime,'-o',str(exe)],check=True,capture_output=True)
        self.assertEqual(subprocess.run([str(exe)],timeout=10).returncode,0)
