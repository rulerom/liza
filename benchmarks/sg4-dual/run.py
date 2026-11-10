#!/usr/bin/env python3
"""B2: fixed single/dual Liza binaries, independently identified RTP sources/collectors."""
import argparse,gzip,json,math,os,platform,queue,socket,struct,subprocess,sys,threading,time
from pathlib import Path
from build import BASE,HERE,ROOT,WARMUP,MAX_PACKETS,SSRC,build,sha
def percentile(hist,p,width,overflow):
    total=sum(hist.values());goal=math.ceil(total*p/100);cumulative=0
    if not total:return None
    for bucket,n in sorted(hist.items()):
        cumulative+=n
        if cumulative>=goal:return None if bucket>=overflow else (bucket+1)*width

def now():return time.clock_gettime_ns(time.CLOCK_MONOTONIC)
def stop(p):
    if p and p.poll() is None:p.kill();p.communicate()
def send(p,command):p.stdin.write(command+'\n');p.stdin.flush()
def line(p,timeout=20):
    q=queue.Queue();threading.Thread(target=lambda:q.put(p.stdout.readline()),daemon=True).start()
    value=q.get(timeout=timeout)
    if not value:raise RuntimeError('missing readiness/acknowledgement: '+p.stderr.read())
    return value.strip()
class Events:
    def __init__(self,p):
        self.rows=[];self.error=None;self.ended=False;self.cv=threading.Condition()
        def read():
            try:
                for row in p.stdout:
                    value=json.loads(row)
                    with self.cv:self.rows.append(value);self.cv.notify_all()
            except Exception as exc:
                with self.cv:self.error=exc
            finally:
                with self.cv:self.ended=True;self.cv.notify_all()
        self.thread=threading.Thread(target=read,daemon=True);self.thread.start()
    def wait(self,kind,owner=None,timeout=20,**values):
        end=time.monotonic()+timeout
        with self.cv:
            while True:
                if self.error:raise self.error
                for row in self.rows:
                    if row.get('event')==kind and (owner is None or row.get('owner')==owner) and all(row.get(k)==v for k,v in values.items()):return row
                if self.ended:raise RuntimeError('service exited before '+kind)
                left=end-time.monotonic()
                if left<=0:raise TimeoutError(kind)
                self.cv.wait(left)

def udp():
    if sys.platform!='darwin':return None
    text=subprocess.check_output(['netstat','-s','-p','udp'],text=True)
    fields={}
    for row in text.splitlines():
        words=row.strip().split(' ',1)
        if len(words)==2 and words[0].isdigit() and words[1] in ('datagrams received','datagrams output','dropped due to full socket buffers','dropped due to no socket','delivered'):fields[words[1]]=int(words[0])
    if len(fields)!=5:raise RuntimeError('UDP counters unavailable')
    return {'time_ns':now(),'raw':text,'fields':fields,'scope':'system-wide; includes warmup, setup, drain and background traffic'}
def reserve(count):
    sockets=[];ports=[[],[]]
    try:
        for group in ports:
            for _ in range(count):
                s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));sockets.append(s);group.append(s.getsockname()[1])
        return ports
    finally:
        for s in sockets:s.close()
def linux_memory(pid):
    if not sys.platform.startswith('linux'):return None
    fields={}
    for row in Path(f'/proc/{pid}/status').read_text().splitlines():
        if row.startswith(('VmHWM:','VmRSS:')):
            k,v,unit=row.split();assert unit=='kB';fields[k[:-1]]=int(v)*1024
    return fields

