"""Protocol identity, bounded publication, backpressure and client progress."""
from pathlib import Path
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import unittest
import unittest.mock

from liza.ir import lower
from liza.modules import load_program
from liza.backend import llvm
from liza.stdlib import link_flags
import test_net
import test_reactor

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'examples/apps/liza_router.liza'
frame=test_reactor.frame
receive=test_reactor.receive


def packet(sock):
    length=struct.unpack('!I',receive(sock,4))[0]
    if length>65536:raise AssertionError('oversized server frame')
    return receive(sock,length)


def send(destination,payload=b''):return frame(b'\x02'+destination+payload)


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class RouterNative(unittest.TestCase):
    start=test_net.NetNative.start
    stop=staticmethod(test_net.NetNative.stop)

    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='liza-router-')
        cls.module=lower(load_program(APP));cls.text=llvm(cls.module)
        cls.executables=[];cls.fault_executables=[]
        runtime=ROOT/'liza/runtime'
        stub=Path(cls.temp.name)/'gated.c'
        stub.write_text(r'''
#include "net_common.h"
#define liza_rt_reactor_write actual_write
#include "reactor_common.h"
#undef liza_rt_reactor_write
#include <stdio.h>
uint64_t liza_rt_reactor_write(reactor*r,uint64_t owner,uint64_t generation,uint64_t slot,
 const uint8_t*data,uint32_t length,uint32_t start,uint32_t count) {
 const char *gate=getenv("LIZA_ROUTER_GATE");
 const char *mode=getenv("LIZA_ROUTER_GATE_MODE");
 int hold=0;
 /* After a positive partial write, freeze either delivery to B or reply to A. */
 if (gate && mode) {
  if (mode[0]=='d' && slot==1 && start>65540 && start<131080) hold=1;
  if (mode[0]=='c' && slot==0 && start>524320 && data[524324]==3) hold=1;
 }
 if (hold) {FILE*f=fopen(gate,"rb");if (!f)return (uint64_t)4<<32;fclose(f);}
 return actual_write(r,owner,generation,slot,data,length,start,count>2?2:count);
}
''')
        for opt in ('0','2'):
            root=Path(cls.temp.name)/opt;root.mkdir();ir=root/'router.ll';ir.write_text(cls.text)
            for faulty in (False,True):
                exe=root/('gated.exe' if faulty else 'router.exe')
                flags=link_flags(cls.module)
                if faulty:
                    flags=[f for f in flags if not Path(f).name.startswith(('net_','reactor_'))]
                    flags=[str(stub),'-I'+str(runtime),*flags]
                result=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*flags,'-o',str(exe)],capture_output=True)
                if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
                (cls.fault_executables if faulty else cls.executables).append(exe)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def connect(self,port):
        s=socket.create_connection(('127.0.0.1',port),timeout=5)
        self.addCleanup(s.close)
        hello=packet(s)
        self.assertEqual(len(hello),13);self.assertEqual(hello[0],1)
        slot,generation=struct.unpack('!IQ',hello[1:])
        self.assertLess(slot,8);self.assertGreater(generation,0)
        return s,hello[1:]

    def test_register_route_maximum_payload_and_self_delivery(self):
        for exe in self.executables+self.fault_executables:
            p,port=self.start(exe,'--ephemeral')
            a,aid=self.connect(port);b,bid=self.connect(port)
            # Fault builds deliberately send only two bytes per syscall.
            payloads=(b'',b'\0\xffbinary',(bytes(range(256))*256)[:65523]) if exe in self.executables else (b'',b'\0\xffbinary')
            for payload in payloads:
                a.sendall(send(bid,payload))
                self.assertEqual(packet(a),b'\x03')
                self.assertEqual(packet(b),b'\x06'+aid+payload)
            a.sendall(send(aid,b'self'))
            self.assertEqual(packet(a),b'\x03')
            self.assertEqual(packet(a),b'\x06'+aid+b'self')
            self.assertIsNone(p.poll())

    def test_stale_id_and_out_of_range_id_never_target_replacement(self):
        for exe in self.executables:
            p,port=self.start(exe,'--ephemeral')
            a,aid=self.connect(port);b,old=self.connect(port)
            b.shutdown(socket.SHUT_WR);self.assertEqual(b.recv(1),b'');b.close()
            c,new=self.connect(port)
            self.assertEqual(old[:4],new[:4]);self.assertNotEqual(old[4:],new[4:])
            for missing in (old,struct.pack('!IQ',0xffffffff,0xffffffffffffffff),struct.pack('!IQ',0,0)):
                a.sendall(send(missing,b'wrong'));self.assertEqual(packet(a),b'\x05')
            c.settimeout(.1)
            with self.assertRaises(socket.timeout):c.recv(1)
            c.settimeout(5);a.sendall(send(new,b'right'))
            self.assertEqual(packet(a),b'\x03');self.assertEqual(packet(c),b'\x06'+aid+b'right')
            self.assertIsNone(p.poll())

    def test_fragmented_request_and_coalesced_control_responses(self):
        for exe in self.executables:
            p,port=self.start(exe,'--ephemeral')
            a,aid=self.connect(port);b,bid=self.connect(port);c,cid=self.connect(port)
            wire=send(bid,b'fragmented');a.sendall(wire[:2])
            c.sendall(send(bid,b'independent'))
            self.assertEqual(packet(c),b'\x03');self.assertEqual(packet(b),b'\x06'+cid+b'independent')
            for byte in wire[2:]:a.sendall(bytes([byte]))
            self.assertEqual(packet(a),b'\x03');self.assertEqual(packet(b),b'\x06'+aid+b'fragmented')
            bad=struct.pack('!IQ',99,1)
            a.sendall(send(bad,b'x')*30)
            for _ in range(30):self.assertEqual(packet(a),b'\x05')
            self.assertIsNone(p.poll())

    def gated_start(self,exe,mode):
        gate=Path(self.temp.name)/(exe.parent.name+'-'+mode+'.gate')
        # Each mode is used once per executable; the file does not exist yet.
        with unittest.mock.patch.dict(os.environ,{'LIZA_ROUTER_GATE':str(gate),'LIZA_ROUTER_GATE_MODE':mode}):
            p,port=self.start(exe,'--ephemeral')
        return p,port,gate

    def test_busy_preserves_partially_sent_delivery(self):
        for exe in self.fault_executables:
            p,port,gate=self.gated_start(exe,'delivery')
            a,aid=self.connect(port);b,bid=self.connect(port)
            payload=b'first\x00\xff'
            a.sendall(send(bid,payload));self.assertEqual(packet(a),b'\x03')
            prefix=receive(b,2) # A positive partial send happened; the remainder is frozen.
            a.sendall(send(bid,b'must-not-replace'));self.assertEqual(packet(a),b'\x04')
            gate.write_bytes(b'continue')
            expected=frame(b'\x06'+aid+payload)
            self.assertEqual(prefix+receive(b,len(expected)-2),expected)
            self.assertIsNone(p.poll())

    def test_partial_delivery_does_not_starve_recipient_requests(self):
        for exe in self.fault_executables:
            with tempfile.TemporaryDirectory() as temp:
                gate=Path(temp)/'gate'
                with unittest.mock.patch.dict(os.environ,{'LIZA_ROUTER_GATE':str(gate),'LIZA_ROUTER_GATE_MODE':'delivery'}):
                    p,port=self.start(exe,'--ephemeral')
                a,aid=self.connect(port);b,bid=self.connect(port);c,cid=self.connect(port)
                a.sendall(send(bid,b'incoming'));self.assertEqual(packet(a),b'\x03')
                prefix=receive(b,2)
                b.sendall(send(cid,b'outgoing'))
                # B can route its own request while the outgoing TCP frame to B is partial.
                self.assertEqual(packet(c),b'\x06'+bid+b'outgoing')
                gate.write_bytes(b'continue')
                expected=frame(b'\x06'+aid+b'incoming')
                self.assertEqual(prefix+receive(b,len(expected)-2),expected)
                self.assertEqual(packet(b),b'\x03')
                self.assertIsNone(p.poll())

    def test_half_close_drains_accepted_delivery(self):
        for exe in self.fault_executables:
            with tempfile.TemporaryDirectory() as temp:
                gate=Path(temp)/'gate'
                with unittest.mock.patch.dict(os.environ,{'LIZA_ROUTER_GATE':str(gate),'LIZA_ROUTER_GATE_MODE':'delivery'}):
                    p,port=self.start(exe,'--ephemeral')
                a,aid=self.connect(port);b,bid=self.connect(port)
                a.sendall(send(bid,b'drain'));self.assertEqual(packet(a),b'\x03')
                prefix=receive(b,2);b.shutdown(socket.SHUT_WR)
                import time
                deadline=time.monotonic()+5
                while True:
                    a.sendall(send(bid,b'probe'));reply=packet(a)
                    if reply==b'\x05':break
                    self.assertEqual(reply,b'\x04');self.assertLess(time.monotonic(),deadline)
                gate.write_bytes(b'continue')
                expected=frame(b'\x06'+aid+b'drain')
                self.assertEqual(prefix+receive(b,len(expected)-2),expected)
                self.assertEqual(b.recv(1),b'')
                self.assertIsNone(p.poll())

    def test_pending_control_pauses_pipelined_requests(self):
        for exe in self.fault_executables:
            p,port,gate=self.gated_start(exe,'control')
            a,aid=self.connect(port);b,bid=self.connect(port)
            a.sendall(send(bid,b'first')+send(bid,b'second'))
            prefix=receive(a,2)
            self.assertEqual(packet(b),b'\x06'+aid+b'first')
            b.settimeout(.15)
            with self.assertRaises(socket.timeout):b.recv(1)
            b.settimeout(5)
            c,cid=self.connect(port);c.sendall(send(bid,b'other-client'))
            self.assertEqual(packet(c),b'\x03');self.assertEqual(packet(b),b'\x06'+cid+b'other-client')
            gate.write_bytes(b'continue')
            self.assertEqual(prefix+receive(a,3),frame(b'\x03'))
            self.assertEqual(packet(a),b'\x03')
            self.assertEqual(packet(b),b'\x06'+aid+b'second')
            self.assertIsNone(p.poll())

    def test_accepted_is_not_delivery_and_disconnect_discards_queue(self):
        for exe in self.fault_executables:
            # Separate gate path: previous test may have opened its gate.
            with tempfile.TemporaryDirectory() as temp:
                with unittest.mock.patch.dict(os.environ,{'LIZA_ROUTER_GATE':str(Path(temp)/'never'),'LIZA_ROUTER_GATE_MODE':'delivery'}):
                    p,port=self.start(exe,'--ephemeral')
                a,aid=self.connect(port);b,bid=self.connect(port)
                a.sendall(send(bid,b'not-delivered'));self.assertEqual(packet(a),b'\x03');receive(b,2)
                linger=struct.pack('HH' if os.name=='nt' else 'ii',1,0)
                b.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,linger);b.close()
                # Busy is valid before the reset is observed; read may already have detected it.
                a.sendall(send(bid,b'cannot-replace'));self.assertIn(packet(a),(b'\x04',b'\x05'))
                Path(temp,'never').write_bytes(b'open')
                # Wait for disconnect processing through observable Unavailable, no fixed sleep.
                import time
                deadline=time.monotonic()+5
                while True:
                    a.sendall(send(bid,b'probe'));reply=packet(a)
                    if reply==b'\x05':break
                    self.assertEqual(reply,b'\x04')
                    self.assertLess(time.monotonic(),deadline)
                c,new=self.connect(port)
                self.assertEqual(new[:4],bid[:4]);self.assertNotEqual(new[4:],bid[4:])
                c.settimeout(.1)
                with self.assertRaises(socket.timeout):c.recv(1)
                self.assertIsNone(p.poll())

    def test_protocol_errors_are_bounded_responses_then_close(self):
        for exe in self.executables:
            for wire,error,eof in [(frame(b''),1,False),(frame(b'\x03'+b'0'*12),1,False),
                                   (frame(b'\x02'+b'0'*11),1,False),(struct.pack('!I',65537),2,False),(struct.pack('!I',0xffffffff),2,False),
                                   (b'\0\0',3,True),(struct.pack('!I',20)+b'\x02',3,True)]:
                p,port=self.start(exe)
                a,aid=self.connect(port);a.sendall(wire)
                if eof:a.shutdown(socket.SHUT_WR)
                self.assertEqual(packet(a),bytes([7,error]))
                self.assertEqual(a.recv(1),b'')
                self.assertEqual(p.wait(timeout=5),4)
            p,port=self.start(exe)
            a,aid=self.connect(port);a.shutdown(socket.SHUT_WR)
            self.assertEqual(a.recv(1),b'');self.assertEqual(p.wait(timeout=5),0)

    def test_active_sender_does_not_starve_other_clients(self):
        for exe in self.executables:
            p,port=self.start(exe,'--ephemeral')
            a,aid=self.connect(port);b,bid=self.connect(port);c,cid=self.connect(port);d,did=self.connect(port)
            errors=[];started=threading.Event()
            def flood():
                try:
                    for i in range(500):
                        a.sendall(send(struct.pack('!IQ',99,1),b'flood'))
                        self.assertEqual(packet(a),b'\x05')
                        if i==0:started.set()
                except Exception as error:errors.append(error);started.set()
            thread=threading.Thread(target=flood);thread.start()
            self.assertTrue(started.wait(5))
            for i in range(20):
                payload=bytes([i]);c.sendall(send(did,payload))
                self.assertEqual(packet(c),b'\x03');self.assertEqual(packet(d),b'\x06'+cid+payload)
            thread.join(10);self.assertFalse(thread.is_alive());self.assertFalse(errors,errors)
            self.assertIsNone(p.poll())

    def test_loop_and_protocol_helpers_do_not_allocate_payload_storage(self):
        for function in ('exchange','put32','put_id','control','classify'):
            body=self.text.split('@liza_liza_router.'+function+'(',1)[1].split('\n}',1)[0]
            for name in ('@malloc','@calloc','@realloc','@liza_rt_region_create','@liza_rt_region_alloc','@liza_rt_vec_reserve'):
                self.assertNotIn(name,body,(function,name))

    def test_last_slot_exact_maximum_and_short_reuse(self):
        for exe in self.executables:
            p,port=self.start(exe,'--ephemeral')
            clients=[self.connect(port) for _ in range(8)]
            last,last_id=clients[-1]
            self.assertEqual(struct.unpack('!I',last_id[:4])[0],7)
            for payload in ((bytes(range(256))*256)[:65523],b'',b'new'):
                last.sendall(send(last_id,payload))
                self.assertEqual(packet(last),b'\x03')
                self.assertEqual(packet(last),b'\x06'+last_id+payload)
            self.assertIsNone(p.poll())
