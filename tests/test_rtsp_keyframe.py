"""Fixed RTCP wire oracle and session-scoped keyframe request scheduling."""
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from test_httpws import build, array
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class RtspKeyframe(unittest.TestCase):
    def test_rtcp_wire_rate_limit_source_change_and_expiry(self):
        req=struct.pack('!BBHII8s',128,204,4,999,1,bytes(8))
        source='''import rtsp.keyframe
fn main()->u32:io {
var state=rtsp.keyframe.create(123)
'''
        cases=[(req,True),(req[:-1],False),(req+b'\0',False),(req[:4]+bytes(4)+req[8:],False),(bytes([129])+req[1:],False),(req[:8]+struct.pack('!I',2)+req[12:],False)]
        for n,(data,expected) in enumerate(cases):
            source+=f'd{n}:[u8;{len(data)}]={array(data)};if rtsp.keyframe.vg_request(view d{n}[0..{len(data)}])!={str(expected).lower()} {{return 1}}\n'
        source+='''offer=rtsp.keyframe.offer(borrow mut state,1000)
if rtsp.keyframe.due(state,1000) {return 2}
packet:[u8;13]=[128,224,0,1,0,0,0,1,0,0,3,9,101]
a=rtsp.keyframe.observe(borrow mut state,view packet[0..13],true,false,1000)
if !rtsp.keyframe.due(state,1000) {return 3}
pli=rtsp.keyframe.request(borrow mut state,1000);bytes=pli.data
w=console.write_bytes(view bytes[0..pli.len])
b=rtsp.keyframe.offer(borrow mut state,1001)
if rtsp.keyframe.due(state,1999)||state.coalesced!=1 {return 4}
if !rtsp.keyframe.due(state,2000) {return 5}
fir=rtsp.keyframe.request(borrow mut state,2000);bytes2=fir.data
w2=console.write_bytes(view bytes2[0..fir.len])
if rtsp.keyframe.due(state,3000) {return 6}
c=rtsp.keyframe.tick(borrow mut state,4000)
if state.waiting||state.timeouts!=1||rtsp.keyframe.due(state,4000) {return 7}
d=rtsp.keyframe.offer(borrow mut state,4000)
if !rtsp.keyframe.due(state,4000) {return 8}
second=rtsp.keyframe.request(borrow mut state,4000)
e=rtsp.keyframe.observe(borrow mut state,view packet[0..13],true,true,4100)
if state.waiting||state.idr!=1||rtsp.keyframe.due(state,5000) {return 9}
f=rtsp.keyframe.offer(borrow mut state,6000)
third=rtsp.keyframe.request(borrow mut state,6000)
new_source:[u8;13]=[128,224,0,2,0,0,0,2,0,0,0,123,101]
g=rtsp.keyframe.observe(borrow mut state,view new_source[0..13],true,false,6100)
if state.waiting||!state.pending||state.sender==123 {return 10}
if rtsp.keyframe.due(state,6999)||!rtsp.keyframe.due(state,7000) {return 11}
// A new connection/session has no inherited requests or camera source.
fresh=rtsp.keyframe.create(123)
if rtsp.keyframe.due(fresh,10000)||fresh.received!=0 {return 12}
cancelled=rtsp.keyframe.cancel(borrow mut state)
if rtsp.keyframe.due(state,10000)||state.pending||state.waiting {return 13}
return 0
}'''
        rr=struct.pack('!BBHI',128,201,1,123)
        sdes=struct.pack('!BBHI',129,202,4,123)+b'\x01\x09liza-rtsp\0'
        pli=rr+sdes+struct.pack('!BBHII',129,206,2,123,777)
        fir=rr+sdes+struct.pack('!BBHIII',132,206,4,123,0,777)+b'\1\0\0\0'
        expected=b'$\1'+len(pli).to_bytes(2,'big')+pli+b'$\1'+len(fir).to_bytes(2,'big')+fir
        with tempfile.TemporaryDirectory(prefix='liza-rtsp-keyframe-') as folder:
            root=Path(folder);shutil.copytree(ROOT/'examples',root/'project')
            entry=root/'project/probe.liza';entry.write_text(source)
            for opt in ('0','2'):
                with self.subTest(opt=opt):
                    out=root/opt;out.mkdir();exe=build(entry,out,opt,root/'project')
                    run=subprocess.run([str(exe)],capture_output=True,timeout=10)
                    self.assertEqual(run.returncode,0,run.stderr)
                    self.assertEqual(run.stdout,expected)
                    self.assertIn(b'timed out',run.stderr)
