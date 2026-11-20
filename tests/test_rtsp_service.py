"""macOS operational acceptance: real child lifecycle, bounded logging and staged upgrades."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

try:
    import pwd
except ImportError:
    pwd = None

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'packaging/macos/rtsp'
spec = importlib.util.spec_from_file_location('rtsp_control', SOURCE / 'control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


@unittest.skipUnless(sys.platform == 'darwin', 'macOS service packaging')
class RtspService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='liza-service-')
        cls.folder = Path(cls.temporary.name)
        cls.supervisor = cls.folder / 'service'
        subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(SOURCE / 'service.c'), '-o', str(cls.supervisor)], check=True, capture_output=True)
        cls.child = cls.folder / 'child'
        cls.child.write_text('#!' + sys.executable + '\n' + r'''
import json, os, signal, sys, time
mode=json.load(open(sys.argv[1]))['mode']
if mode=='fatal':
    print('VG login rejected: check configured credentials', flush=True)
    sys.exit(20)
if mode=='crash':
    os.kill(os.getpid(), signal.SIGKILL)
if mode=='hang':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
if mode=='flood':
    for _ in range(6000):
        print('x'*1000)
    print('y'*10000, flush=True)
    sys.exit(20)
if mode=='reconnect':
    print('RTSP session generation=1 uptime_ms=0', flush=True)
    print('LIZA_RTSP_HEALTH ready=1 received=10 sent=9 input_age_ms=0 output_age_ms=0', flush=True)
    time.sleep(1.5)
    print('RTSP reconnect after error 43 delay_ms=1000 uptime_ms=1500: network unavailable', flush=True)
    time.sleep(2)
    print('RTSP session generation=2 uptime_ms=3500', flush=True)
if mode in ('active', 'reconnect'):
    print('LIZA_RTSP_HEALTH ready=1 received=20 sent=19 input_age_ms=0 output_age_ms=0', flush=True)
while True:
    time.sleep(.1)
''')
        cls.child.chmod(0o755)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.folder)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'
        self.state.mkdir(mode=0o700)
        self.config = self.root / 'config.json'
        self.procs = []
        self.addCleanup(self.stop_children)

    def stop_children(self):
        for p in self.procs:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    p.kill(); p.wait()

    def start(self, mode):
        self.config.write_text(json.dumps({'mode': mode, 'password': 'test-secret-never-log'}))
        self.config.chmod(0o600)
        p = subprocess.Popen([str(self.supervisor), str(self.child), str(self.config), str(self.state), 'release-1'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.procs.append(p)
        return p

    def wait_status(self, wanted, generation=None, timeout=6):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            try:
                value = json.loads((self.state / 'status.json').read_text())
                if value['state'] == wanted and (generation is None or value['generation'] == generation):
                    return value
            except FileNotFoundError:
                pass
            time.sleep(.03)
        self.fail('status did not become ' + wanted)

    def test_active_reconnect_and_independent_generations(self):
        p = self.start('reconnect')
        first = self.wait_status('Running', 1)
        self.assertEqual(first['send_accepted'], 9)
        self.wait_status('Recovering', 1)
        second = self.wait_status('Running', 2)
        self.assertEqual(second['send_accepted'], 19)
        p.terminate(); self.assertEqual(p.wait(10), 0)
        stopped = self.wait_status('Stopped')
        self.assertEqual(stopped['child_pid'], 0)
        with self.assertRaises(ProcessLookupError):
            os.kill(second['child_pid'], 0)

    def test_binding_or_live_process_does_not_imply_running(self):
        p = self.start('idle')
        self.wait_status('Recovering')
        time.sleep(1.2)
        self.assertEqual(json.loads((self.state / 'status.json').read_text())['state'], 'Recovering')
        p.terminate(); self.assertEqual(p.wait(10), 0)

    def test_fatal_latches_and_returns_success_to_launchd(self):
        p = self.start('fatal')
        self.assertEqual(p.wait(5), 0)
        value = self.wait_status('Attention required')
        self.assertEqual(value['exit_code'], 20)
        log = (self.state / 'service.log').read_text()
        self.assertNotIn('test-secret-never-log', log)
        original = (self.state / 'service.log').stat().st_size
        p = self.start('active')
        self.assertEqual(p.wait(5), 0)
        self.assertEqual((self.state / 'service.log').stat().st_size, original)
        self.assertEqual(self.wait_status('Attention required')['child_pid'], 0)
        self.assertEqual(self.wait_status('Attention required')['exit_code'], 20)

    def test_signal_crash_is_restartable(self):
        p = self.start('crash')
        self.assertEqual(p.wait(5), 1)
        self.assertFalse((self.state / 'attention').exists())
        self.assertEqual(self.wait_status('Recovering')['reason'], 'child_crashed')

    def test_sigterm_has_bounded_kill_and_reap(self):
        p = self.start('hang')
        child = self.wait_status('Recovering')['child_pid']
        while child == 0:
            time.sleep(.1)
            child = self.wait_status('Recovering')['child_pid']
        time.sleep(.2)  # child installs SIG_IGN before the operator stop
        started = time.monotonic(); p.terminate()
        self.assertEqual(p.wait(11), 0)
        self.assertLess(time.monotonic() - started, 10)
        with self.assertRaises(ProcessLookupError):
            os.kill(child, 0)

    def test_logs_rotate_with_bounded_disk_and_lines(self):
        p = self.start('flood')
        self.assertEqual(p.wait(15), 0)
        logs = list(self.state.glob('service.log*'))
        self.assertEqual(len(logs), 4)
        self.assertLessEqual(sum(path.stat().st_size for path in logs), 4 * 1024 * 1024)
        self.assertLessEqual(max(len(line) for path in logs for line in path.read_bytes().splitlines()), 2100)

    def test_private_configuration_and_symlink_rejection(self):
        self.config.write_text('{}'); self.config.chmod(0o644)
        p = subprocess.run([str(self.supervisor), str(self.child), str(self.config), str(self.state), 'release-1'], timeout=5)
        self.assertEqual(p.returncode, 0)
        self.assertEqual(self.wait_status('Attention required')['reason'], 'configuration_permissions')
        (self.state / 'attention').unlink()
        victim = self.root / 'victim'; victim.write_text('preserved')
        (self.state / '.status.tmp').symlink_to(victim)
        self.assertEqual(self.start('active').wait(5), 0)
        self.assertEqual(victim.read_text(), 'preserved')

    def bundle(self, release):
        bundle = self.root / release; bundle.mkdir()
        files = {}
        for name in ('bin/liza-rtsp', 'bin/liza-rtsp-service', 'lib/libssl.3.dylib', 'lib/libcrypto.3.dylib',
                     'licenses/Liza.txt', 'licenses/OpenSSL.txt', 'rtspctl.py'):
            target = bundle / name; target.parent.mkdir(exist_ok=True)
            target.write_text(release + name)
            files[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        (bundle / 'manifest.json').write_text(json.dumps({'schema': 1, 'release': release, 'dirty': False,
                                                       'architecture': platform.machine(), 'files': files}))
        return bundle

    def service_config(self):
        data = {'camera_ip': '192.0.2.20', 'camera_url': 'rtsp://192.0.2.20/stream1', 'vg_ip': '192.0.2.10',
                'vg_peer': 'demo.example.org', 'login': 'fixture', 'password': 'private-fixture',
                'conference': 'radio', 'client_version': 618, 'run_ms': 0}
        self.config.write_text(json.dumps(data)); self.config.chmod(0o600)
        return self.config.read_bytes()

    def test_staged_install_upgrade_rollback_and_permissions(self):
        config = self.service_config()
        service = control.Service('test', self.root / 'staging')
        first, second = self.bundle('first'), self.bundle('second')
        service.install(first, pwd.getpwuid(os.getuid()).pw_name, self.config)
        secret = service.root / 'config/config.json'
        self.assertEqual(secret.stat().st_mode & 0o777, 0o600)
        plist = plistlib.loads(service.plist.read_bytes())
        self.assertEqual(plist['KeepAlive'], {'SuccessfulExit': False})
        self.assertTrue(plist['RunAtLoad'])
        self.assertEqual(plist['ExitTimeOut'], 12)
        self.assertFalse(plist['AbandonProcessGroup'])
        self.assertNotIn('private-fixture', service.plist.read_text())
        self.assertNotIn('private-fixture', (service.root / 'releases/first/manifest.json').read_text())
        service.install(second)
        self.assertEqual(secret.read_bytes(), config)
        self.assertEqual(os.readlink(service.root / 'previous'), 'releases/first')
        service.select('first')
        self.assertEqual(os.readlink(service.root / 'current'), 'releases/first')
        self.assertEqual(os.readlink(service.root / 'previous'), 'releases/second')
        third = self.bundle('third')
        with self.assertRaisesRegex(ValueError, 'two releases'):
            service.install(third)
        self.assertEqual(secret.read_bytes(), config)

    def test_rtp_packet_size_configuration_bounds(self):
        config = json.loads(self.service_config())
        for value in (0, 256, 1200, 1472):
            config['rtp_max_packet_bytes'] = value
            control.validate_config(json.dumps(config).encode())
        for value in (1, 255, 1473, True, .5, '1200', None):
            config['rtp_max_packet_bytes'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                control.validate_config(json.dumps(config).encode())

    def test_rtp_pacing_configuration_bounds(self):
        config = json.loads(self.service_config())
        control.validate_config(json.dumps(config).encode())
        for value in (0, 1, 5):
            config['rtp_pace_ms'] = value
            control.validate_config(json.dumps(config).encode())
        for value in (-1, 6, True, .5, '1', None):
            config['rtp_pace_ms'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                control.validate_config(json.dumps(config).encode())

    def test_checksums_symlinks_and_invalid_config_fail_closed(self):
        config = self.service_config()
        bundle = self.bundle('release')
        (bundle / 'bin/liza-rtsp').write_text('tampered')
        service = control.Service('test', self.root / 'staging')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            service.install(bundle, pwd.getpwuid(os.getuid()).pw_name, self.config)
        self.assertFalse(service.root.exists())
        for invalid in (config.replace(b'"run_ms": 0', b'"run_ms": 60000'),
                        b'{"password":"TOP-SECRET","password":"duplicate"}', b'null'):
            with self.assertRaises(ValueError) as caught:
                control.validate_config(invalid)
            self.assertNotIn('TOP-SECRET', str(caught.exception))
        with self.assertRaises(ValueError):
            control.Service('../../escape', self.root)

    def test_cli_uninstall_preserves_config_and_status(self):
        config = self.service_config(); stage = self.root / 'staging'
        service = control.Service('test', stage)
        service.install(self.bundle('first'), pwd.getpwuid(os.getuid()).pw_name, self.config)
        (service.root / 'state/status.json').write_text('{"state":"Stopped","child_pid":0}')
        subprocess.run([sys.executable, str(SOURCE / 'control.py'), '--instance', 'test', '--staging', str(stage),
                        'uninstall'], check=True, capture_output=True)
        self.assertEqual((service.root / 'config/config.json').read_bytes(), config)
        self.assertTrue((service.root / 'state/status.json').exists())
        self.assertFalse(service.plist.exists())
        self.assertFalse((service.root / 'releases').exists())

    @unittest.skipUnless(os.environ.get('LIZA_TEST_LAUNCHD') == '1', 'explicit isolated launchd acceptance')
    def test_launchd_fatal_is_not_restarted_and_crash_is_restarted(self):
        domain = os.environ.get('LIZA_TEST_LAUNCHD_DOMAIN', 'gui/' + str(os.getuid()))
        prefix = ['sudo', '-n'] if domain == 'system' else []
        label = 'ru.liza.fixture.' + str(os.getpid())
        target = domain + '/' + label
        plist = self.root / 'fixture.plist'
        self.config.write_text('{"mode":"fatal"}'); self.config.chmod(0o600)
        properties = {
            'Label': label,
            'ProgramArguments': [str(self.supervisor), str(self.child), str(self.config), str(self.state), 'fixture'],
            'RunAtLoad': True, 'KeepAlive': {'SuccessfulExit': False}, 'ThrottleInterval': 1,
            'ExitTimeOut': 12, 'AbandonProcessGroup': False,
        }
        if domain == 'system':
            properties['UserName'] = pwd.getpwuid(os.getuid()).pw_name
        plist.write_bytes(plistlib.dumps(properties))
        plist.chmod(0o644)
        if domain == 'system':
            subprocess.run(['sudo', '-n', 'chown', 'root:wheel', str(plist)], check=True)
        def launch(*args):
            result = subprocess.run([*prefix, '/bin/launchctl', *args], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result
        def runs():
            text = launch('print', target).stdout
            match = re.search(r'\bruns = (\d+)', text)
            self.assertIsNotNone(match)
            return int(match.group(1))
        launch('bootstrap', domain, str(plist))
        try:
            self.wait_status('Attention required')
            before = runs(); time.sleep(3)
            self.assertEqual(runs(), before, 'fatal exit must not restart the job')
            launch('bootout', target)
            (self.state / 'attention').unlink()
            self.config.write_text('{"mode":"crash"}')
            launch('bootstrap', domain, str(plist))
            until = time.monotonic() + 15
            while runs() < 2 and time.monotonic() < until:
                time.sleep(.1)
            self.assertGreaterEqual(runs(), 2, 'signal crash must restart the job')
            self.config.write_text('{"mode":"active"}')
            active = self.wait_status('Running', timeout=10)
            old_child = active['child_pid']
            launch('kill', 'SIGKILL', target)
            until = time.monotonic() + 6
            while time.monotonic() < until:
                try:
                    os.kill(old_child, 0)
                except ProcessLookupError:
                    break
                time.sleep(.1)
            else:
                self.fail('child survived supervisor crash under launchd')
        finally:
            subprocess.run([*prefix, '/bin/launchctl', 'bootout', target], capture_output=True)


if __name__ == '__main__':
    unittest.main()
