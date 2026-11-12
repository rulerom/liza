"""Independent wire oracles for Liza HTTP Upgrade/WebSocket, at O0 and O2."""
import base64
import hashlib
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from liza.frontend import Parser
from liza.modules import load_program
from liza.ir import lower
from liza.backend import llvm
from liza.stdlib import link_flags

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / 'examples'
GUID = b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11'


def array(data):
    return '[' + ','.join(map(str, data)) + ']'


def build(entry, root, opt, project_root=None, reactor_stub=None, net_stub=None):
    module = lower(load_program(entry, project_root=project_root))
    ir = root / ('client' + opt + '.ll')
    ir.write_text(llvm(module))
    exe = root / ('client' + opt + '.exe')
    flags = link_flags(module)
    if reactor_stub:
        flags = [str(reactor_stub) if Path(f).name in ('reactor_posix.c', 'reactor_windows.c') else f for f in flags]
    if net_stub:
        flags = [str(net_stub) if Path(f).name in ('random_posix.c', 'random_windows.c') else f for f in flags]
    built = subprocess.run(['clang', '-Wno-override-module', '-O' + opt,
                            str(ir), *flags, '-o', str(exe)],
                           capture_output=True, timeout=120)
    if built.returncode:
        raise AssertionError(built.stderr.decode(errors='replace'))
    return exe


def receive(conn, size):
    data = bytearray()
    while len(data) < size:
        chunk = conn.recv(size - len(data))
        if not chunk:
            raise AssertionError('premature EOF')
        data.extend(chunk)
    return bytes(data)


def client_frame(conn):
    first, second = receive(conn, 2)
    assert first & 0x80 and second & 0x80, (first, second)
    size = second & 127
    if size == 126:
        size = struct.unpack('!H', receive(conn, 2))[0]
    if size == 127:
        size = struct.unpack('!Q', receive(conn, 8))[0]
    mask = receive(conn, 4)
    raw = receive(conn, size)
    return first & 15, bytes(b ^ mask[i % 4] for i, b in enumerate(raw))


