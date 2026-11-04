import json,os,socket,struct,subprocess,tempfile,time,unittest
from pathlib import Path
from run import line
from generator import packet
HERE=Path(__file__).resolve().parent

class CollectorAB(unittest.TestCase):
 def test_identity_and_explicit_overflow(self):
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);sockets=[]
   for _ in range(2):
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));sockets.append(s)
   ports=[s.getsockname()[1] for s in sockets]
   (d/'config.h').write_text('#define MAX_PACKETS 600000\n#define WARMUP 200\nstatic const unsigned short ports[]={'+','.join(map(str,ports))+'};\n')
   for name in ('collector','collector_ab'):
    subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(d),str(HERE/(name+'.c')),'-o',str(d/name)],check=True)
   for s in sockets:s.close()
   for mode in ('original','file','memory','overflow'):
    env=dict(os.environ,SG4_COLLECTOR_MODE='memory' if mode in ('memory','overflow') else 'file')
    if mode=='overflow':env['SG4_COLLECTOR_RECORD_LIMIT']='1'
    raw=d/(mode+'.bin');meta=d/(mode+'.json')
    p=subprocess.Popen([str(d/('collector' if mode=='original' else 'collector_ab')),'2','10',str(raw),str(meta)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:
     ready=json.loads(line(p));self.assertEqual(ready['ports'],ports)
     with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
      for port in ports:
       for seq in (0,1):sender.sendto(packet(seq),('127.0.0.1',port))
      if mode!='overflow':
       for data in (packet(0),b'',b'x'*4096,b'\0'+packet(2)[1:]):sender.sendto(data,('127.0.0.1',ports[0]))
     time.sleep(.1)
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
       self.assertTrue(all(x['pending_bytes_at_stop']==0 and x['poll_events_at_stop']==0 for x in m['receivers']))
    finally:
     if p.poll() is None:p.kill();p.communicate()
if __name__=='__main__':unittest.main()
