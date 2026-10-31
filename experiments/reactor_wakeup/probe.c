#if defined(__linux__)
#define _DEFAULT_SOURCE 1
#define _POSIX_C_SOURCE 200809L
#endif
#include "scoped_channel_core.h"
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
typedef SOCKET sock_t;
typedef WSAPOLLFD poll_item;
#define BAD_SOCKET INVALID_SOCKET
#define close_socket closesocket
typedef HANDLE thread_id;
#define THREAD_RESULT DWORD WINAPI
#define THREAD_RETURN return 0
static int thread_start(thread_id *t,LPTHREAD_START_ROUTINE fn,void *arg){*t=CreateThread(NULL,0,fn,arg,0,NULL);return *t!=NULL;}
static int thread_join(thread_id t){DWORD s=WaitForSingleObject(t,INFINITE);CloseHandle(t);return s==WAIT_OBJECT_0;}
static void yield_thread(void){Sleep(0);}
static int would_block(void){return WSAGetLastError()==WSAEWOULDBLOCK;}
static int nonblock(sock_t s){u_long on=1;return ioctlsocket(s,FIONBIO,&on)==0;}
static uint64_t now_ms(void){return GetTickCount64();}
#else
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <pthread.h>
#include <sched.h>
#include <sys/socket.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/eventfd.h>
#endif
typedef int sock_t;
typedef struct pollfd poll_item;
#define BAD_SOCKET (-1)
#define close_socket close
typedef pthread_t thread_id;
#define THREAD_RESULT void *
#define THREAD_RETURN return NULL
static int thread_start(thread_id *t,void *(*fn)(void *),void *arg){return pthread_create(t,NULL,fn,arg)==0;}
static int thread_join(thread_id t){return pthread_join(t,NULL)==0;}
static void yield_thread(void){sched_yield();}
static int would_block(void){return errno==EAGAIN||errno==EWOULDBLOCK;}
static int nonblock(sock_t s){int flags=fcntl(s,F_GETFL,0);return flags>=0&&fcntl(s,F_SETFL,flags|O_NONBLOCK)==0;}
static uint64_t now_ms(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
#endif

typedef struct {sock_t read_fd,write_fd;int eventfd_mode;} wakeup;
static void wake_close(wakeup *w){
    if(w->read_fd!=BAD_SOCKET)close_socket(w->read_fd);
    if(w->write_fd!=BAD_SOCKET && w->write_fd!=w->read_fd)close_socket(w->write_fd);
    w->read_fd=w->write_fd=BAD_SOCKET;
}
/* TCP loopback is used only as a pollable notification transport. */
static int wake_init(wakeup *w,int eventfd_mode){
    w->read_fd=w->write_fd=BAD_SOCKET;w->eventfd_mode=eventfd_mode;
#ifdef __linux__
    if(eventfd_mode){int fd=eventfd(0,EFD_NONBLOCK|EFD_CLOEXEC);if(fd<0)return 0;w->read_fd=w->write_fd=fd;return 1;}
#else
    if(eventfd_mode)return 0;
#endif
    sock_t listener=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);if(listener==BAD_SOCKET)return 0;
    struct sockaddr_in addr;memset(&addr,0,sizeof(addr));addr.sin_family=AF_INET;addr.sin_addr.s_addr=htonl(0x7f000001u);
    if(bind(listener,(struct sockaddr*)&addr,sizeof(addr))||listen(listener,1))goto fail;
#ifdef _WIN32
    int length=(int)sizeof(addr);
#else
    socklen_t length=sizeof(addr);
#endif
    if(getsockname(listener,(struct sockaddr*)&addr,&length))goto fail;
    w->write_fd=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);if(w->write_fd==BAD_SOCKET)goto fail;
    if(connect(w->write_fd,(struct sockaddr*)&addr,sizeof(addr)))goto fail;
    w->read_fd=accept(listener,NULL,NULL);if(w->read_fd==BAD_SOCKET)goto fail;
    close_socket(listener);
