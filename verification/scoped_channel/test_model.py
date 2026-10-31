import itertools
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from model import State,Ring,step,ring_step,logical_queue,linearize

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ACTIONS=[('send',0),('send',1),('receive',None),('close_sender',None),('close_receiver',None)]

class ModelTests(unittest.TestCase):
    def test_bounded_transition_equivalence_and_conservation(self):
        for cap in (1,2):
            seen={(State(),Ring((None,)*cap))}
            for depth in range(7):
                next_states=set(seen)
                for abstract,ring in seen:
                    self.assertEqual(abstract.queue,logical_queue(ring))
                    self.assertEqual(abstract.published,abstract.received+abstract.discarded+len(abstract.queue))
                    self.assertEqual((abstract.published,abstract.received,abstract.discarded),(ring.published,ring.received,ring.discarded))
                    self.assertTrue(0<=ring.head<cap and 0<=ring.tail<cap and 0<=ring.count<=cap)
                    for op,arg in ACTIONS:
                        a,ar=step(abstract,cap,op,arg);b,br=ring_step(ring,op,arg)
                        self.assertEqual(ar,br)
                        self.assertEqual(a.queue,logical_queue(b))
                        next_states.add((a,b))
                seen=next_states
            self.assertGreater(len(seen),10)
            print('capacity',cap,'reachable state pairs',len(seen),'up to depth 7',flush=True)
    def test_linearizer_obeys_real_time(self):
        h=[{'op':'send','arg':3,'result':'ok','start':0,'end':1},
           {'op':'receive','result':'ok:3','start':2,'end':3}]
        self.assertEqual(linearize(h,1),(0,1))
        h[0]['start'],h[0]['end']=2,3;h[1]['start'],h[1]['end']=0,1
        self.assertIsNone(linearize(h,1))
        h[0]['start'],h[0]['end']=0,3;h[1]['start'],h[1]['end']=1,2
        self.assertEqual(linearize(h,1),(0,1))
    def test_mutations_yield_counterexample(self):
        for mutation in ('publication','fifo','closed_priority','release'):
            found=None
            for cap in (1,2):
                for depth in range(1,6):
                    for actions in itertools.product(ACTIONS,repeat=depth):
                        ring=Ring((None,)*cap);history=[]
                        for i,(op,arg) in enumerate(actions):
                            ring,result=ring_step(ring,op,arg,mutation)
                            history.append({'op':op,'arg':arg,'result':result,'start':2*i,'end':2*i+1})
                        if linearize(history,cap) is None:
                            found=(cap,history);break
                    if found:break
                if found:break
            self.assertIsNotNone(found,mutation)
            print('mutation',mutation,'counterexample',found,flush=True)

@unittest.skipUnless(shutil.which('clang'),'Clang required')
class RuntimeHistoryTests(unittest.TestCase):
    def test_selected_runtime_histories(self):
        with tempfile.TemporaryDirectory(prefix='liza-channel-history-') as tmp:
            exe=Path(tmp)/('trace.exe' if sys.platform=='win32' else 'trace')
            cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'liza/runtime'),str(HERE/'trace.c'),str(ROOT/'liza/runtime/scoped_channel_core.c'),'-o',str(exe)]
            if sys.platform!='win32':cmd.append('-pthread')
            b=subprocess.run(cmd,text=True,capture_output=True,timeout=30)
            self.assertEqual(b.returncode,0,b.stdout+b.stderr)
            r=subprocess.run([str(exe)],text=True,capture_output=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
            groups=r.stdout.strip().split('trace ')[1:]
            self.assertEqual(len(groups),200)
            for trace in groups:
                rows=trace.splitlines()[1:];self.assertEqual(len(rows),14)
                operations={}
                for row in rows:
                    seq,phase,ident,kind,arg,result=map(int,row.split())
                    h=operations.setdefault(ident,{'op':('send','receive','close_sender','close_receiver')[kind]})
                    if phase==0:h.update(start=seq,arg=arg)
                    else:
                        h['end']=seq
                        h['result']=('ok','full','empty','closed')[result] if kind in (0,1) else ('ok' if kind==2 else 'discard:'+str(arg))
                        if kind==1 and result==0:h['result']='ok:'+str(arg)
                history=[operations[i] for i in sorted(operations)]
                self.assertIsNotNone(linearize(history,2),history)
if __name__=='__main__':unittest.main()
