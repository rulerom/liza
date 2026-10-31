#include "channel.h"
#include <stdatomic.h>
#include <stdio.h>
#ifdef CH_MEASURE
#include <inttypes.h>
#endif
#include <stdlib.h>
#ifdef _WIN32
#include <windows.h>
typedef HANDLE thread_id;
#define THREAD_RESULT DWORD WINAPI
#define THREAD_RETURN return 0
static int start(thread_id *t, LPTHREAD_START_ROUTINE fn, void *arg) {*t=CreateThread(NULL,0,fn,arg,0,NULL);return *t!=NULL;}
static int join(thread_id t) {DWORD r=WaitForSingleObject(t,INFINITE);CloseHandle(t);return r==WAIT_OBJECT_0;}
static void yield_thread(void) {Sleep(0);}
#else
#include <pthread.h>
#include <sched.h>
typedef pthread_t thread_id;
#define THREAD_RESULT void *
#define THREAD_RETURN return NULL
static int start(thread_id *t,void *(*fn)(void *),void *arg) {return pthread_create(t,NULL,fn,arg)==0;}
static int join(thread_id t) {return pthread_join(t,NULL)==0;}
static void yield_thread(void) {sched_yield();}
#endif
#define CHECK(x) do { if(!(x)){fprintf(stderr,"check failed at line %d: %s\n",__LINE__,#x);return 1;} } while(0)
typedef struct {channel *c;atomic_int go;uint32_t count;int producer_error,consumer_error;} stress_ctx;
static THREAD_RESULT producer(void *arg) {
    stress_ctx *x=arg;while(!atomic_load(&x->go))yield_thread();
    for(uint32_t i=0;i<x->count;i++) {
        ch_status st;while((st=ch_send(x->c,i))==CH_FULL)yield_thread();
        if(st!=CH_OK){x->producer_error=1;break;}
    }
    ch_close_sender(x->c);THREAD_RETURN;
}
static THREAD_RESULT consumer(void *arg) {
    stress_ctx *x=arg;while(!atomic_load(&x->go))yield_thread();
    uint32_t next=0;
    for(;;) {
        uint32_t value=UINT32_MAX;ch_status st=ch_receive(x->c,&value);
        if(st==CH_EMPTY){yield_thread();continue;}
        if(st==CH_CLOSED)break;
        if(st!=CH_OK || value!=next){x->consumer_error=1;break;}
        ++next;
    }
    if(next!=x->count)x->consumer_error=1;
    THREAD_RETURN;
}
typedef struct {channel *c;ch_status result;} race_ctx;
static THREAD_RESULT race_send(void *arg) {race_ctx *x=arg;x->result=ch_send(x->c,42);THREAD_RETURN;}
int main(void) {
    channel *c=NULL;size_t bytes=0;uint32_t x=77;
    CHECK(ch_create(0,SIZE_MAX,&c,&bytes)==CH_INVALID && c==NULL && bytes==0);
    CHECK(ch_create(SIZE_MAX,SIZE_MAX,&c,&bytes)==CH_INVALID && c==NULL);
    CHECK(ch_create(2,SIZE_MAX,&c,&bytes)==CH_OK && bytes>=2*sizeof(uint32_t));
    size_t cost=bytes;ch_destroy(c);c=NULL;
    CHECK(ch_create(2,cost-1,&c,&bytes)==CH_INVALID && c==NULL);
    CHECK(ch_create(2,cost,&c,&bytes)==CH_OK && bytes==cost);
    CHECK(ch_receive(c,&x)==CH_EMPTY && x==77);
    CHECK(ch_send(c,10)==CH_OK && ch_send(c,20)==CH_OK && ch_send(c,30)==CH_FULL);
    CHECK(ch_receive(c,&x)==CH_OK && x==10);
    CHECK(ch_send(c,30)==CH_OK);
    ch_close_sender(c);ch_close_sender(c);
    CHECK(ch_send(c,40)==CH_CLOSED);
    CHECK(ch_receive(c,&x)==CH_OK && x==20);
    CHECK(ch_receive(c,&x)==CH_OK && x==30);
    CHECK(ch_receive(c,&x)==CH_CLOSED);
    CHECK(ch_close_receiver(c)==0 && ch_close_receiver(c)==0);ch_destroy(c);
    CHECK(ch_create(1,SIZE_MAX,&c,&bytes)==CH_OK);
    CHECK(ch_send(c,1)==CH_OK && ch_close_receiver(c)==1 && ch_send(c,2)==CH_CLOSED);
    CHECK(ch_close_receiver(c)==0 && ch_receive(c,&x)==CH_CLOSED);ch_destroy(c);
    for(int round=0;round<1000;round++) {
        CHECK(ch_create(1,SIZE_MAX,&c,&bytes)==CH_OK);
        race_ctx race={c,CH_INVALID};thread_id t;
        CHECK(start(&t,race_send,&race));size_t discarded=ch_close_receiver(c);
        CHECK(join(t));
        CHECK((race.result==CH_OK && discarded==1) || (race.result==CH_CLOSED && discarded==0));
        CHECK(ch_send(c,1)==CH_CLOSED);ch_destroy(c);
    }
    for(size_t cap=1;cap<=64;cap*=4) {
        CHECK(ch_create(cap,SIZE_MAX,&c,&bytes)==CH_OK);
        stress_ctx ctx={0};ctx.c=c;ctx.count=100000;atomic_init(&ctx.go,0);thread_id a,b;
        CHECK(start(&a,producer,&ctx));CHECK(start(&b,consumer,&ctx));atomic_store(&ctx.go,1);
        CHECK(join(a) && join(b));CHECK(!ctx.producer_error && !ctx.consumer_error);
#ifdef CH_MEASURE
        ch_metrics m;ch_get_metrics(c,&m);
        printf("capacity=%zu messages=%u bytes=%zu acquisitions=%" PRIu64 " contended=%" PRIu64 " wait_ns=%" PRIu64 " hold_ns=%" PRIu64 " max_wait_ns=%" PRIu64 " max_hold_ns=%" PRIu64 "\n",cap,ctx.count,bytes,m.acquisitions,m.contended,m.wait_ns,m.hold_ns,m.max_wait_ns,m.max_hold_ns);
#endif
        ch_destroy(c);
    }
    puts("channel probe passed");return 0;
}
