"""Real UDP integration for the bounded RTP fanout application."""
from pathlib import Path
import queue
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import unittest

ROOT=Path(__file__).resolve().parents[1]
APP=ROOT/'examples/apps/rtp_fanout.liza'

def packet(ssrc,seq):
    return struct.pack('!BBHII',0x80,96,seq,42,ssrc)+b'payload'

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class FanoutNative(unittest.TestCase):
    def test_routes_valid_rtp_and_rejects_invalid(self):
        with tempfile.TemporaryDirectory(prefix='liza-fanout-') as tmp:
            for opt in ('0','2'):
                with self.subTest(opt=opt):
                    exe=Path(tmp)/('fanout'+opt+('.exe' if sys.platform=='win32' else ''))
                    built=subprocess.run([sys.executable,'-m','liza','build',str(APP),'-O',opt,'-o',str(exe)],cwd=ROOT,text=True,capture_output=True,timeout=60)
                    self.assertEqual(built.returncode,0,built.stdout+built.stderr)
                    receivers=[socket.socket(socket.AF_INET,socket.SOCK_DGRAM) for _ in range(2)]
                    for r in receivers:r.bind(('127.0.0.1',0));r.settimeout(5)
                    args=[str(exe),'6','42',*[str(r.getsockname()[1]) for r in receivers]]
                    p=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                    try:
                        q=queue.Queue();threading.Thread(target=lambda:q.put(p.stdout.readline()),daemon=True).start()
                        port=int(q.get(timeout=10).strip())
                        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
                            good1=packet(42,1);good2=packet(42,2)
                            inputs=[good1,packet(99,3),b'bad',bytes([0x90,96])+b'\0'*10, b'x'*2049,good2]
                            for data in inputs:sender.sendto(data,('127.0.0.1',port))
                        out,err=p.communicate(timeout=10)
                        self.assertEqual(p.returncode,0,out+err)
                        for r in receivers:
                            self.assertEqual(r.recvfrom(4096)[0],good1)
                            self.assertEqual(r.recvfrom(4096)[0],good2)
                            r.settimeout(.1)
                            with self.assertRaises(socket.timeout):r.recvfrom(4096)
                    finally:
                        if p.poll() is None:p.kill();p.communicate()
                        for r in receivers:r.close()
    def test_invalid_arguments_fail_before_binding(self):
        with tempfile.TemporaryDirectory(prefix='liza-fanout-') as tmp:
            exe=Path(tmp)/('fanout.exe' if sys.platform=='win32' else 'fanout')
            built=subprocess.run([sys.executable,'-m','liza','build',str(APP),'-O','2','-o',str(exe)],cwd=ROOT,text=True,capture_output=True,timeout=60)
            self.assertEqual(built.returncode,0,built.stdout+built.stderr)
            for args in ([],['0','42','9000'],['1','42','0'],['1','42','65536'],['1','4294967296','9000']):
                result=subprocess.run([str(exe),*args],text=True,capture_output=True,timeout=5)
                self.assertEqual(result.returncode,2,(args,result.stdout,result.stderr))
                self.assertEqual(result.stdout,'')

if __name__=='__main__':unittest.main()
