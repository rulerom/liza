"""Chunk-independent framing and the bounded message server, at O0/O2."""
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import unittest

from liza.frontend import CompileError
from liza.ir import lower
from liza.modules import load_program
from liza.backend import llvm
from liza.stdlib import link_flags
import test_io
import test_net

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'examples/apps/liza_message.liza'


def build(root,source,opt,name='test'):
    module=test_io.compile_source(source)
    ir=root/(name+'.ll');ir.write_text(llvm(module))
    exe=root/(name+'.exe')
    result=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*link_flags(module),'-o',str(exe)],capture_output=True)
    if result.returncode:raise AssertionError(result.stderr.decode(errors='replace'))
    return exe


class FramingTypes(unittest.TestCase):
    def test_private_state_and_pure_library(self):
        module=test_io.compile_source('fn main()->u32 {s=framing.create(65536);h=framing.header(42);return u32(h[3])}')
        self.assertFalse(module.externals)
        for source in ('fn main()->u32{s=framing.create(4);return s.length}',
                       'fn main()->u32{s=FrameState(4,0,0,0);return 0}',
                       'fn main()->u32{var s=framing.create(4);s.received=4;return 0}'):
            with self.subTest(source=source),self.assertRaises(CompileError):test_io.compile_source(source)


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class FramingNative(unittest.TestCase):
    def run_source(self,source):
        with tempfile.TemporaryDirectory() as tmp:
            for opt in ('0','2'):
                exe=build(Path(tmp),source,opt)
                result=subprocess.run([str(exe)],capture_output=True,timeout=30)
                self.assertEqual(result.returncode,0,(opt,result.stdout,result.stderr))

    def test_every_partition_of_three_frames(self):
        # Independent expected messages: empty, [0,255], [90]. All 2^14
        # partitions of their 15 wire bytes, including coalesced frames.
        self.run_source('''
fn check(mask:u32)->u32 {
    bytes:[u8;15]=[0,0,0,0,0,0,0,2,0,255,0,0,0,1,90]
    data=view bytes[0..15]
    var state=framing.create(2)
    var begin:u32=0
    var frames:u32=0
    var filled:u32=0
    var end:u32=1
    while end<=15 {
        if end==15 || ((mask>>(end-1))&1)!=0 {
            var cursor=begin
            while cursor<end {
                match framing.feed(state,data,cursor,end-cursor) {
                    Err(e)=>{return 1}
                    Ok(step)=>{
                        if step.next<=cursor || step.next>end {return 2}
                        if step.body_offset!=filled {return 3}
                        var i:u32=0
                        while i<step.payload_count {
                            byte=data[step.payload_start+i]
                            if frames==1 {
                                if filled+i==0 && byte!=0 {return 4}
                                if filled+i==1 && byte!=255 {return 5}
                            } else {if frames!=2 || byte!=90 {return 6}}
                            i=i+1
                        }
                        filled=filled+step.payload_count
                        state=step.state
                        cursor=step.next
                        if step.complete {
                            if frames==0 && step.length!=0 {return 7}
                            if frames==1 && step.length!=2 {return 8}
                            if frames==2 && step.length!=1 {return 9}
                            if filled!=step.length {return 10}
                            frames=frames+1
                            filled=0
                        }
                    }
                }
            }
            // Empty chunks cannot manufacture a frame or advance the parser.
            match framing.feed(state,data,end,0) {
                Err(e)=>{return 11}
                Ok(empty)=>{if empty.complete || empty.next!=end || empty.payload_count!=0 {return 12};state=empty.state}
            }
            begin=end
        }
        end=end+1
    }
    if frames!=3 {return 13}
    match framing.finish(state) {Err(e)=>{return 14} Ok(done)=>{return 0}}
}
fn main()->u32 {
    var mask:u32=0
    while mask<16384 {result=check(mask);if result!=0 {return result};mask=mask+1}
    return 0
}''')

    def test_limits_range_eof_endianness_and_independent_state(self):
        self.run_source('''
fn code(e:FrameError)->u32 {match e {
FrameError.InvalidRange=>{return 1} FrameError.TooLarge=>{return 2}
FrameError.TruncatedHeader=>{return 3} FrameError.TruncatedBody=>{return 4}}}
fn main()->u32 {
    max=framing.header(4294967295)
    if max[0]!=255 || max[1]!=255 || max[2]!=255 || max[3]!=255 {return 1}
    header=framing.header(16909060)
    if header[0]!=1 || header[1]!=2 || header[2]!=3 || header[3]!=4 {return 2}
    bytes:[u8;5]=[0,0,0,2,42]
    data=view bytes[0..5]
    state=framing.create(2)
    match framing.feed(state,data,0,6) {Ok(s)=>{return 3} Err(e)=>{if code(e)!=1 {return 4}}}
    match framing.feed(state,data,6,0) {Ok(s)=>{return 5} Err(e)=>{if code(e)!=1 {return 6}}}
    match framing.feed(state,data,1,4294967295) {Ok(s)=>{return 7} Err(e)=>{if code(e)!=1 {return 8}}}
    var n:u32=1
    while n<=5 {
        match framing.feed(state,data,0,n) {
            Err(e)=>{return 9}
            Ok(step)=>{
                match framing.finish(step.state) {
                    Ok(done)=>{return 10}
                    Err(e)=>{if n<4 {if code(e)!=3 {return 11}} else {if code(e)!=4 {return 12}}}
                }
            }
        }
        n=n+1
    }
    // Feeding a copy never mutates the original state.
    match framing.finish(state) {Err(e)=>{return 13} Ok(done)=>{}}
    match framing.feed(framing.create(1),data,0,4) {Ok(s)=>{return 14} Err(e)=>{if code(e)!=2 {return 15}}}
    huge=view max[0..4]
    match framing.feed(state,huge,0,4) {Ok(s)=>{return 16} Err(e)=>{if code(e)!=2 {return 17}}}
    match framing.feed(framing.create(4294967295),huge,0,4) {
        Err(e)=>{return 18} Ok(step)=>{if step.length!=4294967295 || step.complete {return 19}}
    }
    return 0
}''')


