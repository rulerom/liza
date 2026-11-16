"""Independent TLS/WebSocket/CAN server acceptance; no live credentials in CI."""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import threading
import unittest
from test_tls_transport import TlsTransport as _Fixture
from test_httpws import build,client_frame,receive
setup_fixture=_Fixture.setUpClass.__func__
fixture_command=_Fixture.command.__func__
del _Fixture
ROOT=Path(__file__).resolve().parents[1]

def frame(value):
    data=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
    if len(data)<126:return b'\x81'+bytes([len(data)])+data
    return b'\x81\x7e'+len(data).to_bytes(2,'big')+data

@unittest.skipUnless(os.environ.get('LIZA_TEST_TLS')=='1','Optional TLS CAN: LIZA_TEST_TLS=1')
class CanWorker(unittest.TestCase):
    command=classmethod(fixture_command)
    @classmethod
    def setUpClass(cls):
        setup_fixture(cls)
        (cls.root/'token').write_text('test-can-secret',encoding='utf-8')
        cls.clients=[]
        for opt in ('0','2'):
            folder=cls.root/('can'+opt);folder.mkdir()
            cls.clients.append(build(ROOT/'examples/apps/liza_can.liza',folder,opt,ROOT/'examples'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def drain(self,conn):
        messages=[]
        while True:
            opcode,payload=client_frame(conn)
            if opcode==8:
                conn.sendall(b'\x88\x02\x03\xe8');return messages
            self.assertEqual(opcode,1)
            message=json.loads(payload)
            if message['type']=='heartbeat':
                conn.sendall(frame({'type':'heartbeat_ok','server_time':1794700000001}))
            else:messages.append(message)

    @staticmethod
    def upgrade(conn):
        data=b''
        while not data.endswith(b'\r\n\r\n'):data+=receive(conn,1)
        assert data.startswith(b'GET /can HTTP/1.1\r\n'),data[:40]
        assert b'Host: localhost:' in data
        key=next(line.split(b':',1)[1].strip() for line in data.split(b'\r\n') if line.lower().startswith(b'sec-websocket-key:'))
        proof=base64.b64encode(hashlib.sha1(key+b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
        conn.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+proof+b'\r\n\r\n')
        opcode,payload=client_frame(conn);assert opcode==1
        hello=json.loads(payload)
        assert hello['type']=='hello' and hello['token']=='test-can-secret'
        assert hello['node_id']=='liza-can-test' and hello['role']=='worker'
        assert hello['capabilities']==['example.echo'] and hello['assignment_protocol']==1 and hello['max_concurrent_jobs']==1
        return hello

    @staticmethod
    def ready():return {'type':'hello_ok','node_id':'liza-can-test','role':'worker','server_time':1794700000000,'heartbeat_ms':100,'max_concurrent_jobs':1,'assignment_protocol':1,'lease_timeout_ms':90000}
    @staticmethod
    def job(text='Привет\n🚀',job='job-1',assignment='assignment-1'):
        return {'type':'job','job_id':job,'assignment_id':assignment,'job_type':'example.echo','server_time':1794700000000,'payload':{'text':text}}

    def session(self,exe,handler,expected=0,run_ms=1500,connections=1):
        errors=[];context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(self.root/'server.pem',self.root/'server.key')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));listener.listen(3);listener.settimeout(10)
            def serve():
                try:
                    for attempt in range(connections):
                        with listener.accept()[0] as raw:
                            raw.settimeout(10)
                            with context.wrap_socket(raw,server_side=True) as conn:
                                self.upgrade(conn)
                                if handler(conn) is not False:conn.unwrap().close()
                except (ssl.SSLError,ConnectionError):
                    if expected==0:errors.append('TLS/transport failure')
                except BaseException as e:errors.append(repr(e))
            thread=threading.Thread(target=serve,daemon=True);thread.start()
            run=subprocess.run([str(exe),f'127.0.0.1:{listener.getsockname()[1]}','localhost','liza-can-test','token','ca.pem',str(run_ms)],cwd=self.root,capture_output=True,timeout=15)
            thread.join(11)
            self.assertFalse(thread.is_alive(),'server thread leaked')
            self.assertFalse(errors,(errors,run.returncode,run.stderr,run.stdout))
            self.assertEqual(run.returncode,expected,(run.stdout,run.stderr))
            self.assertNotIn(b'test-can-secret',run.stdout+run.stderr)
            return run

    def test_echo_heartbeat_ping_and_graceful_shutdown(self):
        observations=[]
        def peer(conn):
            conn.sendall(frame(self.ready())+frame(self.job())+b'\x89\x01p')
            seen=[];beats=0;pong=False
            while True:
                opcode,payload=client_frame(conn)
                if opcode==8:
                    self.assertEqual(payload,b'\x03\xe8');conn.sendall(b'\x88\x02\x03\xe8');break
                if opcode==10:self.assertEqual(payload,b'p');pong=True;continue
                self.assertEqual(opcode,1);message=json.loads(payload)
                if message['type']=='heartbeat':
                    beats+=1;conn.sendall(frame({'type':'heartbeat_ok','server_time':1794700000001}));continue
                self.assertEqual(message['job_id'],'job-1');self.assertEqual(message['assignment_id'],'assignment-1');self.assertNotIn('request_id',message)
                seen.append(message)
            self.assertTrue(pong);self.assertGreaterEqual(beats,2)
            self.assertEqual([m['type'] for m in seen],['job_ack','job_event'])
            self.assertEqual(seen[0]['status'],'accepted');self.assertEqual(seen[1]['status'],'completed');self.assertEqual(seen[1]['data']['echo'],'Привет\n🚀')
            observations.append(True)
        for exe in self.clients:
            run=self.session(exe,peer)
            self.assertIn(b'CAN ready',run.stdout);self.assertIn(b'completed=1',run.stdout)
        self.assertEqual(len(observations),2)

    def test_cancel_before_completion_and_reuse_slot(self):
        def peer(conn):
            cancel={'type':'job_cancel','job_id':'job-1','assignment_id':'assignment-1','reason':'test'}
            conn.sendall(frame(self.ready())+frame(self.job())+frame(cancel))
            seen=[]
            while len(seen)<2:
                opcode,payload=client_frame(conn);self.assertEqual(opcode,1)
                seen.append(json.loads(payload))
            self.assertEqual([m['status'] for m in seen],['accepted','cancelled'])
            conn.sendall(frame(self.job('second','job-2','assignment-2')))
            messages=self.drain(conn)
            self.assertEqual([m['status'] for m in messages],['accepted','completed'])
            self.assertEqual(messages[-1]['data']['echo'],'second')
            self.assertEqual(messages[-1]['assignment_id'],'assignment-2')
        for exe in self.clients:
            run=self.session(exe,peer,run_ms=700)
            self.assertIn(b'completed=1 cancelled=1',run.stdout)

    def test_foreign_cancel_and_control_correlation(self):
        def peer(conn):
            cancel={'type':'job_cancel','job_id':'job-1','assignment_id':'old-assignment'}
            control={'type':'control','request_id':'request-1','method':'unknown','params':{},'expects_reply':True}
            conn.sendall(frame(self.ready())+frame(self.job(''))+frame(cancel)+frame(control))
            messages=self.drain(conn)
            results=[m for m in messages if m['type']=='control_result']
            self.assertEqual(len(results),1)
            self.assertEqual(results[0]['request_id'],'request-1');self.assertFalse(results[0]['ok'])
            events=[m for m in messages if m['type']=='job_event']
            self.assertEqual(len(events),1);self.assertEqual(events[0]['status'],'completed')
            self.assertEqual(events[0]['data']['echo'],'')
        for exe in self.clients:self.session(exe,peer,run_ms=700)

    def test_policy_error_does_not_retry(self):
        def peer(conn):
            conn.sendall(frame({'type':'error','code':'unauthorized','message':'denied'}))
            try:conn.recv(1)
            except ssl.SSLError:pass
        for exe in self.clients:
            run=self.session(exe,peer,expected=3)
            self.assertNotIn(b'CAN reconnect',run.stdout)

    def test_unsupported_job_is_failed_without_echo(self):
        def peer(conn):
            job=self.job();job['job_type']='test.ping';job['payload']={}
            conn.sendall(frame(self.ready())+frame(job))
            messages=self.drain(conn)
            self.assertEqual(len(messages),1)
            self.assertEqual(messages[0]['type'],'job_event')
            self.assertEqual(messages[0]['status'],'failed')
            self.assertEqual(messages[0]['assignment_id'],'assignment-1')
            self.assertNotIn('data',messages[0])
        self.session(self.clients[1],peer,run_ms=700)

    def test_reconnect_reused_ids_do_not_replay_old_result(self):
        for exe in self.clients:
            attempts=[]
            def peer(conn):
                attempts.append(True)
                if len(attempts)==1:
                    conn.sendall(frame(self.ready())+frame(self.job('old-session')))
                    opcode,payload=client_frame(conn)
                    self.assertEqual(json.loads(payload)['type'],'job_ack')
                    return False
                conn.sendall(frame(self.ready())+frame(self.job('new-session')))
                messages=self.drain(conn)
                events=[m for m in messages if m['type']=='job_event']
                self.assertEqual(len(events),1)
                self.assertEqual(events[0]['data']['echo'],'new-session')
            run=self.session(exe,peer,run_ms=7000,connections=2)
            self.assertEqual(run.stdout.count(b'CAN ready'),2)
            self.assertEqual(run.stdout.count(b'CAN reconnect'),1)

    def test_wrong_type_missing_identity_and_duplicate_rejected(self):
        bad=[]
        for field in ('job_id','assignment_id','server_time','payload'):
            value=self.job();del value[field];bad.append(value)
        value=self.job();value['assignment_id']=None;bad.append(value)
        value=self.job();value['payload']['text']=123;bad.append(value)
        for value in bad:
            def peer(conn,value=value):
                conn.sendall(frame(self.ready())+frame(value))
                try:conn.recv(1)
                except ssl.SSLError:pass
            self.session(self.clients[1],peer,expected=3)

    def test_unanswered_heartbeat_expires(self):
        def peer(conn):
            conn.sendall(frame(self.ready()))
            # Keep TCP/TLS alive and keep reading; only the CAN acknowledgement
            # is absent. Repeated heartbeats must not postpone its deadline.
            while True:
                try:
                    opcode,payload=client_frame(conn)
                except (AssertionError,ssl.SSLError,ConnectionError):return
                self.assertEqual(opcode,1)
                self.assertEqual(json.loads(payload)['type'],'heartbeat')
        self.session(self.clients[1],peer,expected=3,run_ms=7000)

    def test_token_file_limits_fail_before_network(self):
        path=self.root/'bad-token'
        for value in (b'',b'x'*513,b'with space',b'x\x00y'):
            path.write_bytes(value)
            run=subprocess.run([str(self.clients[1]),'127.0.0.1:1','localhost','liza-can-test','bad-token'],cwd=self.root,capture_output=True,timeout=5)
            self.assertEqual(run.returncode,2)
            self.assertNotIn(value or b'not-a-token',run.stdout+run.stderr)
