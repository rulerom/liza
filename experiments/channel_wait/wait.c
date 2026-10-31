#ifndef _WIN32
#define _DARWIN_C_SOURCE 1
#define _POSIX_C_SOURCE 200809L
#endif
#include "wait.h"
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#ifndef _WIN32
#include <errno.h>
#include <time.h>
#endif
static void lock(wait_channel *c) {
#ifdef _WIN32
    EnterCriticalSection(&c->mutex);
#else
    if(pthread_mutex_lock(&c->mutex))abort();
#endif
}
static void unlock(wait_channel *c) {
#ifdef _WIN32
    LeaveCriticalSection(&c->mutex);
#else
    if(pthread_mutex_unlock(&c->mutex))abort();
#endif
}
static void notify(wait_channel *c) {
#ifdef WAIT_TEST_SKIP_NOTIFY
    (void)c;return;
#endif
#ifdef _WIN32
    WakeAllConditionVariable(&c->changed);
#else
    if(pthread_cond_broadcast(&c->changed))abort();
#endif
}
int wait_now(uint64_t *ms) {
#ifdef _WIN32
    *ms=GetTickCount64();return 0;
#else
    struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t)||t.tv_sec<0)return 1;
    if((uint64_t)t.tv_sec>(UINT64_MAX-(uint64_t)t.tv_nsec/1000000)/1000)return 1;
    *ms=(uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;return 0;
#endif
}
int wait_init(wait_channel *c,uint32_t capacity) {
    if(!capacity||capacity>64)return 1;memset(c,0,sizeof(*c));c->capacity=capacity;
#ifdef _WIN32
    if(!InitializeCriticalSectionEx(&c->mutex,0,0))return 1;
    InitializeConditionVariable(&c->changed);return 0;
#else
    if(pthread_mutex_init(&c->mutex,NULL))return 1;
    pthread_condattr_t attr;if(pthread_condattr_init(&attr)){pthread_mutex_destroy(&c->mutex);return 1;}
#if !defined(__APPLE__)
    if(pthread_condattr_setclock(&attr,CLOCK_MONOTONIC)){pthread_condattr_destroy(&attr);pthread_mutex_destroy(&c->mutex);return 1;}
#endif
    int err=pthread_cond_init(&c->changed,&attr);pthread_condattr_destroy(&attr);
    if(err)pthread_mutex_destroy(&c->mutex);return err!=0;
#endif
}
/* Condition wait uses the same absolute deadline on every recheck. Mutex
   acquisition and post-wakeup reacquisition are not timed in this probe. */
static int condition_wait(wait_channel *c,uint64_t now,uint64_t deadline) {
    if(c->fail_wait)return -1;
    if(!c->wait_calls)c->first_wait_deadline=deadline;
    else if(c->first_wait_deadline!=deadline && c->deadline_changes<UINT32_MAX)c->deadline_changes++;
    if(c->wait_calls<UINT32_MAX)c->wait_calls++;
    if(c->inject_spurious){c->inject_spurious--;return 0;}
#ifdef _WIN32
    uint64_t remaining=deadline-now;
    DWORD ms=remaining>=0xfffffffeu?0xfffffffeu:(DWORD)remaining;
    if(SleepConditionVariableCS(&c->changed,&c->mutex,ms))return 0;
    if(GetLastError()==ERROR_TIMEOUT)return 0;
    abort(); /* An unexpected sync failure has no recoverability promise. */
#elif defined(__APPLE__)
    uint64_t remaining=deadline-now;
    time_t seconds=(time_t)(remaining/1000);
    if(seconds<0 || (uint64_t)seconds!=remaining/1000)return -1;
    struct timespec duration={seconds,(long)((remaining%1000)*1000000)};
    int err=pthread_cond_timedwait_relative_np(&c->changed,&c->mutex,&duration);
    if(err==0 || err==ETIMEDOUT)return 0;
    abort();
#else
    (void)now;
    time_t seconds=(time_t)(deadline/1000);
    if(seconds<0 || (uint64_t)seconds!=deadline/1000)return -1;
    struct timespec when={seconds,(long)((deadline%1000)*1000000)};
    int err=pthread_cond_timedwait(&c->changed,&c->mutex,&when);
    if(err==0 || err==ETIMEDOUT)return 0;
    abort();
#endif
}
wait_status wait_send(wait_channel *c,uint32_t value,uint64_t deadline) {
    lock(c);
    for(;;){
        if(c->sender_closed||c->receiver_closed){unlock(c);return W_CLOSED;}
        uint64_t now;if(c->fail_clock||wait_now(&now)){unlock(c);return W_CLOCK_ERROR;}
        c->decision_ms=now;
        if(now>=deadline){unlock(c);return W_TIMEOUT;}
        if(c->count<c->capacity){c->slots[c->tail]=value;c->tail=(c->tail+1)%c->capacity;c->count++;notify(c);unlock(c);return W_OK;}
#ifdef WAIT_TEST_RESTART_DEADLINE
        if(c->wait_calls==1)deadline+=100; /* Negative control only. */
#endif
        c->waiters++;int error=condition_wait(c,now,deadline);c->waiters--;
        if(error){unlock(c);return W_SYSTEM_ERROR;}
    }
}
wait_status wait_receive(wait_channel *c,uint32_t *value,uint64_t deadline) {
    lock(c);
    for(;;){
        if(c->receiver_closed||(c->sender_closed&&!c->count)){unlock(c);return W_CLOSED;}
        uint64_t now;if(c->fail_clock||wait_now(&now)){unlock(c);return W_CLOCK_ERROR;}
        c->decision_ms=now;
        if(now>=deadline){unlock(c);return W_TIMEOUT;}
        if(c->count){*value=c->slots[c->head];c->head=(c->head+1)%c->capacity;c->count--;notify(c);unlock(c);return W_OK;}
        c->waiters++;int error=condition_wait(c,now,deadline);c->waiters--;
        if(error){unlock(c);return W_SYSTEM_ERROR;}
    }
}
void wait_close_sender(wait_channel *c){lock(c);c->sender_closed=1;notify(c);unlock(c);}
uint32_t wait_close_receiver(wait_channel *c){lock(c);uint32_t n=c->count;c->count=0;c->head=c->tail;c->receiver_closed=1;notify(c);unlock(c);return n;}
uint32_t wait_waiters(wait_channel *c){lock(c);uint32_t n=c->waiters;unlock(c);return n;}
void wait_poke(wait_channel *c){lock(c);notify(c);unlock(c);}
void wait_destroy(wait_channel *c){
#ifdef _WIN32
    DeleteCriticalSection(&c->mutex);
#else
    if(pthread_cond_destroy(&c->changed)||pthread_mutex_destroy(&c->mutex))abort();
#endif
}