#ifdef SO_NOSIGPIPE
    int no_sigpipe=1;
    if(setsockopt(w->write_fd,SOL_SOCKET,SO_NOSIGPIPE,(const void*)&no_sigpipe,sizeof(no_sigpipe))){wake_close(w);return 0;}
#endif
    if(!nonblock(w->read_fd)||!nonblock(w->write_fd)){wake_close(w);return 0;}
    return 1;
fail:
    close_socket(listener);wake_close(w);return 0;
}
static int wake_send(wakeup *w){
#ifdef WAKE_TEST_DROP_NOTIFICATION
    (void)w;return 1;
#endif
#ifdef WAKE_TEST_FAIL_NOTIFICATION
    (void)w;return 0;
#endif
#ifdef __linux__
    if(w->eventfd_mode){uint64_t one=1;return write(w->write_fd,&one,sizeof(one))==(ssize_t)sizeof(one);}
#endif
    const char byte=1;
#ifdef _WIN32
    return send(w->write_fd,&byte,1,0)==1;
#else
#ifdef MSG_NOSIGNAL
    return send(w->write_fd,&byte,1,MSG_NOSIGNAL)==1;
#else
    return send(w->write_fd,&byte,1,0)==1;
#endif
#endif
}
static int wake_drain(wakeup *w){
#ifdef __linux__
    if(w->eventfd_mode){uint64_t count;ssize_t n=read(w->read_fd,&count,sizeof(count));return n==(ssize_t)sizeof(count) || (n<0&&would_block());}
#endif
    char data[512];
    for(unsigned i=0;i<8;i++){
#ifdef _WIN32
        int n=recv(w->read_fd,data,(int)sizeof(data),0);
#else
        ssize_t n=recv(w->read_fd,data,sizeof(data),0);
#endif
        if(n>0)continue;
        return n<0&&would_block();
    }
    return 1; /* Readiness remains set for any undrained bytes. */
}
typedef struct {channel *queue;wakeup wake;sock_t network;atomic_int about_to_wait;uint32_t received,wake_events,net_events,timeouts;atomic_int failure;} receiver;
static THREAD_RESULT receive_loop(void *arg){
    receiver *r=arg;int closed=0;
    for(;;){
        for(;;){uint32_t value=0;liza_scoped_status s=liza_scoped_receive(r->queue,&value);
            if(s==CH_OK){if(value!=r->received){atomic_store(&r->failure,1);THREAD_RETURN;}r->received++;continue;}
            if(s==CH_CLOSED){closed=1;break;}
            if(s!=CH_EMPTY){atomic_store(&r->failure,2);THREAD_RETURN;}break;
        }
        if(closed&&r->net_events)break;
        poll_item fds[2];memset(fds,0,sizeof(fds));fds[0].fd=r->wake.read_fd;fds[0].events=POLLRDNORM;fds[1].fd=r->network;fds[1].events=POLLRDNORM;
        atomic_fetch_add(&r->about_to_wait,1);
#ifdef _WIN32
        int n=WSAPoll(fds,2,5000);
#else
        int n=poll(fds,2,5000);
#endif
        if(n<=0){r->timeouts++;atomic_store(&r->failure,3);THREAD_RETURN;}
        if((fds[0].revents|fds[1].revents)&(POLLERR|POLLHUP|POLLNVAL)){atomic_store(&r->failure,4);THREAD_RETURN;}
        if(fds[0].revents&POLLRDNORM){if(!wake_drain(&r->wake)){atomic_store(&r->failure,5);THREAD_RETURN;}r->wake_events++;}
        if(fds[1].revents&POLLRDNORM){char data[8];int got=(int)recv(r->network,data,sizeof(data),0);if(got!=1||data[0]!='n'){atomic_store(&r->failure,6);THREAD_RETURN;}r->net_events++;}
    }
    THREAD_RETURN;
}
static int run_case(int eventfd_mode,int preposted){
    receiver r;memset(&r,0,sizeof(r));r.network=BAD_SOCKET;r.wake.read_fd=r.wake.write_fd=BAD_SOCKET;atomic_init(&r.about_to_wait,0);atomic_init(&r.failure,0);
    size_t bytes=0;thread_id thread;int started=0,result=1;sock_t network_sender=BAD_SOCKET;
    if(liza_scoped_create(8,1024,&r.queue,&bytes)!=CH_OK)goto done;
    if(!wake_init(&r.wake,eventfd_mode))goto done;
    r.network=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);network_sender=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);
    if(r.network==BAD_SOCKET||network_sender==BAD_SOCKET)goto done;
    struct sockaddr_in addr;memset(&addr,0,sizeof(addr));addr.sin_family=AF_INET;addr.sin_addr.s_addr=htonl(0x7f000001u);
    if(bind(r.network,(struct sockaddr*)&addr,sizeof(addr))||!nonblock(r.network))goto done;
