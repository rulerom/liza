/* Bounded single-threaded socket owner. Protocol state and payloads live in Liza. */
#include "net_platform.h"
#include <stdlib.h>
#include <stdatomic.h>
#ifdef _WIN32
typedef WSAPOLLFD reactor_pollfd;
#else
#include <poll.h>
#include <signal.h>
typedef struct pollfd reactor_pollfd;
#endif
#define REACTOR_MAX 32
uint32_t liza_rt_net_listen(uint16_t, uint64_t*);
uint32_t liza_rt_net_listen_at(uint32_t,uint16_t,uint64_t*);
uint32_t liza_rt_net_accept(uint64_t, uint64_t*);
uint64_t liza_rt_net_port(uint64_t);
uint64_t liza_rt_net_read(uint64_t, uint8_t*, uint32_t);
uint64_t liza_rt_net_write(uint64_t, const uint8_t*, uint32_t, uint32_t, uint32_t);
uint32_t liza_rt_net_close(uint64_t);
typedef struct { uint64_t socket,generation; uint32_t live,interest,ready,phase,error,write_closed; } reactor_slot;
typedef struct { uint64_t owner,listener; uint32_t capacity,listener_open; reactor_slot slots[REACTOR_MAX]; } reactor;
/* Owner identities are process-wide, unique and never wrap. */
static _Atomic uint64_t reactor_next_owner;
/* Process notifications: one explicitly registered reactor, no handler access to it. */
static uint64_t reactor_watcher;
#ifdef _WIN32
static volatile LONG reactor_stop_requested;
static BOOL WINAPI reactor_stop_handler(DWORD event) {
    if (event!=CTRL_C_EVENT && event!=CTRL_BREAK_EVENT) return FALSE;
    InterlockedExchange(&reactor_stop_requested,1);return TRUE;
}
#else
static volatile sig_atomic_t reactor_stop_requested;
static struct sigaction reactor_old_int,reactor_old_term;
static void reactor_stop_handler(int signal_number) {
    (void)signal_number;reactor_stop_requested=1;
}
#endif
uint64_t liza_rt_reactor_watch_shutdown(reactor *r) {
    if (reactor_watcher==r->owner) return 0;
    if (reactor_watcher) return net_failure(7);
#ifdef _WIN32
    InterlockedExchange(&reactor_stop_requested,0);
    if (!SetConsoleCtrlHandler(reactor_stop_handler,TRUE)) return net_failure(7);
#else
    sigset_t signals,old_mask;sigemptyset(&signals);
    sigaddset(&signals,SIGINT);sigaddset(&signals,SIGTERM);
    if (sigprocmask(SIG_BLOCK,&signals,&old_mask)!=0) return net_failure(7);
    struct sigaction action;memset(&action,0,sizeof(action));
    action.sa_handler=reactor_stop_handler;sigemptyset(&action.sa_mask);
    int error=sigaction(SIGINT,&action,&reactor_old_int);
    if (!error && sigaction(SIGTERM,&action,&reactor_old_term)!=0) {
        sigaction(SIGINT,&reactor_old_int,NULL);error=1;
    }
    reactor_stop_requested=0;
    if (!error) reactor_watcher=r->owner;
    if (sigprocmask(SIG_SETMASK,&old_mask,NULL)!=0) error=1;
    if (error) return net_failure(7);
#endif
    reactor_watcher=r->owner;return 0;
}
uint64_t liza_rt_reactor_shutdown_requested(reactor *r) {
    if (reactor_watcher!=r->owner) return net_failure(7);
#ifdef _WIN32
    return InterlockedCompareExchange(&reactor_stop_requested,0,0)!=0;
#else
    return reactor_stop_requested!=0;
#endif
}
static uint32_t reactor_unwatch(reactor *r) {
    if (reactor_watcher!=r->owner) return 0;
    uint32_t error=0;
#ifdef _WIN32
    if (!SetConsoleCtrlHandler(reactor_stop_handler,FALSE)) error=7;
#else
    /* Restore both even if one restoration fails. No pointers survive close. */
    if (sigaction(SIGINT,&reactor_old_int,NULL)!=0) error=7;
    if (sigaction(SIGTERM,&reactor_old_term,NULL)!=0) error=7;
#endif
    reactor_watcher=0;return error;
}
uint64_t liza_rt_reactor_stop_accepting(reactor *r) {
    if (!r->listener_open) return 0;
    r->listener_open=0;
    return net_failure(liza_rt_net_close(r->listener));
}
static uint32_t reactor_nonblocking(uint64_t handle) {
#ifdef _WIN32
    u_long enabled=1;
    if (ioctlsocket((SOCKET)handle,FIONBIO,&enabled)!=0) return net_error();
#else
    int flags=fcntl((int)handle,F_GETFL,0);
    if (flags<0 || fcntl((int)handle,F_SETFL,flags|O_NONBLOCK)<0) return net_error();
#endif
    return 0;
}
static reactor_slot *reactor_find(reactor *r,uint64_t owner,uint64_t generation,uint64_t slot) {
    if (owner!=r->owner || slot>=r->capacity) return NULL;
    reactor_slot *s=&r->slots[slot];
    return s->live && generation==s->generation ? s : NULL;
}
uint32_t liza_rt_reactor_create_at(uint32_t ip,uint16_t port,uint32_t capacity,reactor **out) {
    *out=NULL;
    if (!capacity || capacity>REACTOR_MAX) return 8;
    if (atomic_load_explicit(&reactor_next_owner,memory_order_relaxed)==UINT64_MAX) return 11;
    reactor *r=(reactor*)calloc(1,sizeof(*r));
    if (!r) return 12;
    uint32_t e=liza_rt_net_listen_at(ip,port,&r->listener);
    if (e) {free(r);return e;}
    e=reactor_nonblocking(r->listener);
    if (!e && listen((net_socket)r->listener,(int)capacity)!=0) e=net_error();
    if (e) {liza_rt_net_close(r->listener);free(r);return e;}
    uint64_t previous=atomic_load_explicit(&reactor_next_owner,memory_order_relaxed);
    do {
        if (previous==UINT64_MAX) {uint32_t close_error=liza_rt_net_close(r->listener);free(r);return close_error ? close_error : 11;}
    } while (!atomic_compare_exchange_weak_explicit(&reactor_next_owner,&previous,previous+1,
                                                      memory_order_relaxed,memory_order_relaxed));
    r->owner=previous+1;r->capacity=capacity;r->listener_open=1;*out=r;return 0;
}
uint32_t liza_rt_reactor_create(uint16_t port,uint32_t capacity,reactor **out) {
    return liza_rt_reactor_create_at(INADDR_LOOPBACK,port,capacity,out);
}
uint64_t liza_rt_reactor_port(reactor *r) {return r->listener_open ? liza_rt_net_port(r->listener) : net_failure(5);}
uint32_t liza_rt_reactor_accept(reactor *r,uint64_t *id) {
    id[0]=id[1]=id[2]=0;
    if (!r->listener_open) return 5;
    uint32_t index=r->capacity;
    for (uint32_t i=0;i<r->capacity;i++)
        if (!r->slots[i].live && r->slots[i].generation!=UINT64_MAX) {index=i;break;}
    if (index==r->capacity) return 9;
    uint64_t handle;uint32_t e=liza_rt_net_accept(r->listener,&handle);
    if (e) return e;
    e=reactor_nonblocking(handle);
    if (e) {liza_rt_net_close(handle);return e;}
    reactor_slot *s=&r->slots[index];
    s->socket=handle;s->generation++;s->live=1;s->interest=1;s->ready=0;
    s->phase=0;s->error=0;s->write_closed=0;
    id[0]=r->owner;id[1]=s->generation;id[2]=index;return 0;
}
/* phase: 0 connected, 1 connecting, 2 failed (sticky SO_ERROR result). */
uint32_t liza_rt_reactor_connect_at(reactor *r,uint32_t ip,uint16_t port,uint64_t *id) {
    id[0]=id[1]=id[2]=0;
    if (!port || !ip || ip==UINT32_MAX || (ip>>24)>=224) return 6;
    uint32_t index=r->capacity;
    for (uint32_t i=0;i<r->capacity;i++)
        if (!r->slots[i].live && r->slots[i].generation!=UINT64_MAX) {index=i;break;}
    if (index==r->capacity) return 9;
    if (net_start()!=0) return 7;
    net_socket fd=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    if (fd==NET_INVALID) {uint32_t e=net_error();net_stop();return e;}
    uint32_t e=net_prepare(fd);
    if (!e) e=reactor_nonblocking((uint64_t)fd);
    uint32_t pending=0;
    struct sockaddr_in address;memset(&address,0,sizeof(address));
    address.sin_family=AF_INET;address.sin_addr.s_addr=htonl(ip);address.sin_port=htons(port);
    if (!e && connect(fd,(struct sockaddr*)&address,sizeof(address))!=0) {
#ifdef _WIN32
        int code=WSAGetLastError();
        pending=code==WSAEWOULDBLOCK || code==WSAEINPROGRESS || code==WSAEALREADY;
#else
        int code=errno;
        pending=code==EINPROGRESS || code==EALREADY || code==EINTR;
#endif
        if (!pending) e=net_error();
    }
    if (e) {net_os_close(fd);net_stop();return e;}
    reactor_slot *slot=&r->slots[index];
    slot->socket=(uint64_t)fd;slot->generation++;slot->live=1;slot->interest=2;slot->ready=0;
    slot->phase=pending;slot->error=0;slot->write_closed=0;
    id[0]=r->owner;id[1]=slot->generation;id[2]=index;return 0;
}
uint32_t liza_rt_reactor_connect(reactor *r,uint16_t port,uint64_t *id) {
    return liza_rt_reactor_connect_at(r,INADDR_LOOPBACK,port,id);
}
uint64_t liza_rt_reactor_finish_connect(reactor *r,uint64_t owner,uint64_t generation,uint64_t slot) {
    reactor_slot *s=reactor_find(r,owner,generation,slot);
    if (!s) return net_failure(10);
    if (s->phase==0) return 1;
    if (s->phase==2) return net_failure(s->error);
    /* A fresh zero-time readiness check: SO_ERROR=0 alone can mean still pending. */
#ifdef _WIN32
    fd_set writes,errors;FD_ZERO(&writes);FD_ZERO(&errors);
    FD_SET((SOCKET)s->socket,&writes);FD_SET((SOCKET)s->socket,&errors);
    struct timeval zero={0,0};
    int ready=select(0,NULL,&writes,&errors,&zero);
#else
    struct pollfd fd={(int)s->socket,POLLOUT,0};
    int ready=poll(&fd,1,0);
#endif
    if (ready<0) return net_failure(net_error());
    if (!ready) return 0;
    int error=0;
#ifdef _WIN32
    int size=sizeof(error);
    int result=getsockopt((SOCKET)s->socket,SOL_SOCKET,SO_ERROR,(char*)&error,&size);
#else
    socklen_t size=sizeof(error);
    int result=getsockopt((int)s->socket,SOL_SOCKET,SO_ERROR,&error,&size);
#endif
    if (result!=0) return net_failure(net_error());
    if (error) {
#ifdef _WIN32
        WSASetLastError(error);
#else
        errno=error;
#endif
        s->error=net_error();
        /* A reported connect failure is terminal, not an operation to retry. */
        if (s->error==3 || s->error==4) s->error=7;
        s->phase=2;return net_failure(s->error);
    }
    s->phase=0;return 1;
}
uint64_t liza_rt_reactor_shutdown_write(reactor *r,uint64_t owner,uint64_t generation,uint64_t slot) {
    reactor_slot *s=reactor_find(r,owner,generation,slot);
    if (!s) return net_failure(10);
    if (s->phase==1) return net_failure(4);
    if (s->phase==2) return net_failure(s->error);
    if (s->write_closed) return 0;
#ifdef _WIN32
    int result=shutdown((SOCKET)s->socket,SD_SEND);
#else
    int result=shutdown((int)s->socket,SHUT_WR);
#endif
    if (result!=0) return net_failure(net_error());
    s->write_closed=1;return 0;
}
uint64_t liza_rt_reactor_interest(reactor *r,uint64_t owner,uint64_t generation,uint64_t slot,uint32_t flags) {
    reactor_slot *s=reactor_find(r,owner,generation,slot);
    if (!s) return net_failure(10);
    if (flags>3) return net_failure(6);
    s->interest=flags;return 0;
}
uint64_t liza_rt_reactor_ready(reactor *r,uint64_t owner,uint64_t generation,uint64_t slot) {
    reactor_slot *s=reactor_find(r,owner,generation,slot);
    return s ? s->ready : net_failure(10);
}
uint64_t liza_rt_reactor_poll(reactor *r,uint32_t timeout) {
    for (uint32_t i=0;i<r->capacity;i++) r->slots[i].ready=0;
    if (timeout>INT_MAX) return net_failure(6);
    reactor_pollfd fds[REACTOR_MAX+1];uint32_t indices[REACTOR_MAX+1];uint32_t n=0;
    int available=0;
    for (uint32_t i=0;i<r->capacity;i++) {
        reactor_slot *s=&r->slots[i];
        if (!s->live) {if (s->generation!=UINT64_MAX) available=1;continue;}
        if (!s->interest) continue;
        fds[n].fd=(net_socket)s->socket;fds[n].events=0;fds[n].revents=0;
        if (s->interest&1) fds[n].events|=POLLRDNORM;
        if (s->interest&2) fds[n].events|=POLLWRNORM;
        indices[n++]=i;
    }
    if (available && r->listener_open) {
        fds[n].fd=(net_socket)r->listener;fds[n].events=POLLRDNORM;fds[n].revents=0;
        indices[n++]=REACTOR_MAX;
    }
    /* WSAPoll rejects an empty set. Sleep is the defined empty-set wait. */
#ifdef _WIN32
    if (!n) {Sleep(timeout);return 0;}
    int count=WSAPoll(fds,n,(int)timeout);
#else
    int count=poll(fds,n,(int)timeout);
#endif
    if (count<0) return net_failure(net_error());
    for (uint32_t i=0;i<n;i++) {
        if (indices[i]==REACTOR_MAX) continue;
        uint32_t flags=0;
        if (fds[i].revents&POLLRDNORM) flags|=1;
        if (fds[i].revents&POLLWRNORM) flags|=2;
        if (fds[i].revents&(POLLERR|POLLHUP|POLLNVAL)) flags|=4;
        r->slots[indices[i]].ready=flags;
    }
    return (uint32_t)count;
}
uint64_t liza_rt_reactor_read(reactor *r,uint64_t owner,uint64_t generation,uint64_t slot,
                             uint8_t *data,uint32_t length,uint32_t start,uint32_t count) {
    reactor_slot *s=reactor_find(r,owner,generation,slot);
    if (!s) return net_failure(10);
    if (s->phase==1) return net_failure(4);
    if (s->phase==2) return net_failure(s->error);
    if (start>length || count>length-start || !count) return net_failure(6);
    return liza_rt_net_read(s->socket,data+start,count);
}
uint64_t liza_rt_reactor_write(reactor *r,uint64_t owner,uint64_t generation,uint64_t slot,
                              const uint8_t *data,uint32_t length,uint32_t start,uint32_t count) {
    reactor_slot *s=reactor_find(r,owner,generation,slot);
    if (!s) return net_failure(10);
    if (s->phase==1) return net_failure(4);
    if (s->phase==2) return net_failure(s->error);
    if (s->write_closed) return net_failure(5);
    return liza_rt_net_write(s->socket,data,length,start,count);
}
uint64_t liza_rt_reactor_disconnect(reactor *r,uint64_t owner,uint64_t generation,uint64_t slot) {
    reactor_slot *s=reactor_find(r,owner,generation,slot);
    if (!s) return net_failure(10);
    s->live=0;s->ready=0;s->interest=0;
    return net_failure(liza_rt_net_close(s->socket));
}
uint32_t liza_rt_reactor_close(reactor *r) {
    uint32_t first=0;
    for (uint32_t i=0;i<r->capacity;i++) if (r->slots[i].live) {
        uint32_t e=liza_rt_net_close(r->slots[i].socket);if (!first) first=e;
    }
    if (r->listener_open) {uint32_t e=liza_rt_net_close(r->listener);if (!first) first=e;}
    uint32_t unwatch=reactor_unwatch(r);if (!first) first=unwatch;
    free(r);return first;
}

#ifndef _WIN32
#include <time.h>
#endif
uint32_t liza_rt_reactor_clock(uint64_t *out) {
    *out=0;
#ifdef _WIN32
    *out=GetTickCount64();return 0;
#else
    struct timespec t;
    if(clock_gettime(CLOCK_MONOTONIC,&t)!=0 || t.tv_sec<0)return 7;
    uint64_t seconds=(uint64_t)t.tv_sec, ms=(uint64_t)t.tv_nsec/1000000;
    if(seconds>(UINT64_MAX-ms)/1000)return 7;
    *out=seconds*1000+ms;return 0;
#endif
}
