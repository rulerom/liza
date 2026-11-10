#!/usr/bin/env python3
"""Separate stage-instrumented builds; never overwrite baseline artifacts."""
import argparse,gzip,json,math,struct
from pathlib import Path
from build import build,sha,HERE
from run import trial,percentile

def quantiles(values):
 a=sorted(values)
 return {f'p{p}':a[max(0,math.ceil(len(a)*p/100)-1)] if a else None for p in (50,95,99)}
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--duration',type=int,default=30)
 a=p.parse_args()
 if a.output.exists() or not 1<=a.duration<=60:p.error('fresh output and duration 1..60 required')
 old=json.loads((a.baseline/'report.json').read_text())
 for name in ('fanout.c','fanout.liza','packet.h'):
  if sha(HERE/name)!=old['build']['source_sha256']['benchmarks/sg4-fanout/'+name]:raise RuntimeError('application source changed')
 a.output.mkdir(parents=True);bins,manifest=build(a.output/'build',old['build']['ports'],stage_timing=True)
 for name,digest in old['build']['source_sha256'].items():
  if name.startswith('liza/runtime/') or name in ('packet.liza','receivers.liza'):
   if manifest['source_sha256'].get(name)!=digest:raise RuntimeError('runtime/RTP source changed: '+name)
 report={'status':'incomplete','build':manifest,'baseline_report_sha256':sha(a.baseline/'report.json'),'samples':[],
 'limits':['Diagnostic wall-clock hooks change timing; separate from preserved baseline.','Receive-to-first-send includes observer validation, application parse, checks and first destination lookup; not pure parser time.','Fanout includes destination iteration and 64 send calls. No application source changes.','Every 256th ordinal is correlated; sparse tail percentiles are descriptive only.','Generator timestamp precedes send syscall; collector timestamp follows recvfrom. These are not kernel arrival timestamps.','Local execution and scheduler delays cannot be causally isolated by these samples.']}
 try:
  for variant in ('liza','c'):
   folder=a.output/variant;row=trial(bins,variant,5000,a.duration,old['build']['ports'],folder,archive_level=1)
   timing=row['fanout']['stage_timing']
   if timing['count']!=row['fanout']['valid']:raise RuntimeError('stage count mismatch')
   row['stage_upper_us']={key:{f'p{p}':percentile({int(k):v for k,v in h.items()},p,1,10000) for p in (50,95,99)} for key,h in timing['histograms_1us'].items()}
   with gzip.open(folder/'generator.json.gz','rt') as f:gen=json.load(f)
   points={int(s[0]):s for s in timing['samples']};before=[];first=[];last=[]
   for seq,rx,enter,returned in points.values():before.append((rx-gen['times_ns'][seq])/1e6)
   record=struct.Struct('=QIHH')
   with gzip.open(folder/'records.bin.gz','rb') as f:
    while True:
     chunk=f.read(record.size*8192)
     if not chunk:break
     for stamp,seq,receiver,port in record.iter_unpack(chunk):
      if seq in points:
       _,rx,enter,returned=points[seq]
       if receiver==0:first.append((stamp-enter)/1e6)
       if receiver==63:last.append((stamp-returned)/1e6)
   row['sampled_delays_ms']={'generator_to_receive_return':quantiles(before),'first_send_enter_to_first_receiver':quantiles(first),'last_send_return_to_last_receiver_signed':quantiles(last),'counts':[len(before),len(first),len(last)]}
   report['samples'].append(row);(a.output/'report.json').write_text(json.dumps(report,indent=2))
   print(variant,row['stage_upper_us'],row['sampled_delays_ms'],flush=True)
  report['status']='measured'
 except Exception as exc:report['error']=repr(exc);raise
 finally:(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