@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class HttpWs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='liza-httpws-')
        cls.root = Path(cls.temp.name)
        cls.executables = [build(EXAMPLES / 'liza_ws.liza', cls.root, opt, EXAMPLES)
                           for opt in ('0', '2')]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_entropy_linkage_is_opt_in(self):
        plain = lower(Parser('''fn main()->u32:io {
match net.listen(0) {Err(e)=>{return 1} Ok(s)=>{
closed=net.close_listener(move s);return 0}}}''').parse())
        entropy = lower(Parser('''fn main()->u32:io {
match net.random_u32() {Err(e)=>{return 1} Ok(n)=>{return 0}}}''').parse())
        with patch('sys.platform', 'win32'):
            old_flags = link_flags(plain)
            new_flags = link_flags(entropy)
        self.assertNotIn('-lbcrypt', old_flags)
        self.assertFalse(any('random_windows.c' in f for f in old_flags))
        self.assertIn('-lbcrypt', new_flags)
        self.assertTrue(any('random_windows.c' in f for f in new_flags))

    def session(self, exe, peer, expected=0, stdout=b'', websocket=True):
        errors = []
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(12)
            port = listener.getsockname()[1]

            def serve():
                try:
                    with listener.accept()[0] as conn:
                        conn.settimeout(12)
                        request = bytearray()
                        while not request.endswith(b'\r\n\r\n'):
                            request.extend(receive(conn, 1))
                            self.assertLess(len(request), 8192)
                        lines = bytes(request).split(b'\r\n')
                        self.assertEqual(lines[0], b'GET /can?x=1 HTTP/1.1')
                        fields = dict(line.split(b': ', 1) for line in lines[1:] if line)
                        self.assertEqual(fields[b'Host'], f'127.0.0.1:{port}'.encode())
                        if not websocket:
                            peer(conn, b'')
                            return
                        self.assertEqual(fields[b'Sec-WebSocket-Version'], b'13')
                        key = fields[b'Sec-WebSocket-Key']
                        self.assertEqual(len(base64.b64decode(key, validate=True)), 16)
                        proof = base64.b64encode(hashlib.sha1(key + GUID).digest())
                        response = (b'HTTP/1.1 101 Switching Protocols\r\nuPgRaDe: WebSocket\r\n'
                                    b'Connection: keep-alive, Upgrade\r\nSec-WebSocket-Accept: '
                                    + proof + b'\r\n\r\n')
                        peer(conn, response)
                except BaseException as exc:
                    errors.append(exc)

            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            proc = subprocess.run([str(exe), f'127.0.0.1:{port}', '/can?x=1'],
                                  capture_output=True, timeout=15)
            thread.join(timeout=13)
            self.assertFalse(thread.is_alive(), 'server did not finish')
            if errors:
                raise errors[0]
            self.assertEqual(proc.returncode, expected, proc.stderr)
            self.assertEqual(proc.stdout, stdout)

    def test_coalesced_upgrade_fragmented_utf8_ping_binary_and_close(self):
        def peer(conn, response):
            # UTF-8 scalar split across data frames, with ping between them.
            conn.sendall(response + b'\x01\x02hi' + b'\x89\x03abc'
                         + b'\x00\x01\xe2' + b'\x80\x02\x82\xac'
                         + b'\x82\x02\x00\xff' + b'\x88\x05\x03\xe8bye')
            self.assertEqual(client_frame(conn), (1, b'hello Liza'))
            self.assertEqual(client_frame(conn), (10, b'abc'))
            self.assertEqual(client_frame(conn), (8, b'\x03\xe8bye'))
        for exe in self.executables:
            self.session(exe, peer, stdout='hi€'.encode() + b'\x00\xff')

    def test_fragmented_http_and_extended_frame(self):
        body = b'x' * 2048
        def peer(conn, response):
            for byte in response:
                conn.sendall(bytes([byte]))
            self.assertEqual(client_frame(conn), (1, b'hello Liza'))
            conn.sendall(b'\x82\x7e' + struct.pack('!H', len(body)) + body + b'\x88\x00')
            self.assertEqual(client_frame(conn), (8, b''))
        for exe in self.executables:
            self.session(exe, peer, stdout=body)

    def test_bad_upgrade_and_abnormal_eof(self):
        def wrong(conn, response):
            conn.sendall(response.replace(b'101 Switching', b'200 Switching'))
        def eof(conn, response):
            conn.sendall(response)
            self.assertEqual(client_frame(conn), (1, b'hello Liza'))
        def proof(conn, response):
            conn.sendall(response.replace(b'Sec-WebSocket-Accept: ', b'Sec-WebSocket-Accept: x'))
        for exe in self.executables:
            for peer in (wrong, eof, proof):
                self.session(exe, peer, expected=4)

    def test_http_get_bodies_and_framing_rejection(self):
        root = self.root / 'http'
        root.mkdir()
        for opt in ('0', '2'):
            exe = build(EXAMPLES / 'liza_http.liza', root, opt, EXAMPLES)
            cases = [
                (b'HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello', 0, b'hello'),
                (b'HTTP/1.1 404 Missing\r\n\r\nmissing', 0, b'missing'),
                (b'HTTP/1.1 204 Empty\r\n\r\n', 0, b''),
                (b'HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nx', 4, b'x'),
                (b'HTTP/1.1 200 OK\r\nContent-Length: 4097\r\n\r\n', 4, b''),
                (b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n', 4, b''),
                (b'HTTP/1.1 200 OK\r\nContent-Length: 1\r\nContent-Length: 1\r\n\r\nx', 4, b''),
            ]
            for response, code, body in cases:
                def peer(conn, unused, response=response):
                    conn.sendall(response)
                self.session(exe, peer, expected=code, stdout=body, websocket=False)

    def test_deadline_and_forced_short_writes(self):
        import sys
        root = self.root / 'short'
        root.mkdir()
        shutil.copytree(EXAMPLES / 'httpws', root / 'httpws')
        (root / 'apps/proxy').mkdir(parents=True)
        shutil.copy(EXAMPLES / 'apps/proxy/config.liza', root / 'apps/proxy/config.liza')
        source = root / 'client.liza'
        source.write_text((EXAMPLES / 'liza_ws.liza').read_text().replace(',10000)', ',2000)'))
        runtime = ROOT / 'liza/runtime' / ('reactor_windows.c' if sys.platform == 'win32' else 'reactor_posix.c')
        stub = root / 'short.c'
        stub.write_text('#define liza_rt_reactor_write real_write\n#include "' + runtime.as_posix() + '"\n'
                        '#undef liza_rt_reactor_write\n'
                        'uint64_t liza_rt_reactor_write(reactor*r,uint64_t o,uint64_t g,uint64_t s,'
                        'const uint8_t*d,uint32_t n,uint32_t a,uint32_t c){'
                        'static unsigned calls;if(++calls%3==0)return (uint64_t)4<<32;'
                        'return real_write(r,o,g,s,d,n,a,c>1?1:c); }\n')
        for opt in ('0', '2'):
            exe = build(source, root, opt, reactor_stub=stub)
            def peer(conn, response):
                conn.sendall(response + b'\x89\x03abc' + b'\x88\x00')
                self.assertEqual(client_frame(conn), (1, b'hello Liza'))
                self.assertEqual(client_frame(conn), (10, b'abc'))
                self.assertEqual(client_frame(conn), (8, b''))
            self.session(exe, peer)
            def stalled(conn, response):
                # Client must expire its deadline while the peer sends nothing.
                self.assertEqual(conn.recv(1), b'')
            self.session(exe, stalled, expected=5)

    def test_entropy_failure_does_not_send_an_unmasked_frame(self):
        import sys
        root = self.root / 'entropy'
        root.mkdir()
        runtime = ROOT / 'liza/runtime' / ('random_windows.c' if sys.platform == 'win32' else 'random_posix.c')
        stub = root / 'entropy.c'
        stub.write_text('#define liza_rt_net_random real_random\n#include "' + runtime.as_posix() + '"\n'
                        '#undef liza_rt_net_random\n'
                        'uint64_t liza_rt_net_random(void){static unsigned n;'
                        'if(++n==5)return (uint64_t)7<<32;return real_random();}\n')
        for opt in ('0', '2'):
            exe = build(EXAMPLES / 'liza_ws.liza', root, opt, EXAMPLES, net_stub=stub)
            def peer(conn, response):
                conn.sendall(response)
                self.assertEqual(conn.recv(1), b'')
            self.session(exe, peer, expected=3)

    def test_protocol_vectors(self):
        chunks = ['import httpws.http\nimport httpws.crypto\nimport httpws.websocket\n']
        calls = []
        for i in range(8):
            key = base64.b64encode(bytes((j * 13 + i) % 256 for j in range(16)))
            expected = base64.b64encode(hashlib.sha1(key + GUID).digest())
            chunks.append(f'''fn hash{i}()->u32 {{
key:[u8;24]={array(key)};expected:[u8;28]={array(expected)}
actual=httpws.crypto.accept(key);var i:u32=0
while i<28 {{if actual[i]!=expected[i] {{return 1}};i=i+1}};return 0
}}''')
            calls.append(f'if hash{i}()!=0 {{return 1}}')
        key = base64.b64encode(b'the sample nonce')
        proof = base64.b64encode(hashlib.sha1(key + GUID).digest())
        good = b'HTTP/1.1 101 OK\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + proof + b'\r\n\r\n'
        bad_heads = [good.replace(b'101', b'200'), good.replace(proof, proof.lower()),
                     good.replace(b'Upgrade: websocket', b'Upgrade : websocket'),
                     good.replace(b'Connection: Upgrade', b'Connection: close'),
                     good.replace(b'\r\n\r\n', b'\r\nSec-WebSocket-Extensions: foo\r\n\r\n'),
                     good.replace(b'\r\n\r\n', b'\r\nSec-WebSocket-Protocol: foo\r\n\r\n'),
                     good.replace(b'\r\n\r\n', b'\r\nSec-WebSocket-Accept: '+proof+b'\r\n\r\n'),
                     good.replace(b'\r\nUpgrade', b'\r\n Upgrade')]
        chunks.append(f'''fn headers()->u32 {{
proof:[u8;28]={array(proof)};data:[u8;{len(good)}]={array(good)}
var i:u32=0
while i<{len(good)} {{match httpws.http.upgrade(view data[0..i],proof) {{Err(e)=>{{return 1}} Ok(v)=>{{match v {{None=>{{}} Some(h)=>{{return 2}}}}}}}};i=i+1}}
match httpws.http.upgrade(view data[0..i],proof) {{Err(e)=>{{return 3}} Ok(v)=>{{match v {{None=>{{return 4}} Some(h)=>{{if h.end!=i {{return 5}}}}}}}}}}
''')
        for i, data in enumerate(bad_heads):
            chunks.append(f'd{i}:[u8;{len(data)}]={array(data)};match httpws.http.upgrade(view d{i}[0..{len(data)}],proof) {{Err(e)=>{{}} Ok(v)=>{{return 6}}}}')
        chunks.append('return 0\n}')
        calls.append('if headers()!=0 {return 2}')
        invalid = [b'\x81\x80', b'\xc1\x00', b'\x83\x00', b'\x09\x00',
                   b'\x89\x7e', b'\x80\x00', b'\x01\x00\x81\x00',
                   b'\x82\x7e\x00\x01', b'\x82\x7f'+struct.pack('!Q', 126),
                   b'\x82\x7f'+struct.pack('!Q', 1 << 63),
                   b'\x82\x7e\x10\x01', b'\x81\x01\xff',
                   b'\x81\x01\xe2', b'\x88\x01\x00',
                   b'\x88\x02\x03\xed', b'\x88\x03\x03\xe8\xff']
        for i, wire in enumerate(invalid):
            chunks.append(f'''fn invalid{i}()->u32 {{
var s=httpws.websocket.create();wire:[u8;{len(wire)}]={array(wire)};var i:u32=0
while i<{len(wire)} {{match httpws.websocket.feed(borrow mut s,wire[i]) {{Err(e)=>{{return 0}} Ok(n)=>{{}}}};i=i+1}};return 1
}}''')
            calls.append(f'if invalid{i}()!=0 {{return 3}}')
        # Check client-side mask against an independent RFC example.
        wire = bytes.fromhex('818537fa213d7f9f4d5158')
        chunks.append(f'''fn encoder()->u32 {{
data:[u8;5]=[72,101,108,108,111];expected:[u8;11]={array(wire)}
match httpws.websocket.frame(1,view data[0..5],939139389) {{Err(e)=>{{return 1}} Ok(w)=>{{
if w.len!=11 {{return 2}};var i:u32=0;while i<11 {{if w.data[i]!=expected[i] {{return 3}};i=i+1}}
}}}};return 0
}}''')
        calls.append('if encoder()!=0 {return 4}')
        chunks.append('''fn limits()->u32 {
    var s=httpws.websocket.create()
    match httpws.websocket.feed(borrow mut s,2) {Err(e)=>{return 1} Ok(n)=>{}}
    match httpws.websocket.feed(borrow mut s,126) {Err(e)=>{return 1} Ok(n)=>{}}
    match httpws.websocket.feed(borrow mut s,16) {Err(e)=>{return 1} Ok(n)=>{}}
    match httpws.websocket.feed(borrow mut s,0) {Err(e)=>{return 1} Ok(n)=>{}}
    var i:u32=0
    while i<4096 {match httpws.websocket.feed(borrow mut s,42) {Err(e)=>{return 2} Ok(n)=>{if n!=0 {return 3}}};i=i+1}
    match httpws.websocket.feed(borrow mut s,128) {Err(e)=>{return 4} Ok(n)=>{}}
    match httpws.websocket.feed(borrow mut s,1) {Err(e)=>{} Ok(n)=>{return 5}}
    host:[u8;1]=[97];bad:[u8;3]=[47,13,10];target:[u8;1]=[47]
    key:[u8;24]=[65;24]
    match httpws.http.get(view host[0..1],view bad[0..3]) {Err(e)=>{} Ok(w)=>{return 6}}
    match httpws.http.request(view host[0..1],view target[0..1],key) {Err(e)=>{} Ok(w)=>{return 7}}
    huge:[u8;8192]=[65;8192]
    match httpws.http.response(view huge[0..8192]) {Err(e)=>{} Ok(h)=>{return 8}}
    return 0
}''')
        calls.append('if limits()!=0 {return 5}')

        chunks.append('fn main()->u32 {\n'+'\n'.join(calls)+'\nreturn 0\n}')
        root = self.root / 'vectors'
        root.mkdir()
        shutil.copytree(EXAMPLES / 'httpws', root / 'httpws')
        source = root / 'vectors.liza'
        source.write_text('\n'.join(chunks))
        for opt in ('0', '2'):
            exe = build(source, root, opt)
            result = subprocess.run([str(exe)], capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
