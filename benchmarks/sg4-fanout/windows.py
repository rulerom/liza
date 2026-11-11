#!/usr/bin/env python3
"""Post-process raw records after all trials, so analysis cannot contend with load."""
import argparse,gzip,json,struct
from pathlib import Path
from build import WARMUP
from run import percentile

def main():
 p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args()
 r=json.loads((a.directory/'report.json').read_text());result={'window_seconds':5,'source_status':r['status'],'samples':[]}
 if r['status']!='measured':raise RuntimeError('all paired trials must finish before window analysis')
 for row in r['samples']:
  folder=a.directory/f"pair-{row['pair']}-{row['position']}-{row['variant']}"
  with gzip.open(folder/'generator.json.gz','rt') as f:gen=json.load(f)
  per=r['rate']*5;hist=[{} for _ in range((r['rate']*r['duration_s']+per-1)//per)]
  record=struct.Struct('=QIHH')
  with gzip.open(folder/'records.bin.gz','rb') as f:
   while True:
    chunk=f.read(record.size*8192)
    if not chunk:break
    for stamp,seq,receiver,port in record.iter_unpack(chunk):
     if seq<WARMUP:continue
     delta=stamp-gen['times_ns'][seq]
     if delta<0:raise RuntimeError('negative timing')
     h=hist[(seq-WARMUP)//per];b=min(delta//100000,50000);h[b]=h.get(b,0)+1
  windows=[]
  for i,h in enumerate(hist):
   stamps=gen['times_ns'][WARMUP+i*per:WARMUP+(i+1)*per]
   sent=sum(bool(t) for t in stamps);delivered=sum(h.values());expected=sent*len(row['per_receiver'])
   gaps=[b-a for a,b in zip(stamps,stamps[1:]) if a and b]
   late=[stamp-(gen['phases'][1]['start_ns']+(i*per+j)*1000000000//r['rate']) for j,stamp in enumerate(stamps) if stamp]
   windows.append({'begin_s':i*5,'input_sent':sent,'delivered':delivered,'coverage':delivered/expected if expected else None,'hist_100us':h,'p99_upper_ms':percentile(h,99,.1,50000),
                   'generator_max_gap_ms':max(gaps,default=0)/1e6,'generator_gaps_over_1ms':sum(g>1000000 for g in gaps),'generator_catchup_gaps_under_20us':sum(g<20000 for g in gaps),'generator_max_schedule_lateness_ms':max(late,default=0)/1e6})
  if sum(w['delivered'] for w in windows)!=row['delivered_unique']:raise RuntimeError('window count mismatch')
  result['samples'].append({'pair':row['pair'],'position':row['position'],'variant':row['variant'],'windows':windows})
  print(row['pair'],row['variant'],[w['p99_upper_ms'] for w in windows],flush=True)
 (a.directory/'windows.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
