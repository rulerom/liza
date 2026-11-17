"""Boundaries and independent oracles for RTSP SDP, RTP gating and VGB1."""
import hashlib
import hmac
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from test_httpws import array, build
from liza.frontend import CompileError
from liza.modules import load_program
from liza.ir import lower

ROOT = Path(__file__).resolve().parents[1]
SDP = (b'v=0\r\nm=video 0 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\n'
       b'a=fmtp:96 packetization-mode=1;profile-level-id=640028;'
       b'sprop-parameter-sets=Z2QAKA==,aO48gA==\r\n'
       b'a=control:trackID=1\r\na=framesize:96 1920-1080\r\n')


@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class RtspProtocol(unittest.TestCase):
    def test_receive_cannot_release_region_before_buffer(self):
        source = '''fn main()->u32:io,alloc {
 match net.reactor_udp_create(net.ipv4(127,0,0,1,0),1) {Err(e)=>{return 1} Ok(r)=>{
 match memory.create(4096) {Err(e)=>{c=net.reactor_close(move r);return 1} Ok(region)=>{
 match memory.alloc<u8>(region,8,0) {Err(e)=>{c=memory.close(move region);d=net.reactor_close(move r);return 1} Ok(input)=>{
 (buffer,result)=net.reactor_udp_receive(r,move input)
 closed=memory.close(move region)
 released=memory.release(move buffer)
 d=net.reactor_close(move r);return 0
 }}}}}}
}'''
        with tempfile.TemporaryDirectory() as folder:
            entry = Path(folder) / 'origin.liza'
            entry.write_text(source)
            with self.assertRaisesRegex(CompileError, 'region'):
                lower(load_program(entry))

    def run_liza(self, source):
        with tempfile.TemporaryDirectory(prefix='liza-rtsp-protocol-') as folder:
            root = Path(folder)
            shutil.copytree(ROOT / 'examples', root / 'project')
            entry = root / 'project/probe.liza'
            entry.write_text(source)
            for opt in ('0', '2'):
                out = root / opt
                out.mkdir()
                exe = build(entry, out, opt, root / 'project')
                run = subprocess.run([str(exe)], capture_output=True, timeout=10)
                self.assertEqual(run.returncode, 0, (opt, run.returncode, run.stdout, run.stderr))

    def test_sdp_unicode_free_bounds_and_rtp_recovery(self):
        cases = [(SDP, True), (SDP.replace(b'mode=1', b'mode=2'), False),
                 (SDP.replace(b'mode=1;', b'mode=1;packetization-mode=1;'), False),
                 (SDP.replace(b'640028', b'zz0028'), False),
                 (SDP.replace(b'Z2QAKA==', b'Z2QAKB=='), False),
                 (SDP.replace(b'a=control:trackID=1\r\n', b''), False),
                 (SDP.replace(b'H264/90000', b'VP8/90000'), False)]
        source = 'import rtsp.sdp\nimport rtsp.bridge\nfn main()->u32 {\n'
        for i, (data, valid) in enumerate(cases):
            source += f'd{i}:[u8;{len(data)}]={array(data)};match rtsp.sdp.parse(view d{i}[0..{len(data)}]) {{'
            source += f'Err(e)=>{{{("return " + str(i+1)) if valid else ""}}} Ok(v)=>{{{("" if valid else "return " + str(i+1))}}}}}\n'
        source += 'var state=rtsp.bridge.create(96,456,65535)\n'
        # Non-IDR gated; first IDR opens; a gap closes; FU-A continuation cannot reopen.
        for i, (sequence, payload, send, params) in enumerate([
            (1, b'\x61x', False, False), (2, b'\x65x', True, True),
            (3, b'\x61x', True, False), (5, b'\x7c\x05x', False, False),
            (6, b'\x7c\x85x', True, True), (7, b'\x7c\x45x', True, False),
            (8, b'\x7c\xc5x', False, False), (9, b'\x65x', True, True)]):
            packet = struct.pack('!BBHII', 128, 224, sequence, 90000, 777) + payload
            source += f'p{i}:[u8;{len(packet)}]={array(packet)};a{i}=rtsp.bridge.inspect(state,view p{i}[0..{len(packet)}]);state=a{i}.state;'
            source += f'if a{i}.send!={str(send).lower()}||a{i}.parameters!={str(params).lower()} {{return {20+i}}}\n'
        source += 'if state.discontinuities!=1 {return 40};return 0}'
        self.run_liza(source)

    def test_rtsp_interleaving_and_header_boundaries(self):
        response = b'RTSP/1.0 200 OK\r\nCSeq: 1\r\nContent-Length: 0\r\n\r\n'
        cases = [(response + b'$\0\0\3abc$\1\0\2xy', False, 6),
                 (response.replace(b'CSeq: 1', b'CSeq: 1\r\nCSeq: 2'), True, 0),
                 (response.replace(b'Length: 0', b'Length: 99999'), True, 0),
                 (b'$\2\0\1x', True, 0), (b'$\0\xff\xff', True, 0)]
        source = 'import rtsp.stream\nimport rtsp.bytes\nfn main()->u32 {\n'
        for i, (data, bad, events) in enumerate(cases):
            source += f'''d{i}:[u8;{len(data)}]={array(data)};var s{i}=rtsp.stream.create();var bad{i}=false;var total{i}:u32=0;var n{i}:u32=0
 while n{i}<{len(data)} {{match rtsp.stream.feed(borrow mut s{i},d{i}[n{i}]) {{Err(e)=>{{bad{i}=true;break}} Ok(event)=>{{total{i}=total{i}+event}}}};n{i}=n{i}+1}}
 if bad{i}!={str(bad).lower()} {{return {i+1}}}
'''
            if not bad:
                source += f'if total{i}!={events} {{return 20}}\n'
        bad_channel = b'RTP/AVP/TCP;interleaved=0-10'
        source += f'channel_text:[u8;{len(bad_channel)}]={array(bad_channel)};if rtsp.bytes.parameter(view channel_text[0..{len(bad_channel)}],b"interleaved=0-1") {{return 30}}\n'
        self.run_liza(source + 'return 0}')

    @unittest.skipUnless(os.environ.get('LIZA_TEST_TLS') == '1', 'OpenSSL required')
    def test_rfc4231_hmac_and_vgb1_mac_mutation(self):
        key, data = b'\x0b' * 20, b'Hi There'
        expected = hmac.digest(key, data, 'sha256')
        self.assertEqual(expected.hex(), 'b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7')
        secret = b'0123456789abcdef' * 4
        wire = bytearray(struct.pack('!BBHI4sBBH', 128, 204, 19, 456, b'VGB1', 1, 1, 0) + b'c'*16 + b'\0'*16)
        wire += hmac.digest(secret, wire, 'sha256')
        source = f'''import vg.binding
import can.text
fn main()->u32:io,alloc {{
 key:[u8;20]={array(key)};data:[u8;{len(data)}]={array(data)};expected:[u8;32]={array(expected)}
 match hmac.sha256(view key[0..20],view data[0..{len(data)}]) {{Err(e)=>{{return 1}} Ok(hash)=>{{var i:u32=0;while i<32 {{if hash[i]!=expected[i] {{return 2}};i=i+1}}}}}}
 secret:[u8;64]={array(secret)};var value=can.text.empty()
 match can.text.from_view(view secret[0..64],64) {{Err(e)=>{{return 3}} Ok(v)=>{{value=v}}}}
 var wire:[u8;80]={array(wire)}
 {{if !vg.binding.verify(value,456,view wire[0..80]) {{return 4}}}}
 wire[79]=wire[79]^1
 if vg.binding.verify(value,456,view wire[0..80]) {{return 5}}
 if vg.binding.verify(value,457,view wire[0..80]) {{return 6}}
 match hmac.sha256(view key[0..0],view data[0..0]) {{Err(e)=>{{}} Ok(v)=>{{return 7}}}}
 return 0
}}'''
        self.run_liza(source)

    def test_udp_reactor_buffer_identity_and_datagram_boundaries(self):
        self.run_liza('''fn main()->u32:io,alloc {
 match net.reactor_udp_create(net.ipv4(127,0,0,1,0),2) {Err(e)=>{return 1} Ok(r)=>{
 var port:u16=0;match net.reactor_udp_port(r) {Err(e)=>{c=net.reactor_close(move r);return 2} Ok(n)=>{port=n}}
 match memory.create(4096) {Err(e)=>{c=net.reactor_close(move r);return 3} Ok(region)=>{
 match memory.alloc<u8>(region,8,0) {Err(e)=>{a=memory.close(move region);c=net.reactor_close(move r);return 4} Ok(initial)=>{
 var buffer=move initial;var code:u32=0
 data:[u8;12]=[7;12];sent=net.reactor_udp_send(r,view data[0..12],0,12,net.ipv4(127,0,0,1,port));polled=net.reactor_poll(r,1000)
 (next,result)=net.reactor_udp_receive(r,move buffer);buffer=move next
 match result {Ok(n)=>{code=5} Err(e)=>{match e {UdpError.Truncated=>{} UdpError.AddressInUse=>{code=6} UdpError.PermissionDenied=>{code=6} UdpError.Interrupted=>{code=6} UdpError.WouldBlock=>{code=6} UdpError.InvalidRange=>{code=6} UdpError.Disconnected=>{code=6} UdpError.Other=>{code=6}}}}
 sent2=net.reactor_udp_send(r,view data[0..0],0,0,net.ipv4(127,0,0,1,port));polled2=net.reactor_poll(r,1000)
 (next2,result2)=net.reactor_udp_receive(r,move buffer);buffer=move next2
 match result2 {Err(e)=>{code=7} Ok(meta)=>{if net.udp_length(meta)!=0||net.udp_source_port(meta)!=port {code=8}}}
 (next3,result3)=net.reactor_udp_receive(r,move buffer);buffer=move next3
 match result3 {Ok(meta)=>{code=9} Err(e)=>{}}
 released=memory.release(move buffer);closed=memory.close(move region);reactor_closed=net.reactor_close(move r);return code
 }}}}}}
}''')
