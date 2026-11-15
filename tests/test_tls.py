"""TLS-B: language ownership and independent authenticated HTTPS/WSS oracles."""
import base64
import hashlib
import os
from pathlib import Path
import socket
import shutil
import sys
import ssl
import subprocess
import threading
import unittest
from unittest.mock import patch

from liza.frontend import Parser, CompileError
from liza.ir import lower
from liza.backend import llvm
from test_httpws import build, client_frame, receive
from test_tls_transport import TlsTransport as _Fixture

ROOT = Path(__file__).resolve().parents[1]
# Avoid unittest discovering the imported fixture a second time.
fixture_setup = _Fixture.setUpClass.__func__
fixture_command = _Fixture.command.__func__
del _Fixture


class TlsOwnership(unittest.TestCase):
    def program(self, body):
        return lower(Parser('''fn main()->u32:io,alloc {
        p:[u8;9]=[108,111,99,97,108,104,111,115,116]
        match tls.create(view p[0..9],tls.managed_bytes(),1,1000) {
        Err(e)=>{return 1} Ok(s)=>{''' + body + '}}}').parse())

    def test_session_is_linear(self):
        llvm(self.program('h=tls.handshake(s,2);d=tls.destroy(move s);return 0'))
        for body in [
            'd=tls.destroy(s);return 0',
            'd=tls.destroy(move s);d2=tls.destroy(move s);return 0',
            'd=tls.destroy(move s);h=tls.handshake(s,2);return 0',
            'alias=s;d=tls.destroy(move s);return 0',
            'return 0',
        ]:
            with self.subTest(body=body):
                with self.assertRaises((CompileError, ValueError)):
                    self.program(body)

    def test_tls_is_not_an_implicit_worker_capability(self):
        from test_sg3 import program
        operation='p:[u8;1]=[120];match tls.create(view p[0..1],100000,1,1000) {Err(e)=>{return 1} Ok(s)=>{d=tls.destroy(move s);return 0}}'
        sources=[program(consumer=operation),
                 'fn worker(id:u32)->u32:io,alloc {'+operation+'}\nfn main()->u32:io {r=workers.run(1);return 0}']
        for source in sources:
            with self.assertRaisesRegex((CompileError,ValueError),'unaudited external'):
                lower(Parser(source).parse())

    def test_plain_program_does_not_link_openssl(self):
        from liza.stdlib import link_flags
        plain=lower(Parser('fn main()->u32{return 0}').parse())
        with patch('liza.tls_backend.link_flags',side_effect=AssertionError('unexpected TLS dependency')):
            self.assertFalse(any('ssl' in flag for flag in link_flags(plain)))

    def test_buffer_origin_survives_read(self):
        # A live view must keep the same storage origin across the owned return.
        source='''fn main()->u32:io,alloc {
        p:[u8;1]=[120]
        match tls.create(view p[0..1],tls.managed_bytes(),1,1000) {Err(e)=>{return 1} Ok(s)=>{
        match memory.create(16) {Err(e)=>{d=tls.destroy(move s);return 1} Ok(r)=>{
        match memory.alloc<u8>(r,16,0) {Err(e)=>{c=memory.close(move r);d=tls.destroy(move s);return 1} Ok(b)=>{
        v=memory.view(b)
        (next,result)=tls.read(s,move b,0,16,2)
        x=v[0]
        f=memory.release(move next);c=memory.close(move r);d=tls.destroy(move s);return u32(x)
        }}}}}}}'''
        lower(Parser(source.replace("v=memory.view(b)", "").replace("x=v[0]", "x:u8=0")).parse())
        with self.assertRaisesRegex((CompileError, ValueError), "borrow|view|storage"):
            lower(Parser(source).parse())


