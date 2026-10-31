#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "wait.h"
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#ifdef _WIN32
typedef HANDLE thread_id;
#define THREAD_RESULT DWORD WINAPI
#define THREAD_RETURN return 0
static int start(thread_id *t,LPTHREAD_START_ROUTINE f,void *p){*t=CreateThread(NULL,0,f,p,0,NULL);return *t!=NULL;}
static int join(thread_id t){DWORD s=WaitForSingleObject(t,INFINITE);CloseHandle(t);return s==WAIT_OBJECT_0;}
static void pause_ms(unsigned ms){Sleep(ms);}
#else
#include <pthread.h>
#include <time.h>
typedef pthread_t thread_id;
#define THREAD_RESULT void *
#define THREAD_RETURN return NULL
static int start(thread_id *t,void *(*f)(void *),void *p){return pthread_create(t,NULL,f,p)==0;}
static int join(thread_id t){return pthread_join(t,NULL)==0;}
static void pause_ms(unsigned ms){struct timespec t={(time_t)(ms/1000),(long)((ms%1000)*1000000)};nanosleep(&t,NULL);}
#endif
#define CHECK(x) do {if(!(x)){fprintf(stderr,"failure line %d: %s\n",__LINE__,#x);return 1;}} while(0)
typedef struct {wait_channel *c;uint64_t deadline;wait_status result;atomic_int started;} sender_ctx;
static THREAD_RESULT sender(void *p){sender_ctx *ctx=p;atomic_store(&ctx->started,1);ctx->result=wait_send(ctx->c,22,ctx->deadline);THREAD_RETURN;}
typedef struct {wait_channel *c;uint64_t deadline,returned;wait_status result;atomic_int started;} receiver_ctx;
static THREAD_RESULT receiver(void *p){receiver_ctx *ctx=p;uint32_t value=0;atomic_store(&ctx->started,1);ctx->result=wait_receive(ctx->c,&value,ctx->deadline);if(wait_now(&ctx->returned))abort();THREAD_RETURN;}
typedef struct {wait_channel *c;atomic_int held,go;} holder_ctx;
static void lock_direct(wait_channel *c){
#ifdef _WIN32
    EnterCriticalSection(&c->mutex);
#else
    if(pthread_mutex_lock(&c->mutex))abort();
#endif
}
static void unlock_direct(wait_channel *c){
#ifdef _WIN32
    LeaveCriticalSection(&c->mutex);
#else
    if(pthread_mutex_unlock(&c->mutex))abort();
#endif
}
static THREAD_RESULT holder(void *p){holder_ctx *ctx=p;lock_direct(ctx->c);atomic_store(&ctx->held,1);while(!atomic_load(&ctx->go))pause_ms(1);pause_ms(100);unlock_direct(ctx->c);THREAD_RETURN;}
typedef struct {wait_channel *c;atomic_int started;} poke_ctx;
static int wait_registered(wait_channel *c){for(unsigned i=0;i<2000;i++){if(wait_waiters(c))return 1;pause_ms(1);}return 0;}
static THREAD_RESULT poker(void *p){poke_ctx *ctx=p;atomic_store(&ctx->started,1);for(unsigned i=0;i<30;i++){wait_poke(ctx->c);pause_ms(5);}THREAD_RETURN;}
int main(void){
    wait_channel c;uint64_t now;uint32_t value=99;
    CHECK(wait_init(&c,0)!=0 && wait_init(&c,65)!=0);
    CHECK(wait_now(&now)==0);CHECK(wait_init(&c,1)==0);
    CHECK(wait_send(&c,11,now+1000)==W_OK);wait_close_sender(&c);
    CHECK(wait_receive(&c,&value,0)==W_TIMEOUT && value==99);
    CHECK(wait_now(&now)==0);CHECK(wait_receive(&c,&value,now+1000)==W_OK && value==11);
    CHECK(wait_receive(&c,&value,0)==W_CLOSED);
    wait_destroy(&c);
    CHECK(wait_init(&c,1)==0);CHECK(wait_now(&now)==0);CHECK(wait_send(&c,11,now+1000)==W_OK);
    CHECK(wait_send(&c,22,0)==W_TIMEOUT);CHECK(wait_close_receiver(&c)==1);
    CHECK(wait_send(&c,22,0)==W_CLOSED);wait_destroy(&c);
    CHECK(wait_init(&c,1)==0);c.fail_clock=1;CHECK(wait_receive(&c,&value,UINT64_MAX)==W_CLOCK_ERROR);
    c.fail_clock=0;c.fail_wait=1;CHECK(wait_now(&now)==0);CHECK(wait_receive(&c,&value,now+1000)==W_SYSTEM_ERROR);
    c.fail_wait=0;CHECK(wait_send(&c,9,now+1000)==W_OK);CHECK(wait_receive(&c,&value,now+1000)==W_OK && value==9);wait_destroy(&c);
    CHECK(wait_init(&c,1)==0);c.fail_clock=1;CHECK(wait_close_receiver(&c)==0);
    CHECK(wait_send(&c,9,0)==W_CLOSED);wait_destroy(&c);
    CHECK(wait_init(&c,1)==0);CHECK(wait_now(&now)==0);CHECK(wait_send(&c,11,now+1000)==W_OK);
    sender_ctx sender_state={0};sender_state.c=&c;sender_state.deadline=now+2000;atomic_init(&sender_state.started,0);
    thread_id thread;CHECK(start(&thread,sender,&sender_state));while(!atomic_load(&sender_state.started))pause_ms(1);
    CHECK(wait_registered(&c));
    CHECK(wait_receive(&c,&value,now+1000)==W_OK && value==11);
    CHECK(join(thread));CHECK(sender_state.result==W_OK);
    CHECK(wait_receive(&c,&value,now+2000)==W_OK && value==22);wait_destroy(&c);
    CHECK(wait_init(&c,1)==0);CHECK(wait_now(&now)==0);CHECK(wait_send(&c,11,now+1000)==W_OK);
    sender_state.c=&c;sender_state.deadline=now+2000;sender_state.result=W_SYSTEM_ERROR;atomic_store(&sender_state.started,0);
    CHECK(start(&thread,sender,&sender_state));while(!atomic_load(&sender_state.started))pause_ms(1);
    CHECK(wait_registered(&c));
    CHECK(wait_close_receiver(&c)==1);CHECK(join(thread));CHECK(sender_state.result==W_CLOSED);wait_destroy(&c);
    CHECK(wait_init(&c,1)==0);CHECK(wait_now(&now)==0);
    receiver_ctx receiving={0};receiving.c=&c;receiving.deadline=now+2000;atomic_init(&receiving.started,0);
    CHECK(start(&thread,receiver,&receiving));while(!atomic_load(&receiving.started))pause_ms(1);
    CHECK(wait_registered(&c));wait_close_sender(&c);CHECK(join(thread));CHECK(receiving.result==W_CLOSED);wait_destroy(&c);
    /* Hold the lock across a condition timeout to observe reacquisition delay. */
    CHECK(wait_init(&c,1)==0);CHECK(wait_now(&now)==0);
    receiving.c=&c;receiving.deadline=now+1000;atomic_store(&receiving.started,0);
    CHECK(start(&thread,receiver,&receiving));while(!atomic_load(&receiving.started))pause_ms(1);
    CHECK(wait_registered(&c));lock_direct(&c);uint64_t held_at;CHECK(wait_now(&held_at)==0);
    if(held_at<receiving.deadline) {
        pause_ms((unsigned)(receiving.deadline-held_at)+60);unlock_direct(&c);
        CHECK(join(thread));CHECK(receiving.result==W_TIMEOUT && c.decision_ms>=receiving.deadline);
        printf("reacquire_deadline_ms=%llu reacquire_decision_ms=%llu reacquire_return_ms=%llu\n",(unsigned long long)receiving.deadline,(unsigned long long)c.decision_ms,(unsigned long long)receiving.returned);
    } else {
        unlock_direct(&c);CHECK(join(thread));CHECK(receiving.result==W_TIMEOUT);
        puts("reacquire_skipped=scheduling");
    }
    wait_destroy(&c);
    CHECK(wait_init(&c,1)==0);holder_ctx held={0};held.c=&c;atomic_init(&held.held,0);atomic_init(&held.go,0);
    CHECK(start(&thread,holder,&held));while(!atomic_load(&held.held))pause_ms(1);
    CHECK(wait_now(&now)==0);uint64_t lock_deadline=now+30;atomic_store(&held.go,1);
    CHECK(wait_send(&c,77,lock_deadline)==W_TIMEOUT);uint64_t lock_return;CHECK(wait_now(&lock_return)==0);
    CHECK(join(thread));CHECK(c.decision_ms>=lock_deadline);
    printf("lock_deadline_ms=%llu lock_decision_ms=%llu lock_return_ms=%llu\n",(unsigned long long)lock_deadline,(unsigned long long)c.decision_ms,(unsigned long long)lock_return);
    wait_destroy(&c);
    CHECK(wait_init(&c,1)==0);CHECK(wait_now(&now)==0);CHECK(wait_send(&c,11,now+1000)==W_OK);
    c.inject_spurious=3;
    poke_ctx wake={0};wake.c=&c;atomic_init(&wake.started,0);CHECK(start(&thread,poker,&wake));
    while(!atomic_load(&wake.started))pause_ms(1);
    uint64_t begin;CHECK(wait_now(&begin)==0);uint64_t deadline=begin+80;
    CHECK(wait_send(&c,22,deadline)==W_TIMEOUT);uint64_t returned;CHECK(wait_now(&returned)==0);
    CHECK(c.decision_ms>=deadline);uint64_t decision=c.decision_ms;CHECK(join(thread));
    CHECK(c.wait_calls>=4);CHECK(c.deadline_changes==0);
    CHECK(wait_receive(&c,&value,returned+1000)==W_OK && value==11);
    printf("deadline_ms=%llu decision_ms=%llu return_ms=%llu\n",(unsigned long long)deadline,(unsigned long long)decision,(unsigned long long)returned);
    wait_destroy(&c);puts("wait probe passed");return 0;
}
