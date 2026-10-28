#!/usr/bin/env python3
"""Single-thread real UDP fanout comparison; correctness gate before timing."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import selectors
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'benchmarks/udp-fanout/fanout.c'
LIZA = ROOT / 'examples/apps/rtp_fanout.liza'
SSRC = 0x10203040


def packet(seq, payload=1188, ssrc=SSRC):
    # 12-byte RTP header plus payload; sequence is stored in both RTP and payload.
    if payload < 4: raise ValueError('payload must be at least four bytes')
    return struct.pack('!BBHII', 0x80, 96, seq & 65535, seq, ssrc) + struct.pack('!I', seq) + bytes([seq & 255]) * (payload - 4)


def sockets(count):
    clients=[]
    for _ in range(count):
        s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));s.setblocking(False);clients.append(s)
    return clients


def run_case(binary, payloads, expected, receiver_count, interval, timeout=8, ssrc=SSRC):
    receivers=sockets(receiver_count);ports=[str(s.getsockname()[1]) for s in receivers]
    proc=subprocess.Popen([str(binary),str(len(payloads)),str(ssrc),*ports],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    send_sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    selector=selectors.DefaultSelector()
    for i,s in enumerate(receivers):selector.register(s,selectors.EVENT_READ,i)
    ready=threading.Event();stop=threading.Event();errors=[];received=[];durations=[];sent_times={}
    try:
        result=[]
        threading.Thread(target=lambda:result.append(proc.stdout.readline()),daemon=True).start()
        deadline=time.monotonic()+10
        while not result and proc.poll() is None and time.monotonic()<deadline:time.sleep(.01)
        if not result:raise RuntimeError('server did not report listener port')
        try:port=int(result[0].strip())
        except ValueError:raise RuntimeError('invalid server port: '+repr(result[0]))
        def collect():
            ready.set()
            try:
                while not stop.is_set():
                    for key,_ in selector.select(.025):
                        try:data,source=key.fileobj.recvfrom(65535)
                        except BlockingIOError:continue
                        received.append((key.data,data,source[1],time.perf_counter_ns()))
            except Exception as e:errors.append(repr(e))
        thread=threading.Thread(target=collect);thread.start();ready.wait(2)
        start=time.perf_counter_ns()
        for index,data in enumerate(payloads):
            sent_times[index]=time.perf_counter_ns()
            send_sock.sendto(data,('127.0.0.1',port))
            if interval:
                deadline=(start/1e9)+(index+1)*interval
                time.sleep(max(0,deadline-time.perf_counter()))
        out,err=proc.communicate(timeout=timeout)
        until=time.monotonic()+1.0
        while len(received)<len(expected)*receiver_count and time.monotonic()<until:time.sleep(.005)
        stop.set();thread.join(timeout=3)
        if thread.is_alive() or errors:raise RuntimeError('collector failure: '+repr(errors))
        if proc.returncode:raise RuntimeError(f'fanout failed: {proc.returncode}, {err}')
        wanted={(i,payload) for i in range(receiver_count) for payload in expected}
        actual=[(i,data) for i,data,source,_ in received]
        # Data in each test case is deliberately unique, so duplicate observations are unambiguous.
        if any(source!=port for _,_,source,_ in received):raise RuntimeError('wrong UDP source port')
        unknown=set(actual)-wanted
        missing=wanted-set(actual)
        duplicates=len(actual)-len(set(actual))
        if unknown or missing or duplicates:raise RuntimeError(f'fanout mismatch unknown={len(unknown)} missing={len(missing)} duplicates={duplicates}')
        mapping={data:i for i,data in enumerate(payloads)}
        for _,data,_,stamp in received:
            durations.append((stamp-sent_times[mapping[data]])/1e6)
        elapsed=(time.perf_counter_ns()-start)/1e9
        return {'input_count':len(payloads),'valid_count':len(expected),'receiver_count':receiver_count,'output_received':len(actual),'elapsed_including_drain_s':elapsed,
                'latencies_ms':durations,'duplicates':duplicates,'missing':len(missing),'unknown':len(unknown)}
    finally:
        stop.set()
        if proc.poll() is None:proc.kill();proc.communicate()
        send_sock.close();selector.close()
        for s in receivers:s.close()


def correctness(binary):
    valid=packet(1,20)
    valid_extension=bytes([0x91,96,0,2,0,0,0,2,0x10,0x20,0x30,0x40])+bytes([0,0,0,3])+bytes([0,0,0,1,0,0,0,0])+b'PAYLOAD!'
    valid_padding=bytes([0xa0,96,0,3,0,0,0,3,0x10,0x20,0x30,0x40])+b'abc\x02\x02'
    invalid=[b'',b'\x80'*11,bytes([0x40])+valid[1:],valid[:8]+b'\0\0\0\1'+valid[12:],
             bytes([0x8f])+valid[1:12],bytes([0x90])+valid[1:12]+b'\0\0\0\x01',
             bytes([0xa0])+valid[1:12]+b'\x00',packet(9,2037)]
    payloads=[valid,invalid[0],valid_extension,*invalid[1:4],valid_padding,*invalid[4:]]
    base=run_case(binary,payloads,[valid,valid_extension,valid_padding],3,.003)
    high=packet(8,20,0xffffffff)
    upper=run_case(binary,[high],[high],1,.003,ssrc=0xffffffff)
    return {'rtp_cases':base,'full_ssrc':upper}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--repeats',type=int,default=5)
    parser.add_argument('--receivers',type=int,default=8);parser.add_argument('--packets',type=int,default=200)
    parser.add_argument('--pps',type=int,default=100);parser.add_argument('--check-only',action='store_true')
    a=parser.parse_args()
    if a.output.exists() or not 1<=a.receivers<=64 or not 1<=a.packets<=60000 or not 1<=a.pps<=10000 or a.repeats<1:parser.error('fresh output and valid positive bounded arguments required')
    if not LIZA.exists():parser.error('Liza fanout application is missing: '+str(LIZA))
    with tempfile.TemporaryDirectory(prefix='liza-udp-fanout-') as d:
        d=Path(d);bins={'liza':d/('liza.exe' if os.name=='nt' else 'liza'),'c':d/('c.exe' if os.name=='nt' else 'c')}
        ccmd=['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(SOURCE),'-o',str(bins['c'])]
        lcmd=[sys.executable,'-m','liza','build',str(LIZA),'-O','2','-o',str(bins['liza'])]
        for cmd in (ccmd,lcmd):subprocess.run(cmd,cwd=ROOT,check=True)
        checks={name:correctness(binary) for name,binary in bins.items()}
        print('Correctness gate passed for C and Liza',flush=True)
        samples=[]
        if not a.check_only:
            for repeat in range(a.repeats):
                variants=list(bins);random.Random(9183+repeat).shuffle(variants)
                for name in variants:
                    data=[packet(i) for i in range(a.packets)]
                    row=run_case(bins[name],data,data,a.receivers,1/a.pps,timeout=max(8,a.packets/a.pps+8));row.update(variant=name,repeat=repeat);samples.append(row)
                    print(name,repeat,'received',row['output_received'],flush=True)
        report={'status':'correctness_passed' if a.check_only else 'measured','commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'dirty':subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),'platform':platform.platform(),'python':platform.python_version(),
                'clang':subprocess.check_output(['clang','--version'],text=True).splitlines()[0], 'commands':[ccmd,lcmd],
                'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE,LIZA,ROOT/'examples/apps/rtp/packet.liza',ROOT/'examples/apps/rtp/receivers.liza',Path(__file__))},
                'binary_sha256':{n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in bins.items()},'correctness':checks,'samples':samples,
                'limits':['Single host loopback; Python sender and collector share CPU with process','Low-rate paced latency probe, not max throughput or production fanout','Only complete-delivery runs accepted; no attribution of drops','No process CPU, RSS or syscall measurements','C reference POSIX only; not Windows']}
        a.output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
