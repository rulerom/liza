#!/usr/bin/env python3
"""Paired follow-up using the exact preserved baseline executables."""
import argparse,json,platform,shutil,time
from pathlib import Path
from build import sha,MAX_PACKETS
from run import trial

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
 p.add_argument('--duration',type=int,default=60);p.add_argument('--rate',type=int,default=5000);p.add_argument('--pairs',type=int,default=3)
 a=p.parse_args()
 if a.output.exists() or not 1<=a.pairs<=10 or not 1<=a.duration<=60 or not 1<=a.rate*a.duration<=MAX_PACKETS:p.error('fresh output and bounded configuration required')
 old=json.loads((a.baseline/'report.json').read_text());bins={k:(a.baseline/'build'/k).resolve() for k in ('liza','c','collector')}
 def unchanged():
  for k,path in bins.items():
   if sha(path)!=old['build']['binary_sha256'][k]:raise RuntimeError('baseline binary changed: '+k)
 unchanged();a.output.mkdir(parents=True)
 r={'status':'incomplete','platform':platform.platform(),'baseline_report_sha256':sha(a.baseline/'report.json'),'build':old['build'],'duration_s':a.duration,'rate':a.rate,'pairs':a.pairs,'samples':[],
    'limits':['Same baseline executables; generator/harness source SHA recorded separately.','AB/BA pair order balances first/second position; three pairs are exploratory, not a significance test.','Generator and collector process CPU cover warmup and drain; normalized CPU seconds/offer seconds are diagnostic, not isolated phase CPU.','No affinity, exclusive host reservation, or causal isolation of collector scheduling.','2s quiet interval between cases; compression and accounting finish before next trial.']}
 here=Path(__file__).resolve().parent;r['harness_sha256']={n:sha(here/n) for n in ('paired.py','run.py','generator.py')}
 expected=None
 try:
  for pair in range(a.pairs):
   for position,v in enumerate(('liza','c') if pair%2==0 else ('c','liza')):
    unchanged()
    if shutil.disk_usage(a.output).free<1024**3:raise RuntimeError('less than 1 GiB free; preserve previous samples and stop')
    row=trial(bins,v,a.rate,a.duration,old['build']['ports'],a.output/f'pair-{pair}-{position}-{v}')
    buffers=(row['ready']['rcvbuf'],row['ready']['sndbuf'],row['collector_config']['receive_buffers'])
    if expected is not None and expected!=buffers:raise RuntimeError('socket buffers changed')
    expected=buffers;row.update(pair=pair,position=position)
    row['cpu_seconds_per_offer_second']={k:(row[k]['user_s']+row[k]['system_s'])/row['actual_offer_s'] for k in ('collector','generator_cpu')}
    row['cpu_seconds_per_offer_second']['fanout']=(row['fanout']['measurement_drain_user_s']+row['fanout']['measurement_drain_system_s'])/row['actual_offer_s']
    r['samples'].append(row);(a.output/'report.json').write_text(json.dumps(r,indent=2))
    print(pair,v,'p99_ms',row['latency_upper_ms']['p99'],'coverage',row['coverage_offered'],'cpu',row['cpu_seconds_per_offer_second'],flush=True)
    time.sleep(2)
  r['status']='measured'
 except Exception as exc:r['error']=repr(exc);raise
 finally:(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
