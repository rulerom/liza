"""Application acceptance: real RTP identity, independent stop/fault, bounded recording."""
import importlib.util,json,os,socket,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from build import build,SSRC,WARMUP
from run import analyze,reserve,trial
spec=importlib.util.spec_from_file_location('dual_packet_generator',Path(__file__).with_name('generator.py'))
gen=importlib.util.module_from_spec(spec);spec.loader.exec_module(gen)

@unittest.skipUnless(sys.platform in ('darwin','linux'),'POSIX workload; runtime platform coverage belongs to B1')
class DualOwners(unittest.TestCase):
    def test_real_workload_and_isolation(self):
        with tempfile.TemporaryDirectory(prefix='liza-dual-') as tmp:
            tmp=Path(tmp);ports=reserve(2);bins,manifest=build(tmp/'build',ports)
            results=[]
            for variant,scenario in [('single','capacity'),('dual','capacity'),('dual','stop'),('dual','fault')]:
                row=trial(bins,manifest,variant,[200,200],1,tmp/(variant+'_'+scenario),scenario,probe_invalid=(variant=='dual' and scenario=='capacity'));results.append(row)
                self.assertEqual(row['status'],'measured')
                for stream in row['streams']:
                    self.assertEqual(stream['input_shortfall'],0)
                    self.assertEqual(stream['coverage_offered'],1)
                    self.assertEqual(stream['failed_local_sends'],0)
                    self.assertEqual(stream['delivery_gap_from_local_success'],0)
                if row['invalid_probe']:
                    unclassified=next(e for e in row['events'] if e['event']=='unclassified' and e['owner']==0)
                    self.assertEqual((unclassified['invalid'],unclassified['filtered'],unclassified['truncated']),(4,2,1))
                if scenario!='capacity':
                    self.assertGreater(row['streams'][1]['offered_after_peer_destroy_copies_observed'],0)
                    self.assertEqual(row['streams'][1]['after_peer_destroy_coverage_offered'],1)
                    self.assertNotEqual(row['owner_results'][0]['generation'],row['owner_results'][1]['generation'])
            self.assertEqual(manifest['binary_sha256'],{k:__import__('build').sha(v) for k,v in bins.items()})
            # A recorder failure must fail the trial, never appear as UDP loss.
            with patch.dict(os.environ,{'SG4_COLLECTOR_RECORD_LIMIT':'1'}):
                with self.assertRaisesRegex(RuntimeError,'collector failed'):
                    trial(bins,manifest,'dual',[200,200],1,tmp/'overflow',collector_mode='memory')
            self.assertEqual(json.loads((tmp/'overflow/report.json').read_text())['status'],'incomplete')

    def test_record_identity_and_accounting_rejections(self):
        self.assertNotEqual(gen.packet(10,SSRC[0]),gen.packet(10,SSRC[1]))
        self.assertEqual(gen.packet(10,SSRC[0])[:8],gen.packet(10,SSRC[1])[:8])
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'records.bin';record=struct.Struct('=QIHH')
            generator={'times_ns':[1]*(WARMUP+1),'phases':[{}, {'start_ns':1,'end_ns':1000000001}],'errors':[],'user_s':0,'system_s':0}
            collector={'received':1,'records_stored':1,'measurement_valid':True,'record_overflow':False,'invalid':0,'duplicates':0,'user_s':0,'system_s':0}
            metrics={'succeeded':1,'valid':1,'attempted':1,'failed':0,'unique':1}
            for stamp,ordinal,receiver,port in [(2,WARMUP,0,1234),(2,WARMUP,1,4321)]:
                f.write_bytes(record.pack(stamp,ordinal,receiver,port))
                with self.assertRaisesRegex(RuntimeError,'delivery identity'):analyze(f,generator,collector,metrics,4321,1)
            f.write_bytes(record.pack(2,WARMUP,0,4321));collector['record_overflow']=True
            with self.assertRaisesRegex(RuntimeError,'collector failure'):analyze(f,generator,collector,metrics,4321,1)
if __name__=='__main__':unittest.main()
