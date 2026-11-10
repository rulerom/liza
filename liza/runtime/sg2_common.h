/* Private bounded runner. Only native C callers opt into this module. */
#include "sg2.h"
#include "scoped_channel_core.h"
#include "net_platform.h"
#include <stdatomic.h>
#include <stdlib.h>
#include <time.h>
#ifdef _WIN32
#include <windows.h>
typedef HANDLE sg_thread;
typedef SRWLOCK sg_mutex;
typedef CONDITION_VARIABLE sg_cond;
#define SG_ENTRY DWORD WINAPI
#define SG_RETURN return 0
static void sg_lock(sg_mutex *m){AcquireSRWLockExclusive(m);}
static void sg_unlock(sg_mutex *m){ReleaseSRWLockExclusive(m);}
static int sg_trylock(sg_mutex *m){return TryAcquireSRWLockExclusive(m)!=0;}
static int sg_mutex_init(sg_mutex *m){InitializeSRWLock(m);return 1;}
static void sg_mutex_destroy(sg_mutex *m){(void)m;}
static int sg_cond_init(sg_cond *c){InitializeConditionVariable(c);return 1;}
static void sg_wait(sg_cond *c,sg_mutex *m){if(!SleepConditionVariableSRW(c,m,INFINITE,0))abort();}
static void sg_signal(sg_cond *c){WakeConditionVariable(c);}
static uint64_t sg_now(void){return GetTickCount64();}
static void sg_pause(void){Sleep(1);}
#else
#include <pthread.h>
typedef pthread_t sg_thread;
typedef pthread_mutex_t sg_mutex;
typedef pthread_cond_t sg_cond;
#define SG_ENTRY void *
#define SG_RETURN return NULL
static void sg_lock(sg_mutex *m){if(pthread_mutex_lock(m))abort();}
static void sg_unlock(sg_mutex *m){if(pthread_mutex_unlock(m))abort();}
static int sg_trylock(sg_mutex *m){int e=pthread_mutex_trylock(m);if(e&&e!=EBUSY)abort();return !e;}
static int sg_mutex_init(sg_mutex *m){return !pthread_mutex_init(m,NULL);}
static void sg_mutex_destroy(sg_mutex *m){if(pthread_mutex_destroy(m))abort();}
static int sg_cond_init(sg_cond *c){return !pthread_cond_init(c,NULL);}
static void sg_wait(sg_cond *c,sg_mutex *m){if(pthread_cond_wait(c,m))abort();}
static void sg_signal(sg_cond *c){if(pthread_cond_signal(c))abort();}
static uint64_t sg_now(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();return (uint64_t)t.tv_sec*1000+(uint64_t)t.tv_nsec/1000000;}
static void sg_pause(void){struct timespec t={0,1000000};nanosleep(&t,NULL);}
#endif
#ifdef LIZA_SG2_TESTING
#define SG_EVENT(k,g,i) sg2_test_event(k,g,i)
#else
#define SG_EVENT(k,g,i) ((void)0)
#endif
static void sg_abort(uint64_t generation){SG_EVENT("process_abort",generation,0);(void)generation;_Exit(86);}
static int sg_start(sg_thread *t,
#ifdef _WIN32
    LPTHREAD_START_ROUTINE fn,
#else
    void *(*fn)(void *),
#endif
    void *p,size_t stack) {
#ifdef _WIN32
    *t=CreateThread(NULL,stack,fn,p,STACK_SIZE_PARAM_IS_A_RESERVATION,NULL);return *t!=NULL;
#else
    pthread_attr_t a;if(pthread_attr_init(&a))return 0;
    int e=pthread_attr_setstacksize(&a,stack);if(!e)e=pthread_create(t,&a,fn,p);
    pthread_attr_destroy(&a);return !e;
#endif
}
static int sg_join(sg_thread t){
#ifdef _WIN32
    if(WaitForSingleObject(t,INFINITE)!=WAIT_OBJECT_0)return 0;return CloseHandle(t)!=0;
#else
    return !pthread_join(t,NULL);
#endif
}
uint32_t liza_rt_reactor_create(uint16_t,uint32_t,reactor **);
uint32_t liza_rt_reactor_close(reactor *);
uint64_t liza_rt_reactor_allocation_bytes(void);
enum {SG_FREE,SG_SUBMITTED,SG_JOINING,SG_RETURNED};
typedef struct {
    sg_mutex lock;sg_cond ready;atomic_int initialized;
    size_t stack;
    atomic_int state;uint64_t generation;
    sg_thread handles[3];unsigned count;
    atomic_uint_fast64_t receipts[3];
} sg_service;
/* Two fixed join lanes. A blocked native join cannot occupy B's lane. */
#define SG_GROUP_LIMIT 2
static sg_service services[SG_GROUP_LIMIT];
static atomic_int admitted[SG_GROUP_LIMIT];
static atomic_uint_fast64_t next_generation;
static _Thread_local int sg_owner_active;
static SG_ENTRY sg_reaper(void *ptr) {
    sg_service *service=ptr;
    for(;;){
        sg_lock(&service->lock);
        while(atomic_load(&service->state)!=SG_SUBMITTED)sg_wait(&service->ready,&service->lock);
        sg_thread handles[3];unsigned count=service->count;uint64_t generation=service->generation;
        for(unsigned i=0;i<count;i++)handles[i]=service->handles[i];
        atomic_store(&service->state,SG_JOINING);sg_unlock(&service->lock);
        for(unsigned i=0;i<count;i++){
#ifdef SG2_BREAK_RECEIPT_ORDER
            SG_EVENT("receipt",generation,i);
#endif
            if(!sg_join(handles[i]))sg_abort(generation);
            SG_EVENT("join",generation,i);
            SG_EVENT("receipt",generation,i);
#ifdef LIZA_SG2_TESTING
            if(atomic_load(&sg2_test_stale_receipt))atomic_store(&service->receipts[i],generation-1);
            else
#endif
            atomic_store_explicit(&service->receipts[i],generation,memory_order_release);
        }
#ifdef LIZA_SG2_TESTING
        while(atomic_load(&sg2_test_handback_gate))sg_pause();
#endif
        SG_EVENT("handback",generation,0);
        /* Last access to request contents. Subsequent loop accesses only mailbox. */
        atomic_store_explicit(&service->state,SG_RETURNED,memory_order_release);
    }
    SG_RETURN;
}
static int sg_step(const liza_sg2_config *c,unsigned *step){
    ++*step;
#ifdef LIZA_SG2_TESTING
    return !c->fail_at||*step!=c->fail_at;
#else
    (void)c;return 1;
#endif
}
static int sg_service_init(sg_service *service,const liza_sg2_config *c,unsigned *step){
    if(service->initialized)return service->stack==c->service_stack_bytes;
    if(!sg_step(c,step)||!sg_mutex_init(&service->lock))return 0;
    if(!sg_step(c,step)||!sg_cond_init(&service->ready)){sg_mutex_destroy(&service->lock);return 0;}
    atomic_init(&service->state,SG_FREE);for(unsigned i=0;i<3;i++)atomic_init(&service->receipts[i],0);
    sg_thread t;
    if(!sg_step(c,step)||!sg_start(&t,sg_reaper,service,c->service_stack_bytes)){
#ifndef _WIN32
        pthread_cond_destroy(&service->ready);
#endif
        sg_mutex_destroy(&service->lock);return 0;
    }
#ifdef _WIN32
    if(!CloseHandle(t))abort();
#else
    if(pthread_detach(t))abort();
#endif
    service->stack=c->service_stack_bytes;atomic_store(&service->initialized,1);return 1;
}
typedef struct {net_socket read,write;} sg_wake;
typedef struct sg_group sg_group;
struct liza_sg2_context {sg_group *group;unsigned role;};
static _Thread_local liza_sg2_context *sg_current;
static void sg_check_context(liza_sg2_context *ctx){if(!ctx||sg_current!=ctx)abort();}
typedef struct {atomic_uint_fast64_t version,state,deadline;} sg_status;
struct sg_group {
    sg_mutex lock;channel *fifo;sg_wake data,control;
    liza_sg2_config config;liza_sg2_fn functions[2];liza_sg2_context contexts[3];
    sg_status status[3];
    atomic_int gate,stop_intent,shutdown,monitor_stop,fault,overdue,control_fault;
    reactor *owned_reactor;size_t reactor_bytes;
    atomic_uint_fast64_t shutdown_deadline,delivery_deadline;
    uint64_t generation;uint32_t results[2];int armed,pending;
    unsigned sockets,peak_sockets;
};
static void sg_status_set(sg_status *s,unsigned state,uint64_t deadline){
    uint64_t v=atomic_load(&s->version);if(v>=UINT64_MAX-1)abort();
    atomic_store(&s->version,v+1);atomic_store(&s->state,state);atomic_store(&s->deadline,deadline);atomic_store(&s->version,v+2);
}
static int sg_status_read(sg_status *s,uint64_t *state,uint64_t *deadline){
    for(unsigned i=0;i<8;i++){uint64_t v=atomic_load(&s->version);if(v&1)continue;
        uint64_t a=atomic_load(&s->state),b=atomic_load(&s->deadline);
        if(v==atomic_load(&s->version)){*state=a;*deadline=b;return 1;}}
    return 0;
}
static void sg_fault(sg_group *g,int code){int zero=0;atomic_compare_exchange_strong(&g->fault,&zero,code);}
static void sg_socket_added(sg_group *g){++g->sockets;if(g->sockets>g->peak_sockets)g->peak_sockets=g->sockets;}
static void sg_socket_close(sg_group *g,net_socket *s){if(*s!=NET_INVALID){if(net_os_close(*s))sg_abort(g->generation);*s=NET_INVALID;--g->sockets;}}
static int sg_nonblock(net_socket s){
#ifdef _WIN32
    u_long on=1;return !ioctlsocket(s,FIONBIO,&on);
#else
    int f=fcntl(s,F_GETFL,0);return f>=0&&!fcntl(s,F_SETFL,f|O_NONBLOCK);
#endif
}
static int sg_wake_create(sg_group *g,sg_wake *w,unsigned *step){
    net_socket listener=NET_INVALID;struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(0x7f000001u);
    if(!sg_step(&g->config,step))goto fail;
    listener=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);if(listener==NET_INVALID)goto fail;sg_socket_added(g);
    if(!sg_step(&g->config,step)||bind(listener,(struct sockaddr*)&a,sizeof(a))||listen(listener,1))goto fail;
