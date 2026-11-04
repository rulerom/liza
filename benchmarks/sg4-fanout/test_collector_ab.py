import gzip,hashlib,json,os,sys,socket,struct,subprocess,tempfile,time,unittest
from pathlib import Path
from run import line
from generator import packet
HERE=Path(__file__).resolve().parent

class CollectorAB(unittest.TestCase):
 def test_missing_identity_ranges(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);data=b''.join(struct.pack('=QIHH',*r) for r in [(200,200,0,32100),(201,200,1,32100),(210,201,1,32100),(220,202,0,32100),(221,202,1,32100)])
   (d/'records.bin.gz').write_bytes(gzip.compress(data))
   (d/'generator.json.gz').write_bytes(gzip.compress(json.dumps({'times_ns':[0]*200+[100,110,120]}).encode()))
   row={'per_receiver':[2,3],'input_sent':3,'delivered_unique':5,'ready':{'port':32100},'artifact_sha256':{'records.bin':hashlib.sha256(data).hexdigest()},'fanout':{k:0 for k in ('measure_ns','drain_ns','stop_ns','stopping_ns','finished_ns')}}
   (d/'report.json').write_text(json.dumps({'samples':[row]}))
   cmd=[sys.executable,str(HERE/'missing.py'),'--report',str(d/'report.json'),'--case',str(d),'--sample','0','--output',str(d/'missing.json')]
   subprocess.run(cmd,check=True,capture_output=True,text=True)
   audit=json.loads((d/'missing.json').read_text());self.assertEqual(audit['missing_total'],1)
   gap=audit['receivers'][0]['gaps'][0];self.assertEqual((gap['first'],gap['last'],gap['previous_observed_ns'],gap['next_observed_ns']),(201,201,200,220))
   self.assertEqual(audit['receivers'][1]['gaps'],[])
   row['artifact_sha256']['records.bin']='0'*64;(d/'report.json').write_text(json.dumps({'samples':[row]}))
   self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
 def test_identity_and_explicit_overflow(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);sockets=[]
   for _ in range(2):
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));sockets.append(s)
   ports=[s.getsockname()[1] for s in sockets]
   (d/'config.h').write_text('#define MAX_PACKETS 600000\n#define WARMUP 200\nstatic const unsigned short ports[]={'+','.join(map(str,ports))+'};\n')
   for name in ('collector','collector_ab','collector_ab_test'):
    subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(d)]+(['-DSG4_COLLECTOR_TESTING'] if name=='collector_ab_test' else [])+[str(HERE/(('collector_ab' if name=='collector_ab_test' else name)+'.c')),'-o',str(d/name)],check=True)
   for s in sockets:s.close()
   for mode in ('original','file','memory','overflow','pause'):
    env=dict(os.environ,SG4_COLLECTOR_MODE='memory' if mode in ('memory','overflow') else 'file')
    if mode=='overflow':env['SG4_COLLECTOR_RECORD_LIMIT']='1'
    if mode=='pause':env['SG4_COLLECTOR_TEST_PAUSE_SEQ']='0'
    raw=d/(mode+'.bin');meta=d/(mode+'.json')
    p=subprocess.Popen([str(d/('collector' if mode=='original' else 'collector_ab_test' if mode=='pause' else 'collector_ab')),'2','10',str(raw),str(meta)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:
     ready=json.loads(line(p));self.assertEqual(ready['ports'],ports)
     with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
      for port in ports:
       for seq in (0,1):sender.sendto(packet(seq),('127.0.0.1',port))
      if mode!='overflow':
       for data in (packet(0),b'',b'x'*4096,b'\0'+packet(2)[1:]):sender.sendto(data,('127.0.0.1',ports[0]))
     time.sleep(.7 if mode=='pause' else .1)
     if mode!='overflow':p.stdin.write('S');p.stdin.flush()
     stdout,stderr=p.communicate(timeout=5);m=json.loads(meta.read_text())
     if mode=='overflow':
      self.assertEqual(p.returncode,4);self.assertTrue(m['record_overflow']);self.assertFalse(m['measurement_valid']);self.assertEqual(m['records_stored'],1);self.assertEqual(len(raw.read_bytes()),16)
     else:
      self.assertEqual(p.returncode,0,stderr);self.assertEqual((m['received'],m['invalid'],m['duplicates']),(4,3,1))
      identities={(seq,receiver) for stamp,seq,receiver,port in struct.iter_unpack('=QIHH',raw.read_bytes())}
      self.assertEqual(identities,{(0,0),(1,0),(0,1),(1,1)})
      if mode!='original':
       self.assertTrue(m['measurement_valid']);self.assertEqual(m['records_stored'],4)
       if mode=='pause':
        self.assertTrue(m['test_pause_injected']);self.assertGreaterEqual(m['timing']['store']['max_ns'],450000000)
       self.assertTrue(all(x['pending_bytes_at_stop']==0 and x['poll_events_at_stop']==0 for x in m['receivers']))
    finally:
     if p.poll() is None:p.kill();p.communicate()
if __name__=='__main__':unittest.main()
