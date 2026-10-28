#!/usr/bin/env python3
"""Separate-process loopback fanout diagnostic with a separate control pipe."""
import argparse,hashlib,json,os,platform,random,re,subprocess,sys,tempfile,time
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

def trial(binary,n,packets,rate,drain,folder):
    collector=server=generator=None
    collectfile=folder/'collector.json';genfile=folder/'generator.json'
    before=udp_stats();start_case=time.monotonic_ns()
    try:
        collector=subprocess.Popen([sys.executable,str(WORKER),'collector',str(n),str(packets),str(collectfile)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
        ports=json.loads(start_line(collector))['ports']
        server=subprocess.Popen([str(binary),'2147483647',str(common.SSRC),*map(str,ports)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
        port=int(start_line(server));server_start=process_stats(server.pid)
        generator=subprocess.Popen([sys.executable,str(WORKER),'generator',str(port),str(packets),str(rate),str(genfile)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=ROOT)
        gout,gerr=generator.communicate(timeout=max(10,packets/rate+10))
        if generator.returncode:raise RuntimeError('generator failed '+gerr)
        phase_command_ns=time.monotonic_ns();server.stdin.write('D');server.stdin.flush()
        if start_line(server).strip()!='PHASE':raise RuntimeError('missing phase acknowledgement')
        phase_ack_ns=time.monotonic_ns()
        time.sleep(drain);server_sample=process_stats(server.pid)
        stop_command_ns=time.monotonic_ns();server.stdin.write('S');server.stdin.flush()
        sout,serr=server.communicate(timeout=5)
        if server.returncode:raise RuntimeError('server failed '+serr)
        time.sleep(.2);collector.stdin.write('S');collector.stdin.flush();cout,cerr=collector.communicate(timeout=8)
        if collector.returncode:raise RuntimeError('collector failed '+cerr)
        after=udp_stats();g=json.loads(genfile.read_text());c=json.loads(collectfile.read_text())
        metrics={k:int(v) for k,v in (line.split('=') for line in serr.splitlines() if '=' in line)}
        required=('received','accepted_valid','invalid','wrong_ssrc','truncated','send_attempted','send_succeeded','send_failed','stop_reason','phase_received','phase_valid','phase_seen')
        if any(k not in metrics for k in required) or metrics['phase_seen']!=1 or metrics['stop_reason']!=1:raise RuntimeError('incorrect control report '+repr(metrics))
        if metrics['received']!=sum(metrics[k] for k in ('accepted_valid','invalid','wrong_ssrc','truncated')) or metrics['send_attempted']!=metrics['send_succeeded']+metrics['send_failed'] or metrics['send_attempted']!=metrics['accepted_valid']*n or metrics['phase_received']>metrics['received']:raise RuntimeError('counter mismatch '+repr(metrics))
        if c['invalid'] or c['duplicates']:raise RuntimeError('invalid or duplicate received')
        if any(row[3]!=port for row in c['received']):raise RuntimeError('wrong source port')
        latencies=[(row[2]-g['times_ns'][row[1]])/1e6 for row in c['received'] if g['times_ns'][row[1]]]
        if any(x<0 for x in latencies):raise RuntimeError('clock order mismatch')
        values=sorted(latencies);deltas=None
        if before is not None and after is not None:deltas={k:after[k]-before[k] for k in before.keys() & after.keys()}
        sent=g['sent'];unique=len(c['received'])
        if unique>metrics['send_succeeded']:raise RuntimeError('observed more outputs than successful sends')
        return {'requested_input_pps':rate,'input_attempted':packets,'generator_sent':sent,'generator_errors':g['send_errors'],'generator_elapsed_s':g['elapsed_s'],
                'generator_intervals_us':[(b-a)/1000 for a,b in zip(g['times_ns'],g['times_ns'][1:]) if a and b],
                'generator_finished_ns':g['finished_ns'],'phase_command_ns':phase_command_ns,'phase_ack_ns':phase_ack_ns,'stop_command_ns':stop_command_ns,'case_start_ns':start_case,'drain_seconds':drain,
                'fanout':metrics,'drain_received':metrics['received']-metrics['phase_received'],'collector_unique':unique,
                'collector_missing_from_successful_send':metrics['send_succeeded']-unique,'collector_invalid':c['invalid'],'collector_duplicates':c['duplicates'],
                'latencies_ms':latencies,'p50_ms':values[len(values)//2] if values else None,'p99_ms':values[max(0,(len(values)*99+99)//100-1)] if values else None,
                'cpu_rss':{'generator':g['usage'],'collector':c['usage'],'fanout_start':server_start,'fanout_before_stop':server_sample,'fanout_cpu_delta_s':(server_sample['cpu_seconds']-server_start['cpu_seconds']) if server_sample and server_start else None},
                'udp_host_counters_before':before,'udp_host_counters_after':after,'udp_host_counter_delta':deltas,'termination':'control_pipe'}
    finally:
        stop(generator);stop(server);stop(collector)

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--packets',type=int,default=1000);p.add_argument('--repeats',type=int,default=3);p.add_argument('--receivers',type=int,default=64);p.add_argument('--rates',type=int,nargs='+',default=[5000,10000,20000]);p.add_argument('--drain',type=float,default=.5);a=p.parse_args()
    if os.name=='nt':p.error('NB1-B control shim is POSIX only')
    if a.output.exists() or not 1<=a.packets<=60000 or not 1<=a.repeats<=10 or not 1<=a.receivers<=64 or any(not 1<=r<=100000 for r in a.rates) or not 0<=a.drain<=10:p.error('fresh output and bounded positive parameters required')
    report={'status':'incomplete','revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'dirty':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'platform':platform.platform(),'samples':[],
            'limits':['Benchmark-only POSIX control adapter changes UDP receive boundary; not production runtime','Control D is processed after generator exits and may lag last offered packet; phase boundary is observation by fanout','No strict per-core affinity or independent machine; processes compete for CPU','Generator and collector CPU/RSS include process startup; fanout CPU is sampled, includes drain','OS UDP counters are host-wide and may include unrelated traffic','Fanout RSS and CPU are live ps samples, not peak; time resolution platform-dependent','UDP loss before phase observation cannot distinguish late/reordered packets','Latency excludes lost datagrams; monotonic clock shared on one machine']}
    try:
        with tempfile.TemporaryDirectory(prefix='liza-nb1b-') as tmp:
            tmp=Path(tmp);bins={'liza':tmp/'liza','c':tmp/'c'}
            report['build_commands']=[nb1b_build.build(ROOT,bins['liza']),['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-DNB1B_CONTROL',str(common.SOURCE),'-o',str(bins['c'])]]
            subprocess.run(report['build_commands'][1],cwd=ROOT,check=True)
            paths=[common.SOURCE,common.LIZA,ROOT/'examples/apps/rtp/packet.liza',ROOT/'examples/apps/rtp/receivers.liza',ROOT/'benchmarks/udp-fanout/controlled_runtime.c',ROOT/'benchmarks/udp-fanout/nb1b_build.py',WORKER,Path(__file__),Path(common.__file__)]
            report['source_sha256']={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths}
            report['binary_sha256']={k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in bins.items()}
            for repeat in range(a.repeats):
                cases=[(k,rate) for k in bins for rate in a.rates];random.Random(9183+repeat).shuffle(cases)
                for name,rate in cases:
                    folder=tmp/(name+'-'+str(rate)+'-'+str(repeat));folder.mkdir()
                    row=trial(bins[name],a.receivers,a.packets,rate,a.drain,folder);row.update(variant=name,repeat=repeat);report['samples'].append(row)
                    print(name,rate,'received',row['fanout']['received'],'drain',row['drain_received'],'collector',row['collector_unique'],flush=True)
                    a.output.write_text(json.dumps(report,indent=2)+'\n')
            report['status']='measured'
    except Exception as e:
        report['error']=repr(e);raise
    finally:a.output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
