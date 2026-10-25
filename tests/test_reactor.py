"""Bounded socket ownership, readiness and a multi-client framed server."""
from pathlib import Path
import json
import shutil
import socket
import struct
import subprocess
import tempfile
import unittest

from liza.frontend import CompileError
from liza.modules import load_program
from liza.ir import lower, dump
from liza.backend import llvm
from liza.stdlib import link_flags
import test_io
import test_net

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'examples/apps/liza_reactor.liza'


def receive(sock,n):
    result=bytearray()
    while len(result)<n:
        chunk=sock.recv(n-len(result))
        if not chunk:raise AssertionError('premature EOF')
        result.extend(chunk)
    return bytes(result)


def frame(data):return struct.pack('!I',len(data))+data


class ReactorTypes(unittest.TestCase):
    def test_owner_is_linear_and_allocation_explicit(self):
        source='''fn main()->u32:io,alloc {
match net.reactor_create(0,8) {Err(e)=>{return 1} Ok(r)=>{
p=net.reactor_poll(r,0);c=net.reactor_close(move r);return 0}}}'''
        module=test_io.compile_source(source)
        self.assertFalse(json.loads(dump(module))['type_properties']['net.Reactor']['copyable'])
        for bad in (source.replace('c=net.reactor_close(move r);',''),
                    source.replace('move r','copy r'),source.replace('move r','r'),
                    source.replace(':io,alloc',':io'),
                    source.replace('return 0','again=net.reactor_poll(r,0);return 0'),
                    source.replace('return 0','again=net.reactor_close(move r);return 0')):
            with self.subTest(bad=bad),self.assertRaises(CompileError):test_io.compile_source(bad)

    def test_read_keeps_origin_and_requires_exclusive_buffer(self):
        source='''fn main()->u32:io,alloc {
match net.reactor_create(0,8) {Err(e)=>{return 1} Ok(r)=>{
match memory.create(32) {Err(e)=>{c=net.reactor_close(move r);return 2} Ok(region)=>{
match memory.alloc<u8>(region,32,0) {
Err(e)=>{c=net.reactor_close(move r);f=memory.close(move region);return 3}
Ok(b)=>{var buffer=move b
match net.reactor_accept(r) {Err(e)=>{} Ok(id)=>{
(next,result)=net.reactor_read(r,id,move buffer,0,32);buffer=move next
}}
x=memory.release(move buffer);f=memory.close(move region);c=net.reactor_close(move r);return 0
}}}}}}}'''
        test_io.compile_source(source)
        for bad in (source.replace('(next,result)=','v=memory.view(buffer);(next,result)='),
                    source.replace('buffer=move next','f0=memory.close(move region);buffer=move next'),
                    source.replace('x=memory.release(move buffer);','')):
            with self.subTest(bad=bad),self.assertRaises(CompileError):test_io.compile_source(bad)

    def test_read_adapter_has_no_payload_copy_or_allocation(self):
        text=llvm(lower(load_program(APP)))
        body=text.split('@liza_net.reactor_read(',1)[1].split('\n}',1)[0]
        self.assertIn('@liza_rt_reactor_read',body)
        for name in ('memcpy','memmove','malloc','alloca','region_alloc'):
            self.assertNotIn(name,body)
        self.assertIn('%data, 0',body)


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class ReactorNative(unittest.TestCase):
    start=test_net.NetNative.start
    stop=staticmethod(test_net.NetNative.stop)

    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='liza-reactor-')
        cls.module=lower(load_program(APP));cls.text=llvm(cls.module);cls.executables=[]
        for opt in ('0','2'):
            root=Path(cls.temp.name)/opt;root.mkdir();ir=root/'reactor.ll';ir.write_text(cls.text)
            exe=root/'reactor.exe'
            built=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*link_flags(cls.module),'-o',str(exe)],capture_output=True)
            if built.returncode:raise RuntimeError(built.stderr.decode(errors='replace'))
            cls.executables.append(exe)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def connect(self,port):
        s=socket.create_connection(('127.0.0.1',port),timeout=5)
        self.addCleanup(s.close)
        return s

    def test_stalled_header_does_not_block_other_clients(self):
        for exe in self.executables:
            with self.subTest(exe=exe):
                p,port=self.start(exe,'--ephemeral')
                a=self.connect(port);b=self.connect(port);c=self.connect(port)
                a.sendall(b'\0\0')
                wire=frame(b'B\x00\xff');b.sendall(wire)
                self.assertEqual(receive(b,len(wire)),wire)
                wire=frame(b'')+frame(b'C')+frame(bytes(range(256))*256)
                c.sendall(wire);self.assertEqual(receive(c,len(wire)),wire)
                a.sendall(b'\0\x03abc');self.assertEqual(receive(a,7),frame(b'abc'))
                a.close();b.close();c.close()
                self.assertIsNone(p.poll())

    def test_coalesced_frames_half_close_and_slot_reuse(self):
        for exe in self.executables:
            p,port=self.start(exe,'--ephemeral')
            for _ in range(12):
                with self.connect(port) as s:
                    wire=frame(b'')*40+frame(b'abc')+frame(bytes(range(256))*9)
                    s.sendall(wire);s.shutdown(socket.SHUT_WR)
                    self.assertEqual(receive(s,len(wire)),wire)
                    self.assertEqual(s.recv(1),b'')
            self.assertIsNone(p.poll())

    def test_full_capacity_waits_until_slot_is_released(self):
        for exe in self.executables:
            p,port=self.start(exe,'--ephemeral')
            clients=[self.connect(port) for _ in range(8)]
            for s in clients:
                s.sendall(frame(b'x'));self.assertEqual(receive(s,5),frame(b'x'))
            ninth=self.connect(port);ninth.sendall(frame(b'ninth'));ninth.settimeout(.15)
            with self.assertRaises(socket.timeout):ninth.recv(1)
            clients[3].shutdown(socket.SHUT_WR)
            self.assertEqual(clients[3].recv(1),b'')
            ninth.settimeout(5)
            self.assertEqual(receive(ninth,9),frame(b'ninth'))
            self.assertIsNone(p.poll())

    def test_slow_reader_does_not_block_fast_client(self):
        for exe in self.executables:
            p,port=self.start(exe,'--ephemeral')
            slow=self.connect(port);slow.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,4096)
            # Fill both TCP directions without reading echoed data.
            slow.settimeout(.1);wire=frame(b'x'*65536)
            for _ in range(128):
                try:slow.sendall(wire)
                except socket.timeout:break
            fast=self.connect(port);fast.sendall(frame(b'fast'))
            self.assertEqual(receive(fast,8),frame(b'fast'))
            self.assertIsNone(p.poll())

    def test_once_eof_and_protocol_failure_cleanup(self):
        for exe in self.executables:
            for wire,expected,response in [(frame(b'done'),0,frame(b'done')),
                                            (b'\0\0',4,b''),
                                            (struct.pack('!I',65537),4,b''),
                                            (frame(b'ok')+b'\0',4,frame(b'ok'))]:
                p,port=self.start(exe)
                with self.connect(port) as s:
                    s.sendall(wire);s.shutdown(socket.SHUT_WR)
                    self.assertEqual(receive(s,len(response)),response)
                    self.assertEqual(s.recv(1),b'')
                self.assertEqual(p.wait(timeout=5),expected)
                self.assertEqual(p.stderr.read(),b'')

    def test_reset_does_not_stop_other_clients(self):
        for exe in self.executables:
            p,port=self.start(exe,'--ephemeral')
            broken=self.connect(port)
            broken.sendall(frame(b'x'))
            self.assertEqual(receive(broken,5),frame(b'x'))
            linger=struct.pack('HH' if __import__('sys').platform=='win32' else 'ii',1,0)
            broken.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,linger)
            broken.close()
            healthy=self.connect(port);healthy.sendall(frame(b'healthy'))
            self.assertEqual(receive(healthy,11),frame(b'healthy'))
            self.assertIsNone(p.poll())

    def test_partial_io_and_would_block_after_readiness(self):
        runtime=ROOT/'liza/runtime'
        stub=Path(self.temp.name)/'short.c'
        stub.write_text('''#define liza_rt_net_read real_read
#define liza_rt_net_write real_write
#include "net_common.h"
#undef liza_rt_net_read
#undef liza_rt_net_write
static unsigned reads,writes;
uint64_t liza_rt_net_read(uint64_t h,uint8_t*p,uint32_t n) {
 if (++reads%3==0) return (uint64_t)4<<32;
 return real_read(h,p,n>3?3:n);
}
uint64_t liza_rt_net_write(uint64_t h,const uint8_t*p,uint32_t n,uint32_t s,uint32_t c) {
 if (++writes%3==0) return (uint64_t)4<<32;
 return real_write(h,p,n,s,c>7?7:c);
}
#include "reactor_common.h"
''')
        for opt in ('0','2'):
            exe=Path(self.temp.name)/('short'+opt+'.exe')
            flags=[f for f in link_flags(self.module) if not Path(f).name.startswith(('net_','reactor_'))]
            built=subprocess.run(['clang','-Wno-override-module','-O'+opt,'-I'+str(runtime),str(stub),str(Path(self.temp.name)/opt/'reactor.ll'),*flags,'-o',str(exe)],capture_output=True)
            self.assertEqual(built.returncode,0,built.stderr.decode(errors='replace'))
            p,port=self.start(exe)
            with self.connect(port) as s:
                wire=frame(b'')+frame(bytes(range(256))*3)+frame(b'last')
                s.sendall(wire);s.shutdown(socket.SHUT_WR)
                self.assertEqual(receive(s,len(wire)),wire)
                self.assertEqual(s.recv(1),b'')
            self.assertEqual(p.wait(timeout=5),0)

    def test_runtime_identities_ranges_generations_and_close(self):
        harness=Path(self.temp.name)/'runtime.c'
        harness.write_text(r'''
#define liza_rt_net_close real_close
#include "net_common.h"
#undef liza_rt_net_close
static unsigned close_calls,fail_close;
uint32_t liza_rt_net_close(uint64_t h) {
 uint32_t e=real_close(h);close_calls++;
 if (fail_close) {fail_close=0;return 7;}
 return e;
}
#include "reactor_common.h"
#include <assert.h>
static uint64_t client(reactor *r) {
 assert(net_start()==0);
 net_socket s=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);assert(s!=NET_INVALID);
 struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;
 a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);a.sin_port=htons((uint16_t)liza_rt_reactor_port(r));
 assert(connect(s,(struct sockaddr*)&a,sizeof(a))==0);return (uint64_t)s;
}
static void accepted(reactor *r,uint64_t *id) {
 assert(liza_rt_reactor_poll(r,2000)>0);
 assert(liza_rt_reactor_accept(r,id)==0);
}
#define ID(r,id) r,id[0],id[1],id[2]
int main(void) {
 reactor *a,*b;uint64_t id[3],next[3],bad[3];uint8_t data[8]={0};
 assert(liza_rt_reactor_create(0,0,&a)==8 && a==NULL);
 assert(liza_rt_reactor_create(0,33,&a)==8 && a==NULL);
 assert(liza_rt_reactor_create(0,1,&a)==0);
 assert(liza_rt_reactor_create(0,1,&b)==0);
 assert(liza_rt_reactor_accept(a,id)==4);
 assert(liza_rt_reactor_poll(a,0)==0);
 assert(liza_rt_reactor_poll(a,UINT32_MAX)==net_failure(6));
 uint64_t first=client(a);accepted(a,id);
 assert(liza_rt_reactor_accept(a,bad)==9);
 assert(liza_rt_reactor_ready(ID(b,id))==net_failure(10));
 assert(liza_rt_reactor_disconnect(ID(b,id))==net_failure(10));
 assert(liza_rt_reactor_read(ID(a,id),data,8,0,8)==net_failure(4));
 assert(liza_rt_reactor_read(ID(a,id),data,8,8,1)==net_failure(6));
 assert(liza_rt_reactor_read(ID(a,id),data,8,0,0)==net_failure(6));
 assert(liza_rt_reactor_write(ID(a,id),data,8,UINT32_MAX,2)==net_failure(6));
 assert(liza_rt_reactor_write(ID(a,id),data,8,8,0)==0);
 assert(liza_rt_reactor_interest(ID(a,id),4)==net_failure(6));
 assert(liza_rt_reactor_interest(ID(a,id),2)==0);
 assert(liza_rt_reactor_poll(a,2000)==1);
 assert(liza_rt_reactor_ready(ID(a,id))&2);
 assert(liza_rt_reactor_interest(ID(a,id),0)==0);
 assert(liza_rt_reactor_poll(a,1)==0);
 assert(liza_rt_reactor_ready(ID(a,id))==0);
 assert(liza_rt_reactor_disconnect(ID(a,id))==0);
 assert(liza_rt_reactor_disconnect(ID(a,id))==net_failure(10));
 assert(liza_rt_reactor_read(ID(a,id),data,8,0,8)==net_failure(10));
 assert(liza_rt_reactor_write(ID(a,id),data,8,0,8)==net_failure(10));
 uint64_t second=client(a);accepted(a,next);
 assert(next[0]==id[0] && next[2]==id[2] && next[1]!=id[1]);
 assert(liza_rt_reactor_ready(ID(a,id))==net_failure(10));
 assert(liza_rt_reactor_ready(ID(a,next))==0);
 assert(liza_rt_reactor_interest(ID(a,id),1)==net_failure(10));
 assert(liza_rt_reactor_close(a)==0);
 /* Closing the owner closes its live child. */
 assert(liza_rt_net_read(second,data,8)==0);
 liza_rt_net_close(first);liza_rt_net_close(second);
 assert(liza_rt_reactor_ready(ID(b,next))==net_failure(10));
 b->slots[0].generation=UINT64_MAX;
 assert(liza_rt_reactor_accept(b,bad)==9); /* no generation wrap */
 assert(liza_rt_reactor_poll(b,0)==0);
 assert(liza_rt_reactor_close(b)==0);
 assert(liza_rt_reactor_create(0,2,&a)==0);
 first=client(a);accepted(a,id);second=client(a);accepted(a,next);
 close_calls=0;fail_close=1;
 assert(liza_rt_reactor_close(a)==7 && close_calls==3);
 assert(liza_rt_net_read(first,data,8)==0 && liza_rt_net_read(second,data,8)==0);
 liza_rt_net_close(first);liza_rt_net_close(second);
 reactor_next_owner=UINT64_MAX;
 assert(liza_rt_reactor_create(0,1,&a)==11 && a==NULL);
 return 0;
}
''')
        runtime=ROOT/'liza/runtime'
        for opt in ('0','2'):
            exe=Path(self.temp.name)/('runtime'+opt+'.exe')
            flags=['-lws2_32'] if __import__('sys').platform=='win32' else []
            built=subprocess.run(['clang','-O'+opt,'-I'+str(runtime),str(harness),*flags,'-o',str(exe)],capture_output=True)
            self.assertEqual(built.returncode,0,built.stderr.decode(errors='replace'))
            ran=subprocess.run([str(exe)],capture_output=True,timeout=15)
            self.assertEqual(ran.returncode,0,ran.stderr)

    def test_runtime_hot_path_does_not_allocate_or_copy_payload(self):
        runtime=ROOT/'liza/runtime'
        for opt in ('0','2'):
            built=subprocess.run(['clang','-S','-emit-llvm','-O'+opt,str(runtime/('reactor_windows.c' if __import__('sys').platform=='win32' else 'reactor_posix.c')),'-o','-'],capture_output=True,text=True)
            self.assertEqual(built.returncode,0,built.stderr)
            for operation in ('read','write','poll','ready','interest','accept','disconnect'):
                body=built.stdout.split('@liza_rt_reactor_'+operation+'(',1)[1].split('\n}',1)[0]
                for name in ('@malloc','@calloc','@realloc','@llvm.memcpy','@llvm.memmove'):
                    self.assertNotIn(name,body,(opt,operation,name))
