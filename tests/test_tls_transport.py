"""TLS-A optional native adapter acceptance. LIZA_TEST_TLS=1 requires OpenSSL 3."""
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('LIZA_TEST_TLS') == '1', 'Optional TLS-A: set LIZA_TEST_TLS=1')
class TlsTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ssl.HAS_TLSv1_3:
            raise RuntimeError('TLS-A acceptance needs Python ssl with TLS 1.3 support')
        cls.temp = tempfile.TemporaryDirectory(prefix='liza-tls-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        prefix = os.environ.get('LIZA_OPENSSL_PREFIX')
        if not prefix and sys.platform == 'darwin':
            prefix = subprocess.check_output(['brew', '--prefix', 'openssl@3'], text=True).strip()
        cls.prefix = Path(prefix) if prefix else None
        cls.openssl = str(cls.prefix/'bin/openssl') if cls.prefix and sys.platform != 'win32' else shutil.which('openssl')
        if cls.prefix and sys.platform == 'win32':
            for candidate in (cls.prefix/'tools/openssl/openssl.exe', cls.prefix/'bin/openssl.exe'):
                if candidate.exists():
                    cls.openssl = str(candidate)
                    break
        if not cls.openssl:
            raise RuntimeError('OpenSSL CLI required for local test certificates')
        if cls.prefix:
            os.environ['PATH'] = str(cls.prefix/'bin') + os.pathsep + os.environ.get('PATH', '')
        if cls.prefix and sys.platform == 'win32':
            flags = ['-I'+str(cls.prefix/'include'), str(cls.prefix/'lib/libssl.lib'), str(cls.prefix/'lib/libcrypto.lib')]
        elif cls.prefix:
            flags = ['-I'+str(cls.prefix/'include'), '-L'+str(cls.prefix/'lib'), '-Wl,-rpath,'+str(cls.prefix/'lib'), '-lssl', '-lcrypto']
        else:
            flags = subprocess.check_output(['pkg-config', '--cflags', '--libs', 'openssl'], text=True).split()
        (cls.root/'req.cnf').write_text('[req]\ndistinguished_name=dn\n[dn]\nCN=Liza fixture\n')
        cls.command('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-subj', '/CN=Liza TLS Test CA', '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign', '-days', '2', '-keyout', 'ca.key', '-out', 'ca.pem')
        cls.command('req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-subj', '/CN=Unrelated CA', '-addext', 'basicConstraints=critical,CA:TRUE', '-addext', 'keyUsage=critical,keyCertSign,cRLSign', '-days', '2', '-keyout', 'other.key', '-out', 'other.pem')
        cls.command('req', '-new', '-newkey', 'rsa:2048', '-nodes', '-subj', '/CN=localhost', '-keyout', 'server.key', '-out', 'server.csr')
        (cls.root/'server.ext').write_text('basicConstraints=critical,CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\nsubjectAltName=DNS:localhost,IP:127.0.0.1\n')
        cls.command('x509', '-req', '-in', 'server.csr', '-CA', 'ca.pem', '-CAkey', 'ca.key', '-CAcreateserial', '-days', '1', '-extfile', 'server.ext', '-out', 'server.pem')
        (cls.root/'index').write_text('')
        (cls.root/'serial').write_text('01\n')
        (cls.root/'ca.cnf').write_text('[ca]\ndefault_ca=liza\n[liza]\ndatabase=index\nnew_certs_dir=.\ncertificate=ca.pem\nprivate_key=ca.key\nserial=serial\ndefault_md=sha256\npolicy=policy\n[policy]\ncommonName=supplied\n')
        cls.command('ca', '-config', 'ca.cnf', '-batch', '-notext', '-in', 'server.csr', '-out', 'expired.pem', '-startdate', '20200101000000Z', '-enddate', '20200102000000Z', '-extfile', 'server.ext')
        cls.executables = []
        for opt in ('0', '2'):
            exe = cls.root/('probe'+opt+('.exe' if sys.platform == 'win32' else ''))
            cmd = ['clang', '-std=c11', '-O'+opt, '-Wall', '-Wextra', '-Werror',
                   str(ROOT/'tests/native/tls_transport.c'), str(ROOT/'liza/runtime/tls_openssl.c'),
                   str(ROOT/'liza/runtime'/('net_windows.c' if sys.platform == 'win32' else 'net_posix.c')),
                   *flags, '-o', str(exe)]
            cmd += ['-lws2_32'] if sys.platform == 'win32' else ['-pthread']
            built = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if built.returncode:
                raise RuntimeError(built.stdout+built.stderr)
            cls.executables.append(exe)

    @classmethod
    def command(cls, *args):
        env = dict(os.environ, OPENSSL_CONF=str(cls.root/'req.cnf'))
        run = subprocess.run([cls.openssl, *args], cwd=cls.root, env=env, capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise RuntimeError(run.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_boundary_and_memory_transport_versions(self):
        for exe in self.executables:
            cases = [('boundary', 'ca.pem'),
                     ('memory', 'ca.pem', 'server.pem', 'server.key', '771'),
                     ('memory', 'ca.pem', 'server.pem', 'server.key', '772')]
            for args in cases:
                paths = [str(self.root/a) if a.endswith(('.pem', '.key')) else a for a in args]
                run = subprocess.run([str(exe), *paths], capture_output=True, text=True, timeout=15)
                self.assertEqual(run.returncode, 0, run.stdout+run.stderr)
                print(run.stdout.strip(), flush=True)

    def session(self, exe, peer='localhost', ca='ca.pem', cert='server.pem', mode='echo', expected=0, version=ssl.TLSVersion.TLSv1_3, verify=None):
        errors, names = [], []
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version = version
        ctx.maximum_version = version
        ctx.load_cert_chain(self.root/cert, self.root/'server.key')
        ctx.set_servername_callback(lambda sock, name, context: names.append(name))
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0));listener.listen(1);listener.settimeout(10)
            port = listener.getsockname()[1]

            def serve():
                try:
                    with listener.accept()[0] as conn:
                        conn.settimeout(10)
                        if mode == 'timeout':
                            while conn.recv(8192):
                                pass
                            return
                        with ctx.wrap_socket(conn, server_side=True) as secure:
                            message = bytearray()
                            while len(message) < len(b'TLS-A reactor echo'):
                                block = secure.recv(128)
                                if not block:
                                    break
                                message.extend(block)
                            if expected and mode != 'eof':
                                self.assertEqual(message, b'')
                                return
                            self.assertEqual(message, b'TLS-A reactor echo')
                            if mode == 'eof':
                                # TCP EOF without TLS close_notify must fail.
                                fd = secure.detach()
                                socket.socket(fileno=fd).close()
                                return
                            secure.sendall(message)
                            raw = secure.unwrap()
                            raw.close()
                except (ssl.SSLError, ConnectionError) as exc:
                    if not expected:
                        errors.append(exc)
                except BaseException as exc:
                    errors.append(exc)

            thread = threading.Thread(target=serve, daemon=True);thread.start()
            run = subprocess.run([str(exe), 'network', str(self.root/ca), peer, str(port), mode], capture_output=True, text=True, timeout=12)
            thread.join(11)
            self.assertFalse(thread.is_alive())
            if errors:
                self.fail(str(errors[0])+'\nclient: '+run.stdout+run.stderr)
            self.assertEqual(run.returncode, expected, run.stdout+run.stderr)
            print(run.stdout.strip(), flush=True)
            if verify is not None:
                self.assertIn('failure status=4 verify='+str(verify)+'\n', run.stdout)
            if expected == 0:
                self.assertEqual(names, [None if peer == '127.0.0.1' else peer])

    def test_real_reactor_echo_identity_and_close(self):
        for exe in self.executables:
            for version in (ssl.TLSVersion.TLSv1_2, ssl.TLSVersion.TLSv1_3):
                self.session(exe, version=version)
            self.session(exe, peer='127.0.0.1')

    def test_reject_authentication_errors_deadline_and_unclean_eof(self):
        for exe in self.executables:
            self.session(exe, peer='wrong.invalid', expected=4, verify=62)
            self.session(exe, peer='127.0.0.2', expected=4, verify=64)
            self.session(exe, ca='other.pem', expected=4, verify=20)
            self.session(exe, cert='expired.pem', expected=4, verify=10)
            self.session(exe, mode='timeout', expected=5)
            self.session(exe, mode='eof', expected=4)


if __name__ == '__main__':
    unittest.main()