@unittest.skipUnless(os.environ.get('LIZA_TEST_TLS') == '1', 'Optional TLS: set LIZA_TEST_TLS=1')
class TlsClients(unittest.TestCase):
    command = classmethod(fixture_command)

    @classmethod
    def setUpClass(cls):
        fixture_setup(cls)
        cls.clients = {}
        for mode in ('https', 'wss'):
            for opt in ('0', '2'):
                folder = cls.root/(mode+opt);folder.mkdir()
                cls.clients[mode,opt] = build(ROOT/f'examples/apps/liza_{mode}.liza', folder, opt, ROOT/'examples')

    def test_creation_error_categories_and_abortive_cleanup(self):
        root=self.root/'errors';root.mkdir()
        entry=root/'main.liza'
        source='fn category(e:TlsError)->u32 {\nmatch e {TlsError.Invalid=>{return 3} TlsError.ManagedBudget=>{return 8} TlsError.OutOfMemory=>{return 7} TlsError.WrongThread=>{return 6} TlsError.Configuration=>{return 4} TlsError.Verification(c)=>{return 9} TlsError.Deadline=>{return 5} TlsError.Protocol(c)=>{return 10} TlsError.Transport(t)=>{return 11} TlsError.Output=>{return 12}}}\nfn main()->u32:io,alloc {\np:[u8;9]=[108,111,99,97,108,104,111,115,116]\n'
        cases=[('tls.create(view p[0..9],0,1,1000)',8),
               ('tls.create(view p[0..9],tls.managed_bytes(),1000,1000)',5),
               ('tls.create(view p[0..0],tls.managed_bytes(),1,1000)',3),
               ('tls.create_with_ca(view p[0..9],view p[0..9],tls.managed_bytes(),1,1000)',4)]
        for call,expected in cases:
            source+='{match '+call+' {Err(e)=>{if category(e)!='+str(expected)+' {return 1}} Ok(s)=>{d=tls.destroy(move s);return 2}}}\n'
        source+='match tls.create(view p[0..9],tls.managed_bytes(),1,1000) {Err(e)=>{return 3} Ok(s)=>{d=tls.destroy(move s);return 0}}}'
        entry.write_text(source)
        for opt in ('0','2'):
            exe=build(entry,root,opt)
            run=subprocess.run([str(exe)],cwd=self.root,capture_output=True,timeout=5)
            self.assertEqual(run.returncode,0,run.stderr)

    def test_short_ciphertext_io_and_deadline(self):
        root=self.root/'short';root.mkdir()
        shutil.copytree(ROOT/'examples/httpws',root/'httpws')
        (root/'apps/proxy').mkdir(parents=True)
        shutil.copy(ROOT/'examples/apps/proxy/config.liza',root/'apps/proxy/config.liza')
        cli=root/'httpws/secure_cli.liza'
        cli.write_text(cli.read_text().replace(',10000,websocket)',',1000,websocket)'))
        entry=root/'main.liza';entry.write_text('import httpws.secure_cli\nfn main()->u32:io,alloc{return httpws.secure_cli.run(false)}')
        runtime=ROOT/'liza/runtime'/('reactor_windows.c' if sys.platform=='win32' else 'reactor_posix.c')
        stub=root/'short.c'
        stub.write_text('#define liza_rt_reactor_write real_write\n#define liza_rt_reactor_read real_read\n#include "'+runtime.as_posix()+'"\n'
                        '#undef liza_rt_reactor_write\n#undef liza_rt_reactor_read\n'
                        'uint64_t liza_rt_reactor_write(reactor*r,uint64_t o,uint64_t g,uint64_t s,const uint8_t*d,uint32_t n,uint32_t a,uint32_t c){'
                        'static unsigned calls;if(++calls%3==0)return (uint64_t)4<<32;return real_write(r,o,g,s,d,n,a,c>1?1:c); }\n'
                        'uint64_t liza_rt_reactor_read(reactor*r,uint64_t o,uint64_t g,uint64_t s,uint8_t*d,uint32_t n,uint32_t a,uint32_t c){return real_read(r,o,g,s,d,n,a,c>7?7:c); }\n')
        def response(conn):
            self.request(conn);conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nok')
        def stalled(conn):
            self.request(conn);self.assertEqual(conn.recv(1),b'');return False
        for opt in ('0','2'):
            self.clients['short',opt]=build(entry,root,opt,root,reactor_stub=stub)
            self.assertEqual(self.session('short',opt,response).stdout,b'ok')
            self.session('short',opt,stalled,expected=5)

    def test_sustained_ciphertext_backpressure_with_input(self):
        root=self.root/'backpressure';root.mkdir()
        fixture=ROOT/'tests/fixtures/tls_backpressure.h'
        runtime=ROOT/'liza/runtime'/('reactor_windows.c' if sys.platform=='win32' else 'reactor_posix.c')
        reactor=root/'reactor.c';engine=root/'engine.c'
        reactor.write_text('#define LIZA_TLS_BP_REACTOR "'+runtime.as_posix()+'"\n#include "'+fixture.as_posix()+'"\n')
        engine.write_text('#define LIZA_TLS_BP_ENGINE "'+(ROOT/'liza/runtime/tls_openssl.c').as_posix()+'"\n#include "'+fixture.as_posix()+'"\n')
        from liza.stdlib import link_flags as original_flags
        def flags(module):
            return [str(engine) if Path(f).name=='tls_openssl.c' else f for f in original_flags(module)]
        payloads=[i.to_bytes(2,'big')+bytes([i%251])*123 for i in range(400)]
        def peer(conn):
            request=self.request(conn)
            key=next(line.split(b':',1)[1].strip() for line in request.split(b'\r\n') if line.lower().startswith(b'sec-websocket-key:'))
            proof=base64.b64encode(hashlib.sha1(key+b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
            conn.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+proof+b'\r\n\r\n'+b''.join(b'\x89\x7d'+p for p in payloads))
            self.assertEqual(client_frame(conn),(1,b'Liza'))
            for payload in payloads: self.assertEqual(client_frame(conn),(10,payload))
            conn.sendall(b'\x88\x02\x03\xe8')
            self.assertEqual(client_frame(conn),(8,b'\x03\xe8'))
        for opt in ('0','2'):
            with patch('test_httpws.link_flags',side_effect=flags):
                self.clients['pressure',opt]=build(ROOT/'examples/apps/liza_wss.liza',root,opt,ROOT/'examples',reactor_stub=reactor)
            run=self.session('pressure',opt,peer,version=ssl.TLSVersion.TLSv1_2)
            self.assertRegex(run.stderr,rb'TLS_BP blocked=2 bio_full=[1-9][0-9]* concurrent_reads=[1-9][0-9]* closing=1 violations=0')
            print('pressure O'+opt+': '+run.stderr.decode().strip(),flush=True)
            # The same oracle must reject both retry bugs, not just pass a
            # cooperative socket schedule that never reaches the relevant state.
            for label,before,after,expected,diagnostic in (
                ('tcp','if outgoing!=0 && !write_blocked {','if outgoing!=0 {',3,b'write retry before writable readiness'),
                ('bio','if !plaintext_blocked {','if true {',2,b'plaintext retry before BIO drain')):
                mutant=root/(label+opt);mutant.mkdir()
                shutil.copytree(ROOT/'examples/httpws',mutant/'httpws')
                (mutant/'apps/proxy').mkdir(parents=True)
                shutil.copy(ROOT/'examples/apps/proxy/config.liza',mutant/'apps/proxy/config.liza')
                code=mutant/'httpws/secure.liza';text=code.read_text();self.assertIn(before,text);code.write_text(text.replace(before,after))
                entry=mutant/'main.liza';entry.write_text('import httpws.secure_cli\nfn main()->u32:io,alloc{return httpws.secure_cli.run(true)}')
                with patch('test_httpws.link_flags',side_effect=flags):
                    self.clients['mutant',opt]=build(entry,mutant,opt,mutant,reactor_stub=reactor)
                def rejected(conn):
                    request=self.request(conn)
                    key=next(line.split(b':',1)[1].strip() for line in request.split(b'\r\n') if line.lower().startswith(b'sec-websocket-key:'))
                    proof=base64.b64encode(hashlib.sha1(key+b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
                    conn.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+proof+b'\r\n\r\n'+b''.join(b'\x89\x7d'+p for p in payloads))
                    while conn.recv(4096): pass
                    return False
                rejected_run=self.session('mutant',opt,rejected,expected=expected,version=ssl.TLSVersion.TLSv1_2)
                self.assertIn(diagnostic,rejected_run.stderr)


    def session(self, mode, opt, handler, expected=0, peer='localhost', ca='ca.pem', cert='server.pem', version=ssl.TLSVersion.TLSv1_3):
        errors, names = [], []
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = version;context.maximum_version = version
        context.load_cert_chain(self.root/cert, self.root/'server.key')
        context.set_servername_callback(lambda conn, name, ctx: names.append(name))
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(12)
            def serve():
                try:
                    with listener.accept()[0] as raw:
                        raw.settimeout(12)
                        with context.wrap_socket(raw, server_side=True) as conn:
                            if expected == 7:
                                self.fail('client accepted unauthenticated server')
                            if handler(conn) is False: return
                            # Requires the client's final close_notify to reach TCP.
                            conn.unwrap().close()
                except (ssl.SSLError, ConnectionError) as error:
                    if expected not in (2,3,4,5,7): errors.append(error)
                except BaseException as error:
                    errors.append(error)
            worker=threading.Thread(target=serve,daemon=True);worker.start()
            args=[str(self.clients[mode,opt]), f'127.0.0.1:{listener.getsockname()[1]}','/',peer]
            if ca is not None: args.append(ca)
            run=subprocess.run(args,cwd=self.root,capture_output=True,timeout=15)
            worker.join(13)
            self.assertFalse(worker.is_alive(),'TLS server stuck waiting for close_notify')
            self.assertFalse(errors,repr(errors)+repr((run.returncode,run.stderr)))
            self.assertEqual(run.returncode,expected,run.stderr)
            if expected==7: self.assertEqual(run.stdout,b'')
            if peer=='localhost': self.assertEqual(names,['localhost'])
            if peer=='127.0.0.1': self.assertEqual(names,[None])
            return run

    @staticmethod
    def request(conn):
        data=b''
        while not data.endswith(b'\r\n\r\n'):
            data+=receive(conn,1)
            if len(data)>8192: raise AssertionError('unbounded request')
        return data

    def test_https_versions_and_ip(self):
        def response(conn):
            self.assertIn(b'GET / HTTP/1.1\r\n',self.request(conn))
            wire=b'HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nabc'
            for byte in wire: conn.sendall(bytes([byte]))
        for opt in ('0','2'):
            for version in (ssl.TLSVersion.TLSv1_2,ssl.TLSVersion.TLSv1_3):
                with self.subTest(opt=opt,version=version):
                    self.assertEqual(self.session('https',opt,response,version=version).stdout,b'abc')
            self.assertEqual(self.session('https',opt,response,peer='127.0.0.1').stdout,b'abc')

    def test_verification_is_mandatory(self):
        for opt in ('0','2'):
            for config in ({'peer':'wrong.invalid'},{'peer':'127.0.0.2'},{'ca':'other.pem'},{'ca':None},{'cert':'expired.pem'}):
                with self.subTest(opt=opt,config=config):
                    self.session('https',opt,lambda conn:None,expected=7,**config)

    def test_wss_shared_parser_and_graceful_close(self):
        def websocket(conn):
            request=self.request(conn)
            key=next(line.split(b':',1)[1].strip() for line in request.split(b'\r\n') if line.lower().startswith(b'sec-websocket-key:'))
            proof=base64.b64encode(hashlib.sha1(key+b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
            conn.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+proof+b'\r\n\r\n')
            self.assertEqual(client_frame(conn),(1,b'Liza'))
            # Coalesced fragments and control frames retain unread plaintext.
            conn.sendall(b'\x01\x01h\x89\x01p\x80\x01i\x88\x02\x03\xe8')
            self.assertEqual(client_frame(conn),(10,b'p'))
            self.assertEqual(client_frame(conn),(8,b'\x03\xe8'))
        for opt in ('0','2'):
            self.assertEqual(self.session('wss',opt,websocket).stdout,b'hi')

    def test_tls_close_does_not_complete_an_unfinished_protocol(self):
        for opt in ('0','2'):
            for mode in ('https','wss'):
                self.session(mode,opt,lambda conn:None,expected=4)

    def test_premature_http_body_is_failure(self):
        def short(conn):
            self.request(conn);conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 3\r\n\r\nx')
        for opt in ('0','2'):
            self.assertEqual(self.session('https',opt,short,expected=4).stdout,b'x')
