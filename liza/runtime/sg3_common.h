/* Language adapter: contexts, native handles and Reactor ownership never escape. */
#include "sg2_common.h"
typedef struct {uint64_t socket;uint32_t ready;} sg3_source;
uint64_t liza_rt_reactor_poll_sources(reactor *,int32_t,sg3_source *,uint32_t);
typedef uint32_t (*sg3_fn)(void);
typedef struct {sg3_fn functions[2];} sg3_callbacks;
static atomic_int sg3_pair_admitted;
static _Thread_local int sg3_closed;
static liza_sg2_context *sg3_context(void){sg_check_context(sg_current);return sg_current;}
reactor *liza_rt_group_reactor(void){
    liza_sg2_context *ctx=sg3_context();
    if(ctx->role!=1||!ctx->group->owned_reactor)abort();
    return ctx->group->owned_reactor;
}
static uint32_t sg3_entry(liza_sg2_context *ctx){sg3_closed=0;const sg3_callbacks *callbacks=ctx->group->config.user_data;return callbacks->functions[ctx->role]();}
uint32_t liza_rt_group_run(uint64_t managed,uint64_t process,uint64_t stack,uint64_t service_stack,
                          uint64_t reactor_budget,uint32_t capacity,uint32_t slots,uint32_t operation,uint32_t shutdown,
                          sg3_fn producer,sg3_fn consumer,uint32_t *p,uint32_t *c,uint32_t *fault,uint32_t *control){
    *p=*c=*fault=*control=0;
    if(managed>SIZE_MAX||process>SIZE_MAX||stack>SIZE_MAX||service_stack>SIZE_MAX||reactor_budget>SIZE_MAX)return SG2_INVALID;
    /* Adapter bookkeeping is part of the process budget, in addition to SG2. */
    size_t overhead=SG_GROUP_LIMIT*sizeof(sg3_callbacks)+sizeof(sg3_pair_admitted);
    if(process<overhead)return SG2_INVALID;
    liza_sg2_config cfg={0};cfg.managed_budget=(size_t)managed;cfg.process_budget=(size_t)process-overhead;
    cfg.stack_bytes=(size_t)stack;cfg.service_stack_bytes=(size_t)service_stack;cfg.reactor_budget=(size_t)reactor_budget;
    cfg.reactor_capacity=capacity;cfg.slots=slots;cfg.max_threads=3;cfg.max_socket_handles=5;cfg.operation_ms=operation;cfg.shutdown_ms=shutdown;
#ifdef LIZA_SG2_TESTING
    extern void sg3_test_config(liza_sg2_config *);
    sg3_test_config(&cfg);
#endif
    sg3_callbacks callbacks={{producer,consumer}};cfg.user_data=&callbacks;
    liza_sg2_report report;uint32_t result=liza_sg2_run(&cfg,sg3_entry,sg3_entry,&report);
    *p=report.producer_result;*c=report.consumer_result;*fault=report.fault;*control=report.control_fault;
    return result;
}
/* Pair owners live until both owner threads have returned and been joined.
 * They have no access to another group's sockets or participant handles. */
