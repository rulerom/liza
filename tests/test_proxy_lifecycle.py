"""Bounded gateway lifecycle: real sockets, controlled time/I/O, O0 and O2."""
from pathlib import Path
import os
import queue
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
import unittest

from liza.backend import llvm
from liza.ir import lower
from liza.modules import load_program
from liza.stdlib import link_flags
import test_net

ROOT = Path(__file__).resolve().parents[1]
FAULT = r'''
#define liza_rt_reactor_clock real_clock
#define liza_rt_reactor_shutdown_requested real_requested
#define liza_rt_reactor_poll real_poll
#define liza_rt_reactor_read real_read
#define liza_rt_reactor_write real_write
#define liza_rt_reactor_shutdown_write real_fin
#define liza_rt_reactor_finish_connect real_finish
#include "reactor_common.h"
#undef liza_rt_reactor_clock
#undef liza_rt_reactor_shutdown_requested
#undef liza_rt_reactor_poll
#undef liza_rt_reactor_read
#undef liza_rt_reactor_write
#undef liza_rt_reactor_shutdown_write
#undef liza_rt_reactor_finish_connect
#include <stdio.h>
#ifdef _WIN32
#include <io.h>
#include <fcntl.h>
#endif
static unsigned long long tick=100,reads,writes,fins,polls;
static unsigned stop;
/* Publication replaces a complete file. Existing readers retain the old snapshot.
   Windows CRT fopen does not share DELETE; explicitly allow atomic replacement. */
static FILE *open_control(const char *path) {
#ifdef _WIN32
    HANDLE handle=CreateFileA(path,GENERIC_READ,
        FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,NULL,OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,NULL);
    if(handle==INVALID_HANDLE_VALUE)return NULL;
    int fd=_open_osfhandle((intptr_t)handle,_O_RDONLY|_O_TEXT);
    if(fd<0){CloseHandle(handle);return NULL;}
    FILE *file=_fdopen(fd,"r");
    if(!file)_close(fd);
    return file;
#else
    return fopen(path,"r");
#endif
}
static void control(void) {
    FILE*f=open_control(getenv("LIFECYCLE_GATE"));
    if(f){unsigned long long t;unsigned s;if(fscanf(f,"%llu %u",&t,&s)==2){tick=t;stop=s;}fclose(f);}
}
uint32_t liza_rt_reactor_clock(uint64_t*out){control();*out=tick;return 0;}
uint64_t liza_rt_reactor_shutdown_requested(reactor*r){(void)r;control();return stop;}
uint64_t liza_rt_reactor_poll(reactor*r,uint32_t t){
    uint64_t result=real_poll(r,t>1?1:t);control();polls++;
    FILE*f=fopen(getenv("LIFECYCLE_ACK"),"w");
    if(f){fprintf(f,"%llu %llu %llu %llu %llu %u\n",tick,reads,writes,fins,polls,r->listener_open);fclose(f);}
    return result;
}
uint64_t liza_rt_reactor_read(reactor*r,uint64_t o,uint64_t g,uint64_t s,uint8_t*b,uint32_t l,uint32_t a,uint32_t n){
    uint64_t result=real_read(r,o,g,s,b,l,a,n);if(!(result>>32))reads+=(uint32_t)result;return result;
}
uint64_t liza_rt_reactor_write(reactor*r,uint64_t o,uint64_t g,uint64_t s,const uint8_t*b,uint32_t l,uint32_t a,uint32_t n){
    if(getenv("LIFECYCLE_BLOCK"))return net_failure(4);
    if(n>7)n=7; /* force successful short writes */
    uint64_t result=real_write(r,o,g,s,b,l,a,n);if(!(result>>32))writes+=(uint32_t)result;return result;
}
uint64_t liza_rt_reactor_shutdown_write(reactor*r,uint64_t o,uint64_t g,uint64_t s){fins++;return real_fin(r,o,g,s);}
uint64_t liza_rt_reactor_finish_connect(reactor*r,uint64_t o,uint64_t g,uint64_t s){
    if(getenv("LIFECYCLE_PENDING"))return 0;return real_finish(r,o,g,s);
}
'''

