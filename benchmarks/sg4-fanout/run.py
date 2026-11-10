#!/usr/bin/env python3
"""SG4-A2 POSIX loopback: immutable builds, persistent warmup, independent collector."""
import argparse,gzip,hashlib,json,math,os,platform,queue,random,socket,struct,subprocess,sys,threading,time
from pathlib import Path
from build import build,sha,ROOT,HERE,WARMUP,MAX_PACKETS

def line(p,timeout=20):
    q=queue.Queue();threading.Thread(target=lambda:q.put(p.stdout.readline()),daemon=True).start()
    value=q.get(timeout=timeout)
    if not value:raise RuntimeError('missing acknowledgement: '+p.stderr.read())
    return value.strip()

def send(p,c):p.stdin.write(c+'\n');p.stdin.flush()
def stop(p):
    if p and p.poll() is None:p.kill();p.communicate()
def linux_memory(pid):
    """Linux ru_maxrss can retain the pre-exec launcher's high-water mark."""
    if not sys.platform.startswith('linux'):return None
    fields={}
    for row in Path(f'/proc/{pid}/status').read_text().splitlines():
        if row.startswith(('VmHWM:', 'VmRSS:')):
            key,value,unit=row.split()
            if unit!='kB':raise RuntimeError('unexpected proc RSS units')
            fields[key[:-1]]=int(value)*1024
    if len(fields)!=2:raise RuntimeError('missing live service memory counters')
    return {'source':'/proc/PID/status before shutdown','peak_bytes':fields['VmHWM'],'resident_bytes':fields['VmRSS']}
def percentile(hist,p,width,overflow):
    total=sum(hist.values());goal=math.ceil(total*p/100);cumulative=0
    if not total:return None
    for bucket,n in sorted(hist.items()):
        cumulative+=n
        if cumulative>=goal:return None if bucket>=overflow else (bucket+1)*width

