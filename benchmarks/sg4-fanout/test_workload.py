"""Functional acceptance, including explicit test-only send failure injection."""
import importlib.util,json,socket,struct,subprocess,sys,tempfile,time,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from build import build,WARMUP
from run import line,stop
from generator import packet

class Workload(unittest.TestCase):
    def test_same_callbacks_corpus_and_send_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            for inject in (False,True):
                sockets=[]
                try:
                    for _ in range(2):
                        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));s.settimeout(2);sockets.append(s)
                    ports=[s.getsockname()[1] for s in sockets]
                    bins,manifest=build(tmp/str(inject),ports,inject_send_failure=inject)
                    for variant in ('liza','c'):
                        with self.subTest(variant=variant,inject=inject):
                            p=subprocess.Popen([str(bins[variant])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                            sender=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
                            try:
                                ready=json.loads(line(p));dest=('127.0.0.1',ready['port'])
                                p.stdin.write('M');p.stdin.flush();self.assertEqual(json.loads(line(p))['phase'],1)
                                valid=packet(WARMUP)
                                invalid=bytearray(packet(WARMUP+1));invalid[0]=0
                                wrong=bytearray(packet(WARMUP+2));wrong[8:12]=struct.pack('!I',123)
                                for data in (valid,invalid,wrong,b'X'*4096,b''):sender.sendto(data,dest)
                                for index,s in enumerate(sockets):
                                    if inject and index==0:continue
                                    self.assertEqual(s.recv(2048),valid)
                                time.sleep(.1)
                                p.stdin.write('D');p.stdin.flush();self.assertEqual(json.loads(line(p))['phase'],2)
                                time.sleep(.1);p.stdin.write('S');p.stdin.flush()
                                out,err=p.communicate(timeout=10);self.assertEqual(p.returncode,0,out+err)
                                m=json.loads(out)
                                self.assertEqual((m['received'],m['valid'],m['invalid'],m['wrong_ssrc'],m['truncated']),(5,1,2,1,1))
                                self.assertEqual((m['consumer'],m['attempted'],m['succeeded'],m['failed']),(1,2,1 if inject else 2,1 if inject else 0))
                                self.assertLessEqual(m['stop_ns'],m['stopping_ns']);self.assertLessEqual(m['stopping_ns'],m['finished_ns'])
                                for s in sockets:
                                    s.settimeout(.05)
                                    with self.assertRaises(socket.timeout):s.recv(2048)
                                    s.settimeout(2)
                            finally:sender.close();stop(p)
                finally:
                    for s in sockets:s.close()

    def test_short_driver_clock_and_accounting(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'run'
            p=subprocess.run([sys.executable,str(HERE/'run.py'),'--output',str(output),'--duration','.2','--rates','100','--receivers','2','--repeats','1'],capture_output=True,text=True,timeout=60)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            r=json.loads((output/'report.json').read_text());self.assertEqual(r['status'],'measured')
            for s in r['samples']:
                self.assertEqual(s['input_sent'],20);self.assertEqual(s['delivered_unique'],40)
                self.assertIsNotNone(s['latency_upper_ms']['p99'])
                self.assertLess(s['latency_upper_ms']['p99'],1000)
if __name__=='__main__':unittest.main()
