"""One configurable binary, deterministic connect clocks, and real TCP streams."""
from pathlib import Path
import os
import queue
import threading
import shutil
import socket
import subprocess
import tempfile
import unittest

from liza.backend import llvm
from liza.ir import lower
from liza.modules import load_program
from liza.stdlib import link_flags
import test_net
import test_reactor

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class Operations(unittest.TestCase):
    def start(self,exe,args,env=None):
        process=subprocess.Popen([str(exe),*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
        self.addCleanup(lambda:self.stop(process))
        lines=queue.Queue()
        threading.Thread(target=lambda:lines.put(process.stdout.readline()),daemon=True).start()
        line=lines.get(timeout=10)
        self.assertTrue(line.strip().isdigit(),line)
        return process,int(line)
    stop = staticmethod(test_net.NetNative.stop)

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='liza-ops-')
        cls.root = Path(cls.temp.name)
        module = lower(load_program(ROOT/'examples/apps/liza_proxy_ops.liza'))
        ir = cls.root/'proxy.ll'; ir.write_text(llvm(module))
        cls.executables = []
        stub = cls.root/'fault.c'
        stub.write_text(r'''
#define liza_rt_reactor_clock real_clock
#define liza_rt_reactor_connect_at real_connect_at
#define liza_rt_reactor_finish_connect real_finish
#define liza_rt_reactor_disconnect real_disconnect
#define liza_rt_reactor_close real_close
#include "reactor_common.h"
#undef liza_rt_reactor_clock
#undef liza_rt_reactor_connect_at
#undef liza_rt_reactor_finish_connect
#undef liza_rt_reactor_disconnect
#undef liza_rt_reactor_close
#include <stdio.h>
static int active;
static unsigned disconnected, connects;
static uint64_t first_generation,first_slot;
uint32_t liza_rt_reactor_connect_at(reactor*r,uint32_t ip,uint16_t p,uint64_t*id) {
    uint32_t e=real_connect_at(r,ip,p,id);
    if(!e){active=1;connects++;
        if(connects==1){first_slot=id[2];first_generation=id[1];r->slots[id[2]].phase=1;}
    }
    return e;
}
uint64_t liza_rt_reactor_finish_connect(reactor*r,uint64_t o,uint64_t g,uint64_t s) {
    if(s==first_slot && g==first_generation)return 0;
    return real_finish(r,o,g,s);
}
uint32_t liza_rt_reactor_clock(uint64_t*out) {
    const char *mode=getenv("OPS_CLOCK");
    *out=100;
    if(mode && !strcmp(mode,"gate")) {
        FILE*f=fopen(getenv("OPS_GATE"),"rb");
        if(f){fclose(f);*out=101;}return 0;
    }
    if(active) {
        if(mode && !strcmp(mode,"error"))return 7;
        *out=mode && !strcmp(mode,"backwards")?99:101;
    }
    return 0;
}
uint64_t liza_rt_reactor_disconnect(reactor*r,uint64_t o,uint64_t g,uint64_t s) {
    disconnected++;return real_disconnect(r,o,g,s);
}
uint32_t liza_rt_reactor_close(reactor*r) {
    unsigned live=0;for(uint32_t i=0;i<r->capacity;i++)live+=r->slots[i].live;
    fprintf(stderr,"cleanup:%u:%u\n",disconnected,live);
    return real_close(r);
}
''')
        for opt in ('0','2'):
            exe=cls.root/('proxy'+opt+'.exe')
            subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*link_flags(module),'-o',str(exe)],check=True,capture_output=True)
            fault=cls.root/('fault'+opt+'.exe')
            flags=[f for f in link_flags(module) if not Path(f).name.startswith('reactor_')]
            subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),str(stub),'-I'+str(ROOT/'liza/runtime'),*flags,'-o',str(fault)],check=True,capture_output=True)
            cls.executables.append((exe,fault))
        # Pure elapsed-time arithmetic, including near-UINT64_MAX values.
        (cls.root/'proxy').mkdir()
        shutil.copy(ROOT/'examples/apps/proxy/config.liza',cls.root/'proxy/config.liza')
        source=cls.root/'elapsed.liza'
        source.write_text('''import proxy.config
fn good(start:u64,now:u64,t:u32,expected:u32)->bool {
    match proxy.config.remaining(start,now,t) {Err(e)=>{return false} Ok(n)=>{return n==expected}}
}
fn bad(start:u64,now:u64,t:u32)->bool {
    match proxy.config.remaining(start,now,t) {Err(e)=>{return true} Ok(n)=>{return false}}
}
fn main()->u32 {
    if !good(100,109,10,1) || !good(100,110,10,0) || !good(100,111,10,0) {return 1}
    if !good(18446744073709551614,18446744073709551615,2,1) {return 2}
    if !bad(100,99,10) || !bad(0,0,0) || !bad(0,0,2147483648) {return 3}
    return 0
}''')
        m=lower(load_program(source)); (cls.root/'elapsed.ll').write_text(llvm(m))
        for opt in ('0','2'):
            exe=cls.root/('elapsed'+opt+'.exe')
            subprocess.run(['clang','-Wno-override-module','-O'+opt,str(cls.root/'elapsed.ll'),*link_flags(m),'-o',str(exe)],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def listener(self):
        s=socket.socket();self.addCleanup(s.close);s.bind(('127.0.0.1',0));s.listen(8);s.settimeout(5)
        self.addCleanup(s.close);return s

    def test_elapsed_arithmetic(self):
        for opt in ('0','2'):
            self.assertEqual(subprocess.run([str(self.root/('elapsed'+opt+'.exe'))],timeout=5).returncode,0)

    def test_invalid_arguments_before_socket_creation(self):
        cases=[['--unknown'],['--upstream'],['--once','--ephemeral'],['--once','--once'],
               ['--listen','127.0.0.1:9','--once'],['--upstream','127.0.0.1:0'],
               ['--upstream','0.0.0.0:80'],['--upstream','224.0.0.1:80'],
               ['--listen','127.0.0.1:0','--listen','127.0.0.1:0']]
        for endpoint in ('127.0.0.1:65536','256.0.0.1:80','01.0.0.1:80','1.2.3:80','1.2.3.4:80x',
                         '1.2.3.4:','1.2.3.4:-1',' 1.2.3.4:80','1.2.3.4:80é','9'*500):
            cases.append(['--upstream',endpoint])
        for duration in ('0','-1','2147483648','1x','9'*100,'é'):
            cases.append(['--connect-timeout-ms',duration])
        for exe,_ in self.executables:
            for args in cases:
                with self.subTest(exe=exe.name,args=args):
                    result=subprocess.run([str(exe),*args],capture_output=True,timeout=5)
                    self.assertEqual(result.returncode,2);self.assertEqual(result.stdout,b'')
                    self.assertIn(b'Usage:',result.stderr)

    def test_one_binary_multiple_upstreams_and_half_close(self):
        for exe,_ in self.executables:
            for _ in range(2):
                upstream=self.listener()
                process,port=self.start(exe,['--once','--listen','127.0.0.1:0','--upstream','127.0.0.1:'+str(upstream.getsockname()[1]),'--connect-timeout-ms','2000'])
                client=socket.create_connection(('127.0.0.1',port),timeout=5);self.addCleanup(client.close)
                peer,_=upstream.accept();self.addCleanup(peer.close);peer.settimeout(5)
                payload=bytes(range(256))*100
                client.sendall(payload);client.shutdown(socket.SHUT_WR)
                self.assertEqual(test_reactor.receive(peer,len(payload)),payload)
                self.assertEqual(peer.recv(1),b'')
                peer.sendall(b'answer\x00\xff');peer.shutdown(socket.SHUT_WR)
                self.assertEqual(test_reactor.receive(client,8),b'answer\x00\xff')
                self.assertEqual(client.recv(1),b'')
                self.assertEqual(process.wait(timeout=5),0)

    def test_deadline_and_clock_failure_release_pair(self):
        for _,exe in self.executables:
            for mode in ('timeout','backwards','error'):
                with self.subTest(exe=exe.name,mode=mode):
                    upstream=self.listener()
                    process,port=self.start(exe,['--once','--upstream','127.0.0.1:'+str(upstream.getsockname()[1]),'--connect-timeout-ms','1'],env={**os.environ,'OPS_CLOCK':mode})
                    client=socket.create_connection(('127.0.0.1',port),timeout=5);self.addCleanup(client.close)
                    self.assertEqual(client.recv(1),b'')
                    self.assertEqual(process.wait(timeout=5),3)
                    self.assertIn(b'cleanup:2:0',process.stderr.read())

    def test_stalled_connect_does_not_block_other_pair_and_slot_reuse(self):
        for _,exe in self.executables:
            with self.subTest(exe=exe.name):
                gate=self.root/(exe.name+'.gate')
                upstream=self.listener()
                process,port=self.start(exe,['--ephemeral','--upstream','127.0.0.1:'+str(upstream.getsockname()[1]),'--connect-timeout-ms','1'],env={**os.environ,'OPS_CLOCK':'gate','OPS_GATE':str(gate)})
                stalled=socket.create_connection(('127.0.0.1',port),timeout=5);self.addCleanup(stalled.close)
                stalled_peer,_=upstream.accept();self.addCleanup(stalled_peer.close)
                for attempt in range(2):
                    client=socket.create_connection(('127.0.0.1',port),timeout=5);self.addCleanup(client.close)
                    peer,_=upstream.accept();peer.settimeout(5);self.addCleanup(peer.close)
                    client.sendall(b'other');client.shutdown(socket.SHUT_WR)
                    self.assertEqual(test_reactor.receive(peer,5),b'other');self.assertEqual(peer.recv(1),b'')
                    peer.sendall(b'answer');peer.shutdown(socket.SHUT_WR)
                    self.assertEqual(test_reactor.receive(client,6),b'answer');self.assertEqual(client.recv(1),b'')
                    if attempt==0:
                        gate.write_bytes(b'advance')
                        self.assertEqual(stalled.recv(1),b'')
                self.assertIsNone(process.poll())

    def test_explicit_listener(self):
        self.endpoint_case('127.0.0.1')

    def test_nondefault_ipv4_address(self):
        # The 127/8 route is OS-dependent; no non-loopback traffic is used.
        self.endpoint_case('127.0.0.2')

    def endpoint_case(self,address):
        for exe,_ in self.executables:
            upstream=socket.socket();self.addCleanup(upstream.close)
            reservation=socket.socket();self.addCleanup(reservation.close)
            try:
                upstream.bind((address,0));reservation.bind((address,0))
            except OSError as error:
                if address=='127.0.0.1':raise
                self.skipTest('host does not bind alternate loopback: '+str(error))
            upstream.listen(2);upstream.settimeout(5)
            fixed_port=reservation.getsockname()[1];reservation.close()
            process,port=self.start(exe,['--listen',address+':'+str(fixed_port),'--upstream',address+':'+str(upstream.getsockname()[1])])
            self.assertEqual(port,fixed_port)
            client=socket.create_connection((address,port),timeout=5);self.addCleanup(client.close)
            peer,_=upstream.accept();peer.settimeout(5);self.addCleanup(peer.close)
            client.sendall(b'address');client.shutdown(socket.SHUT_WR)
            self.assertEqual(test_reactor.receive(peer,7),b'address');self.assertEqual(peer.recv(1),b'')
            peer.sendall(b'ok');peer.shutdown(socket.SHUT_WR)
            self.assertEqual(test_reactor.receive(client,2),b'ok');self.assertEqual(client.recv(1),b'')
            self.assertIsNone(process.poll())
