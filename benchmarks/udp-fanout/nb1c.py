#!/usr/bin/env python3
"""Separate-process loopback fanout diagnostic with a separate control pipe."""
import argparse,hashlib,json,os,platform,random,re,struct,subprocess,sys,tempfile,time
from pathlib import Path
import nb1b_build
import run as common
ROOT=Path(__file__).resolve().parents[2]
WORKER=ROOT/'benchmarks/udp-fanout/nb1b_worker.py'

def process_stats(pid):
    try:
        out=subprocess.check_output(['ps','-p',str(pid),'-o','time=','-o','rss='],text=True,stderr=subprocess.DEVNULL).split()
        clock=out[0].split(':');seconds=0.0
        for part in clock:seconds=seconds*60+float(part)
        return {'cpu_seconds':seconds,'rss_bytes':int(out[1])*1024,'source':'ps live sample (RSS not peak)'}
    except (OSError,ValueError,IndexError,subprocess.CalledProcessError):return None

def udp_stats():
    try:
        if sys.platform=='linux':
            rows=Path('/proc/net/snmp').read_text().splitlines();rows=[x.split() for x in rows if x.startswith('Udp:')]
            return dict(zip(rows[-2][1:],map(int,rows[-1][1:])))
        out=subprocess.check_output(['netstat','-s','-p','udp'],text=True,stderr=subprocess.DEVNULL)
        return {'full_socket_buffer_drops':int(re.search(r'(\d+) dropped due to full socket buffers',out)[1]),
                'datagrams_received':int(re.search(r'(\d+) datagrams received',out)[1]),
                'datagrams_output':int(re.search(r'(\d+) datagrams output',out)[1])}
    except (OSError,ValueError,IndexError,TypeError,subprocess.CalledProcessError):return None

def start_line(p):
    import queue,threading
    q=queue.Queue();threading.Thread(target=lambda:q.put(p.stdout.readline()),daemon=True).start()
    line=q.get(timeout=15)
    if not line:raise RuntimeError('process failed to announce readiness')
    return line

def stop(p):
    if p and p.poll() is None:
        p.kill();p.communicate()

