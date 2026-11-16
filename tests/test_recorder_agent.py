"""WSS + actual child process; fixture CLI is independent of the Liza driver."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
from test_httpws import build,client_frame,receive
from test_tls_transport import TlsTransport as _Tls
setup_tls=_Tls.setUpClass.__func__
fixture_command=_Tls.command.__func__
del _Tls
ROOT=Path(__file__).resolve().parents[1]
def frame(message):
    data=json.dumps(message,separators=(',',':'),ensure_ascii=False).encode()
    return b'\x81'+(bytes([len(data)]) if len(data)<126 else b'\x7e'+len(data).to_bytes(2,'big'))+data

@unittest.skipUnless(os.environ.get('LIZA_TEST_TLS')=='1','TLS recorder: LIZA_TEST_TLS=1')
class RecorderAgent(unittest.TestCase):
    command=classmethod(fixture_command)
    @classmethod
    def setUpClass(cls):
        setup_tls(cls)
        cls.agent_temp=tempfile.TemporaryDirectory(prefix='liza-recorder-',dir='/private/tmp' if Path('/private/tmp').is_dir() else None);cls.addClassCleanup(cls.agent_temp.cleanup)
        root=Path(cls.agent_temp.name)
        for name in ('server.pem','server.key','ca.pem'):shutil.copyfile(cls.root/name,root/name)
        cls.root=root;(root/'token').write_text('fixture-can-token')
        cls.native=root/('fixture.exe' if os.name=='nt' else 'fixture')
        result=subprocess.run(['clang',str(ROOT/'tests/native/recorder_fixture.c'),'-o',str(cls.native)],capture_output=True,timeout=120)
        if result.returncode:raise AssertionError(result.stderr.decode(errors='replace'))
        cls.clients=[]
        for opt in ('0','2'):
            folder=root/('build'+opt);folder.mkdir();cls.clients.append(build(ROOT/'examples/apps/liza_recorder.liza',folder,opt,ROOT/'examples'))

    @staticmethod
    def upgrade(conn):
        request=b''
        while not request.endswith(b'\r\n\r\n'):request+=receive(conn,1)
        assert request.startswith(b'GET /can HTTP/1.1\r\n')
        key=next(line.split(b':',1)[1].strip() for line in request.split(b'\r\n') if line.lower().startswith(b'sec-websocket-key:'))
        proof=base64.b64encode(hashlib.sha1(key+b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
        conn.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+proof+b'\r\n\r\n')
        opcode,payload=client_frame(conn);assert opcode==1;hello=json.loads(payload)
        assert hello['role']=='recorder' and hello['capabilities']==['recording','consolidated_native']
        assert hello['node_id']=='liza-recorder-test' and hello['token']=='fixture-can-token'
        assert hello['max_concurrent_jobs']==1

    @staticmethod
    def ready():return {'type':'hello_ok','node_id':'liza-recorder-test','role':'recorder','server_time':1794700000000,'heartbeat_ms':100,'max_concurrent_jobs':1,'assignment_protocol':1,'lease_timeout_ms':90000}
    @staticmethod
    def job(tag='radio',job='record-1',assignment='assign-1'):
        return {'type':'job','job_id':job,'assignment_id':assignment,'job_type':'recording.start','server_time':1794700000000,'payload':{'conference_tag':tag,'conference_session_id':123,'profile':'consolidated_native','auth':{'access_token':'fixture-media-token'},'storage_required':False,'server_url':'https://do-not-contact.invalid','native_recorder':'/bin/sh'}}

    def session(self,exe,peer,run_ms=1800,expected=0,storage_peer=None,local_only=True,ack_ms=15000,storage_abrupt=False):
        errors=[];context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(self.root/'server.pem',self.root/'server.key')
        with tempfile.TemporaryDirectory(prefix='case-',dir=self.root) as folder,socket.socket() as listener:
            root=Path(folder);output=root/'out';config=root/'config.json';config.write_text(json.dumps({'output_dir':str(output),'local_only':local_only,'ack_ms':ack_ms}))
            listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(12)
            def serve():
                try:
                    with listener.accept()[0] as raw:
                        raw.settimeout(12)
                        with context.wrap_socket(raw,server_side=True) as conn:
                            self.upgrade(conn)
                            storage_thread=None
                            if storage_peer:
                                def serve_storage():
                                    try:
                                        with listener.accept()[0] as transport:
                                            transport.settimeout(12)
                                            with context.wrap_socket(transport,server_side=True) as secure:
                                                storage_peer(secure,output)
                                                try:secure.unwrap().close()
                                                except ssl.SSLError:
                                                    if not storage_abrupt:raise
                                    except BaseException as exc:errors.append(repr(exc))
                                storage_thread=threading.Thread(target=serve_storage,daemon=True);storage_thread.start()
                            peer(conn,output);conn.unwrap().close()
                            if storage_thread:
                                storage_thread.join(13)
                                self.assertFalse(storage_thread.is_alive(),'storage thread leaked')
                except BaseException as exc:errors.append(repr(exc))
            thread=threading.Thread(target=serve,daemon=True);thread.start()
            run=subprocess.run([str(exe),f'127.0.0.1:{listener.getsockname()[1]}','localhost','liza-recorder-test','token','ca.pem',str(run_ms),str(self.native),str(config)],cwd=self.root,capture_output=True,timeout=25)
            thread.join(13)
            self.assertFalse(thread.is_alive(),'server thread leaked')
            self.assertFalse(errors,(errors,run.returncode,run.stdout,run.stderr))
            self.assertEqual(run.returncode,expected,(run.stdout,run.stderr))
            self.assertNotIn(b'fixture-media-token',run.stdout+run.stderr);self.assertNotIn(b'fixture-can-token',run.stdout+run.stderr)
            self.assertNotIn(b'vgupl1.fixture-upload-token',run.stdout+run.stderr)
            return run

    def exchange(self,conn,on_message):
        while True:
            opcode,payload=client_frame(conn)
            if opcode==8:conn.sendall(b'\x88\x02\x03\xe8');return
            self.assertEqual(opcode,1);message=json.loads(payload)
            if message['type']=='heartbeat':conn.sendall(frame({'type':'heartbeat_ok','server_time':1794700000001}))
            on_message(message)

    def test_record_stop_marker_and_live_heartbeat(self):
        for exe in self.clients:
            def peer(conn,output):
                conn.sendall(frame(self.ready())+frame(self.job()));seen=[];beats=0
                def observe(message):
                    nonlocal beats
                    if message['type']=='heartbeat':
                        beats+=1
                        if beats==3:conn.sendall(frame({'type':'job_cancel','job_id':'record-1','assignment_id':'assign-1'}))
                    else:seen.append(message)
                self.exchange(conn,observe)
                self.assertGreaterEqual(beats,3)
                self.assertEqual(seen[0]['type'],'job_ack');self.assertEqual(seen[0]['status'],'accepted')
                done=[m for m in seen if m.get('status')=='completed'];self.assertEqual(len(done),1)
                self.assertFalse(done[0]['data']['published']);self.assertTrue(done[0]['data']['local_only'])
                path=Path(done[0]['data']['local_path']);self.assertEqual(path.parent,output/'record-1'/'assign-1')
                self.assertEqual(path.stat().st_size,32);self.assertFalse((path.parent/'.native-recorder.stop').exists())
                self.assertEqual(done[0]['data']['exit_code'],0)
            run=self.session(exe,peer);self.assertIn(b'Recorder CAN ready',run.stdout)

    def test_explicit_stop_is_separate_assignment(self):
        for exe in self.clients:
            def peer(conn,output):
                start=self.job();start['payload'].update(include_video=False,include_audio=True)
                conn.sendall(frame(self.ready())+frame(start));seen=[];sent=False
                def observe(message):
                    nonlocal sent
                    seen.append(message)
                    if message.get('status')=='running' and not sent:
                        sent=True
                        conn.sendall(frame({'type':'job','job_id':'stop-1','assignment_id':'stop-assign',
                            'job_type':'recording.stop','server_time':1794700000000,
                            'payload':{'job_id':'record-1','conference_tag':'radio'}}))
                self.exchange(conn,observe)
                done=[m for m in seen if m.get('status')=='completed']
                self.assertEqual({m['job_id'] for m in done},{'record-1','stop-1'})
                media=next(m for m in done if m['job_id']=='record-1')
                self.assertTrue(media['data']['local_path'].endswith('/output.m4a'))
                self.assertEqual(Path(media['data']['local_path']).stat().st_size,32)
            self.session(exe,peer)

    def test_child_failure_and_missing_artifact_are_not_completed(self):
        for exe in self.clients:
            for tag in ('fail-code','missing-file'):
                with self.subTest(exe=exe,tag=tag):
                    def peer(conn,output):
                        conn.sendall(frame(self.ready())+frame(self.job(tag=tag)));seen=[]
                        self.exchange(conn,seen.append)
                        self.assertEqual(len([m for m in seen if m.get('status')=='accepted']),1)
                        self.assertEqual(len([m for m in seen if m.get('status')=='failed']),1)
                        self.assertFalse(any(m.get('status')=='completed' for m in seen))
                    self.session(exe,peer,run_ms=800)

    def test_storage_required_rejected_before_spawn(self):
        for exe in self.clients:
            def peer(conn,output):
                start=self.job();start['payload']['storage_required']=True
                conn.sendall(frame(self.ready())+frame(start));seen=[]
                self.exchange(conn,seen.append)
                self.assertEqual(len([m for m in seen if m.get('status')=='failed']),1)
                self.assertFalse(any(m.get('status') in ('accepted','running','completed') for m in seen))
                self.assertFalse(output.exists())
            self.session(exe,peer,run_ms=800)

    @staticmethod
    def http_request(conn):
        head=b''
        while not head.endswith(b'\r\n\r\n'):
            b=conn.recv(1)
            if not b:
                if not head:return None
                raise AssertionError('truncated HTTP head')
            head+=b
            if len(head)>8192:raise AssertionError('oversized HTTP head')
        lines=head[:-4].split(b'\r\n');method,target,version=lines[0].decode().split(' ')
        headers=dict((k.decode().lower(),v.decode().strip()) for k,v in (line.split(b':',1) for line in lines[1:]))
        count=int(headers['content-length']);body=receive(conn,count) if count else b''
        return method,target,headers,body

    @staticmethod
    def http_reply(conn,value):
        body=json.dumps(value,separators=(',',':')).encode()
        conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body)

    def test_storage_upload_requires_both_matching_acknowledgements(self):
        for exe in self.clients:
            finalizing=threading.Event();uploaded=bytearray();events=[];beats_during_upload=0
            def storage(conn,output):
                request=self.http_request(conn);self.assertTrue(finalizing.is_set())
                method,target,headers,body=request
                self.assertEqual((method,target),('POST','/api/storage/uploads'))
                self.assertEqual(headers['authorization'],'Bearer vgupl1.fixture-upload-token')
                self.assertEqual(headers['x-upload-filename'],'output.mp4');self.assertEqual(int(headers['x-upload-size']),327680)
                self.http_reply(conn,{'ok':True,'upload_id':'upload-1','blob_id':'blob-1','offset':0,'max_chunk_size':65536})
                while len(uploaded)<327680:
                    method,target,headers,body=self.http_request(conn)
                    self.assertEqual((method,target),('PUT','/api/storage/uploads/upload-1'))
                    self.assertEqual(headers['authorization'],'Bearer vgupl1.fixture-upload-token')
                    self.assertEqual(int(headers['x-upload-offset']),len(uploaded));self.assertGreater(len(body),0);self.assertLessEqual(len(body),65536)
                    uploaded.extend(body);time.sleep(.035)
                    self.http_reply(conn,{'ok':True,'offset':len(uploaded)})
                method,target,headers,body=self.http_request(conn)
                self.assertEqual((method,target),('POST','/api/storage/uploads/upload-1/complete'))
                self.assertEqual(headers['authorization'],'Bearer vgupl1.fixture-upload-token')
                self.http_reply(conn,{'ok':True,'blob_id':'blob-1','url':'/api/storage/blobs/blob-1','offset':327680})
                self.assertIsNone(self.http_request(conn))
            def peer(conn,output):
                start=self.job(tag='large-file');start['payload'].update(storage_required=True,storage_auth={'access_token':'vgupl1.fixture-upload-token'},max_sec=1)
                conn.sendall(frame(self.ready())+frame(start));pending=None;beats=0
                def observe(message):
                    nonlocal pending,beats,beats_during_upload
                    events.append(message)
                    if message['type']=='heartbeat':
                        beats+=1
                        if finalizing.is_set() and len(uploaded)<327680:beats_during_upload+=1
                        if pending and beats>=pending[0]:
                            status=pending[1];pending=None
                            conn.sendall(frame({'type':'job_event_ack','job_id':'record-1','assignment_id':'assign-1','status':status,'ok':True}))
                            if status=='finalizing':finalizing.set()
                    elif message.get('status') in ('finalizing','artifact_ready'):
                        status=message['status']
                        conn.sendall(frame({'type':'job_event_ack','job_id':'record-1','assignment_id':'obsolete','status':status,'ok':True}))
                        pending=(beats+2,status)
                    elif message.get('status')=='completed':
                        self.assertIsNone(pending);self.assertTrue(message['data']['published'])
                        self.assertEqual(message['data']['files'][0]['blob_id'],'blob-1')
                        self.assertEqual(bytes(uploaded),Path(message['data']['local_path']).read_bytes())
                self.exchange(conn,observe)
                self.assertGreater(beats_during_upload,0)
                self.assertEqual([m['status'] for m in events if m.get('type')=='job_event'],['running','finalizing','artifact_ready','completed'])
            self.session(exe,peer,run_ms=4000,storage_peer=storage,local_only=False)

    def test_storage_bad_offset_retains_file_without_completion(self):
        for exe in self.clients:
            def storage(conn,output):
                self.http_request(conn)
                self.http_reply(conn,{'ok':True,'upload_id':'upload-1','offset':0,'max_chunk_size':65536})
                method,target,headers,body=self.http_request(conn)
                self.assertEqual(method,'PUT');self.assertEqual(len(body),32)
                self.http_reply(conn,{'ok':True,'offset':31})
            def peer(conn,output):
                start=self.job();start['payload'].update(storage_required=True,storage_auth={'access_token':'vgupl1.fixture-upload-token'},max_sec=1)
                conn.sendall(frame(self.ready())+frame(start));seen=[]
                def observe(message):
                    seen.append(message)
                    if message.get('status')=='finalizing':
                        conn.sendall(frame({'type':'job_event_ack','job_id':'record-1','assignment_id':'assign-1','status':'finalizing','ok':True}))
                self.exchange(conn,observe)
                self.assertFalse(any(m.get('status') in ('artifact_ready','completed') for m in seen))
                failed=[m for m in seen if m.get('status')=='failed'];self.assertEqual(len(failed),1)
                self.assertEqual(failed[0]['message'],'upload_failed')
                self.assertEqual((output/'record-1/assign-1/output.mp4').stat().st_size,32)
            self.session(exe,peer,run_ms=2000,storage_peer=storage,local_only=False,storage_abrupt=True)

    def test_finalizing_ack_timeout_never_opens_storage(self):
        for exe in self.clients:
            def peer(conn,output):
                start=self.job();start['payload'].update(storage_required=True,storage_auth={'access_token':'vgupl1.fixture-upload-token'},max_sec=1)
                conn.sendall(frame(self.ready())+frame(start));seen=[]
                self.exchange(conn,seen.append)
                self.assertEqual([m['status'] for m in seen if m.get('type')=='job_event'],['running','finalizing','failed'])
                self.assertEqual(next(m for m in seen if m.get('status')=='failed')['message'],'ack_timeout')
                self.assertEqual((output/'record-1/assign-1/output.mp4').stat().st_size,32)
            self.session(exe,peer,run_ms=2000,local_only=False,ack_ms=400)

    def test_artifact_ack_timeout_retains_uploaded_local_file(self):
        for exe in self.clients:
            def storage(conn,output):
                self.http_request(conn)
                self.http_reply(conn,{'ok':True,'upload_id':'upload-1','offset':0,'max_chunk_size':65536})
                method,target,headers,body=self.http_request(conn)
                self.assertEqual(len(body),32)
                self.http_reply(conn,{'ok':True,'offset':32})
                self.http_request(conn)
                self.http_reply(conn,{'ok':True,'offset':32,'blob_id':'blob-1','url':'/api/storage/blobs/blob-1'})
                self.assertIsNone(self.http_request(conn))
            def peer(conn,output):
                start=self.job();start['payload'].update(storage_required=True,storage_auth={'access_token':'vgupl1.fixture-upload-token'},max_sec=1)
                conn.sendall(frame(self.ready())+frame(start));seen=[]
                def observe(message):
                    seen.append(message)
                    if message.get('status')=='finalizing':conn.sendall(frame({'type':'job_event_ack','job_id':'record-1','assignment_id':'assign-1','status':'finalizing','ok':True}))
                    if message.get('status')=='artifact_ready':self.assertFalse(message['data']['published'])
                self.exchange(conn,observe)
                self.assertEqual([m['status'] for m in seen if m.get('type')=='job_event'],['running','finalizing','artifact_ready','failed'])
                self.assertEqual(next(m for m in seen if m.get('status')=='failed')['message'],'ack_timeout')
                self.assertEqual((output/'record-1/assign-1/output.mp4').stat().st_size,32)
            self.session(exe,peer,run_ms=2000,storage_peer=storage,local_only=False,ack_ms=400)
