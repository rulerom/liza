#!/usr/bin/env python3
"""Exact receiver/ordinal gaps from an archived trial; no inferred kernel drops."""
import argparse,array,gzip,hashlib,json,struct
from pathlib import Path
from build import WARMUP,MAX_PACKETS

def main():
 p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--case',type=Path,required=True);p.add_argument('--sample',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 r=json.loads(a.report.read_text());sample=r['samples'][a.sample]
 with gzip.open(a.case/'generator.json.gz','rt') as f:g=json.load(f)
 total=len(g['times_ns']);receivers=len(sample['per_receiver'])
 if total>MAX_PACKETS+WARMUP or not 1<=receivers<=64:raise RuntimeError('unbounded archive')
 stamps=[array.array('Q',[0])*total for _ in range(receivers)]
 previous=[0]*receivers;max_gaps=[(0,0,0)]*receivers;digest=hashlib.sha256();count=0;global_previous=None;global_gap=(0,None,None)
 rec=struct.Struct('=QIHH')
 with gzip.open(a.case/'records.bin.gz','rb') as f:
  while True:
   b=f.read(rec.size*8192)
   if not b:break
   digest.update(b)
   for ts,seq,receiver,port in rec.iter_unpack(b):
    if receiver>=receivers or seq>=total or stamps[receiver][seq]:raise RuntimeError('invalid identity/duplicate')
    stamps[receiver][seq]=ts;count+=1
    if seq>=WARMUP:
     current=(ts,seq,receiver)
     if global_previous and ts-global_previous[0]>global_gap[0]:global_gap=(ts-global_previous[0],global_previous,current)
     global_previous=current
    if previous[receiver] and ts-previous[receiver]>max_gaps[receiver][0]:max_gaps[receiver]=(ts-previous[receiver],previous[receiver],ts)
    previous[receiver]=ts
 if digest.hexdigest()!=sample['artifact_sha256']['records.bin']:raise RuntimeError('record hash mismatch')
 out={'max_global_observation_gap':global_gap,'source_report':str(a.report),'source_sample':a.sample,'record_sha256':digest.hexdigest(),'warmup':WARMUP,'ordinal_end_exclusive':total,'phase_times':{k:sample['fanout'][k] for k in ('measure_ns','drain_ns','stop_ns','stopping_ns','finished_ns')},'receivers':[],
 'limits':['No historical kernel-drop counters or collector store-time instrumentation were collected.','Neighbor timestamps bracket recorded observations; they do not prove socket arrival or loss time.','Missing ordinals are identities not observed before collector termination, not proof of wire loss.']}
 for i,ts in enumerate(stamps):
  gaps=[];seq=WARMUP
  while seq<total:
   if ts[seq]:seq+=1;continue
   begin=seq
   while seq<total and not ts[seq]:seq+=1
   end=seq
   gaps.append({'first':begin,'last':end-1,'count':end-begin,'generator_first_ns':g['times_ns'][begin],'generator_last_ns':g['times_ns'][end-1],
                'previous_ordinal':begin-1 if begin>WARMUP else None,'previous_observed_ns':ts[begin-1] if begin>WARMUP else None,'next_ordinal':end if end<total else None,'next_observed_ns':ts[end] if end<total else None})
  observed=sum(bool(t) for t in ts[WARMUP:]);last=max(j for j in range(total) if ts[j])
  if observed!=sample['per_receiver'][i]:raise RuntimeError('receiver count mismatch')
  out['receivers'].append({'receiver':i,'observed':observed,'missing':total-WARMUP-observed,'last_ordinal':last,'last_ordinal_observed_ns':ts[last],'latest_observation_ns':max(ts),'max_observation_gap_ns':max_gaps[i],'gaps':gaps})
 out['missing_total']=sum(x['missing'] for x in out['receivers'])
 if out['missing_total']!=sample['input_sent']*receivers-sample['delivered_unique']:raise RuntimeError('total mismatch')
 a.output.write_text(json.dumps(out,indent=2)+'\n');print('missing',out['missing_total'],'per receiver range',min(x['missing'] for x in out['receivers']),max(x['missing'] for x in out['receivers']),flush=True)
if __name__=='__main__':main()
