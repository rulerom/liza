#!/usr/bin/env python3
"""Limited loopback diagnostic; raw data and correctness accounting, not a capacity test."""
import argparse,json,os,platform,selectors,signal,socket,statistics,struct,subprocess,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def trial(binary,workers,receivers,publishers,packets,pps):
    sockets=[];selector=selectors.DefaultSelector();done=threading.Event(); observed=set();duplicate=0;invalid=0;latencies=[];reordered=0;last={};lock=threading.Lock()
    for i in range(receivers):
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));s.setblocking(False);sockets.append(s);selector.register(s,selectors.EVENT_READ,i)
    p=subprocess.Popen([str(binary),str(workers),'0',*[str(s.getsockname()[1]) for s in sockets]],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        port=int(p.stdout.readline().strip());publisher=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        def collect():
            nonlocal duplicate,invalid,reordered
            while not done.is_set():
                for key,_ in selector.select(.05):
                    try:data=key.fileobj.recv(4096)
                    except BlockingIOError:continue
                    if len(data)!=1200:invalid+=1;continue
                    src,seq,stamp=struct.unpack('!IIQ',data[:16]);expected=bytes([src])*1184
                    if src>=publishers or seq>=packets or data[16:]!=expected:invalid+=1;continue
                    pair=(key.data,src,seq)
                    if pair in observed:duplicate+=1;continue
                    observed.add(pair);prev=last.get((key.data,src),-1)
                    if seq<prev:reordered+=1
                    last[key.data,src]=max(prev,seq);latencies.append((time.monotonic_ns()-stamp)/1e6)
        t=threading.Thread(target=collect);t.start();start=time.monotonic()
        for seq in range(packets):
            for src in range(publishers):
                data=struct.pack('!IIQ',src,seq,time.monotonic_ns())+bytes([src])*1184
                if publisher.sendto(data,('127.0.0.1',port))!=len(data):raise RuntimeError('short UDP send')
            deadline=start+(seq+1)/pps;time.sleep(max(0,deadline-time.monotonic()))
        until=time.monotonic()+2
        while len(observed)<packets*publishers*receivers and time.monotonic()<until:time.sleep(.01)
        done.set();t.join(5);publisher.close()
        if t.is_alive():raise RuntimeError('collector did not stop')
        if invalid or duplicate or reordered:raise RuntimeError(f'invalid={invalid} duplicate={duplicate} reordered={reordered}')
        p.send_signal(signal.SIGTERM);out,err=p.communicate(timeout=5)
        if p.returncode:raise RuntimeError(err)
        stats=json.loads(err.splitlines()[-1]);expected=packets*publishers*receivers
        latencies.sort()
        return {'workers':workers,'mode':'sequential' if workers==0 else 'threaded','receivers':receivers,'publishers':publishers,'input_sent':packets*publishers,'fanout_expected':expected,'fanout_observed':len(observed),'missing':expected-len(observed),'duplicates':duplicate,'invalid':invalid,'reordered':reordered,'sender':stats,'p50_ms':statistics.median(latencies) if latencies else None,'p99_ms':latencies[max(0,int(len(latencies)*.99)-1)] if latencies else None}
    finally:
        done.set()
        if p.poll() is None:p.kill();p.communicate()
        selector.close()
        for s in sockets:s.close()

def main():
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True);a.add_argument('--packets',type=int,default=100);a.add_argument('--pps',type=int,default=100);args=a.parse_args()
    if args.output.exists() or args.packets<=0 or args.pps<=0:a.error('new output, positive packets and pps required')
    with tempfile.TemporaryDirectory(prefix='liza-rtp-') as d:
        exe=Path(d)/'fanout';cmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror','-pthread',str(ROOT/'benchmarks/rtp-fanout/fanout.c'),'-o',str(exe)];subprocess.run(cmd,check=True)
        rows=[]
        for publishers in (1,2):
            for receivers in (16,64):
                for workers in (0,1,2,4,8):
                    row=trial(exe,workers,receivers,publishers,args.packets,args.pps);rows.append(row);print(json.dumps(row),flush=True)
        report={'status':'measured','platform':platform.platform(),'clang':subprocess.check_output(['clang','--version'],text=True).splitlines()[0], 'command':cmd,'results':rows,'limits':['Loopback and shared Python collector; no NIC or isolated CPU measurement','Stop-and-wait one-packet-in-flight design; not Liza or VideoGrace','Packet is a synthetic framed payload, not parsed RTP','Loss can arise in generator, sender, OS, or collector; no attribution','Latency uses same-host monotonic clock; no CPU or syscall metrics','Fixed sequential case order, one run; not a comparative performance baseline']}
        args.output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
