#!/usr/bin/env python3
"""Verify P3 accounting and the narrow optimized-IR guard observation."""
import argparse,json,re
from pathlib import Path

def verify(root):
 r=json.loads((root/'report.json').read_text());assert r['status']=='measured' and len(r['samples'])==180
 assert r['correctness']['status']=='passed' and r['correctness']['cases']==6785
 assert len(r['forwarded_fields'])==2
 for n in (x['name'] for x in r['workloads']):
  a=r['traffic']['default']['workloads'][n];b=r['traffic']['forward']['workloads'][n]
  assert a['input_bytes']==b['input_bytes']
  for k in ('overflow_intrinsics','conditional_transfers'):assert a[k]-b[k]==a['input_bytes']
  for k in ('state_loads','state_stores','load_spans','store_spans'):assert a[k]==b[k]
 for v,expected in [('default',True),('forward',False)]:
  ir=(root/v/'optimized.ll').read_text();f=re.search(r'(?ms)^define[^\n]*@liza_utf8_stream.feed_byte\([^\n]*\).*?^}',ir)[0]
  assert ('@llvm.uadd.with.overflow.i64' in f)==expected
  if not expected:assert re.search(r'add nuw i64 %v3, 1',f)
 p=json.loads((root/'proof/report.json').read_text());assert p['status']=='passed'
 assert [x['result'] for x in p['checks']]==['unsat']*5+['sat']*2
 assert len(p['replay'])==20
 c=json.loads((root/'controls/report.json').read_text())
 for a in c['applications'].values():assert not a['certificates'] and a['identical_text']
 reg=json.loads((root/'regressions-network/report.json').read_text());assert sum(x['tests'] for x in reg['suites'])==30
 assert all(not x['errors'] and not x['failures'] and not x['skipped'] for x in reg['suites'])
 assert reg['llvm_calls']
 print('P3: 180 timings, exact guard delta, 5 UNSAT, 2 SAT controls, 20 native runs, 30 regressions verified.')

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('results',type=Path);a=p.parse_args();verify(a.results)
