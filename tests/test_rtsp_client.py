"""Independent RTSP, ordinary VG WSS and authenticated UDP wire peers."""
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
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
        if os.environ.get('LIZA_RTSP_RELEASE'):
            cls.clients.append(Path(os.environ['LIZA_RTSP_RELEASE']).resolve())
            return
        for opt in ('0', '2'):
            folder = cls.root / ('rtsp' + opt)
            folder.mkdir()
            cls.clients.append(build(ROOT / 'examples/apps/liza_rtsp.liza', folder, opt, ROOT / 'examples'))

    def scenario(self, exe, bad_cseq=False, drop_after=None, payload_bytes=b'camera-payload', run_ms=4000, stop_on_media=False,
                 cycles=1, stall_keepalive=False, stop_delay=6, drop_wss=False, wrong_peer=False,
                 stall_teardown=False, reject_login=False, client_version=617, required_version=None, service=None,
                 stop_payload=None, ignored_control=(), stop_during_camera_timeout=False, clock_jump=False, keyframe_feedback=None, rtp_pace_ms=0, camera_interval=.03, binding_delay=0, control_reconnect_delay=0, vg_resume_quiet_ms=0, echo_cleanup=False):
        errors, packets, methods, commands = [], [], [], []
        packet_times = []
        stopped = threading.Event()
        moderation_observed = threading.Event()
        live_stderr = self.root / 'live-stderr.log'
        media_seen = [threading.Event() for _ in range(cycles)]
        binding_confirmed = [threading.Event() for _ in range(cycles)]
        binding_confirmed_at = [None for _ in range(cycles)]
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
                conn.settimeout(camera_interval)
                pending = b''
                playing = False
                sequence = 0
                force_idr = False
                feedback_seen = []
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
                    while pending:
                        if pending[0] == 36:
                            if len(pending) < 4:
                                break
                            length = int.from_bytes(pending[2:4], 'big')
                            if len(pending) < length + 4:
                                break
                            self.assertEqual(pending[1], 1)
                            compound, pending = pending[4:4+length], pending[4+length:]
                            self.assertIn(length, (40, 48))
                            self.assertEqual(compound[:4], b'\x80\xc9\0\1')
                            sender = struct.unpack('!I', compound[4:8])[0]
                            self.assertNotIn(sender, (0, 777))
                            self.assertEqual(compound[8:12], b'\x81\xca\0\4')
                            self.assertEqual(compound[12:16], compound[4:8])
                            self.assertEqual(compound[16:28], b'\x01\x09liza-rtsp\0')
                            feedback = compound[28:]
                            self.assertEqual(feedback[4:8], compound[4:8])
                            if length == 40:
                                self.assertEqual(feedback[:4], b'\x81\xce\0\2')
                                self.assertEqual(struct.unpack('!I', feedback[8:12])[0], 777)
                                mode = 'pli'
                            else:
                                self.assertEqual(feedback[:4], b'\x84\xce\0\4')
                                self.assertEqual(feedback[8:12], b'\0'*4)
                                self.assertEqual(struct.unpack('!I', feedback[12:16])[0], 777)
                                self.assertEqual(feedback[17:], b'\0'*3)
                                mode = 'fir'
                            feedback_seen.append((mode, time.monotonic()))
                            history['feedback'] = feedback_seen
                            if mode == keyframe_feedback:
                                force_idr = True
                            continue
                        if b'\r\n\r\n' not in pending:
                            break
                        request, pending = pending.split(b'\r\n\r\n', 1)
                        method = request.split(b' ', 1)[0]
                        if method == b'PLAY':
                            self.assertTrue(binding_confirmed[epoch].is_set(), 'camera PLAY before VG binding confirmation')
                        methods.append(method)
                        history['methods'].append(method)
                        cseq = next(line.split(b':', 1)[1].strip() for line in request.split(b'\r\n') if line.lower().startswith(b'cseq:'))
                        history['cseqs'].append(int(cseq))
                        if stall_keepalive and epoch==0 and method==b'GET_PARAMETER':
                            continue  # RTP continues, but the control reply never arrives.
                        if stall_teardown and method==b'TEARDOWN':
                            continue
                        if echo_cleanup and epoch==0 and method==b'TEARDOWN':
                            continue
                        if stop_during_camera_timeout and method==b'TEARDOWN':
                            self.assertTrue(moderation_observed.wait(3), 'stop command ignored during camera cleanup')
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
                    if playing and not ((stop_during_camera_timeout or (echo_cleanup and epoch==0)) and sequence>=35):
                        sequence += 1
                        # Every fifth packet is an IDR; payload must survive unchanged.
                        is_idr = force_idr or (sequence % 5 == 0 and (not keyframe_feedback or not epoch_packets[epoch]))
                        force_idr = False
                        payload = (b'\x65' if is_idr else b'\x61') + payload_bytes
                        timestamp = (sequence * 3600 + (1916186809 if clock_jump and sequence >= 20 else 0)) % (1 << 32)
                        packet = struct.pack('!BBHII', 128, 224, sequence, timestamp, 777) + payload
                        record = b'$\0' + struct.pack('!H', len(packet)) + packet
                        conn.sendall(record[:3])
                        conn.sendall(record[3:] + b'$\1\0\4\x80\xc8\0\0')
                        if drop_after is not None and (epoch==0 or epoch<cycles-1) and sequence == drop_after:
                            return

        def camera_peer():
            for _ in range(1 if drop_wss else cycles):
                try:
                    camera_session()
                except (ConnectionResetError,BrokenPipeError,ConnectionAbortedError):
                    if not (stall_keepalive or stall_teardown or drop_wss or echo_cleanup):
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
                        if (stall_teardown or echo_cleanup) and str(error)=='premature EOF':
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
                        result=2 if reject_login else 1
                        if required_version is not None and value['connect_request']['client_version']<required_version:
                            result=3  # VideoGrace UpdateRequired; not a transport failure.
                        conn.sendall(message({'connect_response': {'result': result, 'id': 123}}))
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
                        if ignored_control:
                            self.assertTrue(media_seen[epoch].wait(5), 'no media before unrelated control')
                            before = len(epoch_packets[epoch])
                            for payload in ignored_control:
                                conn.sendall(ws(payload))
                            until = time.monotonic() + 3
                            while len(epoch_packets[epoch]) < before + 30 and time.monotonic() < until:
                                time.sleep(.01)
                            self.assertGreaterEqual(len(epoch_packets[epoch]), before + 30,
                                                    'unrelated control stopped publication')
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
                            self.assertTrue(media_seen[epoch].wait(5+(vg_resume_quiet_ms/1000 if epoch else 0)), 'no authorized media')
                            # Exercise TLS beyond the old zero-duration + 5 s
                            # lifetime, then stop through the existing control API.
                            time.sleep(stop_delay)
                            conn.sendall(ws(stop_payload) if stop_payload is not None else message({'device_disconnect': {'device_id': 7}}))
                    elif 'device_disconnect' in value and echo_cleanup:
                        conn.sendall(message({'device_disconnect': {'device_id': 7}}))
                    elif 'device_disconnect' in value and stop_during_camera_timeout:
                        conn.sendall(message({'member_action': {'id': [], 'action': 9}}))
                        until = time.monotonic() + 3
                        while time.monotonic() < until:
                            if b'moderator requested disconnect' in live_stderr.read_bytes():
                                moderation_observed.set()
                                break
                            time.sleep(.01)
                        self.assertTrue(moderation_observed.is_set(), 'moderator stop was ignored after camera timeout')

        def control_peer():
            for epoch in range(cycles):
                if epoch:
                    time.sleep(control_reconnect_delay)
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
                        if not binding_confirmed[epoch].is_set():
                            time.sleep(binding_delay)
                            binding_confirmed_at[epoch]=time.monotonic()
                        binding_confirmed[epoch].set()
                        udp.sendto(signed(data, 4, epoch_key(epoch)), source)
                else:
                    packets.append(data)
                    packet_times.append(time.monotonic())
                    epoch=struct.unpack('!I', data[8:12])[0]-456
                    self.assertIn(epoch,range(cycles))
                    epoch_packets[epoch].append(data)
                    if len(epoch_packets[epoch])>=10:media_seen[epoch].set()
                    if keyframe_feedback and len(epoch_packets[epoch]) == 12:
                        request = struct.pack('!BBHII8s', 128, 204, 4, 999, 1, bytes(8))
                        # Native APP's source is the receiver (999), not author 456.
                        # Wrong port and malformed messages must not create requests.
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as alien:
                            alien.sendto(request, source)
                        udp.sendto(request[:-1], source)
                        udp.sendto(request[:8] + struct.pack('!I', 2) + request[12:], source)
                        for _ in range(20):
                            udp.sendto(request, source)


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
        config['client_version']=client_version
        config['rtp_pace_ms']=rtp_pace_ms
        config['vg_resume_quiet_ms']=vg_resume_quiet_ms
        if wrong_peer:
            config['vg_peer']='wrong.example'
        path = self.root / 'rtsp-config.json'
        path.write_text(json.dumps(config))
        path.chmod(0o600)
        command = [str(exe), str(path)]
        if service:
            state = self.root / 'service-state'
            state.mkdir(mode=0o700)
            self.service_samples = []
            def observe_status():
                while not stopped.wait(.05):
                    try:
                        self.service_samples.append(json.loads((state / 'status.json').read_text()))
                    except FileNotFoundError:
                        pass
            threads.append(threading.Thread(target=guarded, args=(observe_status,), daemon=True))
            command = [str(service), str(exe), str(path), str(state), 'fixture']
        for thread in threads:
            thread.start()
        try:
            try:
                if stop_during_camera_timeout:
                    with live_stderr.open('wb') as stream:
                        run = subprocess.run(command, stdout=subprocess.PIPE, stderr=stream, timeout=20)
                    run.stderr = live_stderr.read_bytes()
                else:
                    run = subprocess.run(command, capture_output=True, timeout=45 if stall_keepalive else 20)
            except subprocess.TimeoutExpired as error:
                self.fail(('client timeout',error.stdout,error.stderr,errors,camera_runs,commands,[len(p) for p in epoch_packets]))
        finally:
            self.process_finished_at = time.monotonic()
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
        self.packet_times = packet_times
        self.binding_confirmed_at = binding_confirmed_at
        return run, packets, methods, commands

    @unittest.skipUnless(os.environ.get('LIZA_RTSP_SERVICE_BINARY'), 'bundled operational launcher acceptance')
    def test_operational_launcher_observes_live_generation_and_media(self):
        run, packets, methods, commands = self.scenario(self.clients[0], run_ms=8500,
                                                       service=Path(os.environ['LIZA_RTSP_SERVICE_BINARY']))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertGreater(len(packets), 10)
        active = [s for s in self.service_samples if s['state'] == 'Running']
        self.assertTrue(active, self.service_samples)
        self.assertTrue(all(s['generation'] == 1 and s['send_accepted'] > 0 for s in active))
        self.assertNotIn('fixture-password', (self.root / 'service-state/service.log').read_text())

    def test_publish_and_cleanup(self):
        for exe in self.clients:
            with self.subTest(exe=exe.name):
                run, packets, methods, commands = self.scenario(exe, run_ms=6500)
                self.assertEqual(run.returncode, 0, (run.stdout, run.stderr))
                health = re.findall(rb'LIZA_RTSP_HEALTH ready=1 received=(\d+) sent=(\d+) input_age_ms=(\d+) output_age_ms=(\d+)', run.stderr)
                self.assertTrue(health, run.stderr)
                latest = list(map(int, health[-1]))
                self.assertGreater(latest[0], 0)
                self.assertGreater(latest[1], 0)
                self.assertLess(latest[2], 5000)
                self.assertLess(latest[3], 5000)
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

    def test_paced_media_preserves_rtp_and_bounds_burst_rate(self):
        for exe in self.clients:
            with self.subTest(exe=exe.name):
                run, packets, methods, _ = self.scenario(exe, rtp_pace_ms=1, camera_interval=.0005, run_ms=1800)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn(b'RTP media send pacing enabled: wait_ms=1', run.stderr)
                self.assertGreater(len(packets), 20)
                self.assertGreater(self.packet_times[-1]-self.packet_times[0], (len(packets)-1)*.00075)
                sequences = [struct.unpack('!H', packet[2:4])[0] for packet in packets]
                for previous, current in zip(sequences, sequences[1:]):
                    self.assertEqual(current, (previous+1) % 65536)
                for packet in packets:
                    self.assertIn(packet[12:], (SPS, PPS, b'\x61camera-payload', b'\x65camera-payload'))
                self.assertIn(b'TEARDOWN', methods)

    def test_moderator_stop_cancels_pending_keyframe_fallback(self):
        for exe in self.clients:
            with self.subTest(exe=exe.name):
                run, packets, methods, _ = self.scenario(exe, keyframe_feedback='ignore', run_ms=0,
                                                        stop_on_media=True, stop_delay=.4)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn(b'Camera keyframe PLI queued', run.stderr)
                self.assertNotIn(b'Camera keyframe FIR queued', run.stderr)
                self.assertNotIn(b'keyframe request timed out', run.stderr)
                self.assertEqual(methods.count(b'PLAY'), 1)
                self.assertIn(b'TEARDOWN', methods)

    def test_camera_feedback_partial_tcp_writes_and_wouldblock(self):
        if os.environ.get('LIZA_RTSP_RELEASE'):
            self.skipTest('requires instrumented reactor build')
        stub = self.root / 'feedback-reactor.c'
        header = json.dumps((ROOT / 'liza/runtime/reactor_common.h').as_posix())
        stub.write_text('#include <stdio.h>\n#define liza_rt_reactor_write real_reactor_write\n#include ' + header + '''\n#undef liza_rt_reactor_write
uint64_t liza_rt_reactor_write(reactor *r,uint64_t owner,uint64_t generation,uint64_t slot,const uint8_t *data,uint32_t length,uint32_t start,uint32_t count) {
    static unsigned attempts;
    if (length>=2 && data[0]==36 && data[1]==1) {
        if (!attempts) fputs("RTCP_WRITE_STUB short+WouldBlock\\n",stderr);
        if ((attempts++ % 3)==0) return net_failure(4);
        if (count>3) count=3;
    }
    return real_reactor_write(r,owner,generation,slot,data,length,start,count);
}
''')
        for opt in ('0', '2'):
            with self.subTest(opt=opt):
                folder = self.root / ('feedback-partial' + opt)
                folder.mkdir()
                exe = build(ROOT / 'examples/apps/liza_rtsp.liza', folder, opt, ROOT / 'examples', reactor_stub=stub)
                run, packets, methods, _ = self.scenario(exe, keyframe_feedback='pli', run_ms=4500)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn(b'RTCP_WRITE_STUB short+WouldBlock', run.stderr)
                self.assertIn(b'Camera IDR observed after keyframe request', run.stderr)
                self.assertEqual(methods.count(b'PLAY'), 1)
                self.assertGreater(len(packets), 20)

    def test_vg_keyframe_feedback_reaches_camera_and_observes_idr(self):
        for mode in ('pli', 'fir', 'ignore'):
            for exe in self.clients:
                with self.subTest(mode=mode, exe=exe.name):
                    run, packets, methods, _ = self.scenario(exe, keyframe_feedback=mode, run_ms=4500)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertIn(b'Camera keyframe PLI queued', run.stderr)
                    self.assertEqual(run.stderr.count(b'Camera keyframe PLI queued'), 1)
                    self.assertEqual(methods.count(b'PLAY'), 1)
                    if mode == 'pli':
                        self.assertNotIn(b'Camera keyframe FIR queued', run.stderr)
                    else:
                        self.assertEqual(run.stderr.count(b'Camera keyframe FIR queued'), 1)
                    if mode == 'ignore':
                        self.assertIn(b'Camera keyframe request timed out', run.stderr)
                        self.assertNotIn(b'Camera IDR observed after', run.stderr)
                    else:
                        self.assertIn(b'Camera IDR observed after', run.stderr)
                        idrs = [i for i, packet in enumerate(packets) if packet[12:] == b'\x65camera-payload']
                        self.assertGreaterEqual(len(idrs), 2)
                        for i in idrs:
                            self.assertGreaterEqual(i, 2)
                            self.assertEqual([packet[12:] for packet in packets[i-2:i]], [SPS, PPS])

                    self.assertIn(b'vg_requests=20 coalesced=19', run.stderr)
                    self.assertGreater(len(packets), 20)

    def test_clock_anomaly_is_logged_without_rewriting_or_reconnecting(self):
        for exe in self.clients:
            with self.subTest(exe=exe.name):
                run, packets, methods, _ = self.scenario(exe, clock_jump=True, run_ms=2000)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertIn(b'RTP anomaly: clock_jump', run.stderr)
                self.assertIn(b'clock_jumps=1', run.stderr)
                timestamps = [struct.unpack('!I', packet[4:8])[0] for packet in packets]
                self.assertIn(20 * 3600 + 1916186809, timestamps)
                self.assertIn(21 * 3600 + 1916186809, timestamps)
                self.assertEqual(methods.count(b'PLAY'), 1)
                for packet in packets:
                    self.assertIn(packet[12:], (SPS, PPS, b'\x61camera-payload', b'\x65camera-payload'))

    def test_wrong_cseq_rejected(self):
        for exe in self.clients:
            run, packets, methods, commands = self.scenario(exe, bad_cseq=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertFalse(packets)
            self.assertEqual(methods, [b'OPTIONS'])
            self.assertNotIn(b'RTSP reconnect',run.stderr)

    def test_moderator_and_server_stop_commands_are_terminal(self):
        # Engine/Proto/CmdMemberAction.cpp forwards action=9 to the selected
        # connection with id:[], not the moderator's original target list.
        cases = [
            (b'{"member_action":{"id":[],"action":9,"actor_id":456,"actor_name":"moderator"}}', b'moderator requested disconnect'),
            (b'{"disconnect_from_conference"}', b'requested disconnect from conference'),
            (b'{"disconnect"}', b'requested session disconnect'),
            (b'{"disconnect_from_conference":{}}', b'requested disconnect from conference'),
        ]
        for exe in self.clients:
            for payload, reason in cases:
                with self.subTest(exe=exe.name, payload=payload):
                    run, packets, methods, commands = self.scenario(exe, run_ms=0, stop_on_media=True,
                                                                   stop_delay=.1, stop_payload=payload)
                    self.assertEqual(run.returncode, 0, (run.stdout, run.stderr))
                    self.assertGreater(len(packets), 10)
                    self.assertIn(reason, run.stderr)
                    self.assertIn(b'without reconnect', run.stderr)
                    self.assertNotIn(b'RTSP reconnect', run.stderr)
                    self.assertNotIn(b'generation=2', run.stdout)
                    self.assertEqual(commands.count('connect_request'), 1)
                    self.assertIn(b'TEARDOWN', methods)
                    self.assertIn('device_disconnect', commands)
                    self.assertIn('disconnect_from_conference', commands)

    def test_moderation_ack_and_other_device_do_not_stop_publication(self):
        for exe in self.clients:
            run, packets, methods, commands = self.scenario(
                exe, run_ms=0, stop_on_media=True, stop_delay=.1,
                stop_payload=b'{"member_action":{"id":[],"action":9}}',
                ignored_control=(b'{"member_action":{"id":[],"action":9,"result":1}}',
                                 b'{"member_action":{"id":[],"action":11}}',
                                 b'{"device_disconnect":{"device_id":999}}'))
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertGreater(len(packets), 40)
            self.assertIn(b'moderator requested disconnect', run.stderr)
            self.assertNotIn(b'RTSP reconnect', run.stderr)

    def test_moderator_stop_wins_during_camera_timeout_cleanup(self):
        for exe in self.clients:
            run, packets, methods, commands = self.scenario(exe, run_ms=0, stop_during_camera_timeout=True)
            self.assertEqual(run.returncode, 0, (run.stdout, run.stderr))
            self.assertGreater(len(packets), 10)
            self.assertIn(b'TEARDOWN', methods)
            self.assertIn(b'moderator requested disconnect', run.stderr)
            self.assertNotIn(b'RTSP reconnect', run.stderr)
            self.assertNotIn(b'generation=2', run.stdout)

    def recovered(self, exe, **fault):
        run,packets,methods,commands=self.scenario(exe,cycles=2,run_ms=0,stop_on_media=True,stop_delay=.2,**fault)
        self.assertEqual(run.returncode,0,(run.stdout,run.stderr))
        camera,control,epochs=self.attempts
        preserved=bool(fault.get('drop_wss'))
        self.assertEqual(len(camera),1 if preserved else 2)
        self.assertEqual(len(control),2)
        self.assertEqual(commands.count('connect_request'),2)
        self.assertEqual(commands.count('device_connect'),2)
        if preserved:
            self.assertIn(b'camera RTSP session preserved',run.stderr)
            self.assertEqual(methods.count(b'PLAY'),1)
            self.assertEqual(methods.count(b'TEARDOWN'),1)
        else:
            self.assertIn(b'RTSP session generation=2',run.stdout)
        self.assertNotIn(b'RTSP session generation=3',run.stdout)
        self.assertIn(b'delay_ms=1000',run.stderr)
        if not preserved:
            self.assertGreaterEqual(camera[1]['started']-camera[0]['started'],1)
        for epoch in range(2):
            if not preserved:
                self.assertEqual(camera[epoch]['cseqs'][0],1)
            self.assertGreaterEqual(len(epochs[epoch]),10)
            self.assertEqual([p[12:] for p in epochs[epoch][:3]],[SPS,PPS,b'\x65'+fault.get('payload_bytes',b'camera-payload')])
            self.assertEqual(struct.unpack('!H',epochs[epoch][0][2:4])[0],1)
        return run

    def test_paced_reconnect_and_moderator_stop(self):
        for exe in self.clients:
            run = self.recovered(exe, drop_after=35, rtp_pace_ms=1)
            self.assertEqual(run.stderr.count(b'RTP media send pacing enabled: wait_ms=1'), 2)

    def test_camera_disconnect_reconnects_with_fresh_binding_and_idr(self):
        for exe in self.clients:
            run=self.recovered(exe,drop_after=35)
            self.assertIn(b'after error 35',run.stderr)

    def test_own_device_removal_echo_does_not_cancel_camera_recovery(self):
        for exe in self.clients:
            run=self.recovered(exe,echo_cleanup=True)
            self.assertIn(b'Camera removal acknowledged during local cleanup',run.stderr)
            # Only the final explicit stop of the recovered publication is terminal.
            self.assertEqual(run.stderr.count(b'VideoGrace requested removal of this camera'),1)
            self.assertLess(run.stderr.index(b'Camera removal acknowledged during local cleanup'),
                            run.stderr.index(b'RTSP reconnect after error'))

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

    def test_camera_is_drained_during_vg_backoff_without_rtsp_restart(self):
        for exe in self.clients:
            run=self.recovered(exe,drop_wss='reset',control_reconnect_delay=2,
                               payload_bytes=b'x'*1300,camera_interval=.004)
            counts=[int(n) for n in re.findall(rb'Camera packets drained without VG publication=(\d+)',run.stderr)]
            self.assertTrue(counts,run.stderr)
            self.assertGreater(max(counts),30,run.stderr)

    def test_global_deadline_stops_preserved_camera_during_vg_outage(self):
        for exe in self.clients:
            run, packets, methods, commands=self.scenario(
                exe,drop_wss='reset',run_ms=1600)
            # The global budget may report the last transport failure during an outage.
            self.assertIn(run.returncode,(0,43),(run.stdout,run.stderr))
            self.assertEqual(methods.count(b'PLAY'),1)
            self.assertEqual(methods.count(b'TEARDOWN'),1)

    def test_experimental_ten_second_media_quiet_period_preserves_camera(self):
        for exe in self.clients:
            run,packets,methods,commands=self.scenario(
                exe,drop_wss='reset',cycles=2,run_ms=0,stop_on_media=True,
                stop_delay=.2,vg_resume_quiet_ms=10000,camera_interval=.01)
            self.assertEqual(run.returncode,0,(run.stdout,run.stderr))
            first={}
            for packet,stamp in zip(packets,self.packet_times):
                first.setdefault(struct.unpack('!I',packet[8:12])[0],stamp)
            self.assertLess(first[456]-self.binding_confirmed_at[0],2)
            self.assertGreaterEqual(first[457]-self.binding_confirmed_at[1],9.99)
            self.assertLess(first[457]-self.binding_confirmed_at[1],13)
            self.assertEqual(methods.count(b'PLAY'),1)
            self.assertEqual(methods.count(b'TEARDOWN'),1)
            self.assertEqual(len(self.attempts[0]),1)
            counts=[int(n) for n in re.findall(rb'quiet period ended; drained camera packets=(\d+)',run.stderr)]
            self.assertTrue(counts,run.stderr)
            self.assertGreater(counts[0],100)
            self.assertEqual([p[12:] for p in self.attempts[2][1][:3]],[SPS,PPS,b'\x65camera-payload'])
            self.assertNotRegex(run.stderr,rb'RTP anomaly:[^\n]*\bpacket_pause\b')
            self.assertNotRegex(run.stderr,rb'RTP anomaly:[^\n]*\bsequence_discontinuity\b')

    def test_deadline_ends_media_quiet_period_without_publication(self):
        for exe in self.clients:
            run,packets,methods,commands=self.scenario(
                # The budget includes two TLS/VGB1 handshakes and reconnect
                # backoff. Leave startup margin on shared runners while the
                # 10 s quiet period still outlasts the entire 7 s run budget.
                exe,drop_wss='reset',cycles=2,run_ms=7000,vg_resume_quiet_ms=10000)
            self.assertEqual(run.returncode,0,(run.stdout,run.stderr))
            self.assertIsNotNone(self.binding_confirmed_at[1],run.stderr)
            self.assertLess(self.process_finished_at-self.binding_confirmed_at[1],10)
            self.assertFalse(self.attempts[2][1])
            self.assertIn(b'Experimental RTP quiet period after VG binding',run.stderr)
            self.assertNotIn(b'quiet period ended',run.stderr)
            self.assertEqual(methods.count(b'TEARDOWN'),1)

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
            self.assertFalse(methods, 'RTSP commands sent before authenticated VG session')
            self.assertIn(b'TLS verification',run.stderr)
            self.assertNotIn(b'RTSP reconnect',run.stderr)

    def test_login_rejection_is_fatal_without_retry(self):
        for exe in self.clients:
            run,packets,methods,commands=self.scenario(exe,reject_login=True,run_ms=0)
            self.assertNotEqual(run.returncode,0)
            self.assertIn(b'invalid login or password',run.stderr)
            self.assertFalse(packets)
            self.assertFalse(methods, 'RTSP commands sent before accepted VG login')
            self.assertEqual(commands.count('connect_request'),1)
            self.assertNotIn(b'RTSP reconnect',run.stderr)

    def test_camera_play_waits_for_binding_after_wss_reset(self):
        for exe in self.clients:
            run, packets, methods, commands = self.scenario(
                exe, cycles=2, drop_wss='reset', run_ms=0,
                stop_on_media=True, stop_delay=.2, binding_delay=.3)
            self.assertEqual(run.returncode, 0, (run.stdout, run.stderr))
            self.assertEqual(methods.count(b'PLAY'), 1)
            self.assertEqual(methods.count(b'TEARDOWN'), 1)
            self.assertTrue(all(len(epoch) >= 10 for epoch in self.attempts[2]))

    def test_server_version_upgrade_needs_updated_client_configuration(self):
        for exe in self.clients:
            run,packets,methods,commands=self.scenario(exe,client_version=617,required_version=618,run_ms=0)
            self.assertEqual(run.returncode,20,(run.stdout,run.stderr))
            self.assertIn(b'UpdateRequired',run.stderr)
            self.assertIn(b'client_version=617',run.stderr)
            self.assertIn(b'update client_version in config and restart',run.stderr)
            self.assertFalse(packets)
            self.assertNotIn(b'RTSP reconnect',run.stderr)
            run,packets,methods,commands=self.scenario(exe,client_version=618,required_version=618,run_ms=1000)
            self.assertEqual(run.returncode,0,(run.stdout,run.stderr))
            self.assertGreater(len(packets),10)

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
            starts=[int(value) for value in re.findall(rb'RTSP session generation=\d+ uptime_ms=(\d+)',run.stdout)]
            pauses=[(int(delay),int(at)) for delay,at in re.findall(rb'RTSP reconnect after error \d+ delay_ms=(\d+) uptime_ms=(\d+)',run.stderr)]
            # Windows can spend ~2 s refusing a TCP connect. The budget limits
            # time and attempt spacing, not an OS-independent attempt count.
            self.assertGreaterEqual(len(starts),1,(run.stdout,run.stderr))
            self.assertLessEqual(len(starts),3,(run.stdout,run.stderr))
            self.assertTrue(all(at<3500 for at in starts),starts)
            for index,(delay,at) in enumerate(pauses):
                self.assertEqual(delay,(1000,2000,4000)[index])
            for index,at in enumerate(starts[1:]):
                self.assertLess(index,len(pauses))
                self.assertGreaterEqual(at,pauses[index][1]+pauses[index][0])

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
