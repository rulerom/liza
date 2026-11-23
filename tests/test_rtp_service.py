"""Native CAN RTP worker registration against an independent WSS peer."""
import base64
import hashlib
import json
import os
import socket
import ssl
import subprocess
import threading
import time
import struct
import hmac
import unittest

from test_httpws import build, client_frame
from test_rtsp_client import setup_fixture, fixture_command, message, ws, signed, KEY, SPS, PPS
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('LIZA_TEST_TLS') == '1', 'Requires OpenSSL and local TLS peers')
class RtpService(unittest.TestCase):
    command = classmethod(fixture_command)

    @classmethod
    def setUpClass(cls):
        setup_fixture(cls)
        cls.clients = []
        for opt in ('0', '2'):
            folder = cls.root / ('service' + opt)
            folder.mkdir()
            cls.clients.append(build(ROOT / 'examples/apps/liza_rtsp_service.liza', folder, opt, ROOT / 'examples'))

    def registration(self, exe, downgrade=False):
        errors, seen = [], []
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.root / 'server.pem', self.root / 'server.key')
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(10)

            def serve():
                try:
                    with listener.accept()[0] as raw:
                        raw.settimeout(8)
                        with context.wrap_socket(raw, server_side=True) as conn:
                            request = bytearray()
                            while not request.endswith(b'\r\n\r\n'):
                                request.extend(conn.recv(1))
                            self.assertTrue(request.startswith(b'GET /can HTTP/1.1\r\n'))
                            headers = dict(line.split(b': ', 1) for line in bytes(request).split(b'\r\n')[1:] if b': ' in line)
                            accept = base64.b64encode(hashlib.sha1(headers[b'Sec-WebSocket-Key'] + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
                            conn.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + accept + b'\r\n\r\n')
                            opcode, payload = client_frame(conn)
                            self.assertEqual(opcode, 1)
                            hello = json.loads(payload)
                            self.assertEqual(hello['token'], 'fixture-service-key')
                            self.assertEqual(hello['capabilities'], [])
                            self.assertEqual(hello['contracts'], {'service_auth': 1, 'rtp_service': 1})
                            ready = dict(type='hello_ok', node_id='liza-rtsp', service_id='liza-rtsp', credential_id='fixture-credential', role='worker', contracts=hello['contracts'], assignment_protocol=1, max_concurrent_jobs=1, heartbeat_ms=100, lease_timeout_ms=90000)
                            if downgrade:
                                ready.pop('contracts')
                            conn.sendall(message(ready))
                            while True:
                                try:
                                    opcode, payload = client_frame(conn)
                                except (AssertionError, ConnectionError, ssl.SSLError):
                                    if downgrade:
                                        return
                                    raise
                                if opcode == 8:
                                    conn.sendall(ws(payload, 0x88))
                                    conn.unwrap().close()
                                    return
                                self.assertEqual(opcode, 1)
                                value = json.loads(payload)
                                seen.append(value['type'])
                                self.assertEqual(value['type'], 'heartbeat')
                                self.assertEqual(value['load']['jobs'], 0)
                                conn.sendall(message({'type': 'heartbeat_ok'}))
                except BaseException as error:
                    errors.append(error)

            token = self.root / 'service-token'
            token.write_text('fixture-service-key\n')
            config = self.root / 'service.json'
            config.write_text(json.dumps(dict(node_id='liza-rtsp', service_id='liza-rtsp', camera_ip='127.0.0.1', camera_url='rtsp://127.0.0.1/stream1', vg_ip='127.0.0.1', vg_peer='localhost', vg_port=listener.getsockname()[1], ca_file=str(self.root / 'ca.pem'), service_token_file=str(token), run_ms=900)))
            thread = threading.Thread(target=serve, daemon=True)
            thread.start()
            result = subprocess.run([str(exe), str(config)], capture_output=True, timeout=12)
            thread.join(9)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors, repr(errors))
            self.assertEqual(result.returncode, 3 if downgrade else 0, result.stdout + result.stderr)
            self.assertNotIn(b'fixture-service-key', result.stdout + result.stderr)
            if not downgrade:
                self.assertIn(b'CAN RTP service registered', result.stdout)
                self.assertIn('heartbeat', seen)

    def test_registration_only_heartbeat_and_graceful_shutdown(self):
        for exe in self.clients:
            with self.subTest(exe=exe.name):
                self.registration(exe)

    def test_missing_required_contract_fails_closed(self):
        for exe in self.clients:
            with self.subTest(exe=exe.name):
                self.registration(exe, downgrade=True)

    def publication(self, exe, can_loss=False):
        examples = {e['name']: e['value'] for e in json.loads((ROOT / 'tests/fixtures/rtp_service_examples.json').read_text())['examples']}
        ready = examples['hello_ok']
        ready.update(node_id='liza-rtsp', service_id='liza-rtsp', heartbeat_ms=100)
        job = examples['publication_job']
        job['payload']['source']['source_ref'] = 'stream1'
        job['payload']['auth']['access_token'] = 'fixture-job-token'
        errors, packets, events, methods = [], [], [], []
        stop, bound, complete = threading.Event(), threading.Event(), threading.Event()
        reconnected = threading.Event()
        media_at_reconnect = []
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.root / 'server.pem', self.root / 'server.key')
        tcp, camera, udp = socket.socket(), socket.socket(), socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for listener in (tcp, camera):
            listener.bind(('127.0.0.1', 0)); listener.listen(3); listener.settimeout(10)
        udp.bind(('127.0.0.1', 0)); udp.settimeout(.1)

        def checked(fn):
            def run():
                try:
                    fn()
                except BaseException as error:
                    if not stop.is_set():
                        errors.append(error)
            return run

        def upgrade(conn):
            request = b''
            while not request.endswith(b'\r\n\r\n'):
                chunk = conn.recv(1)
                if not chunk:
                    raise AssertionError('EOF during upgrade')
                request += chunk
            key = next(line.split(b':', 1)[1].strip() for line in request.split(b'\r\n') if line.lower().startswith(b'sec-websocket-key:'))
            accept = base64.b64encode(hashlib.sha1(key + b'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest())
            conn.sendall(b'HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: ' + accept + b'\r\n\r\n')
            return request.split(b' ')[1]

        def can_peer(conn):
            opcode, payload = client_frame(conn)
            self.assertEqual(opcode, 1)
            hello = json.loads(payload)
            self.assertEqual(hello['token'], 'fixture-service-key')
            self.assertEqual(hello['capabilities'], ['rtsp.ingest', 'rtp.publish', 'video.h264'])
            conn.sendall(message(ready) + message(job))
            wrong_cancel = False
            cancelling = False
            while not stop.is_set():
                opcode, payload = client_frame(conn)
                if opcode == 8:
                    conn.sendall(ws(payload, 0x88)); conn.unwrap().close(); return
                value = json.loads(payload)
                if value['type'] == 'heartbeat':
                    conn.sendall(message({'type': 'heartbeat_ok'}))
                    if len(packets) >= 8 and not wrong_cancel:
                        conn.sendall(message(dict(type='job_cancel', job_id=job['job_id'], assignment_id='stale-assignment')))
                        wrong_cancel = True
                    if len(packets) >= 25 and not cancelling:
                        if can_loss:
                            # Lose the CAN transport while media is active. The
                            # next CAN session must not reuse this job/token.
                            conn.close()
                            return
                        conn.sendall(message(dict(type='job_cancel', job_id=job['job_id'], assignment_id=job['assignment_id'])))
                        cancelling = True
                else:
                    events.append(value)
                    self.assertEqual(value['job_id'], job['job_id'])
                    self.assertEqual(value['assignment_id'], job['assignment_id'])
                    if value['status'] == 'cancelled':
                        complete.set()

        def control_peer(conn):
            while not stop.is_set():
                try:
                    opcode, payload = client_frame(conn)
                except (AssertionError, ConnectionError, ssl.SSLError):
                    if can_loss:
                        return
                    raise
                if opcode == 8:
                    conn.sendall(ws(payload, 0x88)); conn.unwrap().close(); return
                if opcode == 9:
                    conn.sendall(ws(payload, 0x8a)); continue
                value = json.loads(payload)
                if 'connect_request' in value:
                    auth = value['connect_request']
                    self.assertEqual(auth['access_token'], 'fixture-job-token')
                    self.assertNotIn('login', auth); self.assertNotIn('password', auth)
                    self.assertTrue(auth['control_instance_id'])
                    conn.sendall(message({'connect_response': {'result': 1, 'id': 9001}}))
                elif 'connect_to_conference_request' in value:
                    self.assertIs(value['connect_to_conference_request']['connect_members'], False)
                    conn.sendall(message({'connect_to_conference_response': {'result': 1}}))
                elif 'device_params' in value:
                    self.assertEqual(value['device_params']['track_id'], 'lobby-video')
                    conn.sendall(message({'device_params': {'id': 700, 'ssrc': 70001, 'track_id': 'lobby-video'}}))
                elif 'device_connect' in value:
                    route = examples['rtc_assignment']
                    route['device_connect'].update(address='127.0.0.1', port=udp.getsockname()[1], rtp_binding_key=KEY.decode())
                    conn.sendall(message(route))

        def tls_peer():
            children = []
            def session(conn, fn):
                try:
                    fn(conn)
                finally:
                    conn.close()
            expected_paths = (b'/can', b'/control', b'/can') if can_loss else (b'/can', b'/control')
            for index, expected in enumerate(expected_paths):
                raw = tcp.accept()[0]; raw.settimeout(10)
                conn = context.wrap_socket(raw, server_side=True)
                self.assertEqual(upgrade(conn), expected)
                if index == 2:
                    opcode, payload = client_frame(conn)
                    self.assertEqual(opcode, 1)
                    self.assertEqual(json.loads(payload)['type'], 'hello')
                    conn.sendall(message(ready))
                    media_at_reconnect.append(len(packets))
                    reconnected.set()
                    while True:
                        opcode, payload = client_frame(conn)
                        if opcode == 8:
                            conn.sendall(ws(payload, 0x88)); conn.unwrap().close(); break
                        value = json.loads(payload)
                        self.assertEqual(value['type'], 'heartbeat', 'old assignment emitted in a new CAN session')
                        self.assertEqual(value['load']['jobs'], 0)
                        self.assertEqual(value['load']['rtp_publications'], [])
                        self.assertEqual(len(packets), media_at_reconnect[0], 'old media survived CAN loss')
                        conn.sendall(message({'type': 'heartbeat_ok'}))
                    complete.set()
                    break
                fn = can_peer if expected == b'/can' else control_peer
                thread = threading.Thread(target=checked(lambda c=conn, f=fn: session(c, f)), daemon=True)
                thread.start(); children.append(thread)
            for child in children:
                child.join(12)

        def camera_peer():
            with camera.accept()[0] as conn:
                conn.settimeout(.015)
                pending = b''; playing = False; sequence = 0
                while not stop.is_set():
                    try:
                        chunk = conn.recv(8192)
                        if not chunk:
                            return
                        pending += chunk
                    except socket.timeout:
                        pass
                    while pending:
                        if pending[0] == 36:
                            if len(pending) < 4 or len(pending) < 4 + int.from_bytes(pending[2:4], 'big'):
                                break
                            pending = pending[4 + int.from_bytes(pending[2:4], 'big'):]; continue
                        if b'\r\n\r\n' not in pending:
                            break
                        request, pending = pending.split(b'\r\n\r\n', 1)
                        method = request.split(b' ')[0]; methods.append(method)
                        cseq = next(line.split(b':', 1)[1].strip() for line in request.split(b'\r\n') if line.lower().startswith(b'cseq:'))
                        body, headers = b'', b''
                        if method == b'DESCRIBE':
                            body = (b'v=0\r\nm=video 0 RTP/AVP 96\r\na=rtpmap:96 H264/90000\r\na=fmtp:96 packetization-mode=1;sprop-parameter-sets='
                                    + base64.b64encode(SPS) + b',' + base64.b64encode(PPS) + b'\r\na=framesize:96 1920-1080\r\na=control:trackID=1\r\n')
                            headers = b'Content-Type: application/sdp\r\nContent-Base: rtsp://127.0.0.1/stream1/\r\n'
                        if method == b'SETUP':
                            headers = b'Session: fixture\r\nTransport: RTP/AVP/TCP;unicast;interleaved=0-1\r\n'
                        conn.sendall(b'RTSP/1.0 200 OK\r\nCSeq: ' + cseq + b'\r\n' + headers + b'Content-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
                        if method == b'PLAY':
                            self.assertTrue(bound.is_set()); playing = True
                        if method == b'TEARDOWN':
                            return
                    if playing:
                        sequence += 1
                        payload = (b'\x65' if sequence % 5 == 0 else b'\x61') + b'camera-payload'
                        packet = struct.pack('!BBHII', 128, 224, sequence, sequence * 3600, 777) + payload
                        conn.sendall(b'$\0' + struct.pack('!H', len(packet)) + packet)

        def udp_peer():
            endpoint = None
            while not stop.is_set():
                try:
                    data, peer = udp.recvfrom(8192)
                except socket.timeout:
                    continue
                if endpoint is None:
                    endpoint = peer
                self.assertEqual(peer, endpoint, 'binding and media must share a connected socket')
                if data[1] == 204:
                    self.assertEqual(data[48:], hmac.digest(KEY, data[:48], 'sha256'))
                    if data[12] == 1:
                        challenge = bytearray(data); challenge[32:48] = b'server-nonce-1234'
                        udp.sendto(signed(challenge, 2), peer)
                    elif data[12] == 3:
                        bound.set(); udp.sendto(signed(data, 4), peer)
                else:
                    self.assertTrue(bound.is_set())
                    self.assertEqual(data[1] & 127, 102)
                    self.assertEqual(struct.unpack('!I', data[8:12])[0], 70001)
                    packets.append(data)

        token = self.root / 'publication-token'; token.write_text('fixture-service-key\n')
        config = self.root / 'publication.json'
        config.write_text(json.dumps(dict(node_id='liza-rtsp', service_id='liza-rtsp', source_ref='stream1', camera_ip='127.0.0.1', camera_port=camera.getsockname()[1], camera_url='rtsp://127.0.0.1/stream1', vg_ip='127.0.0.1', vg_peer='localhost', vg_port=tcp.getsockname()[1], ca_file=str(self.root / 'ca.pem'), service_token_file=str(token), run_ms=5000)))
        threads = [threading.Thread(target=checked(fn), daemon=True) for fn in (tls_peer, camera_peer, udp_peer)]
        for thread in threads:
            thread.start()
        process = subprocess.Popen([str(exe), str(config)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            done = (reconnected if can_loss else complete).wait(10)
            stdout, stderr = process.communicate(timeout=7)
            self.assertFalse(errors, repr(errors) + repr((process.returncode, stdout, stderr, events, methods)))
            self.assertTrue(done, stdout + stderr)
            self.assertEqual(process.returncode, 0, stdout + stderr)
            self.assertEqual([event['status'] for event in events], ['accepted', 'running'] if can_loss else ['accepted', 'running', 'cancelled'])
            if can_loss:
                self.assertEqual(len(packets), media_at_reconnect[0])
                self.assertIn(b'CAN session generation=2', stdout)
            else:
                self.assertIn(b'TEARDOWN', methods)
            self.assertEqual(packets[0][12:], SPS); self.assertEqual(packets[1][12:], PPS)
            self.assertEqual(packets[2][12:], b'\x65camera-payload')
            self.assertNotIn(b'fixture-job-token', stdout + stderr)
        finally:
            stop.set()
            if process.poll() is None:
                process.kill(); process.communicate()
            tcp.close(); camera.close(); udp.close()
            for thread in threads:
                thread.join(2)

    def test_scoped_publication_binding_media_and_cancellation(self):
        for exe in self.clients:
            with self.subTest(exe=exe.name):
                self.publication(exe)

    def test_can_loss_discards_assignment_before_reconnect(self):
        for exe in self.clients:
            with self.subTest(exe=exe.name):
                self.publication(exe, can_loss=True)
