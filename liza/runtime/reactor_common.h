/* Bounded single-threaded socket owner. Protocol state and payloads live in Liza. */
#include "net_platform.h"
#include <stdlib.h>
#ifdef _WIN32
typedef WSAPOLLFD reactor_pollfd;
#else
#include <poll.h>
typedef struct pollfd reactor_pollfd;
#endif
#define REACTOR_MAX 32
uint32_t liza_rt_net_listen(uint16_t, uint64_t*);
uint32_t liza_rt_net_accept(uint64_t, uint64_t*);
uint64_t liza_rt_net_port(uint64_t);
uint64_t liza_rt_net_read(uint64_t, uint8_t*, uint32_t);
uint64_t liza_rt_net_write(uint64_t, const uint8_t*, uint32_t, uint32_t, uint32_t);
uint32_t liza_rt_net_close(uint64_t);
typedef struct { uint64_t socket,generation; uint32_t live,interest,ready; } reactor_slot;
typedef struct { uint64_t owner,listener; uint32_t capacity; reactor_slot slots[REACTOR_MAX]; } reactor;
/* No tasks/threads in this runtime contract. Never wrap identities. */
static uint64_t reactor_next_owner;
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
uint32_t liza_rt_reactor_create(uint16_t port,uint32_t capacity,reactor **out) {
    *out=NULL;
    if (!capacity || capacity>REACTOR_MAX) return 8;
    if (reactor_next_owner==UINT64_MAX) return 11;
    reactor *r=(reactor*)calloc(1,sizeof(*r));
    if (!r) return 12;
    uint32_t e=liza_rt_net_listen(port,&r->listener);
    if (e) {free(r);return e;}
    e=reactor_nonblocking(r->listener);
    if (!e && listen((net_socket)r->listener,(int)capacity)!=0) e=net_error();
    if (e) {liza_rt_net_close(r->listener);free(r);return e;}
    r->owner=++reactor_next_owner;r->capacity=capacity;*out=r;return 0;
}
uint64_t liza_rt_reactor_port(reactor *r) {return liza_rt_net_port(r->listener);}
uint32_t liza_rt_reactor_accept(reactor *r,uint64_t *id) {
    id[0]=id[1]=id[2]=0;
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
    id[0]=r->owner;id[1]=s->generation;id[2]=index;return 0;
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
    if (available) {
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
    if (start>length || count>length-start || !count) return net_failure(6);
    return liza_rt_net_read(s->socket,data+start,count);
}
uint64_t liza_rt_reactor_write(reactor *r,uint64_t owner,uint64_t generation,uint64_t slot,
                              const uint8_t *data,uint32_t length,uint32_t start,uint32_t count) {
    reactor_slot *s=reactor_find(r,owner,generation,slot);
    if (!s) return net_failure(10);
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
    uint32_t e=liza_rt_net_close(r->listener);if (!first) first=e;
    free(r);return first;
}