def trial(binaries,variant,rate,duration,ports,folder,archive_level=9,collector_env=None,collector_finished=None):
    folder.mkdir();packets=round(rate*duration);server=collector=generator=None
    try:
        collector=subprocess.Popen([str(binaries['collector']),str(len(ports)),str(packets+WARMUP),str(folder/'records.bin'),str(folder/'collector.json')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=collector_env)
        cc=json.loads(line(collector))
        if cc['ports']!=ports:raise RuntimeError('collector port configuration changed')
        server=subprocess.Popen([str(binaries[variant])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        ready=json.loads(line(server));port=ready['port']
        generator=subprocess.Popen([sys.executable,str(HERE/'generator.py'),str(port),str(packets),str(rate),str(WARMUP),str(folder/'generator.json')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        if line(generator)!='READY':raise RuntimeError('generator readiness')
        send(generator,'W')
        if line(generator)!='W':raise RuntimeError('warmup')
        time.sleep(.2) # drain warmup before phase acknowledgement, same processes
        server.stdin.write('M');server.stdin.flush();ma=json.loads(line(server))
        if ma['phase']!=1:raise RuntimeError('measurement phase')
        send(generator,'M')
        if line(generator,duration+20)!='M':raise RuntimeError('measurement')
        go,ge=generator.communicate(timeout=5)
        if generator.returncode:raise RuntimeError(ge)
        server.stdin.write('D');server.stdin.flush();da=json.loads(line(server))
        if da['phase']!=2:raise RuntimeError('drain phase')
        time.sleep(.5)
        memory=linux_memory(server.pid)
        server.stdin.write('S');server.stdin.flush();so,se=server.communicate(timeout=10)
        if server.returncode:raise RuntimeError('fanout: '+so+se)
        metrics=json.loads(so.strip())
        time.sleep(1)
        collector_stop_requested_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        collector.stdin.write('S');collector.stdin.flush();co,ce=collector.communicate(timeout=10)
        if collector.returncode:raise RuntimeError(f'collector exited {collector.returncode}; inspect collector.json for explicit recorder failure: '+ce)
        collector_exit_observation=collector_finished() if collector_finished else None
        gen=json.loads((folder/'generator.json').read_text());col=json.loads((folder/'collector.json').read_text())
        if metrics['result'] or metrics['fault'] or metrics['producer'] or metrics['control_fault']:raise RuntimeError('runtime failure')
        if metrics['consumer']!=metrics['valid']+metrics['warmup_valid']:raise RuntimeError('application result disagrees with independent observer')
        if metrics['received']!=sum(metrics[k] for k in ('valid','invalid','wrong_ssrc','truncated')):raise RuntimeError('receive accounting')
        if metrics['attempted']!=metrics['valid']*len(ports) or metrics['attempted']!=metrics['succeeded']+metrics['failed']:raise RuntimeError('send accounting')
        if col['invalid'] or col['duplicates']:raise RuntimeError('collector integrity')
        hist={};delivered=0;warmup_delivered=0;per_receiver=[0]*len(ports);last=[-1]*len(ports);reordered=0
        record=struct.Struct('=QIHH');end=gen['phases'][1]['end_ns'];delivered_before_end=0
        with (folder/'records.bin').open('rb') as f:
            while True:
                chunk=f.read(record.size*8192)
                if not chunk:break
                if len(chunk)%record.size:raise RuntimeError('partial collector record')
                for stamp,seq,receiver,source in record.iter_unpack(chunk):
                    if source!=port or receiver>=len(ports) or seq>=len(gen['times_ns']) or not gen['times_ns'][seq]:raise RuntimeError('unexpected delivery identity')
                    if seq<WARMUP:warmup_delivered+=1;continue
                    delta=stamp-gen['times_ns'][seq]
                    if delta<0:raise RuntimeError('clock order')
                    if seq<last[receiver]:reordered+=1
                    last[receiver]=seq;per_receiver[receiver]+=1;delivered+=1
                    if stamp<=end:delivered_before_end+=1
                    bucket=min(delta//100000,50000);hist[bucket]=hist.get(bucket,0)+1
        if delivered+warmup_delivered!=col['received']:raise RuntimeError('collector accounting')
        if delivered>metrics['succeeded']:raise RuntimeError('delivery exceeds successful sends')
        sent=sum(bool(t) for t in gen['times_ns'][WARMUP:]);elapsed=(end-gen['phases'][1]['start_ns'])/1e9
        rss_unit=1 if sys.platform=='darwin' else 1024
        cycle_hist={int(k):v for k,v in metrics['cycle_hist_10us'].items()}
        intervals=[b-a for a,b in zip(gen['times_ns'][WARMUP:],gen['times_ns'][WARMUP+1:]) if a and b]
        interval_hist={}
        for delta in intervals:
            bucket=min(delta//10000,10000);interval_hist[bucket]=interval_hist.get(bucket,0)+1
        row={'status':'measured','collector_exit_observation':collector_exit_observation,'collector_stop_requested_ns':collector_stop_requested_ns,'variant':variant,'requested_input_pps':rate,'duration_s':duration,'input_sent':sent,'input_errors':gen['errors'],'generator_phases':gen['phases'],'actual_offer_s':elapsed,
             'input_shortfall':sent-metrics['received_unique'],'delivered_unique':delivered,'per_receiver':per_receiver,'delivery_gap_from_local_success':metrics['succeeded']-delivered,'reordered':reordered,'corrupt':col['invalid'],'duplicates':col['duplicates'],
             'coverage_offered':delivered/(sent*len(ports)) if sent else None,'coverage_successful':delivered/metrics['succeeded'] if metrics['succeeded'] else None,
             'throughput':{'received_including_drain_per_offer_s':metrics['received']/elapsed,'successful_sends_including_drain_per_offer_s':metrics['succeeded']/elapsed,'delivered_within_offer_window_pps':delivered_before_end/elapsed,'delivered_including_drain_per_offer_s':delivered/elapsed},
             'latency_hist_100us':hist,'latency_upper_ms':{f'p{p}':percentile(hist,p,.1,50000) for p in (50,95,99)},'pacing_hist_10us':interval_hist,'cycle_upper_us':{f'p{p}':percentile(cycle_hist,p,10,10000) for p in (50,95,99)},
             'ready':ready,'measure_ack':ma,'drain_ack':da,'fanout':metrics,'collector':col,'collector_config':cc,'generator_cpu':{k:gen[k] for k in ('user_s','system_s','maxrss_native')},'fanout_memory':memory,'fanout_peak_rss_bytes':memory['peak_bytes'] if memory else metrics['maxrss_native']*rss_unit,
             'shutdown_observe_ms':(metrics['stopping_ns']-metrics['stop_ns'])/1e6,'shutdown_join_ms':(metrics['finished_ns']-metrics['stop_ns'])/1e6,
             'drain_received':metrics['received']-metrics['phase_received'],'artifact_sha256':{name:sha(folder/name) for name in ('records.bin','collector.json','generator.json')}}
        # Histograms and counters are retained in the manifest. Raw timing records
        # are compressed on disk, outside the source repository.
        for name in ('records.bin','generator.json'):
            path=folder/name
            with path.open('rb') as src,gzip.open(str(path)+'.gz','wb',compresslevel=archive_level) as dst:
                import shutil;shutil.copyfileobj(src,dst)
            path.unlink()
        return row
    finally:
        for p in (generator,server,collector):stop(p)

def git_info(*args):
    p=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,text=True)
    return p.stdout.strip() if p.returncode==0 else 'unavailable (source snapshot)'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--duration',type=float,default=5);parser.add_argument('--repeats',type=int,default=5);parser.add_argument('--rates',type=int,nargs='+',default=[2000,5000,10000]);parser.add_argument('--receivers',type=int,default=64);parser.add_argument('--seed',type=int,default=4182);parser.add_argument('--environment-label',default='host loopback')
    a=parser.parse_args()
    if os.name=='nt':parser.error('POSIX measurement harness; Windows functional acceptance is SG4-A1')
    if a.output.exists() or not 1<=a.receivers<=64 or not 1<=a.repeats<=10 or not .1<=a.duration<=60 or any(r<=0 or r*a.duration>MAX_PACKETS for r in a.rates):parser.error('fresh output and bounded workload required')
    a.output.mkdir(parents=True);a.output=a.output.resolve();report={'status':'incomplete','revision':os.environ.get('LIZA_BENCH_REVISION') or git_info('rev-parse','HEAD'),'dirty':git_info('status','--short'),'platform':platform.platform(),'machine':platform.machine(),'logical_cpus':os.cpu_count(),'uname':list(platform.uname()),'target':subprocess.check_output(['clang','-dumpmachine'],text=True).strip(),'python':sys.version,'clang':subprocess.check_output(['clang','--version'],text=True),'parameters':vars(a)|{'output':str(a.output)},'samples':[],
      'limits':['Loopback on one host; generator/collector contend with service. Linux container/VM must be identified separately.','Same SG2/SG3 lifecycle and benchmark observer in both variants; not an independent-runtime comparison.','Observer validates RTP again for independent accounting; this cost is included equally. Consumer return count cross-checks it.','One startup command sample per process, not a command-latency percentile estimate.','Supervisor/service per-thread CPU unavailable; total process CPU includes them. Callback CPU excludes wrapper cleanup.','CPU measurement interval includes drain; peak RSS includes startup/warmup.','Latency histogram upper bounds (100us), overflow >=5s returns null percentile. Only delivered packets contribute.','One packet per next; cycle timing includes observer and application work, excludes blocking poll.','No cross-host one-way latency or physical network performance claim.','Warmup 200 packets at 1k/s, same processes; 0.2s warmup drain, 0.5s fanout drain, 1s collector drain.'],
      'budgets':{'group_managed_limit':65536,'process_managed_limit':65536,'reactor_limit':65536,'region_limit':4096,'participant_stack_requested_total':3145728,'service_stack_requested':1048576,'harness_seen_bytes':MAX_PACKETS+WARMUP,'harness_histogram_bytes':10001*8,'harness_threads':1,'harness_pipe_handles':2,'collector_seen_bytes_max':a.receivers*(MAX_PACKETS+WARMUP),'kernel_buffers':'reported actual sizes, outside managed limits'}}
    reserved=[]
    try:
        for _ in range(a.receivers):
            s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));reserved.append(s)
        ports=[s.getsockname()[1] for s in reserved];binaries,manifest=build(a.output/'build',ports);report['build']=manifest
        report['generated_config']=(a.output/'build/config.liza').read_text();report['generated_c_config']=(a.output/'build/config.h').read_text()
        for s in reserved:s.close()
        cases=[(repeat,rate,variant) for repeat in range(a.repeats) for rate in a.rates for variant in ('liza','c')];random.Random(a.seed).shuffle(cases);report['order']=cases
        expected_buffers=None
        for index,(repeat,rate,variant) in enumerate(cases):
            try:
                if any(sha(p)!=manifest['binary_sha256'][k] for k,p in binaries.items()):raise RuntimeError('binary changed between repeats')
                row=trial(binaries,variant,rate,a.duration,ports,a.output/f'case-{index}')
                buffers=(row['ready']['rcvbuf'],row['ready']['sndbuf'],row['collector_config']['receive_buffers'])
                if expected_buffers is None:expected_buffers=buffers
                if buffers!=expected_buffers:raise RuntimeError('socket buffers changed between variants')
                row['repeat']=repeat;report['samples'].append(row)
                print(variant,rate,'received',row['fanout']['received'],'delivered',row['delivered_unique'],'p99_ms',row['latency_upper_ms']['p99'],flush=True)
            except Exception as exc:
                report['samples'].append({'status':'failed','variant':variant,'repeat':repeat,'rate':rate,'error':repr(exc)});raise
            (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        report['status']='measured'
    except Exception as exc:
        report['error']=repr(exc)
        if isinstance(exc,subprocess.CalledProcessError):report['stderr']=exc.stderr
        raise
    finally:
        for s in reserved:s.close()
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
