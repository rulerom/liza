"""Check separate control pipe, phase counters, and unchanged UDP bytes."""
import queue,socket,struct,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
import nb1b_build
ROOT=Path(__file__).resolve().parents[2]

@unittest.skipIf(sys.platform=='win32','experimental POSIX control adapter')
class Control(unittest.TestCase):
    def test_independent_pipe_and_drain(self):
        with tempfile.TemporaryDirectory(prefix='liza-nb1b-test-') as temp:
            root=Path(temp);variants={'liza':root/'liza','c':root/'c'}
            nb1b_build.build(ROOT,variants['liza'])
            subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DNB1B_CONTROL',str(ROOT/'benchmarks/udp-fanout/fanout.c'),'-o',str(variants['c'])],check=True)
            for kind,exe in variants.items():
                with self.subTest(kind=kind),socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as dest:
                    dest.bind(('127.0.0.1',0));dest.settimeout(5)
                    p=subprocess.Popen([str(exe),'1000','42',str(dest.getsockname()[1])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                    try:
                        port=int(p.stdout.readline());data=struct.pack('!BBHII',128,96,1,0,42)+b'abc'
                        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
                            sender.sendto(data,('127.0.0.1',port));self.assertEqual(dest.recvfrom(100)[0],data)
                            p.stdin.write('D');p.stdin.flush();self.assertEqual(p.stdout.readline().strip(),'PHASE')
                            # The old marker is now ordinary invalid data, never control.
                            sender.sendto(b'LZSTOP01',('127.0.0.1',port))
                            sender.sendto(data,('127.0.0.1',port));self.assertEqual(dest.recvfrom(100)[0],data)
                            p.stdin.write('S');p.stdin.flush();out,err=p.communicate(timeout=5)
                        self.assertEqual(p.returncode,0,out+err)
                        m={k:int(v) for k,v in (line.split('=') for line in err.splitlines())}
                        self.assertEqual(m['phase_seen'],1);self.assertEqual(m['phase_received'],1)
                        self.assertEqual(m['received'],3);self.assertEqual(m['accepted_valid'],2)
                        self.assertEqual(m['invalid'],1);self.assertEqual(m['send_succeeded'],2)
                        self.assertEqual(m['stop_reason'],1)
                    finally:
                        if p.poll() is None:p.kill();p.communicate()
