#!/usr/bin/env python3
"""C fanout held fixed: original collector reference, then matched file/memory pairs."""
import argparse,json,os,platform,re,shutil,subprocess,time
from pathlib import Path
from build import sha,HERE
from run import trial

def udp():
 p=subprocess.run(['netstat','-s','-p','udp'],capture_output=True,text=True,check=True)
 if 'Operation not permitted' in p.stderr:raise RuntimeError(p.stderr)
 keys=('datagrams received','datagrams output','dropped due to full socket buffers','dropped due to no socket','delivered')
 fields={}
 for line in p.stdout.splitlines():
  m=re.fullmatch(r'\s*(\d+) (.+)',line)
  if m and m[2] in keys:fields[m[2]]=int(m[1])
 if len(fields)!=len(keys):raise RuntimeError('UDP counters unavailable')
 return {'time_ns':time.clock_gettime_ns(time.CLOCK_MONOTONIC),'fields':fields,'raw':p.stdout}

def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--duration',type=int,default=60);p.add_argument('--pairs',type=int,default=2)
 a=p.parse_args()
 if platform.system()!='Darwin' or a.output.exists() or not 1<=a.duration<=60 or not 1<=a.pairs<=4:p.error('macOS, fresh output, duration 1..60 and pairs 1..4 required')
 old=json.loads((a.baseline/'report.json').read_text());a.output.mkdir(parents=True)
 bins={k:(a.baseline/'build'/k).resolve() for k in ('c','liza','collector')}
 for k,b in bins.items():
  if sha(b)!=old['build']['binary_sha256'][k]:raise RuntimeError('baseline binary changed')
 original=bins['collector'];collector=a.output/'collector_ab'
 command=['clang','-std=c11','-O2','-g','-Wall','-Wextra','-Werror','-I'+str((a.baseline/'build').resolve()),str(HERE/'collector_ab.c'),'-o',str(collector.resolve())]
 subprocess.run(command,check=True,capture_output=True,text=True,timeout=120)
 order=[('reference',0,'original')]+[(f'pair-{i}',j,mode) for i in range(a.pairs) for j,mode in enumerate(('file','memory') if i%2==0 else ('memory','file'))]
 r={'status':'incomplete','platform':platform.platform(),'baseline_report_sha256':sha(a.baseline/'report.json'),'baseline_build':old['build'],'build_command':command,'collector_sha256':sha(collector),'source_sha256':{n:sha(HERE/n) for n in ('collector_ab.py','collector_ab.c','run.py','generator.py')},'duration_s':a.duration,'rate':5000,'order':order,'samples':[],
 'limits':['C fanout and generator held fixed; two A/B pairs are exploratory.','Original collector reference is uninstrumented; file/memory use one new binary with identical validation and timing hooks.','Kernel UDP counters cover setup/warmup/measurement/drain until collector exit, before post-processing; system-wide, not per socket or exclusively attributable.','Outside-recv timing includes idle poll, validation, storage and scheduling; wall timing does not isolate blocking I/O.','Memory buffer is bounded and prefaulted before Ready; overflow exits 4 and invalidates the trial.','Cutoff snapshots observe queues without extending drain; no guarantee about future arrivals.','Record compression and fsync happen after processes exit, followed by 2s quiet time.','Generator/collector CPU include warmup and post-phase flushing; do not treat them as phase-only CPU.']}
 try:
  for group,position,mode in order:
   r['active_case']=[group,position,mode]
   if shutil.disk_usage(a.output).free<1024**3:raise RuntimeError('less than 1 GiB free')
   for k in ('c','liza'):
    if sha(bins[k])!=old['build']['binary_sha256'][k]:raise RuntimeError('service binary changed')
   if sha(original)!=old['build']['binary_sha256']['collector'] or sha(collector)!=r['collector_sha256']:raise RuntimeError('collector changed')
   bins['collector']=original if mode=='original' else collector.resolve()
   env=dict(os.environ,SG4_COLLECTOR_MODE='memory' if mode=='memory' else 'file');env.pop('SG4_COLLECTOR_RECORD_LIMIT',None)
   before=udp();folder=a.output/f'{group}-{position}-{mode}'
   row=trial(bins,'c',5000,a.duration,old['build']['ports'],folder,archive_level=1,collector_env=env,collector_finished=udp)
   after=row['collector_exit_observation'];row.update(group=group,position=position,collector_mode=mode,kernel_before=before,kernel_after=after,kernel_delta={k:after['fields'][k]-v for k,v in before['fields'].items()})
   if mode!='original' and (not row['collector']['measurement_valid'] or row['collector']['records_stored']!=row['collector']['received']):raise RuntimeError('recorder failure')
   if r['samples']:
    ref=r['samples'][0]
    if row['collector_config']['receive_buffers']!=ref['collector_config']['receive_buffers'] or (row['ready']['rcvbuf'],row['ready']['sndbuf'])!=(ref['ready']['rcvbuf'],ref['ready']['sndbuf']):raise RuntimeError('socket buffers changed')
   r['samples'].append(row);r.pop('active_case');(a.output/'report.json').write_text(json.dumps(r,indent=2))
   print(group,mode,'p99_ms',row['latency_upper_ms']['p99'],'coverage',row['coverage_offered'],'kernel_full',row['kernel_delta']['dropped due to full socket buffers'],flush=True)
   for path in folder.iterdir():
    if path.is_file():
     with path.open('r+b') as f:os.fsync(f.fileno())
   time.sleep(2)
  r['status']='measured'
 except Exception as exc:r['error']=repr(exc);raise
 finally:(a.output/'report.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
