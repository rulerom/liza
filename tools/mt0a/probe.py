#!/usr/bin/env python3
"""Socket distribution probe, not the Liza reactor or a production gateway."""
import argparse
import json
import platform
import queue
import socket
import threading

class Dispatcher:
    """Queue owns a socket after put succeeds; sender owns it after Full."""
    def __init__(self, workers, capacity):
        if workers < 1 or capacity < 1: raise ValueError('positive limits required')
        self.queues=[queue.Queue(maxsize=capacity) for _ in range(workers)]
        self.sent=[0]*workers;self.full=0;self.next=0
    def submit(self, conn):
        index=self.next;self.next=(index+1)%len(self.queues)
        try:self.queues[index].put_nowait(conn)
        except queue.Full:
            self.full+=1;conn.close();return False
        self.sent[index]+=1;return True
    def discard_pending(self):
        for q in self.queues:
            while True:
                try: conn=q.get_nowait()
                except queue.Empty:break
                conn.close();q.task_done()

def shared(workers,connections,capacity):
    dispatcher=Dispatcher(workers,capacity);received=[0]*workers;errors=[]
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(max(16,connections));listener.settimeout(10)
    stop=threading.Event()
    def worker(i):
        q=dispatcher.queues[i]
        while not stop.is_set() or not q.empty():
            try:conn=q.get(timeout=.05)
            except queue.Empty:continue
            try:
                conn.settimeout(3)
                if conn.recv(1)!=b'X':raise ValueError('wrong payload')
                conn.sendall(bytes([i]));received[i]+=1
            except Exception as e:errors.append(repr(e))
            finally:conn.close();q.task_done()
    threads=[threading.Thread(target=worker,args=(i,)) for i in range(workers)]
    for t in threads:t.start()
    clients=[];answers=[]
    try:
        for _ in range(connections):
            c=socket.create_connection(listener.getsockname(),timeout=5);c.settimeout(5);clients.append(c)
            conn,_=listener.accept();dispatcher.submit(conn)
        for c in clients:
            try:c.sendall(b'X');answers.append(c.recv(1))
            except (OSError,TimeoutError):answers.append(b'')
        for q in dispatcher.queues:q.join()
    finally:
        listener.close()
        for c in clients:c.close()
        stop.set()
        for t in threads:t.join(timeout=5)
        dispatcher.discard_pending()
    if any(t.is_alive() for t in threads):raise RuntimeError('worker failed to join')
    counts=[answers.count(bytes([i])) for i in range(workers)]
    if errors or counts!=received or sum(received)+dispatcher.full!=connections:raise RuntimeError((errors,counts,received,dispatcher.full))
    return {'status':'passed','workers':workers,'connections':connections,'queue_capacity_each':capacity,'delivered':received,'refused':dispatcher.full}

def reuseport(workers,connections):
    if platform.system()=='Windows' or not hasattr(socket,'SO_REUSEPORT'):
        return {'status':'unsupported','reason':'No established equivalent to SO_REUSEPORT on this platform'}
    listeners=[];threads=[];counts=[0]*workers;errors=[];stop=threading.Event();port=None
    try:
        for _ in range(workers):
            s=socket.socket();listeners.append(s);s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEPORT,1)
            s.bind(('127.0.0.1',port or 0));s.listen(max(16,connections));s.settimeout(.1);port=s.getsockname()[1]
        def worker(i):
            while not stop.is_set():
                try:c,_=listeners[i].accept()
                except socket.timeout:continue
                except OSError as e:
                    if not stop.is_set():errors.append(repr(e))
                    break
                with c:
                    try:
                        c.settimeout(3)
                        if c.recv(1)!=b'X':raise ValueError('wrong payload')
                        c.sendall(bytes([i]));counts[i]+=1
                    except Exception as e:errors.append(repr(e))
        threads=[threading.Thread(target=worker,args=(i,)) for i in range(workers)]
        for t in threads:t.start()
        answers=[]
        for _ in range(connections):
            with socket.create_connection(('127.0.0.1',port),timeout=5) as c:
                c.settimeout(5);c.sendall(b'X');answers.append(c.recv(1))
        if any(len(x)!=1 or x[0]>=workers for x in answers):raise RuntimeError('invalid worker reply')
        if [answers.count(bytes([i])) for i in range(workers)]!=counts or errors:raise RuntimeError((counts,errors))
        return {'status':'passed','workers':workers,'connections':connections,'delivered':counts}
    except OSError as e:
        if not threads:return {'status':'unsupported','reason':str(e)}
        raise
    finally:
        stop.set()
        for t in threads:t.join(timeout=5)
        for s in listeners:s.close()
        if any(t.is_alive() for t in threads):raise RuntimeError('worker failed to join')

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);p.add_argument('--connections',type=int,default=64);p.add_argument('--queue-capacity',type=int,default=64);p.add_argument('--output',required=True)
    a=p.parse_args()
    if not 1<=a.workers<=8 or not 1<=a.connections<=512 or a.queue_capacity<1:p.error('workers 1..8, connections 1..512, capacity positive')
    result={'platform':platform.platform(),'python':platform.python_version(),'shared_listener':shared(a.workers,a.connections,a.queue_capacity),'listeners_per_worker':reuseport(a.workers,a.connections),'limits':['Python threads and sockets, not Liza runtime','loopback, sequential connects, not a load-balancing benchmark','SO_REUSEPORT behavior is OS-specific; result does not establish fairness']}
    with open(a.output,'x',encoding='utf-8') as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
