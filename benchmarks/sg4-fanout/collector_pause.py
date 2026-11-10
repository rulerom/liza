#!/usr/bin/env python3
"""Explicit synthetic 500ms recorder pause; not a filesystem fault or baseline."""
import argparse,json,os,subprocess
from pathlib import Path
from build import HERE,sha
from run import trial
from collector_ab import udp

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():p.error('fresh output required')
 old=json.loads((a.baseline/'report.json').read_text());a.output.mkdir(parents=True)
 bins={k:(a.baseline/'build'/k).resolve() for k in ('c','liza','collector')}
 if sha(bins['c'])!=old['build']['binary_sha256']['c']:raise RuntimeError('service binary changed')
 binary=(a.output/'collector_pause').resolve();cmd=['clang','-std=c11','-O2','-g','-DSG4_COLLECTOR_TESTING','-I'+str((a.baseline/'build').resolve()),str(HERE/'collector_ab.c'),'-o',str(binary)]
 subprocess.run(cmd,check=True);bins['collector']=binary
 report={'status':'incomplete','test_pause_ms':500,'test_pause_ordinal':12700,'build_command':cmd,'collector_sha256':sha(binary),'baseline_build':old['build'],'source_sha256':{n:sha(HERE/n) for n in ('collector_ab.c','collector_pause.py','run.py')},'limits':['Synthetic nanosleep inside recorder stage, not an actual file I/O failure.','Matching signature supports the mechanism but cannot establish the historical pause cause.','Kernel counters are system-wide and include background traffic.']}
 try:
  before=udp();row=trial(bins,'c',5000,5,old['build']['ports'],a.output/'case',archive_level=1,collector_env=dict(os.environ,SG4_COLLECTOR_MODE='file',SG4_COLLECTOR_TEST_PAUSE_SEQ='12700'),collector_finished=udp)
  if not row['collector']['test_pause_injected']:raise RuntimeError('pause was not reached')
  after=row['collector_exit_observation'];row.update(kernel_before=before,kernel_after=after,kernel_delta={k:after['fields'][k]-v for k,v in before['fields'].items()})
  report.update(status='measured',samples=[row]);print('gap',row['delivery_gap_from_local_success'],'kernel full',row['kernel_delta']['dropped due to full socket buffers'],'store max ms',row['collector']['timing']['store']['max_ns']/1e6)
 except Exception as exc:report['error']=repr(exc);raise
 finally:(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