def trial(binary,collector_binary,n,packets,rate,drain,folder,collector_drain=1.0):
    collector=server=generator=None
    collectfile=folder/'collector.json';recordsfile=folder/'records.bin';genfile=folder/'generator.json'
    before=udp_stats();start_case=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    try:
        collector=subprocess.Popen([str(collector_binary),str(n),str(packets),str(recordsfile),str(collectfile)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
        collector_config=json.loads(start_line(collector));ports=collector_config['ports']
        server=subprocess.Popen([str(binary),'2147483647',str(common.SSRC),*map(str,ports)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
        port=int(start_line(server));server_start=process_stats(server.pid)
        generator=subprocess.Popen([sys.executable,str(WORKER),'generator',str(port),str(packets),str(rate),str(genfile)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
        gout,gerr=generator.communicate(timeout=max(10,packets/rate+10))
        if generator.returncode:raise RuntimeError('generator failed '+gerr)
        phase_command_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC);server.stdin.write('D');server.stdin.flush()
        if start_line(server).strip()!='PHASE':raise RuntimeError('missing phase acknowledgement')
        phase_ack_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        time.sleep(drain);server_sample=process_stats(server.pid)
        stop_command_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC);server.stdin.write('S');server.stdin.flush()
        sout,serr=server.communicate(timeout=5)
        if server.returncode:raise RuntimeError('server failed '+serr)
        time.sleep(collector_drain);collector.stdin.write('S');collector.stdin.flush();cout,cerr=collector.communicate(timeout=8)
        if collector.returncode:raise RuntimeError('collector failed '+cerr)
        after=udp_stats();g=json.loads(genfile.read_text());c=json.loads(collectfile.read_text())
        metrics={k:int(v) for k,v in (line.split('=') for line in serr.splitlines() if '=' in line)}
        required=('received','accepted_valid','invalid','wrong_ssrc','truncated','send_attempted','send_succeeded','send_failed','stop_reason','phase_received','phase_valid','phase_seen')
        if any(k not in metrics for k in required) or metrics['phase_seen']!=1 or metrics['stop_reason']!=1:raise RuntimeError('incorrect control report '+repr(metrics))
        if metrics['received']!=sum(metrics[k] for k in ('accepted_valid','invalid','wrong_ssrc','truncated')) or metrics['send_attempted']!=metrics['send_succeeded']+metrics['send_failed'] or metrics['send_attempted']!=metrics['accepted_valid']*n or metrics['phase_received']>metrics['received']:raise RuntimeError('counter mismatch '+repr(metrics))
        if c['invalid'] or c['duplicates']:raise RuntimeError('invalid or duplicate received')
        histogram={};unique=0;record=struct.Struct('=QIHH')
        with recordsfile.open('rb') as f:
            while True:
                chunk=f.read(record.size*8192)
                if not chunk:break
                if len(chunk)%record.size:raise RuntimeError('invalid collector record')
                for stamp,seq,receiver,source in record.iter_unpack(chunk):
                    if receiver>=n or source!=port or seq>=packets or not g['times_ns'][seq]:raise RuntimeError('bad output record')
                    delta=stamp-g['times_ns'][seq]
                    if delta<0:raise RuntimeError('clock order mismatch')
                    bucket=delta//100000
                    histogram[bucket]=histogram.get(bucket,0)+1;unique+=1
        if unique!=c['received']:raise RuntimeError('collector count mismatch')
        def percentile(p):
            goal=(unique*p+99)//100;total=0
            for bucket,count in sorted(histogram.items()):
                total+=count
                if total>=goal:return (bucket+1)/10
            return None
        deltas=None
        if before is not None and after is not None:deltas={k:after[k]-before[k] for k in before.keys() & after.keys()}
        sent=g['sent']
        if unique>metrics['send_succeeded']:raise RuntimeError('observed more outputs than successful sends')
        return {'requested_input_pps':rate,'input_attempted':packets,'generator_sent':sent,'generator_errors':g['send_errors'],'generator_elapsed_s':g['elapsed_s'],
                'generator_intervals_us':[(b-a)/1000 for a,b in zip(g['times_ns'],g['times_ns'][1:]) if a and b],
                'generator_finished_ns':g['finished_ns'],'phase_command_ns':phase_command_ns,'phase_ack_ns':phase_ack_ns,'stop_command_ns':stop_command_ns,'case_start_ns':start_case,'drain_seconds':drain,'collector_drain_seconds':collector_drain,
                'fanout':metrics,'drain_received':metrics['received']-metrics['phase_received'],'collector_unique':unique,
                'collector_missing_from_successful_send':metrics['send_succeeded']-unique,'collector_invalid':c['invalid'],'collector_duplicates':c['duplicates'],
                'latency_histogram_100us':histogram,'latency_percentiles_upper_ms':{'p50':percentile(50),'p95':percentile(95),'p99':percentile(99)},'collector_socket_receive_buffers':collector_config['receive_buffers'],
                'cpu_rss':{'generator':g['usage'],'collector':{'user_s':c['user_s'],'system_s':c['system_s'],'maxrss_bytes':int(c['maxrss_native'] if sys.platform=='darwin' else c['maxrss_native']*1024)},'fanout_start':server_start,'fanout_before_stop':server_sample,'fanout_cpu_delta_s':(server_sample['cpu_seconds']-server_start['cpu_seconds']) if server_sample and server_start else None},
                'udp_host_counters_before':before,'udp_host_counters_after':after,'udp_host_counter_delta':deltas,'termination':'control_pipe'}
    finally:
        stop(generator);stop(server);stop(collector)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--duration',type=int,default=5);p.add_argument('--repeats',type=int,default=3);p.add_argument('--receivers',type=int,default=64);p.add_argument('--rates',type=int,nargs='+',default=[2000,5000,10000]);p.add_argument('--drain',type=float,default=.5);p.add_argument('--collector-drain',type=float,default=1.0);a=p.parse_args()
    if os.name=='nt':p.error('NB1-B control shim is POSIX only')
    if a.output.exists() or not 1<=a.duration<=30 or not 1<=a.repeats<=10 or not 1<=a.receivers<=64 or any(not 1<=r<=100000 for r in a.rates) or not 0<=a.drain<=10 or not 0<=a.collector_drain<=10 or any(r*a.duration>60000 for r in a.rates):p.error('fresh output and bounded positive parameters required')
    report={'status':'incomplete','revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'dirty':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'platform':platform.platform(),'python':sys.version,'clang':subprocess.check_output(['clang','--version'],text=True).splitlines()[0],'parameters':{'duration_s':a.duration,'repeats':a.repeats,'receivers':a.receivers,'rates':a.rates,'drain_s':a.drain,'collector_drain_s':a.collector_drain},'samples':[],
            'limits':['Benchmark-only POSIX control adapter changes UDP receive boundary; not production runtime','Control D is processed after generator exits and may lag last offered packet; phase boundary is observation by fanout','No strict per-core affinity or independent machine; native collector, generator and fanout still compete for CPU','Warmup uses separate short-lived processes; does not warm measured process state','Generator and collector CPU/RSS include process startup; fanout CPU is sampled, includes drain','Latency percentiles are 100us histogram bucket upper bounds; raw per-packet timestamps are not persisted','OS UDP counters are host-wide and may include unrelated traffic','Fanout RSS and CPU are live ps samples, not peak; time resolution platform-dependent','UDP loss before phase observation cannot distinguish late/reordered packets','Latency excludes lost datagrams; monotonic clock shared on one machine','Collector stops after a bounded drain; missing observations can include packets still queued at stop']}
    try:
        with tempfile.TemporaryDirectory(prefix='liza-nb1b-') as tmp:
            tmp=Path(tmp);bins={'liza':tmp/'liza','c':tmp/'c'};collector_binary=tmp/'collector'
            report['build_commands']=[nb1b_build.build(ROOT,bins['liza']),['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DNB1B_CONTROL',str(common.SOURCE),'-o',str(bins['c'])]]
            subprocess.run(report['build_commands'][1],cwd=ROOT,check=True)
            collector_cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'benchmarks/udp-fanout/nb1c_collector.c'),'-o',str(collector_binary)]
            subprocess.run(collector_cmd,cwd=ROOT,check=True);report['build_commands'].append(collector_cmd)
            paths=[common.SOURCE,common.LIZA,ROOT/'examples/apps/rtp/packet.liza',ROOT/'examples/apps/rtp/receivers.liza',ROOT/'benchmarks/udp-fanout/controlled_runtime.c',ROOT/'benchmarks/udp-fanout/nb1b_build.py',WORKER,Path(__file__),Path(common.__file__),ROOT/'benchmarks/udp-fanout/nb1c_collector.c']
            report['source_sha256']={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
            report['binary_sha256']={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in {**bins,'collector':collector_binary}.items()}
            # Separate warmup processes exercise code and OS paths; measured
            # processes are newly started, so this is not in-process warmup.
            report['warmup']=[]
            for name in bins:
                folder=tmp/('warmup-'+name);folder.mkdir()
                row=trial(bins[name],collector_binary,min(a.receivers,16),300,1000,.2,folder)
                if row['fanout']['received']!=300 or row['collector_unique']!=300*min(a.receivers,16):raise RuntimeError('warmup correctness failure')
                report['warmup'].append({'variant':name,'received':row['fanout']['received'],'collector_unique':row['collector_unique']})
            buffer_configuration=None
            for repeat in range(a.repeats):
                cases=[(k,rate) for k in bins for rate in a.rates];random.Random(9183+repeat).shuffle(cases)
                for name,rate in cases:
                    folder=tmp/(name+'-'+str(rate)+'-'+str(repeat));folder.mkdir()
                    try:
                        row=trial(bins[name],collector_binary,a.receivers,rate*a.duration,rate,a.drain,folder,a.collector_drain)
                    except Exception as error:
                        report['samples'].append({'variant':name,'repeat':repeat,'requested_input_pps':rate,'termination':'forced_or_failed','error':repr(error)})
                        raise
                    config=(row['fanout'].get('socket_rcvbuf'),row['fanout'].get('socket_sndbuf'))
                    if None in config:raise RuntimeError('missing actual fanout socket buffer sizes')
                    if buffer_configuration is None:buffer_configuration=config
                    if config!=buffer_configuration:raise RuntimeError('fanout socket buffer sizes differ between runs')
                    row.update(variant=name,repeat=repeat);report['samples'].append(row)
                    print(name,rate,'received',row['fanout']['received'],'drain',row['drain_received'],'collector',row['collector_unique'],flush=True)
                    a.output.write_text(json.dumps(report,indent=2)+'\n')
            report['status']='measured'
    except Exception as e:
        report['error']=repr(e);raise
    finally:a.output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
