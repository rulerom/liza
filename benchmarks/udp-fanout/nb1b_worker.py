#!/usr/bin/env python3
"""Generator and collector processes for the NB1-B loopback experiment."""
import json,os,resource,selectors,socket,struct,sys,time
from pathlib import Path
import run as common

def usage():
    r=resource.getrusage(resource.RUSAGE_SELF)
    return {'user_s':r.ru_utime,'system_s':r.ru_stime,'maxrss_bytes':int(r.ru_maxrss if sys.platform=='darwin' else r.ru_maxrss*1024)}

def generator(port,packets,pps,destination):
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);start=time.clock_gettime_ns(time.CLOCK_MONOTONIC);times=[];errors=[]
    try:
        for i in range(packets):
            delay=(start+int(i*1e9/pps)-time.clock_gettime_ns(time.CLOCK_MONOTONIC))/1e9
            if delay>0:time.sleep(delay)
            data=common.packet(i);timestamp=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
            try:
                n=sock.sendto(data,('127.0.0.1',port))
                if n!=len(data):raise OSError('short send')
                times.append(timestamp)
            except OSError as e:times.append(0);errors.append({'seq':i,'error':str(e)})
    finally:sock.close()
    finished_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
    elapsed=(finished_ns-start)/1e9
    Path(destination).write_text(json.dumps({'finished_ns':finished_ns,'times_ns':times,'offered':packets,'sent':sum(bool(t) for t in times),'send_errors':errors,'elapsed_s':elapsed,'usage':usage()}))

def collector(n,packets,destination):
    sockets=common.sockets(n);selector=selectors.DefaultSelector()
    for i,s in enumerate(sockets):selector.register(s,selectors.EVENT_READ,i)
    selector.register(sys.stdin,selectors.EVENT_READ,-1)
    received=[];invalid=0;duplicates=0;seen=set();print(json.dumps({'ports':[s.getsockname()[1] for s in sockets]}),flush=True)
    try:
        running=True
        while running:
            for key,_ in selector.select(.05):
                if key.data==-1:
                    command=os.read(0,1)
                    if command!=b'S':raise RuntimeError('invalid collector stop')
                    running=False;break
                try:data,peer=key.fileobj.recvfrom(65535)
                except BlockingIOError:continue
                stamp=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
                if len(data)!=1200:invalid+=1;continue
                seq=struct.unpack('!I',data[12:16])[0]
                if seq>=packets or data!=common.packet(seq):invalid+=1;continue
                key_id=(key.data,seq)
                if key_id in seen:duplicates+=1;continue
                seen.add(key_id);received.append([key.data,seq,stamp,peer[1]])
    finally:
        selector.close()
        for s in sockets:s.close()
    Path(destination).write_text(json.dumps({'received':received,'invalid':invalid,'duplicates':duplicates,'usage':usage()}))

if __name__=='__main__':
    if sys.argv[1]=='generator':generator(int(sys.argv[2]),int(sys.argv[3]),int(sys.argv[4]),sys.argv[5])
    elif sys.argv[1]=='collector':collector(int(sys.argv[2]),int(sys.argv[3]),sys.argv[4])
    else:raise SystemExit('unknown role')