#ifdef _WIN32
    int len=sizeof(a);
#else
    socklen_t len=sizeof(a);
#endif
    if(!sg_step(&g->config,step)||getsockname(listener,(struct sockaddr*)&a,&len))goto fail;
    if(!sg_step(&g->config,step))goto fail;
    w->write=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);if(w->write==NET_INVALID)goto fail;sg_socket_added(g);
    if(!sg_step(&g->config,step)||connect(w->write,(struct sockaddr*)&a,sizeof(a)))goto fail;
    if(!sg_step(&g->config,step))goto fail;
    w->read=accept(listener,NULL,NULL);if(w->read==NET_INVALID)goto fail;sg_socket_added(g);
    if(!sg_step(&g->config,step)||net_prepare(w->read)||net_prepare(w->write)||!sg_nonblock(w->read)||!sg_nonblock(w->write))goto fail;
    sg_socket_close(g,&listener);return 1;
fail:
    sg_socket_close(g,&listener);sg_socket_close(g,&w->read);sg_socket_close(g,&w->write);return 0;
}
static int sg_wake_send(sg_wake *w){
    char byte=1;
#ifdef MSG_NOSIGNAL
    return send(w->write,&byte,1,MSG_NOSIGNAL)==1;
#else
    return send(w->write,&byte,1,0)==1;
#endif
}
static int sg_wake_drain(sg_wake *w){
    char bytes[64];for(unsigned i=0;i<8;i++){
        int n=(int)recv(w->read,bytes,sizeof(bytes),0);if(n>0)continue;
        return n<0&&net_error()==4;
    }return 1;
}
static int sg_notify(sg_group *g){
    if(atomic_load(&g->fault))return 0;
    if(!g->armed||g->pending)return 1;
#ifdef LIZA_SG2_TESTING
    if(g->config.data_fault){sg_fault(g,1);return 0;}
#endif
    if(!sg_wake_send(&g->data)){sg_fault(g,1);return 0;}g->pending=1;return 1;
}
uint32_t liza_sg2_reactor_create(liza_sg2_context *ctx,uint16_t port,reactor **out){
    sg_check_context(ctx);if(ctx->role!=1||!out)abort();*out=NULL;sg_group *g=ctx->group;
    if(g->owned_reactor)return 6;
    uint32_t e=liza_rt_reactor_create(port,g->config.reactor_capacity,&g->owned_reactor);
    if(!e){g->reactor_bytes=(size_t)liza_rt_reactor_allocation_bytes();*out=g->owned_reactor;}
    return e;
}
uint32_t liza_sg2_send(liza_sg2_context *ctx,uint32_t value){
    sg_check_context(ctx);if(ctx->role!=0)abort();sg_group *g=ctx->group;sg_lock(&g->lock);
    if(atomic_load(&g->shutdown)||atomic_load(&g->fault)||atomic_load(&g->delivery_deadline)){sg_unlock(&g->lock);return SG2_NOT_PUBLISHED;}
    liza_scoped_status s=liza_scoped_send(g->fifo,value);uint32_t r=SG2_NOT_PUBLISHED;
    if(s==CH_OK){atomic_store(&g->delivery_deadline,sg_now()+g->config.operation_ms);r=sg_notify(g)?SG2_PUBLISHED:SG2_PUBLISHED_FAULT;}
    sg_unlock(&g->lock);return r;
}
void liza_sg2_busy(liza_sg2_context *ctx){sg_check_context(ctx);sg_status_set(&ctx->group->status[ctx->role],1,sg_now()+ctx->group->config.operation_ms);}
uint32_t liza_sg2_take_or_arm(liza_sg2_context *ctx,uint32_t *value){
    sg_check_context(ctx);if(ctx->role!=1||!value)abort();sg_group *g=ctx->group;sg_lock(&g->lock);g->armed=0;
    if(g->pending){if(!sg_wake_drain(&g->data))sg_fault(g,1);g->pending=0;}
    if(atomic_load(&g->shutdown))liza_scoped_close_sender(g->fifo);
    liza_scoped_status s=liza_scoped_receive(g->fifo,value);
    if(s==CH_OK){atomic_store(&g->delivery_deadline,0);liza_sg2_busy(ctx);}
    if(s==CH_EMPTY&&!atomic_load(&g->fault)){g->armed=1;sg_status_set(&g->status[1],0,0);}
    uint32_t r=s==CH_OK?SG2_VALUE:s==CH_CLOSED?SG2_CLOSED:atomic_load(&g->fault)?SG2_NOTIFY_FAULT:SG2_EMPTY;
    sg_unlock(&g->lock);return r;
}
void liza_sg2_sources(liza_sg2_context *ctx,uint64_t out[2]){sg_check_context(ctx);if(ctx->role!=1)abort();out[0]=(uint64_t)ctx->group->data.read;out[1]=(uint64_t)ctx->group->control.read;}
void liza_sg2_control_drain(liza_sg2_context *ctx){sg_check_context(ctx);if(ctx->role!=1)abort();if(!sg_wake_drain(&ctx->group->control))sg_fault(ctx->group,2);}
void liza_sg2_request_stop(liza_sg2_context *ctx){sg_check_context(ctx);atomic_store(&ctx->group->stop_intent,1);}
int liza_sg2_stopping(liza_sg2_context *ctx){sg_check_context(ctx);return atomic_load(&ctx->group->shutdown);}
static SG_ENTRY sg_participant(void *ptr){
    liza_sg2_context *ctx=ptr;sg_group *g=ctx->group;unsigned role=ctx->role;
    while(!atomic_load(&g->gate))sg_pause();
    if(atomic_load(&g->gate)>0){
        sg_current=ctx;liza_sg2_busy(ctx);
        if(role<2){SG_EVENT("callback",g->generation,role);g->results[role]=g->functions[role](ctx);
            sg_lock(&g->lock);if(!role){liza_scoped_close_sender(g->fifo);(void)sg_notify(g);}else liza_scoped_close_receiver(g->fifo);sg_unlock(&g->lock);
            if(role==1&&g->owned_reactor){if(liza_rt_reactor_close(g->owned_reactor))sg_fault(g,5);g->owned_reactor=NULL;SG_EVENT("reactor_close",g->generation,role);}
        }else{
            uint64_t missing[2]={0,0};
            while(!atomic_load(&g->monitor_stop)){
#ifdef LIZA_SG2_TESTING
                while(atomic_load(&sg2_test_supervisor_gate))sg_pause();
#endif
                uint64_t now=sg_now();
                for(unsigned i=0;i<2;i++){uint64_t state,deadline;
                    if(sg_status_read(&g->status[i],&state,&deadline)){missing[i]=0;if(state==1&&now>=deadline)atomic_store(&g->overdue,1);}
                    else {if(!missing[i])missing[i]=now;if(now-missing[i]>=g->config.operation_ms)atomic_store(&g->overdue,1);}}
                uint64_t delivery=atomic_load(&g->delivery_deadline);if(delivery&&now>=delivery)atomic_store(&g->overdue,1);
                liza_sg2_busy(ctx);sg_pause();
            }
        }
    }
    sg_current=NULL;sg_status_set(&g->status[role],2,0);SG_EVENT("exit",g->generation,role);SG_RETURN;
}
static void sg_stop(sg_group *g){
    if(atomic_load(&g->shutdown))return;
    atomic_store(&g->shutdown_deadline,sg_now()+g->config.shutdown_ms);atomic_store(&g->shutdown,1);SG_EVENT("stopping",g->generation,0);
#ifdef LIZA_SG2_TESTING
    if(g->config.control_fault){atomic_store(&g->control_fault,1);sg_fault(g,2);SG_EVENT("control_fault",g->generation,0);return;}
#endif
    if(!sg_wake_send(&g->control)){atomic_store(&g->control_fault,1);sg_fault(g,2);SG_EVENT("control_fault",g->generation,0);}
}
static int sg_receipt(sg_service *service,uint64_t generation,unsigned i){
#ifdef SG2_BREAK_FOREIGN_RECEIPT
    (void)generation;return atomic_load_explicit(&service->receipts[i],memory_order_acquire)!=0;
#else
    return service->generation==generation&&atomic_load_explicit(&service->receipts[i],memory_order_acquire)==generation;
#endif
}
static void sg_submit(sg_service *service,sg_thread *threads,unsigned n,uint64_t generation,uint32_t timeout){
    uint64_t deadline=sg_now()+timeout;
    while(!sg_trylock(&service->lock)){if(sg_now()>=deadline)sg_abort(generation);sg_pause();}
    if(atomic_load(&service->state)!=SG_FREE)abort();
    for(unsigned i=0;i<3;i++){atomic_store(&service->receipts[i],0);if(i<n)service->handles[i]=threads[i];}
    service->count=n;service->generation=generation;SG_EVENT("submitted",generation,n);
    atomic_store_explicit(&service->state,SG_SUBMITTED,memory_order_release);sg_signal(&service->ready);sg_unlock(&service->lock);
}
uint32_t liza_sg2_run(const liza_sg2_config *c,liza_sg2_fn producer,liza_sg2_fn consumer,liza_sg2_report *out){
    if(!out)return SG2_INVALID;memset(out,0,sizeof(*out));out->schema_version=2;out->max_active_groups=SG_GROUP_LIMIT;
    if(sg_current||sg_owner_active){out->result=SG2_BUSY;return SG2_BUSY;}
    unsigned slot=SG_GROUP_LIMIT;
    /* Reuse a compatible initialized lane before allocating another reaper.
     * stack is immutable after initialized's atomic publication. */
    for(unsigned pass=0;pass<2&&slot==SG_GROUP_LIMIT;pass++)for(unsigned i=0;i<SG_GROUP_LIMIT;i++){
        int initialized=atomic_load(&services[i].initialized);
        if((pass==0&&!initialized)||(pass==1&&initialized))continue;
        if(initialized&&c&&services[i].stack!=c->service_stack_bytes)continue;
        int zero=0;if(atomic_compare_exchange_strong(&admitted[i],&zero,1)){slot=i;break;}
    }
    if(slot==SG_GROUP_LIMIT){
        uint32_t denied=SG2_INVALID;
        for(unsigned i=0;i<SG_GROUP_LIMIT;i++)if(!atomic_load(&services[i].initialized)||!c||services[i].stack==c->service_stack_bytes)denied=SG2_BUSY;
        out->result=denied;return denied;
    }
    sg_owner_active=1;sg_service *service=&services[slot];out->group_slot=slot;
    uint32_t result=SG2_INVALID;unsigned step=0,n=0;sg_thread threads[3];sg_group *g=NULL;
    size_t fifo_bytes=0;int lock_ready=0,net_ready=0;
    if(!c||!producer||!consumer||c->managed_budget<sizeof(sg_group)||c->process_budget<sizeof(services)+sizeof(admitted)+sizeof(next_generation)||
       c->reactor_capacity==0||c->reactor_capacity>32||c->reactor_budget<liza_rt_reactor_allocation_bytes()||c->max_threads<3||c->max_socket_handles<5||!c->slots||c->slots>65536||!c->operation_ms||!c->shutdown_ms||
       c->stack_bytes<65536||c->stack_bytes>SIZE_MAX/3||c->stack_bytes%65536||
       c->service_stack_bytes<65536||c->service_stack_bytes%65536)goto finish;
    if(service->initialized&&service->stack!=c->service_stack_bytes)goto finish;
    uint_fast64_t generation=atomic_load(&next_generation);
    do{if(generation==UINT64_MAX)goto finish;}while(!atomic_compare_exchange_weak(&next_generation,&generation,generation+1));
    out->generation=generation+1;SG_EVENT("slot",out->generation,slot);out->participant_stack_requested_bytes=3*c->stack_bytes;
    out->service_stack_requested_bytes=c->service_stack_bytes;result=SG2_STARTUP_FAILED;
    if(!sg_service_init(service,c,&step))goto finish;
    if(!sg_step(c,&step))goto finish;
    g=calloc(1,sizeof(*g));if(!g)goto finish;g->config=*c;g->generation=out->generation;
    g->data.read=g->data.write=g->control.read=g->control.write=NET_INVALID;
    atomic_init(&g->gate,0);atomic_init(&g->stop_intent,0);atomic_init(&g->shutdown,0);atomic_init(&g->monitor_stop,0);
    atomic_init(&g->control_fault,0);atomic_init(&g->fault,0);atomic_init(&g->overdue,0);atomic_init(&g->shutdown_deadline,0);atomic_init(&g->delivery_deadline,0);
    for(unsigned i=0;i<3;i++){atomic_init(&g->status[i].version,0);atomic_init(&g->status[i].state,0);atomic_init(&g->status[i].deadline,0);g->contexts[i]=(liza_sg2_context){g,i};}
    g->functions[0]=producer;g->functions[1]=consumer;out->group_managed_bytes_live=out->group_managed_bytes_peak=sizeof(*g);
    if(!sg_step(c,&step)||!sg_mutex_init(&g->lock))goto cleanup;lock_ready=1;
    if(!sg_step(c,&step))goto cleanup;
    liza_scoped_status allocation=liza_scoped_create(c->slots,c->managed_budget-sizeof(*g),&g->fifo,&fifo_bytes);
    if(allocation!=CH_OK){if(allocation==CH_INVALID)result=SG2_INVALID;goto cleanup;}
    out->fifo_allocation_bytes=fifo_bytes;out->group_managed_bytes_peak+=fifo_bytes;out->group_managed_bytes_live+=fifo_bytes;
    if(!sg_step(c,&step)||net_start())goto cleanup;net_ready=1;
    if(!sg_wake_create(g,&g->data,&step)||!sg_wake_create(g,&g->control,&step))goto cleanup;
    for(unsigned i=0;i<3;i++)sg_status_set(&g->status[i],1,sg_now()+c->operation_ms);
    for(unsigned i=0;i<3;i++){if(!sg_step(c,&step)||!sg_start(&threads[i],sg_participant,&g->contexts[i],c->stack_bytes))break;n++;}
    if(n){
        out->participant_threads_live=n;out->participant_native_handles_live=n;out->join_records_in_use=1;
        sg_submit(service,threads,n,g->generation,c->shutdown_ms);
        atomic_store(&g->gate,n==3?1:-1);uint64_t until=n==3?0:sg_now()+c->shutdown_ms,unavailable=0;
        if(n==3)result=SG2_OK;
        for(;;){
            uint64_t now=sg_now();
            if(n==3){
                uint64_t s0,d0,s1,d1;
                if(sg_status_read(&g->status[0],&s0,&d0)&&sg_status_read(&g->status[1],&s1,&d1)&&s0==2&&s1==2)sg_stop(g);
                if(atomic_load(&g->overdue))sg_fault(g,3);
                if(atomic_load(&g->fault)||atomic_load(&g->stop_intent))sg_stop(g);
                if(sg_receipt(service,g->generation,0)&&sg_receipt(service,g->generation,1)&&!atomic_load(&g->monitor_stop)){
                    sg_stop(g);atomic_store(&g->monitor_stop,1);
                }
                uint64_t st,dl;if(sg_status_read(&g->status[2],&st,&dl)){unavailable=0;if(st==1&&now>=dl){sg_fault(g,4);sg_stop(g);}}
                else {if(!unavailable)unavailable=now;if(now-unavailable>=c->operation_ms)sg_stop(g);}
                /* Running has no group lifetime limit. Stop publishes one absolute deadline. */
                until=atomic_load(&g->shutdown_deadline);
            }
#ifdef SG2_BREAK_EARLY_REUSE
            if(n==3&&sg_receipt(service,g->generation,0)&&sg_receipt(service,g->generation,1)&&sg_receipt(service,g->generation,2)){
                SG_EVENT("record_free",g->generation,0);atomic_store(&service->state,SG_FREE);
            }
#endif
            if(atomic_load_explicit(&service->state,memory_order_acquire)==SG_RETURNED){
                for(unsigned i=0;i<n;i++)if(!sg_receipt(service,g->generation,i))sg_abort(g->generation);
                out->participant_threads_live=0;out->participant_native_handles_live=0;
                break;
            }
#ifdef SG2_BREAK_EARLY_RELEASE
            if(until&&now>=until)goto cleanup;
#endif
            if(until&&now>=until){SG_EVENT("unresponsive",g->generation,0);SG_EVENT("retained",g->generation,0);sg_abort(g->generation);}
            sg_pause();
        }
        SG_EVENT("stopped",g->generation,0);
    }
cleanup:
    /* Any Submitted request must have fully handed back before cleanup/reuse. */
    if(n&&atomic_load_explicit(&service->state,memory_order_acquire)!=SG_RETURNED){SG_EVENT("release_rejected",g->generation,0);sg_abort(g->generation);}
    if(g){out->control_fault=(uint32_t)atomic_load(&g->control_fault);out->reactor_allocation_bytes=g->reactor_bytes;out->fault=(uint32_t)atomic_load(&g->fault);out->producer_result=g->results[0];out->consumer_result=g->results[1];out->group_socket_handles_peak=g->peak_sockets;
        sg_socket_close(g,&g->control.read);sg_socket_close(g,&g->control.write);sg_socket_close(g,&g->data.read);sg_socket_close(g,&g->data.write);
        if(net_ready)net_stop();
#ifndef SG2_BREAK_ROLLBACK
        if(g->fifo){liza_scoped_destroy(g->fifo);out->group_managed_bytes_live-=fifo_bytes;}
#endif
        if(lock_ready)sg_mutex_destroy(&g->lock);
        out->group_socket_handles_live=g->sockets;SG_EVENT("destroy",g->generation,0);free(g);out->group_managed_bytes_live-=sizeof(*g);
    }
    if(n){out->join_records_in_use=0;atomic_store(&service->state,SG_FREE);SG_EVENT("record_free",out->generation,0);}
    if(result==SG2_OK&&out->fault)result=SG2_FAULTED;
finish:
    out->startup_steps=step;out->result=result;out->process_service_threads=0;
    for(unsigned i=0;i<SG_GROUP_LIMIT;i++)if(atomic_load(&services[i].initialized)){
        out->process_service_threads++;out->process_service_stack_requested_bytes+=services[i].stack;
    }
    out->process_managed_bytes=sizeof(services)+sizeof(admitted)+sizeof(next_generation);
    sg_owner_active=0;atomic_store(&admitted[slot],0);return result;
}
