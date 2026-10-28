#!/usr/bin/env python3
"""Open-loop loopback stress pilot. Loss is recorded rather than rejected."""
import argparse,hashlib,json,os,platform,random,selectors,socket,struct,subprocess,sys,tempfile,threading,time
from pathlib import Path
import run as baseline
ROOT=Path(__file__).resolve().parents[2]

def trial(exe,receivers,packets,rate):
    clients=baseline.sockets(receivers);sel=selectors.DefaultSelector()
    for i,s in enumerate(clients):sel.register(s,selectors.EVENT_READ,i)
    p=subprocess.Popen([str(exe),str(packets),str(baseline.SSRC),*[str(s.getsockname()[1]) for s in clients]],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    sender=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);done=threading.Event();ready=threading.Event()
    seen=set();times=[0]*packets;latencies=[];duplicates=0;invalid=0;errors=[];collector=None
    try:
        lines=[];threading.Thread(target=lambda:lines.append(p.stdout.readline()),daemon=True).start()
        deadline=time.monotonic()+10
        while not lines and p.poll() is None and time.monotonic()<deadline:time.sleep(.01)
        if not lines:raise RuntimeError('listener failed to start')
        port=int(lines[0].strip())
        def collect():
            nonlocal duplicates,invalid
            ready.set()
            try:
                while not done.is_set():
                    for key,_ in sel.select(.02):
                        try:data,source=key.fileobj.recvfrom(65535)
                        except BlockingIOError:continue
                        if len(data)!=1200 or source[1]!=port:invalid+=1;continue
                        seq=struct.unpack('!I',data[12:16])[0]
                        if seq>=packets or data!=baseline.packet(seq):invalid+=1;continue
                        ident=(key.data,seq)
                        if ident in seen:duplicates+=1;continue
                        seen.add(ident)
                        if times[seq]:latencies.append((time.perf_counter_ns()-times[seq])/1e6)
            except Exception as e:errors.append(repr(e))
        collector=threading.Thread(target=collect);collector.start()
        if not ready.wait(5):raise RuntimeError('collector startup timeout')
        start=time.perf_counter_ns();sent=0
        for i in range(packets):
            target=start+int(i*1e9/rate);delay=(target-time.perf_counter_ns())/1e9
            if delay>0:time.sleep(delay)
            data=baseline.packet(i);times[i]=time.perf_counter_ns()
            if sender.sendto(data,('127.0.0.1',port))!=len(data):raise RuntimeError('short send')
            sent+=1
        offered_s=(time.perf_counter_ns()-start)/1e9
        try:out,err=p.communicate(timeout=2);exited=True
        except subprocess.TimeoutExpired:p.terminate();out,err=p.communicate(timeout=5);exited=False
        time.sleep(.2);done.set();collector.join(5)
        if collector.is_alive() or errors:raise RuntimeError('collector error '+repr(errors))
        values=sorted(latencies)
        return {'requested_input_pps':rate,'input_sent':sent,'offered_duration_s':offered_s,'actual_offered_pps':sent/offered_s,
                'receivers':receivers,'expected_outputs':sent*receivers,'unique_outputs':len(seen),'missing_outputs':sent*receivers-len(seen),
                'duplicate_outputs':duplicates,'invalid_outputs':invalid,'process_exited_normally':exited and p.returncode==0,
                'process_returncode':p.returncode,'stderr':err[-1000:],
                'latencies_ms':latencies,'p50_ms':values[len(values)//2] if values else None,'p99_ms':values[max(0,(len(values)*99+99)//100-1)] if values else None}
    finally:
        done.set()
        if p.poll() is None:p.kill();p.communicate()
        if collector is not None:collector.join(5)
        sender.close();sel.close()
        for s in clients:s.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--packets',type=int,default=1000);ap.add_argument('--repeats',type=int,default=3);a=ap.parse_args()
    if a.output.exists() or not 1<=a.packets<=60000 or not 1<=a.repeats<=10:ap.error('fresh output and valid packet and repeat counts required')
    report={'status':'incomplete','platform':platform.platform(),'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'dirty':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'samples':[],
       'limits':['Loopback only; Python sender/collector competes with server','Input reaching server is not measured; missing output cannot be assigned to sender, kernel, server or collector','Latency excludes lost datagrams and is subject to collector scheduling','A timed-out server is terminated because finite input count cannot distinguish dropped input','No process CPU, OS drop counters or syscall counts','C and Liza use different internal lookup paths']}
    try:
        with tempfile.TemporaryDirectory(prefix='liza-udp-load-') as d:
            bins={'liza':Path(d)/'liza','c':Path(d)/'c'}
            cmds=[[sys.executable,'-m','liza','build',str(baseline.LIZA),'-O','2','-o',str(bins['liza'])],['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(baseline.SOURCE),'-o',str(bins['c'])]]
            for cmd in cmds:subprocess.run(cmd,cwd=ROOT,check=True)
            report['commands']=cmds;report['clang']=subprocess.check_output(['clang','--version'],text=True).splitlines()[0]
            paths=[baseline.SOURCE,baseline.LIZA,ROOT/'examples/apps/rtp/packet.liza',ROOT/'examples/apps/rtp/receivers.liza',Path(__file__),Path(baseline.__file__)]
            report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
            report['binary_sha256']={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in bins.items()}
            report['correctness']={name:baseline.correctness(exe) for name,exe in bins.items()}
            print('correctness passed',flush=True)
            cases=[(name,n,rate) for name in bins for n in (16,64) for rate in (500,1000,3000)]
            for repeat in range(a.repeats):
                random.Random(9183+repeat).shuffle(cases)
                for name,n,rate in cases:
                    row=trial(bins[name],n,a.packets,rate);row.update(variant=name,repeat=repeat);report['samples'].append(row)
                    print(name,n,rate,'received',row['unique_outputs'],'/',row['expected_outputs'],'exit',row['process_exited_normally'],flush=True)
                    a.output.write_text(json.dumps(report,indent=2)+'\n')
            report['status']='measured'
    finally:a.output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
