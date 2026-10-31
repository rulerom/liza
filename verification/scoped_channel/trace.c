/* Test-only logical-event recorder around the actual C channel core. */
#include "scoped_channel_core.h"
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
typedef HANDLE thread_id;
#define THREAD_RESULT DWORD WINAPI
#define THREAD_RETURN return 0
static int start(thread_id *t,LPTHREAD_START_ROUTINE fn,void *p){*t=CreateThread(NULL,0,fn,p,0,NULL);return *t!=NULL;}
static int join(thread_id t){DWORD s=WaitForSingleObject(t,INFINITE);CloseHandle(t);return s==WAIT_OBJECT_0;}
static void yield_thread(void){Sleep(0);}
#else
#include <pthread.h>
#include <sched.h>
typedef pthread_t thread_id;
#define THREAD_RESULT void *
#define THREAD_RETURN return NULL
static int start(thread_id *t,void *(*fn)(void *),void *p){return pthread_create(t,NULL,fn,p)==0;}
static int join(thread_id t){return pthread_join(t,NULL)==0;}
static void yield_thread(void){sched_yield();}
#endif
typedef struct {int phase,id,op;uint32_t arg,result;} event;
typedef struct {channel *c;atomic_int go,clock,first_ready;event events[14];} context;
static void log_event(context *c,int phase,int id,int op,uint32_t arg,uint32_t result){
    int i=atomic_fetch_add_explicit(&c->clock,1,memory_order_relaxed);
    if(i<0||i>=14)abort();c->events[i]=(event){phase,id,op,arg,result};
}
static THREAD_RESULT producer(void *p){
    context *c=p;while(!atomic_load(&c->go))yield_thread();
    for(int i=0;i<3;i++){
        log_event(c,0,i,0,(uint32_t)i,0);
        if(i==0){atomic_fetch_add(&c->first_ready,1);while(atomic_load(&c->first_ready)<2)yield_thread();}
        uint32_t result=(uint32_t)liza_scoped_send(c->c,(uint32_t)i);
        log_event(c,1,i,0,(uint32_t)i,result);
    }
    log_event(c,0,3,2,0,0);liza_scoped_close_sender(c->c);log_event(c,1,3,2,0,0);
    THREAD_RETURN;
}
static THREAD_RESULT consumer(void *p){
    context *c=p;while(!atomic_load(&c->go))yield_thread();
    for(int i=4;i<6;i++){
        uint32_t value=0;log_event(c,0,i,1,0,0);
        if(i==4){atomic_fetch_add(&c->first_ready,1);while(atomic_load(&c->first_ready)<2)yield_thread();}
        uint32_t status=(uint32_t)liza_scoped_receive(c->c,&value);
        log_event(c,1,i,1,value,status);
    }
    log_event(c,0,6,3,0,0);uint32_t n=(uint32_t)liza_scoped_close_receiver(c->c);log_event(c,1,6,3,n,0);
    THREAD_RETURN;
}
int main(void){
    for(int round=0;round<200;round++){
        context c={0};size_t bytes=0;thread_id a,b;
        atomic_init(&c.go,0);atomic_init(&c.clock,0);atomic_init(&c.first_ready,0);
        if(liza_scoped_create(2,1024,&c.c,&bytes)!=CH_OK)return 1;
        if(!start(&a,producer,&c)||!start(&b,consumer,&c))return 2;
        atomic_store(&c.go,1);
        if(!join(a)||!join(b)||atomic_load(&c.clock)!=14)return 3;
        printf("trace %d\n",round);
        for(int i=0;i<14;i++){
            event e=c.events[i];printf("%d %d %d %d %u %u\n",i,e.phase,e.id,e.op,e.arg,e.result);
        }
        liza_scoped_destroy(c.c);
    }
    return 0;
}
