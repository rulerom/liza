"""Bounded duplex TCP relay: real streams, half-close, connecting and faults."""
from pathlib import Path
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import unittest
import unittest.mock

from liza.ir import lower
from liza.modules import load_program
from liza.backend import llvm
from liza.stdlib import link_flags
import test_net
import test_reactor

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'examples/apps/liza_proxy.liza'
receive=test_reactor.receive


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class ProxyNative(unittest.TestCase):
    start=test_net.NetNative.start
    stop=staticmethod(test_net.NetNative.stop)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='liza-proxy-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.count=0

    def listener(self):
        s=socket.socket();s.bind(('127.0.0.1',0));s.listen(16);s.settimeout(8)
        self.addCleanup(s.close);return s

    def connect(self,port):
        s=socket.create_connection(('127.0.0.1',port),timeout=8);self.addCleanup(s.close);return s

    def build(self,port,opt,fault=False):
        self.count+=1;root=self.root/str(self.count);root.mkdir();(root/'relay').mkdir()
        # The application has one build-time upstream, not runtime routing.
        source=APP.read_text().replace('var upstream:u16=9003','var upstream:u16='+str(port))
        path=root/'liza_proxy.liza';path.write_text(source)
        shutil.copy(ROOT/'examples/apps/relay/direction.liza',root/'relay/direction.liza')
        module=lower(load_program(path));text=llvm(module)
        ir=root/'proxy.ll';ir.write_text(text);exe=root/'proxy.exe';flags=link_flags(module)
        if fault:
            runtime=ROOT/'liza/runtime';stub=root/'fault.c'
            stub.write_text(r'''
#define liza_rt_net_read real_read
#define liza_rt_net_write real_write
#include "net_common.h"
#undef liza_rt_net_read
#undef liza_rt_net_write
static unsigned reads,writes;
uint64_t liza_rt_net_read(uint64_t h,uint8_t*p,uint32_t n) {
 if (++reads%7==0) return (uint64_t)4<<32;
 return real_read(h,p,n>13?13:n);
}
uint64_t liza_rt_net_write(uint64_t h,const uint8_t*p,uint32_t n,uint32_t s,uint32_t c) {
 if (++writes%5==0) return (uint64_t)4<<32;
 return real_write(h,p,n,s,c>7?7:c);
}
#define liza_rt_reactor_connect real_connect
#define liza_rt_reactor_finish_connect real_finish
#include "reactor_common.h"
#undef liza_rt_reactor_connect
#undef liza_rt_reactor_finish_connect
#include <stdio.h>
uint32_t liza_rt_reactor_connect(reactor*r,uint16_t p,uint64_t*id) {
 uint32_t e=real_connect(r,p,id);
 if (!e && getenv("LIZA_CONNECT_GATE")) r->slots[id[2]].phase=1;
 return e;
}
uint64_t liza_rt_reactor_finish_connect(reactor*r,uint64_t o,uint64_t g,uint64_t s) {
 const char*gate=getenv("LIZA_CONNECT_GATE");
 if (gate) {FILE*f=fopen(gate,"rb");if (!f)return 0;fclose(f);}
 return real_finish(r,o,g,s);
}
''')
            flags=[f for f in flags if not Path(f).name.startswith(('net_','reactor_'))]
            flags=[str(stub),'-I'+str(runtime),*flags]
        result=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*flags,'-o',str(exe)],capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        return exe,text

    def test_request_half_close_then_complete_response(self):
        for opt in ('0','2'):
            for fault in (False,True):
                listener=self.listener();exe,text=self.build(listener.getsockname()[1],opt,fault)
                p,port=self.start(exe);client=self.connect(port)
                upstream,_=listener.accept();upstream.settimeout(8);self.addCleanup(upstream.close)
                request=bytes(range(256))*(11 if fault else 257)
                client.sendall(request);client.shutdown(socket.SHUT_WR)
                self.assertEqual(receive(upstream,len(request)),request)
                self.assertEqual(upstream.recv(1),b'')
                response=request[::-1]+b'\x00\xffresponse'
                upstream.sendall(response);upstream.shutdown(socket.SHUT_WR)
                self.assertEqual(receive(client,len(response)),response)
                self.assertEqual(client.recv(1),b'');self.assertEqual(p.wait(timeout=8),0)
                self.assertEqual(p.stderr.read(),b'')

    def test_client_eof_and_buffer_are_preserved_during_connect(self):
        for opt in ('0','2'):
            for payload in (b'',b'before-connect\x00\xff',bytes(range(256))*13):
                listener=self.listener();exe,text=self.build(listener.getsockname()[1],opt,True)
                gate=self.root/('connect-'+opt+str(len(payload)))
                with unittest.mock.patch.dict(os.environ,{'LIZA_CONNECT_GATE':str(gate)}):p,port=self.start(exe)
                client=self.connect(port);upstream,_=listener.accept();self.addCleanup(upstream.close)
                client.sendall(payload);client.shutdown(socket.SHUT_WR)
                upstream.settimeout(.15)
                with self.assertRaises(socket.timeout):upstream.recv(1)
                gate.write_bytes(b'connected');upstream.settimeout(8)
                self.assertEqual(receive(upstream,len(payload)),payload);self.assertEqual(upstream.recv(1),b'')
                upstream.sendall(b'after-eof');upstream.shutdown(socket.SHUT_WR)
                self.assertEqual(receive(client,9),b'after-eof');self.assertEqual(client.recv(1),b'')
                self.assertEqual(p.wait(timeout=8),0)

    def test_upstream_half_close_still_allows_client_to_send(self):
        for opt in ('0','2'):
            listener=self.listener();exe,text=self.build(listener.getsockname()[1],opt)
            p,port=self.start(exe);client=self.connect(port);upstream,_=listener.accept()
            upstream.settimeout(8);self.addCleanup(upstream.close)
            upstream.sendall(b'greeting');upstream.shutdown(socket.SHUT_WR)
            self.assertEqual(receive(client,8),b'greeting');self.assertEqual(client.recv(1),b'')
            payload=bytes(range(256))*31
            client.sendall(payload);client.shutdown(socket.SHUT_WR)
            self.assertEqual(receive(upstream,len(payload)),payload);self.assertEqual(upstream.recv(1),b'')
            self.assertEqual(p.wait(timeout=8),0)

    def test_simultaneous_large_streams_with_asymmetric_readers(self):
        for opt in ('0','2'):
            listener=self.listener();exe,text=self.build(listener.getsockname()[1],opt)
            p,port=self.start(exe);client=self.connect(port);upstream,_=listener.accept()
            upstream.settimeout(15);client.settimeout(15);self.addCleanup(upstream.close)
            a=bytes(range(256))*4097;b=(b'\xff\0other-direction'*65537)
            errors=[]
            def write(sock,data):
                try:sock.sendall(data);sock.shutdown(socket.SHUT_WR)
                except Exception as e:errors.append(e)
            def read(sock,expected,size,delay):
                try:
                    got=bytearray()
                    while True:
                        chunk=sock.recv(size)
                        if not chunk:break
                        got.extend(chunk)
                        if delay:time.sleep(delay)
                    self.assertEqual(bytes(got),expected)
                except Exception as e:errors.append(e)
            jobs=[threading.Thread(target=write,args=(client,a)),threading.Thread(target=write,args=(upstream,b)),
                  threading.Thread(target=read,args=(client,b,997,.0001)),threading.Thread(target=read,args=(upstream,a,4093,0))]
            for job in jobs:job.start()
            for job in jobs:job.join(20)
            self.assertTrue(all(not j.is_alive() for j in jobs));self.assertFalse(errors,errors)
            self.assertEqual(p.wait(timeout=8),0)

    def test_eight_pairs_stalled_client_and_slot_reuse(self):
        for opt in ('0','2'):
            listener=self.listener();exe,text=self.build(listener.getsockname()[1],opt)
            p,port=self.start(exe,'--ephemeral');clients=[];servers=[]
            for i in range(8):
                clients.append(self.connect(port));s,_=listener.accept();s.settimeout(8);self.addCleanup(s.close);servers.append(s)
            # Pair zero stays idle; every other pair makes independent progress.
            for i in range(1,8):
                data=bytes([i])*5000;clients[i].sendall(data);self.assertEqual(receive(servers[i],len(data)),data)
                servers[i].sendall(data[::-1]);self.assertEqual(receive(clients[i],len(data)),data[::-1])
            for i in range(8):
                clients[i].shutdown(socket.SHUT_WR);self.assertEqual(servers[i].recv(1),b'')
                servers[i].shutdown(socket.SHUT_WR);self.assertEqual(clients[i].recv(1),b'')
            fresh=self.connect(port);s,_=listener.accept();s.settimeout(8);self.addCleanup(s.close)
            fresh.sendall(b'new');fresh.shutdown(socket.SHUT_WR)
            self.assertEqual(receive(s,3),b'new');self.assertEqual(s.recv(1),b'')
            s.shutdown(socket.SHUT_WR);self.assertEqual(fresh.recv(1),b'');self.assertIsNone(p.poll())

    def test_connection_refused_and_reset_close_entire_pair(self):
        for opt in ('0','2'):
            refused=socket.socket();refused.bind(('127.0.0.1',0));self.addCleanup(refused.close)
            port=refused.getsockname()[1] # Bound but not listening: cannot be reused by the proxy listener.
            exe,text=self.build(port,opt);p,port=self.start(exe);client=self.connect(port)
            try:self.assertEqual(client.recv(1),b'')
            except ConnectionResetError:pass
            self.assertEqual(p.wait(timeout=8),3)
            for side in ('client','upstream'):
                listener=self.listener();exe,text=self.build(listener.getsockname()[1],opt)
                p,port=self.start(exe);client=self.connect(port);upstream,_=listener.accept()
                upstream.settimeout(8);self.addCleanup(upstream.close)
                client.sendall(b'sync');self.assertEqual(receive(upstream,4),b'sync')
                broken,other=(client,upstream) if side=='client' else (upstream,client)
                linger=struct.pack('HH' if os.name=='nt' else 'ii',1,0)
                broken.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,linger);broken.close()
                try:self.assertEqual(other.recv(1),b'')
                except ConnectionResetError:pass
                self.assertEqual(p.wait(timeout=8),3)

    def test_no_payload_allocation_or_copy_in_relay(self):
        module=lower(load_program(APP));text=llvm(module)
        body=text.split('@liza_liza_proxy.exchange(',1)[1].split('\n}',1)[0]
        for forbidden in ('@liza_rt_region_create','@liza_rt_region_alloc','@liza_rt_vec_reserve','@malloc','@calloc'):
            self.assertNotIn(forbidden,body)
        # No buffer.update: successful reads already populate the outgoing storage.
        function=next(fn for fn in module if fn.name.endswith('.exchange'))
        operations=[op.op for block in function.blocks for op in block.operations]
        self.assertNotIn('buffer.update',operations)

    def test_connect_state_and_shutdown_runtime_contract(self):
        harness=self.root/'state.c'
        harness.write_text(r'''
#include "net_common.h"
#ifndef _WIN32
#include <poll.h>
#endif
#include <assert.h>
static int ready_now,connect_error,probes,shutdowns;
#ifdef _WIN32
static int probe_select(int n,fd_set*r,fd_set*w,fd_set*e,const struct timeval*t) {return ready_now;}
static int probe_error(SOCKET s,int level,int option,char*out,int*length) {
 assert(level==SOL_SOCKET && option==SO_ERROR);*(int*)out=connect_error;probes++;return 0;
}
static int probe_shutdown(SOCKET s,int how) {assert(how==SD_SEND);shutdowns++;return 0;}
#define select probe_select
#else
static int probe_poll(struct pollfd*f,nfds_t n,int timeout) {assert(timeout==0);return ready_now;}
static int probe_error(int s,int level,int option,void*out,socklen_t*length) {
 assert(level==SOL_SOCKET && option==SO_ERROR);*(int*)out=connect_error;probes++;return 0;
}
static int probe_shutdown(int s,int how) {assert(how==SHUT_WR);shutdowns++;return 0;}
#define poll probe_poll
#endif
#define getsockopt probe_error
#define shutdown probe_shutdown
#include "reactor_common.h"
int main(void) {
 reactor r;memset(&r,0,sizeof(r));r.owner=1;r.capacity=1;
 reactor_slot*s=&r.slots[0];s->live=1;s->generation=1;s->phase=1;s->ready=2;
 uint8_t bytes[2]={0};uint64_t id[3];
 assert(liza_rt_reactor_connect(&r,0,id)==6);
 assert(liza_rt_reactor_connect(&r,1,id)==9 && id[0]==0 && id[1]==0 && id[2]==0);
 assert(liza_rt_reactor_finish_connect(&r,1,1,0)==0 && probes==0);
 assert(liza_rt_reactor_read(&r,1,1,0,bytes,2,0,1)==net_failure(4));
 assert(liza_rt_reactor_write(&r,1,1,0,bytes,2,0,1)==net_failure(4));
 assert(liza_rt_reactor_shutdown_write(&r,1,1,0)==net_failure(4) && shutdowns==0);
 ready_now=1;
#ifdef _WIN32
 connect_error=WSAECONNREFUSED;
#else
 connect_error=ECONNREFUSED;
#endif
 uint64_t failed=liza_rt_reactor_finish_connect(&r,1,1,0);
 assert(failed>>32 && probes==1 && s->phase==2);
 connect_error=0;
 assert(liza_rt_reactor_finish_connect(&r,1,1,0)==failed && probes==1);
 assert(liza_rt_reactor_read(&r,1,1,0,bytes,2,0,1)==failed);
 assert(liza_rt_reactor_write(&r,1,1,0,bytes,2,0,1)==failed);
 assert(liza_rt_reactor_shutdown_write(&r,1,1,0)==failed);
 s->phase=1;s->error=0;
 assert(liza_rt_reactor_finish_connect(&r,1,1,0)==1 && probes==2);
 assert(liza_rt_reactor_finish_connect(&r,1,1,0)==1 && probes==2);
 assert(liza_rt_reactor_shutdown_write(&r,1,1,0)==0 && shutdowns==1);
 assert(liza_rt_reactor_shutdown_write(&r,1,1,0)==0 && shutdowns==1);
 assert(liza_rt_reactor_write(&r,1,1,0,bytes,2,0,1)==net_failure(5));
 assert(liza_rt_reactor_finish_connect(&r,2,1,0)==net_failure(10));
 assert(liza_rt_reactor_shutdown_write(&r,1,2,0)==net_failure(10));
 return 0;
}
''')
        for opt in ('0','2'):
            exe=self.root/('state'+opt+'.exe')
            flags=['-lws2_32'] if os.name=='nt' else []
            built=subprocess.run(['clang','-O'+opt,'-I'+str(ROOT/'liza/runtime'),str(harness),*flags,'-o',str(exe)],capture_output=True)
            self.assertEqual(built.returncode,0,built.stderr.decode(errors='replace'))
            ran=subprocess.run([str(exe)],capture_output=True,timeout=8)
            self.assertEqual(ran.returncode,0,ran.stderr)

    def test_pure_direction_boundaries_and_invalid_progress(self):
        root=self.root/'model';root.mkdir();(root/'relay').mkdir()
        shutil.copy(ROOT/'examples/apps/relay/direction.liza',root/'relay/direction.liza')
        path=root/'state.liza'
        path.write_text('''import relay.direction
fn main()->u32 {
 d=relay.direction.empty()
 if relay.direction.queued(d)!=0 || relay.direction.readable(d)!=2048 {return 1}
 match relay.direction.write(d,1) {Ok(x)=>{return 2} Err(e)=>{}}
 match relay.direction.shutdown(d) {Ok(x)=>{return 3} Err(e)=>{}}
 match relay.direction.read(d,2049) {Ok(x)=>{return 4} Err(e)=>{}}
 match relay.direction.read(d,2048) {
 Err(e)=>{return 5}
 Ok(full)=>{
  if relay.direction.readable(full)!=0 {return 6}
  match relay.direction.read(full,0) {Ok(x)=>{return 7} Err(e)=>{}}
  match relay.direction.write(full,1) {
   Err(e)=>{return 8}
   Ok(partial)=>{
    if relay.direction.queued(partial)!=2047 || relay.direction.readable(partial)!=0 {return 9}
    match relay.direction.write(partial,2047) {
     Err(e)=>{return 10}
     Ok(empty)=>{
      if empty.head!=0 || empty.tail!=0 {return 11}
      match relay.direction.read(empty,0) {
       Err(e)=>{return 12}
       Ok(eof)=>{
        if !relay.direction.needs_fin(eof) {return 13}
        match relay.direction.read(eof,1) {Ok(x)=>{return 14} Err(e)=>{}}
        match relay.direction.shutdown(eof) {
         Err(e)=>{return 15}
         Ok(fin)=>{if !fin.fin || relay.direction.needs_fin(fin) {return 16}}
        }
       }
      }
     }
    }
   }
  }
 }
 }
 bad=relay.direction.Direction(4294967295,0,false,false)
 if relay.direction.valid(bad) {return 17}
 match relay.direction.read(bad,4294967295) {Ok(x)=>{return 18} Err(e)=>{}}
 match relay.direction.write(bad,4294967295) {Ok(x)=>{return 19} Err(e)=>{}}
 return 0
}''')
        module=lower(load_program(path));ir=root/'state.ll';ir.write_text(llvm(module))
        for opt in ('0','2'):
            exe=root/('state'+opt+'.exe')
            built=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),'-o',str(exe)],capture_output=True)
            self.assertEqual(built.returncode,0,built.stderr)
            self.assertEqual(subprocess.run([str(exe)],timeout=8).returncode,0)