#ifdef _WIN32
    int length=(int)sizeof(addr);
#else
    socklen_t length=sizeof(addr);
#endif
    if(getsockname(r.network,(struct sockaddr*)&addr,&length))goto done;
    if(sendto(network_sender,"n",1,0,(struct sockaddr*)&addr,sizeof(addr))!=1)goto done;
    if(preposted){if(liza_scoped_send(r.queue,0)!=CH_OK||!wake_send(&r.wake))goto done;}
    if(!thread_start(&thread,receive_loop,&r))goto done;started=1;
    if(!preposted){
        uint64_t until=now_ms()+10000;
        while(atomic_load(&r.about_to_wait)<2){if(atomic_load(&r.failure)||now_ms()>=until)goto stop;yield_thread();}
    }
    for(uint32_t i=(uint32_t)preposted;i<256;i++){
        liza_scoped_status s;
        uint64_t until=now_ms()+10000;
        while((s=liza_scoped_send(r.queue,i))==CH_FULL){if(atomic_load(&r.failure)||now_ms()>=until)goto stop;yield_thread();}
        if(s!=CH_OK||!wake_send(&r.wake))goto stop;
    }
    liza_scoped_close_sender(r.queue);if(!wake_send(&r.wake))goto stop;
    if(!thread_join(thread))abort();started=0;
    if(atomic_load(&r.failure)||r.received!=256||r.net_events!=1||!r.wake_events||r.timeouts)goto done;
    printf("mode=%s preposted=%d received=%u network=%u wake_events=%u bytes=%zu\n",eventfd_mode?"eventfd":"socket",preposted,r.received,r.net_events,r.wake_events,bytes);
    result=0;goto done;
stop:
    liza_scoped_close_sender(r.queue);(void)wake_send(&r.wake);
done:
    if(result)fprintf(stderr,"probe failed: mode=%s preposted=%d worker_error=%d\n",eventfd_mode?"eventfd":"socket",preposted,atomic_load(&r.failure));
    if(started && !thread_join(thread))abort();
    if(r.queue)liza_scoped_destroy(r.queue);
    wake_close(&r.wake);if(r.network!=BAD_SOCKET)close_socket(r.network);if(network_sender!=BAD_SOCKET)close_socket(network_sender);
    return result;
}
int main(void){
#ifdef _WIN32
    WSADATA data;if(WSAStartup(MAKEWORD(2,2),&data))return 1;
#endif
#if defined(WAKE_TEST_DROP_NOTIFICATION) || defined(WAKE_TEST_FAIL_NOTIFICATION)
    int result=run_case(0,0);
#else
    int result=run_case(0,1)||run_case(0,0);
#endif
#ifdef __linux__
    result=result||run_case(1,1)||run_case(1,0);
#endif
#ifdef _WIN32
    WSACleanup();
#endif
    return result;
}
