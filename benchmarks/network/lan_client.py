import socket,threading,time,json,sys,concurrent.futures
host,port,count,mode=sys.argv[1],int(sys.argv[2]),int(sys.argv[3]),sys.argv[4]
barrier=threading.Barrier(count)
payload=bytes(range(256))*32768 if mode=='throughput' else bytes(range(64))
def recv(s,n):
 out=bytearray()
 while len(out)<n:
  b=s.recv(min(65536,n-len(out)))
  if not b:raise ValueError('unexpected EOF')
  out.extend(b)
 return out
def go(i):
 with socket.create_connection((host,port),timeout=20) as s:
  s.settimeout(60);barrier.wait(timeout=20);start=time.perf_counter_ns();samples=[]
  if mode=='latency':
   for _ in range(200):
    t=time.perf_counter_ns();s.sendall(payload)
    if recv(s,len(payload))!=payload:raise ValueError('incorrect payload')
    samples.append((time.perf_counter_ns()-t)/1e6)
   s.shutdown(socket.SHUT_WR)
  else:
   errors=[]
   def send():
    try:s.sendall(payload);s.shutdown(socket.SHUT_WR)
    except Exception as e:errors.append(repr(e))
   t=threading.Thread(target=send);t.start()
   if recv(s,len(payload))!=payload:raise ValueError('incorrect payload')
   t.join(60)
   if t.is_alive() or errors:raise ValueError(str(errors))
  if s.recv(1)!=b'':raise ValueError('missing EOF')
  return {'seconds':(time.perf_counter_ns()-start)/1e9,'latency_ms':samples}
with concurrent.futures.ThreadPoolExecutor(max_workers=count) as pool: rows=list(pool.map(go,range(count)))
print(json.dumps({'clients':rows,'bytes_each_direction':len(payload)*count*(200 if mode=='latency' else 1)}))
