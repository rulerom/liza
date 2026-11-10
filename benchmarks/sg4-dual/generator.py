"""Two independent paced RTP sources with a shared absolute measurement start."""
import importlib.util,json,resource,socket,struct,sys,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('sg4_baseline_generator',Path(__file__).resolve().parents[1]/'sg4-fanout/generator.py')
baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
baseline_packet=baseline.packet

def packet(seq,ssrc):
    data=bytearray(baseline_packet(seq));struct.pack_into('!I',data,8,ssrc);return data

def main():
    ip,port,packets,rate,warmup,ssrc,duration_s,output=sys.argv[1:]
    duration_s=float(duration_s)
    port,packets,rate,warmup,ssrc=map(int,(port,packets,rate,warmup,ssrc))
    if not 0<=packets<=600000 or not 0<=rate<=100000 or (packets>0 and rate==0) or not 0<=warmup<=200:raise ValueError('bounds')
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);times=[0]*(packets+warmup);errors=[];phases=[]
    print('READY',flush=True)
    for cmd,begin,count,pps in [('W',0,warmup,1000),('M',warmup,packets,max(rate,1))]:
        words=sys.stdin.readline().split()
        if not words or words[0]!=cmd:raise RuntimeError('phase order')
        start=int(words[1]) if len(words)==2 else time.clock_gettime_ns(time.CLOCK_MONOTONIC)
        for seq in range(begin,begin+count):
            deadline=start+(seq-begin)*1000000000//pps
            delay=(deadline-time.clock_gettime_ns(time.CLOCK_MONOTONIC))/1e9
            if delay>0:time.sleep(delay)
            data=packet(seq,ssrc);stamp=time.clock_gettime_ns(time.CLOCK_MONOTONIC)
            try:
                if sock.sendto(data,(ip,port))!=len(data):raise OSError('short datagram')
                times[seq]=stamp
            except OSError as exc:errors.append({'seq':seq,'error':str(exc)})
        window_ns=round(duration_s*1e9) if cmd=='M' else count*1000000000//pps
        delay=(start+window_ns-time.clock_gettime_ns(time.CLOCK_MONOTONIC))/1e9
        if delay>0:time.sleep(delay)
        phases.append({'command':cmd,'start_ns':start,'end_ns':time.clock_gettime_ns(time.CLOCK_MONOTONIC)})
        print(cmd,flush=True)
    r=resource.getrusage(resource.RUSAGE_SELF)
    Path(output).write_text(json.dumps({'times_ns':times,'errors':errors,'phases':phases,'user_s':r.ru_utime,'system_s':r.ru_stime,'maxrss_native':r.ru_maxrss}))
if __name__=='__main__':main()
