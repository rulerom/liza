"""Persistent, paced generator: warmup and measurement in the same process."""
import json,resource,socket,struct,sys,time
from pathlib import Path

def packet(seq):return struct.pack('!BBHII',128,96,seq&65535,seq,0x10203040)+struct.pack('!I',seq)+bytes([seq&255])*1184

def main():
    port,packets,rate,warmup=map(int,sys.argv[1:5]);output=Path(sys.argv[5])
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    times=[0]*(packets+warmup);errors=[];phases=[]
    print('READY',flush=True)
    for command,begin,count,pps in [('W',0,warmup,1000),('M',warmup,packets,rate)]:
        if sys.stdin.readline().strip()!=command:raise RuntimeError('phase order')
        start=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        for seq in range(begin,begin+count):
            deadline=start+(seq-begin)*1000000000//pps
            delay=(deadline-time.clock_gettime_ns(time.CLOCK_MONOTONIC))/1e9
            if delay>0:time.sleep(delay)
            data=packet(seq);stamp=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
            try:
                n=sock.sendto(data,('127.0.0.1',port))
                if n!=len(data):raise OSError('short datagram')
                times[seq]=stamp
            except OSError as exc:errors.append({'seq':seq,'error':str(exc)})
        # End the full requested offer window, including the final interpacket interval.
        delay=(start+count*1000000000//pps-time.clock_gettime_ns(time.CLOCK_MONOTONIC))/1e9
        if delay>0:time.sleep(delay)
        phases.append({'command':command,'start_ns':start,'end_ns':time.clock_gettime_ns(time.CLOCK_MONOTONIC)})
        print(command,flush=True)
    r=resource.getrusage(resource.RUSAGE_SELF)
    output.write_text(json.dumps({'times_ns':times,'errors':errors,'phases':phases,'user_s':r.ru_utime,'system_s':r.ru_stime,'maxrss_native':r.ru_maxrss}))
if __name__=='__main__':main()