@unittest.skipUnless(shutil.which('clang'),'Clang required')
class MessageNative(unittest.TestCase):
    start=test_net.NetNative.start
    stop=staticmethod(test_net.NetNative.stop)

    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='liza-message-')
        cls.module=lower(load_program(APP));cls.text=llvm(cls.module);cls.executables=[]
        for opt in ('0','2'):
            root=Path(cls.temp.name)/opt;root.mkdir();ir=root/'message.ll';ir.write_text(cls.text)
            exe=root/'message.exe'
            built=subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*link_flags(cls.module),'-o',str(exe)],capture_output=True)
            if built.returncode:raise RuntimeError(built.stderr.decode(errors='replace'))
            cls.executables.append(exe)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    @staticmethod
    def frame(payload):return struct.pack('!I',len(payload))+payload

    def collect(self,s):
        result=bytearray()
        while True:
            block=s.recv(8192)
            if not block:return bytes(result)
            result.extend(block)

    def test_coalesced_binary_empty_and_maximum_messages(self):
        payloads=[b'',b'\x00\xff\xfe',bytes(range(256))*256,b'after']
        wire=b''.join(self.frame(p) for p in payloads)
        for exe in self.executables:
            p,port=self.start(exe)
            with socket.create_connection(('127.0.0.1',port),timeout=10) as s:
                s.sendall(wire);s.shutdown(socket.SHUT_WR)
                self.assertEqual(self.collect(s),wire)
            self.assertEqual(p.wait(timeout=10),0,p.stderr.read())

    def test_fragmented_header_body_and_no_premature_response(self):
        frame=self.frame(b'hello\x00\xff')
        for exe in self.executables:
            p,port=self.start(exe)
            with socket.create_connection(('127.0.0.1',port),timeout=10) as s:
                for byte in frame[:-1]:
                    s.sendall(bytes([byte]))
                    s.settimeout(0.03)
                    with self.assertRaises(socket.timeout):s.recv(1)
                s.settimeout(10);s.sendall(frame[-1:]);s.shutdown(socket.SHUT_WR)
                self.assertEqual(self.collect(s),frame)
            self.assertEqual(p.wait(timeout=10),0,p.stderr.read())

    def test_eof_at_every_prefix_and_oversized_lengths(self):
        frame=self.frame(b'abc')
        cases=[(b'',0,b'')]+[(frame[:n],4,b'') for n in range(1,len(frame))]
        cases += [(self.frame(b'ok')+frame[:6],4,self.frame(b'ok')),
                  (struct.pack('!I',65537),4,b''),(struct.pack('!I',0xffffffff),4,b'')]
        for exe in self.executables:
            for data,status,response in cases:
                with self.subTest(exe=exe,data=data):
                    p,port=self.start(exe)
                    with socket.create_connection(('127.0.0.1',port),timeout=10) as s:
                        s.sendall(data);s.shutdown(socket.SHUT_WR)
                        self.assertEqual(self.collect(s),response)
                    self.assertEqual(p.wait(timeout=10),status)
                    self.assertEqual(p.stderr.read(),b'Invalid frame\n' if status else b'')

    def test_short_writes_and_error_cleanup(self):
        # Preserve the real Liza parser/application; replace only the OS boundary.
        c=r'''#include <stdint.h>
#include <stdlib.h>
#include <string.h>
static const uint8_t wire[]={0,0,0,3,0,255,42,0,0,0,0};
static uint32_t reads,writes,output,closes;
static void verify(void){if(closes!=2 || writes!=WRITES || output!=OUTPUT)_Exit(90);}
uint32_t liza_rt_net_listen(uint16_t p,uint64_t*h){*h=10;atexit(verify);return 0;}
uint32_t liza_rt_net_accept(uint64_t h,uint64_t*out){if(h!=10)_Exit(91);*out=11;return 0;}
uint64_t liza_rt_net_port(uint64_t h){return 12345;}
uint64_t liza_rt_net_read(uint64_t h,uint8_t*p,uint32_t n){
if(h!=11 || n!=2048)_Exit(92);
if(READERR)return (uint64_t)5<<32;
if(!reads++){memcpy(p,wire,2);return 2;}
if(TRUNCATED || reads>2)return 0;
memcpy(p,wire+2,9);return 9;}
uint64_t liza_rt_net_write(uint64_t h,const uint8_t*p,uint32_t n,uint32_t start,uint32_t count){
if(h!=11 || !count || start>n || count>n-start)_Exit(93);
writes++;
if(WRITEERR && writes==5)return (uint64_t)5<<32;
if(output>=sizeof(wire) || p[start]!=wire[output])_Exit(94);
output++;return 1;}
uint32_t liza_rt_net_close(uint64_t h){if(h!=(closes?10:11))_Exit(95);closes++;return CLOSEERR?7:0;}
'''
        cases=((0,0,0,0,11,11,0),(1,0,0,0,0,0,3),(0,1,0,0,5,4,3),
               (0,0,1,0,0,0,4),(0,0,0,1,11,11,3))
        for opt in ('0','2'):
            for readerr,writeerr,truncated,closeerr,writes,output,status in cases:
                with self.subTest(opt=opt,case=(readerr,writeerr,truncated,closeerr)):
                    root=Path(self.temp.name);stub=root/'stub.c';stub.write_text(c);exe=root/'stub.exe'
                    flags=[f'-D{k}={v}' for k,v in zip(('READERR','WRITEERR','TRUNCATED','CLOSEERR','WRITES','OUTPUT'),(readerr,writeerr,truncated,closeerr,writes,output))]
                    runtime=[f for f in link_flags(self.module) if 'net_' not in f]
                    built=subprocess.run(['clang','-Wno-override-module','-O'+opt,*flags,str(root/opt/'message.ll'),str(stub),*runtime,'-o',str(exe)],capture_output=True)
                    self.assertEqual(built.returncode,0,built.stderr)
                    r=subprocess.run([str(exe),'--once'],capture_output=True,timeout=10)
                    self.assertEqual(r.returncode,status,r.stderr)
                    self.assertEqual(r.stdout,b'12345\n')
                    self.assertEqual(r.stderr,b'Invalid frame\n' if status==4 else (b'Connection I/O failed\n' if status else b''))

    def test_next_client_after_invalid_frame(self):
        for exe in self.executables:
            p,port=self.start(exe,'--ephemeral')
            for wire in (b'\0',self.frame(b'next'),self.frame(b'')):
                with socket.create_connection(('127.0.0.1',port),timeout=10) as s:
                    s.sendall(wire);s.shutdown(socket.SHUT_WR)
                    self.assertEqual(self.collect(s),b'' if wire==b'\0' else wire)
            self.assertIsNone(p.poll())
