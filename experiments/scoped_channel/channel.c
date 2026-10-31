#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "channel.h"
#include <stdlib.h>
#ifdef CH_MEASURE
#include <time.h>
#endif
#ifdef _WIN32
#include <windows.h>
typedef SRWLOCK ch_mutex;
static int lock_init(ch_mutex *m) {InitializeSRWLock(m);return 0;}
static void lock(ch_mutex *m) {AcquireSRWLockExclusive(m);}
static void unlock(ch_mutex *m) {ReleaseSRWLockExclusive(m);}
static void lock_destroy(ch_mutex *m) {(void)m;}
#else
#include <pthread.h>
#ifdef CH_MEASURE
#include <errno.h>
#endif
typedef pthread_mutex_t ch_mutex;
static int lock_init(ch_mutex *m) {return pthread_mutex_init(m,NULL);}
static void lock(ch_mutex *m) {if(pthread_mutex_lock(m))abort();}
static void unlock(ch_mutex *m) {if(pthread_mutex_unlock(m))abort();}
static void lock_destroy(ch_mutex *m) {if(pthread_mutex_destroy(m))abort();}
#endif
struct channel {
    ch_mutex mutex;
    size_t capacity,head,tail,count;
    int sender_closed,receiver_closed;
#ifdef CH_MEASURE
    ch_metrics metrics;
    uint64_t hold_start;
#endif
    uint32_t slots[];
};
#ifdef CH_MEASURE
static uint64_t ch_now_ns(void) {
#ifdef _WIN32
    LARGE_INTEGER v,f;if(!QueryPerformanceCounter(&v)||!QueryPerformanceFrequency(&f))abort();
    return (uint64_t)(((long double)v.QuadPart*1000000000.0L)/(long double)f.QuadPart);
#else
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();
    return (uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec;
#endif
}
static void ch_lock(channel *c) {
    uint64_t before=ch_now_ns();int contended;
#ifdef _WIN32
    contended=!TryAcquireSRWLockExclusive(&c->mutex);
    if(contended)lock(&c->mutex);
#else
    int rc=pthread_mutex_trylock(&c->mutex);
    if(rc && rc!=EBUSY)abort();
    contended=rc!=0;if(contended)lock(&c->mutex);
#endif
    uint64_t now=ch_now_ns(), wait=now-before;
    c->metrics.acquisitions++;c->metrics.contended+=(uint64_t)contended;
    c->metrics.wait_ns+=wait;if(wait>c->metrics.max_wait_ns)c->metrics.max_wait_ns=wait;
    c->hold_start=now;
}
static void ch_unlock(channel *c) {
    uint64_t hold=ch_now_ns()-c->hold_start;
    c->metrics.hold_ns+=hold;if(hold>c->metrics.max_hold_ns)c->metrics.max_hold_ns=hold;
    unlock(&c->mutex);
}
void ch_get_metrics(channel *c,ch_metrics *out) {ch_lock(c);*out=c->metrics;ch_unlock(c);}
#else
static void ch_lock(channel *c) {lock(&c->mutex);}
static void ch_unlock(channel *c) {unlock(&c->mutex);}
#endif
ch_status ch_create(size_t n,size_t budget,channel **out,size_t *bytes) {
    if(!out || !bytes)return CH_INVALID;
    *out=NULL;*bytes=0;
    if(!n || n>65536 || n>(SIZE_MAX-sizeof(channel))/sizeof(uint32_t))return CH_INVALID;
    size_t cost=sizeof(channel)+n*sizeof(uint32_t);
    if(cost>budget)return CH_INVALID;
#ifdef CH_TEST_FAIL_ALLOC
    channel *c=NULL;
#else
    channel *c=malloc(cost);
#endif
    if(!c)return CH_NOMEM;
    if(lock_init(&c->mutex)){free(c);return CH_NOMEM;}
#ifdef CH_MEASURE
    c->metrics=(ch_metrics){0};c->hold_start=0;
#endif
    c->capacity=n;c->head=c->tail=c->count=0;c->sender_closed=c->receiver_closed=0;
    *bytes=cost;*out=c;return CH_OK;
}
ch_status ch_send(channel *c,uint32_t value) {
    ch_lock(c);
    if(c->sender_closed || c->receiver_closed){ch_unlock(c);return CH_CLOSED;}
    if(c->count==c->capacity){
#ifdef CH_TEST_BREAK_FULL
        c->slots[c->head]^=1; /* Negative control: corrupt state on Full. */
#endif
        ch_unlock(c);return CH_FULL;
    }
    /* Lock reserves the tail; publish only after the complete scalar copy. */
    c->slots[c->tail]=value;
    c->tail = c->tail+1==c->capacity ? 0 : c->tail+1;
    ++c->count;ch_unlock(c);return CH_OK;
}
ch_status ch_receive(channel *c,uint32_t *value) {
    ch_lock(c);
    if(c->receiver_closed){ch_unlock(c);return CH_CLOSED;}
    if(!c->count){ch_status status=c->sender_closed?CH_CLOSED:CH_EMPTY;ch_unlock(c);return status;}
    *value=c->slots[c->head];
    c->head = c->head+1==c->capacity ? 0 : c->head+1;
    --c->count;ch_unlock(c);return CH_OK;
}
void ch_close_sender(channel *c) {ch_lock(c);c->sender_closed=1;ch_unlock(c);}
size_t ch_close_receiver(channel *c) {
    ch_lock(c);size_t discarded=c->count;
    c->receiver_closed=1;c->count=0;c->head=c->tail;
    ch_unlock(c);return discarded;
}
void ch_destroy(channel *c) {lock_destroy(&c->mutex);free(c);}