@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='liza-lifecycle-');cls.root=Path(cls.temp.name)
        module=lower(load_program(ROOT/'examples/apps/liza_proxy_ops.liza'))
        ir=cls.root/'proxy.ll';ir.write_text(llvm(module))
        stub=cls.root/'fault.c';stub.write_text(FAULT)
        cls.executables=[]
        for opt in ('0','2'):
            normal=cls.root/('proxy'+opt+'.exe');fault=cls.root/('fault'+opt+'.exe')
            flags=link_flags(module)
            subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*flags,'-o',str(normal)],check=True,capture_output=True)
            flags=[f for f in flags if not Path(f).name.startswith('reactor_')]
            subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),str(stub),'-I'+str(ROOT/'liza/runtime'),*flags,'-o',str(fault)],check=True,capture_output=True)
            cls.executables.append((normal,fault))
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def setUp(self):
        self.case=tempfile.TemporaryDirectory();self.addCleanup(self.case.cleanup)
        self.gate=Path(self.case.name)/'gate';self.ack=Path(self.case.name)/'ack';self.control(100,0)
    def control(self,t,stop):
        tmp=self.gate.with_suffix('.next');tmp.write_text(f'{t} {stop}\n');os.replace(tmp,self.gate)
    def wait_ack(self,predicate):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            try:
                values=list(map(int,self.ack.read_text().split()))
                if len(values)==6 and predicate(values):return values
            except (OSError,ValueError):pass
            time.sleep(.005)
        self.fail('runtime did not reach expected controlled transition')
    def listener(self):
        s=socket.socket();self.addCleanup(s.close);s.bind(('127.0.0.1',0));s.listen(8);s.settimeout(5);return s
    def start(self,exe,up,args=(),extra=None):
        self.ack.unlink(missing_ok=True)
        env=dict(os.environ,LIFECYCLE_GATE=str(self.gate),LIFECYCLE_ACK=str(self.ack));env.update(extra or {})
        p=subprocess.Popen([str(exe),'--ephemeral','--upstream',f'127.0.0.1:{up.getsockname()[1]}','--metrics',*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
        self.addCleanup(lambda:test_net.NetNative.stop(p))
        lines=queue.Queue();threading.Thread(target=lambda:lines.put(p.stdout.readline()),daemon=True).start()
        line=lines.get(timeout=10);self.assertTrue(line.strip().isdigit(),line)
        return p,int(line)
    def connect(self,port,up):
        c=socket.create_connection(('127.0.0.1',port),timeout=5);self.addCleanup(c.close)
        u,_=up.accept();u.settimeout(5);self.addCleanup(u.close);return c,u
    def recv(self,s,n):
        data=b''
        while len(data)<n:
            part=s.recv(n-len(data));self.assertTrue(part);data+=part
        return data
    def ping(self,c,u,data=b'hello'):
        c.sendall(data);self.assertEqual(self.recv(u,len(data)),data)
        u.sendall(data);self.assertEqual(self.recv(c,len(data)),data)
    def finish(self,p,code=0):
        out,err=p.communicate(timeout=8);self.assertEqual(p.returncode,code,err);self.assertEqual(out,b'')
        return {k:int(v) for k,v in (line.split('=') for line in err.decode().splitlines())}
    def test_idle_is_per_pair_and_slot_can_be_reused(self):
        for _,exe in self.executables:
            self.control(100,0);up=self.listener();p,port=self.start(exe,up,['--idle-timeout-ms','10'])
            a,ua=self.connect(port,up);b,ub=self.connect(port,up);self.ping(a,ua);self.ping(b,ub)
            self.control(109,0);self.ping(b,ub)
            self.wait_ack(lambda x:x[0]==109)
            self.control(110,0);self.assertEqual(a.recv(1),b'');self.assertEqual(ua.recv(1),b'')
            self.ping(b,ub)
            c,uc=self.connect(port,up);self.ping(c,uc)
            for client,server in ((b,ub),(c,uc)):
                client.shutdown(socket.SHUT_WR);self.assertEqual(server.recv(1),b'')
                server.shutdown(socket.SHUT_WR);self.assertEqual(client.recv(1),b'')
            self.control(110,1);m=self.finish(p)
            self.assertEqual((m['accepted'],m['closed'],m['idle_timeouts'],m['active']),(3,3,1,0))
            self.assertEqual(m['discarded'],0)
    def test_fixed_drain_deadline_despite_progress_and_repeated_stop(self):
        for _,exe in self.executables:
            self.control(100,0);up=self.listener();p,port=self.start(exe,up,['--drain-timeout-ms','50'])
            c,u=self.connect(port,up);self.ping(c,u)
            self.control(100,1);self.wait_ack(lambda x:x[5]==0)
            with self.assertRaises(OSError):socket.create_connection(('127.0.0.1',port),timeout=.2)
            self.control(149,1);self.ping(c,u,b'progress')
            self.assertIsNone(p.poll())
            self.control(150,1);self.assertEqual(c.recv(1),b'');m=self.finish(p)
            self.assertEqual((m['drain_forced'],m['closed'],m['idle_timeouts']),(1,1,0))
            self.assertEqual((m['forward_read'],m['forward_written'],m['reverse_read'],m['reverse_written']),(13,13,13,13))
    def test_full_queue_wouldblock_no_fin_and_discard_accounting(self):
        for _,exe in self.executables:
            self.control(100,0);up=self.listener();p,port=self.start(exe,up,['--drain-timeout-ms','50'],{'LIFECYCLE_BLOCK':'1'})
            c,u=self.connect(port,up);c.sendall(b'x'*3000);c.shutdown(socket.SHUT_WR)
            first=self.wait_ack(lambda x:x[1]==2048)
            self.control(100,1);self.wait_ack(lambda x:x[5]==0)
            self.control(149,1);last=self.wait_ack(lambda x:x[0]==149 and x[4]>first[4]+3)
            self.assertEqual(last[1:4],[2048,0,0])
            self.control(150,1);m=self.finish(p)
            self.assertEqual((m['discarded'],m['forward_read'],m['forward_written'],m['drain_forced']),(2048,2048,0,1))
    def test_drain_precedes_connect_deadline_with_pending_eof(self):
        for _,exe in self.executables:
            self.control(100,0);up=self.listener();p,port=self.start(exe,up,['--drain-timeout-ms','50','--connect-timeout-ms','50'],{'LIFECYCLE_PENDING':'1'})
            c,u=self.connect(port,up);c.sendall(b'request');c.shutdown(socket.SHUT_WR)
            self.wait_ack(lambda x:x[1]==7)
            self.control(100,1);self.wait_ack(lambda x:x[5]==0)
            self.control(150,1);m=self.finish(p)
            self.assertEqual((m['drain_forced'],m['connect_timeouts'],m['discarded']),(1,0,7))
    @unittest.skipIf(os.name=='nt','POSIX signals; Windows uses controlled stop in portable tests')
    def test_sigterm_drains_half_close_and_exact_binary_response(self):
        for exe,_ in self.executables:
            up=self.listener();p,port=self.start(exe,up,['--drain-timeout-ms','5000'])
            c,u=self.connect(port,up);c.sendall(b'request');c.shutdown(socket.SHUT_WR)
            self.assertEqual(self.recv(u,7),b'request');self.assertEqual(u.recv(1),b'')
            p.send_signal(signal.SIGTERM)
            # Existing half-closed pair must remain alive for the response.
            data=bytes(range(256))*512
            worker=threading.Thread(target=lambda:(u.sendall(data),u.shutdown(socket.SHUT_WR)),daemon=True);worker.start()
            self.assertEqual(self.recv(c,len(data)),data);self.assertEqual(c.recv(1),b'');worker.join(timeout=5)
            m=self.finish(p);self.assertEqual((m['drain_forced'],m['errors'],m['discarded']),(0,0,0))
            self.assertEqual((m['reverse_read'],m['reverse_written']),(len(data),len(data)))
    def test_new_options_reject_invalid_values(self):
        for exe,_ in self.executables:
            for args in (['--idle-timeout-ms','0'],['--drain-timeout-ms','2147483648'],['--metrics','--metrics'],['--idle-timeout-ms','1','--idle-timeout-ms','2']):
                r=subprocess.run([str(exe),*args],capture_output=True,timeout=5)
                self.assertEqual(r.returncode,2);self.assertEqual(r.stdout,b'')
    def test_eof_and_fin_do_not_refresh_idle(self):
        for _,exe in self.executables:
            self.control(100,0);up=self.listener();p,port=self.start(exe,up,['--idle-timeout-ms','10'])
            c,u=self.connect(port,up);self.ping(c,u)
            self.control(109,0);c.shutdown(socket.SHUT_WR);self.assertEqual(u.recv(1),b'')
            self.wait_ack(lambda x:x[0]==109 and x[3]>0)
            self.control(110,0);self.assertEqual(c.recv(1),b'')
            self.control(110,1);m=self.finish(p);self.assertEqual(m['idle_timeouts'],1)
    def test_clock_regression_closes_all_pairs(self):
        for _,exe in self.executables:
            self.control(100,0);up=self.listener();p,port=self.start(exe,up)
            a,ua=self.connect(port,up);b,ub=self.connect(port,up);self.ping(a,ua);self.ping(b,ub)
            self.control(99,0);m=self.finish(p,3)
            self.assertEqual((m['active'],m['closed'],m['errors']),(0,2,2))
            self.assertEqual(a.recv(1),b'');self.assertEqual(b.recv(1),b'')
    def test_metrics_saturate_without_trap(self):
        folder=Path(self.case.name);(folder/'proxy').mkdir()
        shutil.copy(ROOT/'examples/apps/proxy/metrics.liza',folder/'proxy/metrics.liza')
        source=folder/'metrics.liza';source.write_text('''import proxy.metrics
fn main()->u32 {
    var s=proxy.metrics.create()
    s.accepted=18446744073709551615
    a=proxy.metrics.accepted(borrow mut s)
    if !s.overflow || s.active!=1 || s.accepted!=18446744073709551615 {return 1}
    s.forward_read=18446744073709551614
    b=proxy.metrics.transfer(borrow mut s,0,2)
    if s.forward_read!=18446744073709551615 {return 2}
    s.closed=18446744073709551615
    s.discarded=18446744073709551614
    s.drain_forced=18446744073709551615
    c=proxy.metrics.closed(borrow mut s,4,2048)
    if s.active!=0 || s.closed!=18446744073709551615 || s.discarded!=18446744073709551615 || s.drain_forced!=18446744073709551615 {return 3}
    return 0
}''')
        m=lower(load_program(source));ir=folder/'metrics.ll';ir.write_text(llvm(m))
        for opt in ('0','2'):
            exe=folder/('metrics'+opt+'.exe')
            subprocess.run(['clang','-Wno-override-module','-O'+opt,str(ir),*link_flags(m),'-o',str(exe)],check=True,capture_output=True)
            self.assertEqual(subprocess.run([str(exe)],timeout=5).returncode,0)
    def test_listener_shutdown_and_notification_ownership(self):
        source=Path(self.case.name)/'adapter.c';source.write_text(r'''
#define liza_rt_net_close real_net_close
#include "net_common.h"
#undef liza_rt_net_close
static unsigned fail_close,close_calls;
uint32_t liza_rt_net_close(uint64_t handle) {
    uint32_t result=real_net_close(handle);close_calls++;
    if(fail_close){fail_close=0;return 7;}return result;
}
#ifndef _WIN32
#include <signal.h>
static int fail_registration;
static int injected_sigaction(int sig,const struct sigaction *action,struct sigaction *old) {
    if(fail_registration && sig==SIGTERM && action){fail_registration=0;errno=EIO;return -1;}
    return sigaction(sig,action,old);
}
#define sigaction(...) injected_sigaction(__VA_ARGS__)
#endif
#include "reactor_common.h"
#ifndef _WIN32
#undef sigaction
#endif
int main(void) {
    reactor *a,*b,*c;
    if(liza_rt_reactor_create(0,2,&a)||liza_rt_reactor_create(0,2,&b))return 1;
    if(liza_rt_reactor_shutdown_requested(a)!=net_failure(7))return 2;
#ifndef _WIN32
    struct sigaction original_int,original_term,current;
    sigset_t original_mask,current_mask;
    if(sigaction(SIGINT,NULL,&original_int)||sigaction(SIGTERM,NULL,&original_term)
       ||sigprocmask(SIG_SETMASK,NULL,&original_mask))return 16;
    fail_registration=1;
    if(liza_rt_reactor_watch_shutdown(a)!=net_failure(7)||reactor_watcher)return 17;
    if(sigaction(SIGINT,NULL,&current)||current.sa_handler!=original_int.sa_handler)return 18;
    if(sigaction(SIGTERM,NULL,&current)||current.sa_handler!=original_term.sa_handler)return 19;
    if(sigprocmask(SIG_SETMASK,NULL,&current_mask)
       ||sigismember(&original_mask,SIGINT)!=sigismember(&current_mask,SIGINT)
       ||sigismember(&original_mask,SIGTERM)!=sigismember(&current_mask,SIGTERM))return 20;
#endif
    if(liza_rt_reactor_watch_shutdown(a)||liza_rt_reactor_watch_shutdown(a))return 3;
    if(liza_rt_reactor_watch_shutdown(b)!=net_failure(7))return 4;
#ifdef _WIN32
    if(!reactor_stop_handler(CTRL_BREAK_EVENT))return 5;
#else
    raise(SIGTERM);
#endif
    if(liza_rt_reactor_shutdown_requested(a)!=1)return 6;
    fail_close=1;close_calls=0;
    if(liza_rt_reactor_stop_accepting(a)!=net_failure(7)||liza_rt_reactor_stop_accepting(a)||close_calls!=1)return 7;
    uint64_t id[3];if(liza_rt_reactor_accept(a,id)!=5)return 8;
    if(liza_rt_reactor_port(a)!=net_failure(5))return 9;
    uint64_t start,end;
    if(liza_rt_reactor_clock(&start)||liza_rt_reactor_poll(a,100)||liza_rt_reactor_clock(&end))return 10;
    if(end<start || end-start<50)return 11; /* closed listener is absent, no POLLNVAL spin */
    if(liza_rt_reactor_create(0,2,&c))return 12; /* may reuse the closed descriptor */
    if(liza_rt_reactor_close(a) || (liza_rt_reactor_port(c)>>32))return 13;
#ifndef _WIN32
    if(sigaction(SIGINT,NULL,&current)||current.sa_handler!=original_int.sa_handler)return 21;
    if(sigaction(SIGTERM,NULL,&current)||current.sa_handler!=original_term.sa_handler)return 22;
#endif
    if(liza_rt_reactor_watch_shutdown(b)||liza_rt_reactor_shutdown_requested(b))return 14;
    if(liza_rt_reactor_close(b)||liza_rt_reactor_close(c))return 15;
    return 0;
}''')
        m=lower(load_program(ROOT/'examples/apps/liza_proxy_ops.liza'))
        flags=[f for f in link_flags(m) if not Path(f).name.startswith(('net_','reactor_'))]
        for opt in ('0','2'):
            exe=Path(self.case.name)/('adapter'+opt+'.exe')
            subprocess.run(['clang','-O'+opt,str(source),'-I'+str(ROOT/'liza/runtime'),*flags,'-o',str(exe)],check=True,capture_output=True)
            r=subprocess.run([str(exe)],capture_output=True,timeout=5);self.assertEqual(r.returncode,0,r.stderr)

    def test_control_publication_with_live_reader(self):
        # The child explicitly acknowledges an open handle before replacement;
        # its original read must remain coherent while a new open sees the update.
        source=Path(self.case.name)/'publication.c'
        source.write_text(FAULT+r'''
int main(int argc,char **argv) {
    if(argc!=2)return 1;
    FILE *old=open_control(argv[1]);if(!old)return 2;
    puts("opened");fflush(stdout);
    if(getchar()!='!')return 3;
    unsigned long long t;unsigned s;
    if(fscanf(old,"%llu %u",&t,&s)!=2 || t!=100 || s!=0)return 4;
    fclose(old);
    FILE *current=open_control(argv[1]);if(!current)return 5;
    if(fscanf(current,"%llu %u",&t,&s)!=2 || t!=150 || s!=1)return 6;
    fclose(current);return 0;
}
''')
        m=lower(load_program(ROOT/'examples/apps/liza_proxy_ops.liza'))
        flags=[f for f in link_flags(m) if not Path(f).name.startswith('reactor_')]
        for opt in ('0','2'):
            self.control(100,0)
            exe=Path(self.case.name)/('publication'+opt+'.exe')
            subprocess.run(['clang','-O'+opt,str(source),'-I'+str(ROOT/'liza/runtime'),*flags,'-o',str(exe)],check=True,capture_output=True)
            p=subprocess.Popen([str(exe),str(self.gate)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.addCleanup(lambda p=p:test_net.NetNative.stop(p))
            self.addCleanup(p.stdin.close)
            lines=queue.Queue()
            threading.Thread(target=lambda:lines.put(p.stdout.readline()),daemon=True).start()
            self.assertEqual(lines.get(timeout=5).rstrip(b'\r\n'),b'opened')
            self.control(150,1)  # no retry: replacement must succeed with old open
            out,err=p.communicate(b'!',timeout=5)
            self.assertEqual((p.returncode,out),(0,b''),err)
