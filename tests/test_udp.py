"""UDP resources, datagram boundaries and actual loopback traffic."""
from pathlib import Path
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'examples/apps/udp_echo.liza'

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class UdpNative(unittest.TestCase):
    def test_resource_rejects_leak_and_copy(self):
        programs = (
            "fn main()->u32:io {match net.udp_bind(net.ipv4(127,0,0,1,0)) {Err(e)=>{return 0} Ok(s)=>{return 0}}}",
            "fn main()->u32:io {match net.udp_bind(net.ipv4(127,0,0,1,0)) {Err(e)=>{return 0} Ok(s)=>{other=copy s;return 0}}}",
        )
        with tempfile.TemporaryDirectory(prefix='liza-udp-invalid-') as tmp:
            for index, source in enumerate(programs):
                path=Path(tmp)/('invalid'+str(index)+'.liza');path.write_text(source)
                result=subprocess.run([sys.executable,'-m','liza','check',str(path)],cwd=ROOT,capture_output=True,text=True,timeout=20)
                self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIn('resource',result.stderr.lower())

    def test_echo_empty_exact_and_truncation(self):
        with tempfile.TemporaryDirectory(prefix='liza-udp-') as tmp:
            for opt in ('0','2'):
                with self.subTest(opt=opt):
                    exe=Path(tmp)/('udp-'+opt+('.exe' if sys.platform=='win32' else ''))
                    build=subprocess.run([sys.executable,'-m','liza','build',str(APP),'-O',opt,'-o',str(exe)],cwd=ROOT,capture_output=True,text=True,timeout=60)
                    self.assertEqual(build.returncode,0,build.stdout+build.stderr)
                    proc=subprocess.Popen([str(exe)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                    try:
                        q=queue.Queue();threading.Thread(target=lambda:q.put(proc.stdout.readline()),daemon=True).start()
                        port=int(q.get(timeout=10).strip())
                        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as client:
                            client.bind(('127.0.0.1',0));client.settimeout(4)
                            for data in (b'',b'12345678'):
                                client.sendto(data,('127.0.0.1',port))
                                result,source=client.recvfrom(128)
                                self.assertEqual(result,data);self.assertEqual(source[1],port)
                            client.sendto(b'123456789',('127.0.0.1',port))
                            out,err=proc.communicate(timeout=10)
                            self.assertEqual(proc.returncode,0,out+err)
                            client.settimeout(.1)
                            with self.assertRaises(socket.timeout):client.recvfrom(128)
                    finally:
                        if proc.poll() is None:proc.kill();proc.communicate()

if __name__=='__main__':unittest.main()