def analyze(records,generator,collector,metrics,port,receivers,after_destroy=None):
    timestamps=generator['times_ns'];offered=sum(bool(t) for t in timestamps[WARMUP:]);hist={};late_hist={}
    delivered=warmup=late=0;coverage=[0]*receivers;last=[-1]*receivers;reordered=0
    record=struct.Struct('=QIHH')
    with records.open('rb') as source:
        for chunk in iter(lambda:source.read(record.size*8192),b''):
            if len(chunk)%record.size:raise RuntimeError('partial record')
            for stamp,ordinal,receiver,sender in record.iter_unpack(chunk):
                if receiver>=receivers or sender!=port or ordinal>=len(timestamps) or not timestamps[ordinal]:raise RuntimeError('delivery identity')
                if ordinal<WARMUP:warmup+=1;continue
                delta=stamp-timestamps[ordinal]
                if delta<0:raise RuntimeError('clock order')
                delivered+=1;coverage[receiver]+=1;reordered+=ordinal<last[receiver];last[receiver]=ordinal
                bucket=min(delta//100000,50000);hist[bucket]=hist.get(bucket,0)+1
                if after_destroy is not None and timestamps[ordinal]>=after_destroy:
                    late+=1;late_hist[bucket]=late_hist.get(bucket,0)+1
    if delivered+warmup!=collector['received'] or collector['records_stored']!=collector['received']:raise RuntimeError('recorder accounting')
    if not collector['measurement_valid'] or collector['record_overflow'] or collector['invalid'] or collector['duplicates']:raise RuntimeError('collector failure, not UDP loss')
    if delivered>metrics['succeeded'] or metrics['attempted']!=metrics['valid']*receivers or metrics['succeeded']+metrics['failed']!=metrics['attempted']:raise RuntimeError('fanout accounting')
    phase=generator['phases'][1];elapsed=(phase['end_ns']-phase['start_ns'])/1e9
    offered_after=sum(bool(t) and t>=after_destroy for t in timestamps[WARMUP:]) if after_destroy else None
    intervals=[b-a for a,b in zip(timestamps[WARMUP:],timestamps[WARMUP+1:]) if a and b]
    cpu_total=generator['user_s']+generator['system_s'];collector_cpu=collector['user_s']+collector['system_s']
    return {'input_sent':offered,'input_errors':generator['errors'],'received_unique':metrics['unique'],'input_shortfall':offered-metrics['unique'],
            'successful_local_sends':metrics['succeeded'],'failed_local_sends':metrics['failed'],'delivered_unique':delivered,'per_receiver':coverage,'reordered':reordered,
            'delivery_gap_from_local_success':metrics['succeeded']-delivered,'coverage_offered':delivered/(offered*receivers) if offered else None,
            'coverage_successful':delivered/metrics['succeeded'] if metrics['succeeded'] else None,'latency_hist_100us':hist,
            'latency_upper_ms':{f'p{p}':percentile(hist,p,.1,50000) for p in (50,95,99)},'offer_s':elapsed,'actual_input_sent_pps':offered/elapsed,
            'delivered_copies_per_offer_s':delivered/elapsed,'generator_cpu_s':cpu_total,'collector_cpu_s':collector_cpu,
            'offered_after_peer_destroy_packets':offered_after,'offered_after_peer_destroy_copies_observed':late,
            'after_peer_destroy_coverage_offered':late/(offered_after*receivers) if offered_after else None,
            'generator_max_interpacket_gap_ns':max(intervals,default=None),'after_peer_destroy_latency_upper_ms':{f'p{p}':percentile(late_hist,p,.1,50000) for p in (50,95,99)},
            'after_peer_destroy_hist_100us':late_hist}

def trial(bins,manifest,variant,rates,duration,folder,scenario='capacity',collector_mode='file',probe_invalid=False):
    if collector_mode not in ('file','memory'):raise ValueError('collector mode')
    folder=Path(folder);folder.mkdir();server=None;collectors=[];generators=[];events=None;before=udp();n=1 if variant=='single' else 2
    if scenario!='capacity' and variant!='dual':raise ValueError('independent early stop requires dual owners')
    durations=[duration/2 if scenario!='capacity' else duration,duration]
    counts=[round(r*d) for r,d in zip(rates,durations)]
    if max(counts)>MAX_PACKETS:raise ValueError('bounded offered packets')
    result={'status':'incomplete','variant':variant,'scenario':scenario,'rates':rates,'duration_s':duration,'collector_mode':collector_mode,'invalid_probe':probe_invalid}
    try:
        readiness=[]
        for stream in range(2):
            p=subprocess.Popen([str(bins[f'collector{stream}']),str(len(manifest['ports'][stream])),str(counts[stream]+WARMUP),str(folder/f'records{stream}.bin'),str(folder/f'collector{stream}.json')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'SG4_COLLECTOR_MODE':collector_mode})
            collectors.append(p);ready=json.loads(line(p));readiness.append(ready)
            if ready['ports']!=manifest['ports'][stream]:raise RuntimeError('endpoint configuration changed')
        server=subprocess.Popen([str(bins[variant])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        events=Events(server);ready=[events.wait('ready',i) for i in range(n)]
        for stream in range(2):
            owner=0 if variant=='single' else stream;ip=manifest['binds'][owner]
            p=subprocess.Popen([sys.executable,str(HERE/'generator.py'),ip,str(ready[owner]['port']),str(counts[stream]),str(rates[stream]),str(WARMUP),str(SSRC[stream]),str(durations[stream]),str(folder/f'generator{stream}.json')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            generators.append(p)
            if line(p)!='READY':raise RuntimeError('generator ready')
        warm_start=now()+100000000
        for p in generators:send(p,f'W {warm_start}')
        for p in generators:
            if line(p)!='W':raise RuntimeError('warmup')
        time.sleep(.2)
        for i in range(n):send(server,f'M{i}');events.wait('phase',i,phase=1)
        if probe_invalid:
            # Acceptance-only corpus; never enabled in measurement series.
            probe=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
            bad=[struct.pack('!BBHIII',0,96,WARMUP,WARMUP,SSRC[0],WARMUP)+bytes(1184),bytes([0x8f])+bytes(11),bytes([0x90,96])+bytes(10)+bytes([0,0,255,255]),bytes([0xa0,96])+bytes(10),bytes(4096)]
            def tagged(ssrc):return struct.pack('!BBHIII',128,96,WARMUP,WARMUP,ssrc,WARMUP)+bytes([WARMUP&255])*1184
            bad.append(tagged(0xdeadbeef))
            if variant=='dual':bad.append(tagged(SSRC[1]))
            for packet in bad:probe.sendto(packet,(manifest['binds'][0],ready[0]['port']))
            probe.close()
        start=now()+100000000
        for p in generators:send(p,f'M {start}')
        peer_destroy=None
        if scenario!='capacity':
            if line(generators[0],duration+20)!='M':raise RuntimeError('A offer end')
            send(server,'D0');events.wait('phase',0,phase=2);time.sleep(.15)
            send(server,'F0' if scenario=='fault' else 'S0')
            destroyed=events.wait('destroy',0);peer_destroy=destroyed['time_ns']
            if peer_destroy>=start+round(duration*1e9):raise RuntimeError('A did not destroy while B still offered')
            # The successful B offer must continue beyond A cleanup.
            if line(generators[1],duration+20)!='M':raise RuntimeError('B offer end')
        else:
            for p in generators:
                if line(p,duration+20)!='M':raise RuntimeError('offer end')
        for p in generators:
            out,err=p.communicate(timeout=5)
            if p.returncode:raise RuntimeError(err)
        remaining=[1] if scenario!='capacity' else list(range(n))
        for i in remaining:send(server,f'D{i}');events.wait('phase',i,phase=2)
        time.sleep(.5);memory=linux_memory(server.pid)
        for i in remaining:send(server,f'S{i}')
        server.wait(timeout=15);events.thread.join(timeout=5)
        if server.returncode or events.error or events.thread.is_alive():raise RuntimeError('service failure: '+server.stderr.read())
        time.sleep(1);collector_stop=now()
        for p in collectors:
            if p.poll() is None:
                try:send(p,'S')
                except BrokenPipeError:pass
        for p in collectors:
            out,err=p.communicate(timeout=15)
            if p.returncode:raise RuntimeError(f'collector failed ({p.returncode}), not network loss: '+err)
        after=udp();rows=events.rows
        owner_results=[next(r for r in rows if r.get('event')=='owner_result' and r['owner']==i) for i in range(n)]
        for i,r in enumerate(owner_results):
            expected_fault=scenario=='fault' and i==0
            if r['result']!=(4 if expected_fault else 0) or r['fault']!=(1 if expected_fault else 0) or r['producer'] or r['control_fault']:raise RuntimeError('unexpected group result')
            if r['joins']!=7 or r['receipts']!=7 or r['group_socket_handles_live']:raise RuntimeError('ownership accounting')
        streams=[];artifact_hashes={}
        for stream in range(2):
            owner=0 if variant=='single' else stream
            metrics=next(r for r in rows if r.get('event')=='stream_result' and r['owner']==owner and r['stream']==stream)
            gen=json.loads((folder/f'generator{stream}.json').read_text());col=json.loads((folder/f'collector{stream}.json').read_text())
            row=analyze(folder/f'records{stream}.bin',gen,col,metrics,ready[owner]['port'],len(manifest['ports'][stream]),peer_destroy if stream==1 else None)
            row.update(stream=stream,ssrc=SSRC[stream],metrics=metrics,collector=col,generator_phases=gen['phases'])
            if peer_destroy and stream==1 and row['offered_after_peer_destroy_copies_observed']==0:raise RuntimeError('no B delivery from packets offered after A destroy')
            streams.append(row)
            for name in (f'records{stream}.bin',f'generator{stream}.json'):
                p=folder/name;artifact_hashes[name]=sha(p)
                with p.open('rb') as src,gzip.open(str(p)+'.gz','wb',compresslevel=1) as dest:
                    while True:
                        chunk=src.read(1024*1024)
                        if not chunk:break
                        dest.write(chunk)
                p.unlink()
        usage=next(r for r in rows if r.get('event')=='usage');unit=1 if sys.platform=='darwin' else 1024
        result.update(status='measured',ready=ready,collector_ready=readiness,collector_stop_requested_ns=collector_stop,owner_results=owner_results,
                      usage=usage,service_peak_rss_bytes=(usage['maxrss_native']*unit if memory is None else memory['VmHWM']*1024),linux_memory=memory,
                      streams=streams,events=rows,artifact_sha256=artifact_hashes,peer_destroy_ns=peer_destroy,kernel_before=before,kernel_after=after,
                      kernel_delta={k:after['fields'][k]-v for k,v in before['fields'].items()} if before else None)
    except Exception as exc:
        result['error']=repr(exc)
        if events:result['events']=events.rows
        raise
    finally:
        for p in [server,*collectors,*generators]:stop(p)
        if events:events.thread.join(timeout=5)
        for p in [server,*collectors,*generators]:
            if p:
                for stream in (p.stdin,p.stdout,p.stderr):
                    if stream and not stream.closed:stream.close()
        (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--duration',type=float,default=5);p.add_argument('--repeats',type=int,default=5);p.add_argument('--receivers',type=int,default=64);p.add_argument('--bind-a',default='127.0.0.1');p.add_argument('--bind-b',default='127.0.0.1');a=p.parse_args()
    if a.output.exists() or not 1<=a.receivers<=64 or not .5<=a.duration<=60 or not 1<=a.repeats<=20:p.error('fresh output and bounded configuration required')
    a.output.mkdir(parents=True);bins,manifest=build(a.output/'build',reserve(a.receivers),(a.bind_a,a.bind_b))
    report={'status':'incomplete','build':manifest,'samples':[],'limits':['Same-host loopback; not physical NIC isolation or hard latency isolation.','Single owner multiplexes two SSRCs in one UDP queue; dual uses two queues. CPU and queue capacity change together.','No background-load exclusion or affinity. Kernel counters are global. Collector scheduling and recording remain possible bottlenecks.','No C comparison or SG5. Performance series do not establish an exact capacity threshold.']}
    try:
        for scenario in ('stop','fault'):
            report['samples'].append(trial(bins,manifest,'dual',[2000,2000],a.duration,a.output/scenario,scenario))
        profiles=[(0,2000),(2000,2000),(5000,5000),(10000,2000)]
        for profile_index,rates in enumerate(profiles):
            for rep in range(a.repeats):
                for variant in (('single','dual') if (rep+profile_index)%2==0 else ('dual','single')):
                    name=f'{rates[0]}-{rates[1]}-{rep}-{variant}';report['active_case']=name
                    report['samples'].append(trial(bins,manifest,variant,list(rates),a.duration,a.output/name))
                    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');time.sleep(1)
        if any(sha(bins[k])!=v for k,v in manifest['binary_sha256'].items()):raise RuntimeError('binary changed between repeats')
        report['status']='measured';report.pop('active_case',None)
    except Exception as exc:report['error']=repr(exc);raise
    finally:(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