typedef struct {
    uint64_t args[9];sg3_fn producer,consumer;uint32_t values[5];atomic_int *gate;
} sg3_pair_owner;
#ifdef LIZA_SG4_B1_TESTING
static unsigned sg3_pair_fail_start;
#endif
static SG_ENTRY sg3_pair_entry(void *ptr){
    sg3_pair_owner *o=ptr;
    int gate;while(!(gate=atomic_load(o->gate)))sg_pause();
    if(gate>0)o->values[4]=liza_rt_group_run(o->args[0],o->args[1],o->args[2],o->args[3],o->args[4],
        (uint32_t)o->args[5],(uint32_t)o->args[6],(uint32_t)o->args[7],(uint32_t)o->args[8],
        o->producer,o->consumer,&o->values[0],&o->values[1],&o->values[2],&o->values[3]);
    SG_RETURN;
}
void liza_rt_group_run_pair(
    uint64_t am,uint64_t ap,uint64_t ast,uint64_t ass,uint64_t ar,uint32_t ac,uint32_t asl,uint32_t ao,uint32_t ash,
    uint64_t bm,uint64_t bp,uint64_t bst,uint64_t bss,uint64_t br,uint32_t bc,uint32_t bsl,uint32_t bo,uint32_t bsh,
    sg3_fn pa,sg3_fn ca,sg3_fn pb,sg3_fn cb,uint32_t out[10]){
    memset(out,0,10*sizeof(*out));out[4]=out[9]=SG2_STARTUP_FAILED;
    if(sg_current||sg_owner_active){out[4]=out[9]=SG2_BUSY;return;}
    size_t overhead=2*sizeof(sg3_pair_owner)+sizeof(atomic_int)+2*sizeof(sg_thread);
    if(ast>SIZE_MAX/3||bst>SIZE_MAX/3||ast<65536||bst<65536||ast%65536||bst%65536||
       ap<overhead||bp<overhead||!pa||!ca||!pb||!cb){out[4]=out[9]=SG2_INVALID;return;}
    int zero=0;if(!atomic_compare_exchange_strong(&sg3_pair_admitted,&zero,1)){out[4]=out[9]=SG2_BUSY;return;}
    atomic_int gate;atomic_init(&gate,0);
    sg3_pair_owner owners[2]={
        {{am,ap-overhead,ast,ass,ar,ac,asl,ao,ash},pa,ca,{0,0,0,0,SG2_STARTUP_FAILED},&gate},
        {{bm,bp-overhead,bst,bss,br,bc,bsl,bo,bsh},pb,cb,{0,0,0,0,SG2_STARTUP_FAILED},&gate}};
    sg_thread threads[2];unsigned n=0,fail_start=0;
#ifdef LIZA_SG4_B1_TESTING
    fail_start=sg3_pair_fail_start;
#endif
    if(fail_start!=1&&sg_start(&threads[0],sg3_pair_entry,&owners[0],(size_t)ast)){
        n=1;if(fail_start!=2&&sg_start(&threads[1],sg3_pair_entry,&owners[1],(size_t)bst))n=2;
    }
    atomic_store(&gate,n==2?1:-1);
    for(unsigned i=0;i<n;i++)if(!sg_join(threads[i]))sg_abort(0);
    for(unsigned i=0;i<2;i++)for(unsigned j=0;j<5;j++)out[i*5+j]=owners[i].values[j];
    atomic_store(&sg3_pair_admitted,0);
}
uint32_t liza_rt_reactor_udp_create(uint32_t,uint16_t,uint32_t,reactor **);
uint64_t liza_rt_reactor_udp_port(reactor *);
uint32_t liza_rt_reactor_udp_receive(reactor *,uint8_t *,uint32_t,uint64_t *);
uint64_t liza_rt_reactor_udp_send(reactor *,const uint8_t *,uint32_t,uint32_t,uint32_t,uint32_t,uint16_t);
uint32_t liza_rt_group_udp_bind(uint32_t ip,uint16_t port){
    liza_sg2_context *ctx=sg3_context();if(ctx->role!=1)abort();
    sg_group *g=ctx->group;if(g->owned_reactor)return 6;
    uint32_t e=liza_rt_reactor_udp_create(ip,port,g->config.reactor_capacity,&g->owned_reactor);
    if(!e)g->reactor_bytes=(size_t)liza_rt_reactor_allocation_bytes();
    return e;
}
uint64_t liza_rt_group_udp_port(void){return liza_rt_reactor_udp_port(liza_rt_group_reactor());}
uint32_t liza_rt_group_udp_receive(uint8_t *data,uint32_t capacity,uint64_t *out){
    return liza_rt_reactor_udp_receive(liza_rt_group_reactor(),data,capacity,out);
}
uint64_t liza_rt_group_udp_send(const uint8_t *data,uint32_t length,uint32_t start,uint32_t count,uint32_t ip,uint16_t port){
    return liza_rt_reactor_udp_send(liza_rt_group_reactor(),data,length,start,count,ip,port);
}
uint32_t liza_rt_group_send(uint32_t value){return liza_sg2_send(sg3_context(),value);}
uint32_t liza_rt_group_listen(uint16_t port){reactor *r=NULL;return liza_sg2_reactor_create(sg3_context(),port,&r);}
uint32_t liza_rt_group_stop(void){liza_sg2_request_stop(sg3_context());return 0;}
uint32_t liza_rt_group_busy(void){liza_sg2_busy(sg3_context());return 0;}
uint32_t liza_rt_group_stopping(void){
    liza_sg2_context *ctx=sg3_context();
    int stopped=liza_sg2_stopping(ctx);
    /* Observing stop must publish its deadline, including through this ABI. */
    if(stopped&&!atomic_load(&ctx->group->shutdown_deadline))abort();
    return (uint32_t)stopped;
}
uint64_t liza_rt_group_next(void){
    liza_sg2_context *ctx=sg3_context();reactor *r=liza_rt_group_reactor();
    uint64_t handles[2];liza_sg2_sources(ctx,handles);
    sg3_source sources[2]={{handles[0],0},{handles[1],0}};
    for(;;){
        uint32_t value=0,status=liza_sg2_take_or_arm(ctx,&value);
        if(status==SG2_VALUE)return value;
        if(liza_rt_group_stopping())return (uint64_t)3<<32;
        if(status==SG2_NOTIFY_FAULT)return (uint64_t)4<<32;
        if(status==SG2_CLOSED&&!sg3_closed){sg3_closed=1;liza_sg2_busy(ctx);return (uint64_t)2<<32;}
        /* Sender closure is reported once; existing TCP work can continue. */
        if(sg3_closed)sg_status_set(&ctx->group->status[1],0,0);
        uint64_t events=liza_rt_reactor_poll_sources(r,-1,sources,2);
        liza_sg2_busy(ctx);
        if(events>>32)return ((uint64_t)5<<32)|(events>>32);
        if(sources[1].ready)liza_sg2_control_drain(ctx);
        /* Inspect accepted work before reporting Stopping, even on a control-only wake. */
        if(liza_rt_group_stopping())continue;
        /* Data/control-only wakeups are handled internally; no Empty polling API. */
        if(sources[0].ready&4)sg_fault(ctx->group,1);
        if(sources[1].ready&4){atomic_store(&ctx->group->control_fault,1);sg_fault(ctx->group,2);}
        uint32_t network=(uint32_t)events-(sources[0].ready!=0)-(sources[1].ready!=0);
        if(network)return ((uint64_t)1<<32)|network;
    }
}
