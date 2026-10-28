#!/usr/bin/env python3
"""Loopback exploratory L4 comparison. Run on an otherwise idle machine."""
import argparse, concurrent.futures, hashlib, json, platform, random, signal, socket, subprocess, tempfile, threading, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def receive(sock, length):
    out=bytearray()
    while len(out)<length:
        chunk=sock.recv(min(65536,length-len(out)))
        if not chunk: raise RuntimeError('unexpected EOF')
        out.extend(chunk)
    return bytes(out)

def run_case(exe, kind, clients, mode, size):
    upstream=socket.socket(); upstream.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    upstream.bind(('127.0.0.1',0)); upstream.listen(16); upstream.settimeout(15)
    port=upstream.getsockname()[1]
    args=[str(exe),str(port)] if kind=='c' else [str(exe),'--ephemeral','--upstream',f'127.0.0.1:{port}']
    process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        line=process.stdout.readline(); listen=int(line.strip())
        barrier=threading.Barrier(clients)
        failures=[]
        def echo():
            try:
                conn,_=upstream.accept()
                with conn:
                    conn.settimeout(30)
                    while True:
                        data=conn.recv(65536)
                        if not data: conn.shutdown(socket.SHUT_WR); break
                        conn.sendall(data)
            except Exception as e: failures.append(repr(e))
        servers=[threading.Thread(target=echo,daemon=True) for _ in range(clients)]
        for t in servers:t.start()
        payload=bytes(range(256))*(size//256)+bytes(range(size%256))
        def client(_):
            with socket.create_connection(('127.0.0.1',listen),timeout=15) as s:
                s.settimeout(30);barrier.wait(timeout=15); start=time.perf_counter_ns(); latency=[]
                if mode=='latency':
                    for _ in range(100):
                        t=time.perf_counter_ns();s.sendall(payload)
                        if receive(s,len(payload))!=payload:raise RuntimeError('payload mismatch')
                        latency.append((time.perf_counter_ns()-t)/1e6)
                else:
                    errors=[]
                    def send():
                        try:s.sendall(payload);s.shutdown(socket.SHUT_WR)
                        except Exception as e:errors.append(repr(e))
                    t=threading.Thread(target=send);t.start()
                    if receive(s,len(payload))!=payload: raise RuntimeError('payload mismatch')
                    t.join(timeout=30)
                    if t.is_alive() or errors:raise RuntimeError(f'sender failed {errors}')
                    if s.recv(1)!=b'':raise RuntimeError('missing half-close EOF')
                if mode=='latency':
                    s.shutdown(socket.SHUT_WR)
                    if s.recv(1)!=b'':raise RuntimeError('missing half-close EOF')
                return {'seconds':(time.perf_counter_ns()-start)/1e9,'latencies_ms':latency}
        start=time.perf_counter_ns()
        with concurrent.futures.ThreadPoolExecutor(max_workers=clients) as pool: rows=list(pool.map(client,range(clients)))
        seconds=(time.perf_counter_ns()-start)/1e9
        for t in servers:t.join(timeout=5)
        if failures or any(t.is_alive() for t in servers):raise RuntimeError(f'upstream failure {failures}')
        return {'seconds_including_connect':seconds,'clients':rows,'bytes_each_direction':clients*size*(100 if mode=='latency' else 1)}
    finally:
        upstream.close(); process.send_signal(signal.SIGTERM)
        try:out,err=process.communicate(timeout=8)
        except subprocess.TimeoutExpired:process.kill();out,err=process.communicate();raise RuntimeError('proxy did not stop')
        if process.returncode!=0:raise RuntimeError(f'proxy failed: {process.returncode} {err}')

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--repeats',type=int,default=5);a=p.parse_args()
    if a.output.exists() or a.repeats<1:p.error('output must be new and repeats positive')
    with tempfile.TemporaryDirectory(prefix='liza-net-bench-') as tmp:
        tmp=Path(tmp); liza=tmp/'liza-proxy'; c=tmp/'c-proxy'
        commands=[['python3','-m','liza','build','examples/apps/liza_proxy_ops.liza','-O','2','-o',str(liza)],['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'benchmarks/network/relay.c'),'-o',str(c)]]
        for cmd in commands:subprocess.run(cmd,cwd=ROOT,check=True)
        binaries={'liza':liza,'c':c};results=[]
        cases=[(kind,clients,mode) for kind in binaries for clients in (1,8) for mode in ('throughput','latency')]
        for repeat in range(a.repeats):
            random.Random(9183+repeat).shuffle(cases)
            for kind,clients,mode in cases:
                size=1048576 if mode=='throughput' else 64
                row=run_case(binaries[kind],kind,clients,mode,size)
                row.update(kind=kind,concurrency=clients,mode=mode,repeat=repeat)
                results.append(row);print(kind,clients,mode,repeat,flush=True)
        report={'status':'measured','machine':platform.platform(),'processor':platform.processor(),'git':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'clang':subprocess.check_output(['clang','--version'],text=True).splitlines()[0], 'commands':commands,
                'working_tree_status':subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True),
                'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'benchmarks/network/relay.c',ROOT/'benchmarks/network/run.py']},
                'binary_sha256':{k:hashlib.sha256(v.read_bytes()).hexdigest() for k,v in binaries.items()},'samples':results,
                'limitations':['Loopback; Python clients and echo servers share the machine.','C relay lacks Liza operational idle/connect deadlines, drain and metrics; core relay comparison only.','Throughput includes connection setup and is round-trip bytes per direction; not NIC throughput.']}
        a.output.write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
