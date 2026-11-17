"""Independent RTSP, ordinary VG WSS and authenticated UDP wire peers."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import select
import signal
import socket
import ssl
import struct
import subprocess
import threading
import time
import unittest

from test_httpws import build, client_frame, receive
from test_tls_transport import TlsTransport as _Fixture

setup_fixture = _Fixture.setUpClass.__func__
fixture_command = _Fixture.command.__func__
del _Fixture
ROOT = Path(__file__).resolve().parents[1]
KEY = b'0123456789abcdef' * 4
SPS, PPS = b'\x67\x64\x00\x28', b'\x68\xee\x3c\x80'


def ws(data, first=0x81):
    if len(data) < 126:
        return bytes([first, len(data)]) + data
    return bytes([first, 126]) + struct.pack('!H', len(data)) + data


def message(value):
    return ws(json.dumps(value, separators=(',', ':')).encode())


def signed(packet, phase, key=KEY):
    packet = bytearray(packet)
    packet[12] = phase
    packet[48:] = hmac.digest(key, packet[:48], 'sha256')
    return packet


@unittest.skipUnless(os.environ.get('LIZA_TEST_TLS') == '1', 'LIZA_TEST_TLS=1 requires OpenSSL')
class RtspClient(unittest.TestCase):
    command = classmethod(fixture_command)

    @classmethod
    def setUpClass(cls):
        setup_fixture(cls)
        cls.clients = []
        for opt in ('0', '2'):
            folder = cls.root / ('rtsp' + opt)
            folder.mkdir()
            cls.clients.append(build(ROOT / 'examples/apps/liza_rtsp.liza', folder, opt, ROOT / 'examples'))

    def scenario(self, exe, bad_cseq=False, drop_after=None, payload_bytes=b'camera-payload', run_ms=4000, stop_on_media=False,
                 cycles=1, stall_keepalive=False, stop_delay=6, drop_wss=False, wrong_peer=False,
                 stall_teardown=False, reject_login=False):
        errors, packets, methods, commands = [], [], [], []
        stopped = threading.Event()
        media_seen = [threading.Event() for _ in range(cycles)]
        camera_runs, control_runs = [], []
        epoch_packets = [[] for _ in range(cycles)]
        def epoch_key(epoch):
            return KEY if epoch==0 else hashlib.sha256(str(epoch).encode()).hexdigest().encode()
        def epoch_nonce(epoch):
            return b'server-nonce-123' if epoch==0 else hashlib.sha256(b'nonce'+str(epoch).encode()).digest()[:16]
        listeners = [socket.socket() for _ in range(2)]
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for listener in listeners:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(12)
        udp.bind(('127.0.0.1', 0))
        udp.settimeout(.1)
        camera, control = listeners
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.root / 'server.pem', self.root / 'server.key')

        def camera_session():
            with camera.accept()[0] as conn:
                epoch=len(camera_runs)
                history={'methods': [], 'cseqs': [], 'started': time.monotonic()}
                camera_runs.append(history)
                conn.settimeout(.03)
                pending = b''
                playing = False
                sequence = 0
                while not stopped.is_set():
                    try:
                        chunk = conn.recv(8192)
                        if not chunk:
                            if stall_keepalive and epoch==0:
                                # Linux may report ECONNRESET instead of EOF
                                # when the client discards unread interleaved
                                # RTP after the control deadline. Exercise both
                                # platforms through the same session boundary.
                                raise ConnectionResetError('deadline closed the streaming camera connection')
                            break
                        pending += chunk
                    except socket.timeout:
                        pass
                    while b'\r\n\r\n' in pending:
                        request, pending = pending.split(b'\r\n\r\n', 1)
                        method = request.split(b' ', 1)[0]
                        methods.append(method)
                        history['methods'].append(method)
                        cseq = next(line.split(b':', 1)[1].strip() for line in request.split(b'\r\n') if line.lower().startswith(b'cseq:'))
                        history['cseqs'].append(int(cseq))
                        if stall_keepalive and epoch==0 and method==b'GET_PARAMETER':
                            continue  # RTP continues, but the control reply never arrives.
                        if stall_teardown and method==b'TEARDOWN':
                            continue
                        if bad_cseq:
                            cseq = str(int(cseq) + 1).encode()
                        body = b''
                        headers = b''
                        if method == b'DESCRIBE':
                            body = (b'v=0\r\nm=video 0 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\n'
                                    b'a=fmtp:96 packetization-mode=1;profile-level-id=640028;sprop-parameter-sets='
                                    + base64.b64encode(SPS) + b',' + base64.b64encode(PPS)
                                    + b'\r\na=framesize:96 1920-1080\r\na=control:trackID=1\r\n')
                            headers = b'Content-Type: application/sdp\r\nContent-Base: rtsp://127.0.0.1/stream1/\r\n'
                        if method == b'SETUP':
                            self.assertIn(b'Transport: RTP/AVP/TCP;unicast;interleaved=0-1', request)
                            headers = b'Session: fixture;timeout=60\r\nTransport: RTP/AVP/TCP;unicast;interleaved=0-1\r\n'
                        response = b'RTSP/1.0 200 OK\r\nCSeq: ' + cseq + b'\r\n' + headers + b'Content-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body
                        # Fragment the header independently of RTP record framing.
                        conn.sendall(response[:7])
                        conn.sendall(response[7:])
                        if method == b'PLAY':
                            playing = True
                        if method == b'TEARDOWN':
                            return
                    if playing:
                        sequence += 1
                        # Every fifth packet is an IDR; payload must survive unchanged.
                        payload = (b'\x65' if sequence % 5 == 0 else b'\x61') + payload_bytes
                        packet = struct.pack('!BBHII', 128, 224, sequence, sequence * 3600, 777) + payload
                        record = b'$\0' + struct.pack('!H', len(packet)) + packet
                        conn.sendall(record[:3])
                        conn.sendall(record[3:] + b'$\1\0\4\x80\xc8\0\0')
                        if drop_after is not None and (epoch==0 or epoch<cycles-1) and sequence == drop_after:
                            return

        def camera_peer():
            for _ in range(cycles):
                try:
                    camera_session()
                except (ConnectionResetError,BrokenPipeError,ConnectionAbortedError):
                    if not (stall_keepalive or stall_teardown or drop_wss):
                        raise
                    # Expected end of this faulted session, not end of the
                    # camera listener. The next connection must be accepted.
                    camera_runs[-1]['peer_reset']=True

        def control_session():
            with control.accept()[0] as raw, context.wrap_socket(raw, server_side=True) as conn:
                epoch=len(control_runs)
                control_runs.append(time.monotonic())
                ssrc=456+epoch
                conn.settimeout(12)
                request = b''
                while not request.endswith(b'\r\n\r\n'):
                    request += receive(conn, 1)
                self.assertTrue(request.startswith(b'GET / HTTP/1.1\r\n'))
                key = next(line.split(b':', 1)[1].strip() for line in request.split(b'\r\n') if line.lower().startswith(b'sec-websocket-key:'))
                proof = base64.b64encode(hashlib.sha1(key + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
                conn.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + proof + b'\r\n\r\n')
                while True:
                    try:
                        opcode, data = client_frame(conn)
                    except AssertionError as error:
                        if stall_teardown and str(error)=='premature EOF':
                            return  # The bounded shutdown deadline closed TCP.
                        raise
                    if opcode == 8:
                        conn.sendall(b'\x88\x02\x03\xe8')
                        conn.unwrap().close()
                        return
                    if opcode == 9:
                        conn.sendall(bytes([138, len(data)]) + data)
                        continue
                    self.assertEqual(opcode, 1)
                    value = json.loads(data)
                    commands.append(next(iter(value)))
                    if 'connect_request' in value:
                        self.assertEqual(value['connect_request']['login'], 'fixture-login')
                        conn.sendall(message({'connect_response': {'result': 0 if reject_login else 1, 'id': 123}}))
                        large = json.dumps({'conferences_list': {'unused': 'x' * 34000}}).encode()
                        conn.sendall(ws(large[:4096], 1) + ws(large[4096:], 128))
                    elif 'connect_to_conference_request' in value:
                        self.assertEqual(value['connect_to_conference_request']['tag'], 'radio')
                        conn.sendall(message({'connect_to_conference_response': {'result': 1}}))
                    elif 'device_params' in value:
                        conn.sendall(message({'device_params': {'id': 7, 'ssrc': ssrc}}))
                    elif 'device_connect' in value:
                        self.assertEqual(value['device_connect']['video_codec'], 2)
                        conn.sendall(message({'device_connect': {'connect_type': 1, 'device_id': 7, 'author_ssrc': ssrc, 'address': '0.0.0.0', 'port': udp.getsockname()[1], 'rtp_binding_key': epoch_key(epoch).decode()}}))
                        if drop_wss and epoch==0:
                            self.assertTrue(media_seen[epoch].wait(5), 'no first-generation media')
                            if drop_wss in ('close','policy'):
                                conn.sendall(ws(struct.pack('!H',1008 if drop_wss=='policy' else 1001),0x88))
                                opcode,data=client_frame(conn)
                                self.assertEqual(opcode,8)
                                conn.unwrap().close()
                                return
                            if drop_wss!='eof':
                                conn.setsockopt(socket.SOL_SOCKET,socket.SO_LINGER,struct.pack('hh' if os.name=='nt' else 'ii',1,0))
                            return
                        if stop_on_media and epoch==cycles-1:
                            self.assertTrue(media_seen[epoch].wait(5), 'no authorized media')
                            # Exercise TLS beyond the old zero-duration + 5 s
                            # lifetime, then stop through the existing control API.
                            time.sleep(stop_delay)
                            conn.sendall(message({'device_disconnect': {'device_id': 7}}))

        def control_peer():
            for _ in range(cycles):
                control_session()

        def udp_peer():
            while not stopped.is_set():
                try:
                    data, source = udp.recvfrom(8192)
                except socket.timeout:
                    continue
                if len(data) == 80 and data[8:12] == b'VGB1':
                    epoch=struct.unpack('!I', data[4:8])[0]-456
                    self.assertIn(epoch,range(cycles))
                    self.assertEqual(data[48:], hmac.digest(epoch_key(epoch), data[:48], 'sha256'))
                    self.assertEqual(data[13:16], b'\1\0\0')
                    if data[12] == 1:
                        challenge = bytearray(data)
                        challenge[32:48] = epoch_nonce(epoch)
                        udp.sendto(signed(challenge, 2, epoch_key(epoch)), source)
                    elif data[12] == 3:
                        self.assertEqual(data[32:48], epoch_nonce(epoch))
                        udp.sendto(signed(data, 4, epoch_key(epoch)), source)
                else:
                    packets.append(data)
                    epoch=struct.unpack('!I', data[8:12])[0]-456
                    self.assertIn(epoch,range(cycles))
                    epoch_packets[epoch].append(data)
                    if len(epoch_packets[epoch])>=10:media_seen[epoch].set()

        def guarded(fn):
            try:
                fn()
            except ssl.SSLError as error:
                if not wrong_peer:
                    errors.append(repr(error))
            except BaseException as error:
                errors.append(repr(error))

        threads = [threading.Thread(target=guarded, args=(fn,), daemon=True) for fn in (camera_peer, control_peer, udp_peer)]
        config = dict(camera_ip='127.0.0.1', camera_port=camera.getsockname()[1], camera_url='rtsp://127.0.0.1/stream1', vg_ip='127.0.0.1', vg_port=control.getsockname()[1], vg_peer='localhost', login='fixture-login', password='fixture-password', conference='radio', ca_file=str(self.root / 'ca.pem'), run_ms=run_ms)
        if wrong_peer:
            config['vg_peer']='wrong.example'
        path = self.root / 'rtsp-config.json'
        path.write_text(json.dumps(config))
        for thread in threads:
            thread.start()
        try:
            try:
                run = subprocess.run([str(exe), str(path)], capture_output=True, timeout=45 if stall_keepalive else 20)
            except subprocess.TimeoutExpired as error:
                self.fail(('client timeout',error.stdout,error.stderr,errors,camera_runs,commands,[len(p) for p in epoch_packets]))
        finally:
            stopped.set()
            for listener in listeners:
                listener.close()
            for thread in threads:
                thread.join(2)
            udp.close()
        self.assertFalse(any(t.is_alive() for t in threads), ('peer leaked', run.returncode, run.stdout, run.stderr, errors, methods, commands))
        self.assertFalse(errors, (errors, run.returncode, run.stdout, run.stderr, methods, commands))
        self.assertNotIn(b'fixture-password', run.stdout + run.stderr)
        self.attempts=(camera_runs,control_runs,epoch_packets)
        return run, packets, methods, commands

    def test_publish_and_cleanup(self):
        for exe in self.clients:
            with self.subTest(exe=exe.name):
                run, packets, methods, commands = self.scenario(exe)
                self.assertEqual(run.returncode, 0, (run.stdout, run.stderr))
                self.assertGreater(len(packets), 10)
                self.assertEqual(packets[0][12:], SPS)
                self.assertEqual(packets[1][12:], PPS)
                self.assertEqual(packets[2][12:], b'\x65camera-payload')
                previous = None
                for packet in packets:
                    _, pt, sequence, timestamp, ssrc = struct.unpack('!BBHII', packet[:12])
                    self.assertEqual(pt & 127, 102)
                    self.assertEqual(ssrc, 456)
                    self.assertEqual(timestamp % 3600, 0)
                    if previous is not None:
                        self.assertEqual(sequence, (previous + 1) % 65536)
                    previous = sequence
                    if packet[12:] not in (SPS, PPS):
                        self.assertIn(packet[12:], (b'\x61camera-payload', b'\x65camera-payload'))
                        self.assertTrue(pt & 128)
                self.assertEqual(methods, [b'OPTIONS', b'DESCRIBE', b'SETUP', b'PLAY', b'TEARDOWN'])
                self.assertIn('device_disconnect', commands)
                self.assertIn('disconnect_from_conference', commands)

    def test_wrong_cseq_rejected(self):
        for exe in self.clients:
            run, packets, methods, commands = self.scenario(exe, bad_cseq=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertFalse(packets)
            self.assertEqual(methods, [b'OPTIONS'])
            self.assertNotIn(b'RTSP reconnect',run.stderr)

    def recovered(self, exe, **fault):
        run,packets,methods,commands=self.scenario(exe,cycles=2,run_ms=0,stop_on_media=True,stop_delay=.2,**fault)
        self.assertEqual(run.returncode,0,(run.stdout,run.stderr))
        camera,control,epochs=self.attempts
        self.assertEqual(len(camera),2)
        self.assertEqual(len(control),2)
        self.assertEqual(commands.count('connect_request'),2)
        self.assertEqual(commands.count('device_connect'),2)
        self.assertIn(b'RTSP session generation=2',run.stdout)
        self.assertNotIn(b'RTSP session generation=3',run.stdout)
        self.assertIn(b'delay_ms=1000',run.stderr)
        self.assertGreaterEqual(camera[1]['started']-camera[0]['started'],1)
        for epoch in range(2):
            self.assertEqual(camera[epoch]['cseqs'][0],1)
            self.assertGreaterEqual(len(epochs[epoch]),10)
            self.assertEqual([p[12:] for p in epochs[epoch][:3]],[SPS,PPS,b'\x65camera-payload'])
            self.assertEqual(struct.unpack('!H',epochs[epoch][0][2:4])[0],1)
        return run

    def test_camera_disconnect_reconnects_with_fresh_binding_and_idr(self):
        for exe in self.clients:
            run=self.recovered(exe,drop_after=35)
            self.assertIn(b'after error 35',run.stderr)

    def test_repeated_camera_failures_create_three_independent_sessions(self):
        for exe in self.clients:
            run,packets,methods,commands=self.scenario(exe,cycles=3,drop_after=35,run_ms=0,stop_on_media=True,stop_delay=.2)
            self.assertEqual(run.returncode,0,(run.stdout,run.stderr))
            camera,control,epochs=self.attempts
            self.assertEqual(len(control),3)
            self.assertEqual(commands.count('connect_request'),3)
            self.assertEqual(commands.count('device_disconnect'),3)
            self.assertIn(b'delay_ms=1000',run.stderr)
            self.assertIn(b'delay_ms=2000',run.stderr)
            for epoch in range(3):
                self.assertEqual(camera[epoch]['cseqs'][0],1)
                self.assertEqual([p[12:] for p in epochs[epoch][:3]],[SPS,PPS,b'\x65camera-payload'])

    def test_keepalive_timeout_recovers_while_rtp_continues(self):
        for exe in self.clients:
            run=self.recovered(exe,stall_keepalive=True)
            self.assertIn(b'phase=6',run.stderr)
            self.assertIn(b'after error 32',run.stderr)
            self.assertTrue(self.attempts[0][0].get('peer_reset'))

    def test_wss_disconnect_recovers_with_new_login(self):
        for exe in self.clients:
            for fault in ('reset','eof','close'):
                self.recovered(exe,drop_wss=fault)

    def test_wss_policy_close_is_fatal_without_retry(self):
        for exe in self.clients:
            run,packets,methods,commands=self.scenario(exe,drop_wss='policy',run_ms=0)
            self.assertNotEqual(run.returncode,0,(run.stdout,run.stderr))
            self.assertIn(b'WSS peer close code=1008',run.stderr)
            self.assertNotIn(b'RTSP reconnect',run.stderr)

    def test_wrong_tls_identity_is_fatal_without_retry(self):
        for exe in self.clients:
            run,packets,methods,commands=self.scenario(exe,wrong_peer=True,run_ms=0)
            self.assertNotEqual(run.returncode,0)
            self.assertFalse(packets)
            self.assertIn(b'TLS verification',run.stderr)
            self.assertNotIn(b'RTSP reconnect',run.stderr)

    def test_login_rejection_is_fatal_without_retry(self):
        for exe in self.clients:
            run,packets,methods,commands=self.scenario(exe,reject_login=True,run_ms=0)
            self.assertNotEqual(run.returncode,0)
            self.assertFalse(packets)
            self.assertEqual(commands.count('connect_request'),1)
            self.assertNotIn(b'RTSP reconnect',run.stderr)

    def test_remote_stop_does_not_reconnect_when_teardown_times_out(self):
        for exe in self.clients:
            run,packets,methods,commands=self.scenario(exe,stall_teardown=True,run_ms=0,stop_on_media=True,stop_delay=.2)
            self.assertNotEqual(run.returncode,0,(run.stdout,run.stderr))
            self.assertIn(b'phase=7',run.stderr)
            self.assertEqual(commands.count('connect_request'),1)
            self.assertNotIn(b'RTSP reconnect',run.stderr)

    def unavailable_config(self, run_ms):
        reservations=[socket.socket(),socket.socket()]
        for reservation in reservations:
            reservation.bind(('127.0.0.1',0))
        ports=[s.getsockname()[1] for s in reservations]
        for reservation in reservations:
            reservation.close()
        config=dict(camera_ip='127.0.0.1',camera_port=ports[0],camera_url='rtsp://127.0.0.1/stream1',
                    vg_ip='127.0.0.1',vg_port=ports[1],vg_peer='localhost',login='fixture-login',
                    password='fixture-password',conference='radio',ca_file=str(self.root/'ca.pem'),run_ms=run_ms)
        path=self.root/'unavailable.json'
        path.write_text(json.dumps(config))
        return path

    def test_backoff_respects_global_deadline(self):
        for exe in self.clients:
            path=self.unavailable_config(3500)
            start=time.monotonic()
            run=subprocess.run([str(exe),str(path)],capture_output=True,timeout=8)
            self.assertNotEqual(run.returncode,0,(run.stdout,run.stderr))
            self.assertGreaterEqual(time.monotonic()-start,3.3)
            self.assertEqual(run.stdout.count(b'RTSP session generation='),3,(run.stdout,run.stderr))
            for delay in (1000,2000,4000):
                self.assertIn(('delay_ms='+str(delay)).encode(),run.stderr)

    @unittest.skipUnless(os.name=='posix','POSIX shutdown signal')
    def test_sigterm_during_backoff_stops_without_another_attempt(self):
        for exe in self.clients:
            proc=subprocess.Popen([str(exe),str(self.unavailable_config(0))],stdout=subprocess.PIPE,stderr=subprocess.PIPE,bufsize=0)
            lines=[]
            try:
                deadline=time.monotonic()+12
                while time.monotonic()<deadline:
                    if select.select([proc.stderr],[],[],.1)[0]:
                        line=proc.stderr.readline();lines.append(line)
                        if b'delay_ms=4000' in line:
                            break
                        if not line:
                            break
                self.assertIn(b'delay_ms=4000',b''.join(lines))
                proc.send_signal(signal.SIGTERM)
                stdout,stderr=proc.communicate(timeout=3)
                self.assertEqual(proc.returncode,0,(stdout,b''.join(lines)+stderr))
                self.assertEqual(stdout.count(b'RTSP session generation='),3)
            finally:
                if proc.poll() is None:
                    proc.kill();proc.communicate()

    def test_camera_disconnect_exhausts_global_budget_without_recovery(self):
        for exe in self.clients:
            run, packets, methods, commands = self.scenario(exe, drop_after=35)
            self.assertNotEqual(run.returncode, 0)
            self.assertGreater(len(packets), 0, (run.stdout, run.stderr))
            self.assertEqual(methods, [b'OPTIONS', b'DESCRIBE', b'SETUP', b'PLAY'])
            self.assertEqual(commands.count('connect_request'), 1)
            self.assertIn('device_disconnect', commands)
            self.assertIn('disconnect_from_conference', commands)

    def test_maximum_record_crosses_byte_batches_and_socket_reads(self):
        payload=bytes(n % 256 for n in range(4083))
        for exe in self.clients:
            run, packets, methods, commands = self.scenario(exe, payload_bytes=payload)
            self.assertEqual(run.returncode,0,(run.stdout,run.stderr))
            self.assertGreater(len(packets),10)
            self.assertEqual(packets[0][12:],SPS)
            self.assertEqual(packets[1][12:],PPS)
            self.assertEqual(packets[2][12:],b'\x65'+payload)
            for packet in packets[2:]:
                self.assertEqual(len(packet),4096)
                self.assertIn(packet[12],(0x61,0x65))
                self.assertEqual(packet[13:],payload)

    def test_unlimited_survives_tls_then_stops_on_server_command(self):
        for exe in self.clients:
            run,packets,methods,commands=self.scenario(exe,run_ms=0,stop_on_media=True)
            self.assertEqual(run.returncode,0,(run.stdout,run.stderr))
            self.assertGreater(len(packets),50)
            self.assertIn(b'TEARDOWN',methods)
            self.assertIn('device_disconnect',commands)
            self.assertIn('disconnect_from_conference',commands)
