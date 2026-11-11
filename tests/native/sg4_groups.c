/* B1 native owners: two UDP groups, independent joins, gates and receipt oracle. */
#define main helper_probe_main
#include "../../experiments/reactor_wakeup/probe.c"
#undef main
#include "../../liza/runtime/reactor_common.h"
#define liza_rt_reactor_poll_sources b1_sg3_poll
#include "../../liza/runtime/sg3_common.h"
#undef liza_rt_reactor_poll_sources
uint64_t b1_sg3_poll(reactor *r,int32_t timeout,sg3_source *sources,uint32_t n){reactor_source copy[2];if(n>2)abort();for(unsigned i=0;i<n;i++)copy[i]=(reactor_source){sources[i].socket,0};uint64_t result=liza_rt_reactor_poll_sources(r,timeout,copy,n);for(unsigned i=0;i<n;i++)sources[i].ready=copy[i].ready;return result;}
#ifndef _WIN32
#include <dirent.h>
#endif
#define CHECK(x) do{if(!(x)){fprintf(stderr,"failed: %s line %d\n",#x,__LINE__);exit(2);}}while(0)
atomic_int sg2_test_handback_gate,sg2_test_stale_receipt,sg2_test_supervisor_gate;
void sg3_test_config(liza_sg2_config *c){(void)c;}
static const char *mode;
static atomic_uint_fast64_t held_generation,foreign_generation;
static atomic_int handback_release;
static sg_mutex log_lock;
static unsigned event_sequence;
static struct {unsigned exits,joins,receipts,returned,destroyed,freed,expected,slot;unsigned handback_sequence,destroy_sequence,free_sequence;} logbook[1024];
void sg2_test_event(const char *k,uint64_t gen,unsigned role){
    CHECK(gen<1024);
    if(!strcmp(k,"release_rejected")){puts("release_rejected");fflush(stdout);}
    if(!strcmp(k,"process_abort")){puts("process_abort no-cleanup");fflush(stdout);return;}
    if(!strcmp(k,"handback")&&gen==atomic_load(&held_generation)){
        if(!strcmp(mode,"handback"))while(!atomic_load(&handback_release))sg_pause();
        if(!strcmp(mode,"foreign")||!strcmp(mode,"stale")){
            uint64_t wrong=!strcmp(mode,"stale")?gen-1:atomic_load(&foreign_generation);
            for(unsigned i=0;i<SG_GROUP_LIMIT;i++)if(services[i].generation==gen)atomic_store(&services[i].receipts[0],wrong);
        }
    }
    sg_lock(&log_lock);unsigned sequence=++event_sequence;
    if(!strcmp(k,"slot"))logbook[gen].slot=role;
    if(!strcmp(k,"submitted"))logbook[gen].expected=(1u<<role)-1;
    if(!strcmp(k,"retained"))CHECK(!logbook[gen].destroyed);
    if(!strcmp(k,"exit"))logbook[gen].exits|=1u<<role;
    if(!strcmp(k,"join")){CHECK(logbook[gen].exits&(1u<<role));logbook[gen].joins|=1u<<role;}
    if(!strcmp(k,"receipt")){CHECK(logbook[gen].joins&(1u<<role));logbook[gen].receipts|=1u<<role;}
    if(!strcmp(k,"handback")){CHECK(logbook[gen].joins==logbook[gen].expected);logbook[gen].returned=1;logbook[gen].handback_sequence=sequence;}
    if(!strcmp(k,"stopped"))CHECK(logbook[gen].returned&&logbook[gen].joins==logbook[gen].expected);
    if(!strcmp(k,"destroy")){CHECK(!logbook[gen].exits||logbook[gen].returned);logbook[gen].destroyed=1;logbook[gen].destroy_sequence=sequence;}
    if(!strcmp(k,"record_free")){CHECK(logbook[gen].destroyed&&logbook[gen].returned);logbook[gen].freed=1;logbook[gen].free_sequence=sequence;}
    sg_unlock(&log_lock);
}
typedef struct {
    liza_sg2_config config;liza_sg2_report report;uint32_t result;
    atomic_int ready,port,stop,hold,release,done,traffic,commands,callbacks;
    unsigned char tag;
    atomic_uint_fast64_t generation;
} test_group;
static uint32_t producer(liza_sg2_context *ctx){
    test_group *t=(test_group *)ctx->group->config.user_data;atomic_fetch_add(&t->callbacks,1);
    atomic_store(&t->generation,ctx->group->generation);
    while(!atomic_load(&t->ready))sg_pause();
    uint32_t publication=liza_sg2_send(ctx,42);CHECK(publication==(t->config.data_fault?SG2_PUBLISHED_FAULT:SG2_PUBLISHED));
    net_socket s=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);CHECK(s!=NET_INVALID);
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(0x7f000001u);a.sin_port=htons((uint16_t)atomic_load(&t->port));
    while(!atomic_load(&t->stop)&&!liza_sg2_stopping(ctx)){
        CHECK(sendto(s,(const char *)&t->tag,1,0,(struct sockaddr *)&a,sizeof(a))==1);sg_pause();
    }
    CHECK(!net_os_close(s));liza_sg2_request_stop(ctx);return 17;
}
static uint32_t consumer(liza_sg2_context *ctx){
    test_group *t=(test_group *)ctx->group->config.user_data;atomic_fetch_add(&t->callbacks,1);
    CHECK(!liza_rt_group_udp_bind(0x7f000001u,0));reactor *r=ctx->group->owned_reactor;
    atomic_store(&t->port,(int)liza_rt_group_udp_port());uint64_t handles[2];liza_sg2_sources(ctx,handles);
    reactor_source sources[2]={{handles[0],0},{handles[1],0}};
    for(;;){
        uint32_t v=0,s=liza_sg2_take_or_arm(ctx,&v);
        if(s==SG2_VALUE){CHECK(v==42);atomic_fetch_add(&t->commands,1);continue;}
        if(liza_sg2_stopping(ctx))break;
        CHECK(s==SG2_EMPTY||s==SG2_CLOSED||s==SG2_NOTIFY_FAULT);
        if(s==SG2_CLOSED)sg_status_set(&ctx->group->status[1],0,0);
        atomic_store(&t->ready,1);
        CHECK(!(liza_rt_reactor_poll_sources(r,-1,sources,2)>>32));
        if(sources[1].ready)liza_sg2_control_drain(ctx);
        uint8_t byte;uint64_t meta;uint32_t e=liza_rt_group_udp_receive(&byte,1,&meta);
        if(!e){CHECK(byte==t->tag);atomic_fetch_add(&t->traffic,1);}else CHECK(e==4);
    }
    while(atomic_load(&t->hold)&&!atomic_load(&t->release))sg_pause();
    return 23;
}
static SG_ENTRY owner(void *ptr){test_group *t=ptr;t->result=liza_sg2_run(&t->config,producer,consumer,&t->report);atomic_store(&t->done,1);SG_RETURN;}
static void setup(test_group *t){
    memset(t,0,sizeof(*t));
    atomic_init(&t->ready,0);atomic_init(&t->port,0);atomic_init(&t->stop,0);atomic_init(&t->hold,0);
    atomic_init(&t->release,0);atomic_init(&t->done,0);atomic_init(&t->traffic,0);atomic_init(&t->commands,0);
    atomic_init(&t->callbacks,0);atomic_init(&t->generation,0);t->config=(liza_sg2_config){0};
    t->config.managed_budget=65536;t->config.process_budget=65536;t->config.stack_bytes=1048576;t->config.service_stack_bytes=1048576;
    t->config.reactor_budget=65536;t->config.reactor_capacity=2;t->config.slots=2;t->config.max_threads=3;t->config.max_socket_handles=5;
    t->config.operation_ms=10000;t->config.shutdown_ms=3000;t->config.user_data=t;
}
static void await(atomic_int *p){uint64_t until=sg_now()+5000;while(!atomic_load(p)){CHECK(sg_now()<until);sg_pause();}}
static void progress(test_group *t){int old=atomic_load(&t->traffic);uint64_t until=sg_now()+1000;while(atomic_load(&t->traffic)<=old){CHECK(!atomic_load(&t->done)&&sg_now()<until);sg_pause();}}
static void finish(test_group *t,sg_thread thread,uint32_t result){
    atomic_store(&t->stop,1);atomic_store(&t->release,1);await(&t->done);CHECK(sg_join(thread));CHECK(t->result==result);
    CHECK(t->report.max_active_groups==2&&!t->report.group_managed_bytes_live&&!t->report.group_socket_handles_live&&!t->report.join_records_in_use);
    CHECK(!t->report.participant_native_handles_live&&t->report.process_service_threads<=2);
    if(!t->config.fail_at){
        CHECK(t->report.producer_result==17&&t->report.consumer_result==23&&atomic_load(&t->commands)==1);
        unsigned gen=(unsigned)t->report.generation;CHECK(logbook[gen].slot==t->report.group_slot);
        CHECK(logbook[gen].handback_sequence<logbook[gen].destroy_sequence&&logbook[gen].destroy_sequence<logbook[gen].free_sequence);
    }
}
static unsigned handles(void){
#ifdef _WIN32
    DWORD n;CHECK(GetProcessHandleCount(GetCurrentProcess(),&n));return n;
#else
    DIR *d=opendir("/dev/fd");CHECK(d);unsigned n=0;struct dirent *e;while((e=readdir(d)))if(e->d_name[0]!='.')n++;closedir(d);return n;
#endif
}
static atomic_int pair_callbacks;
static uint32_t pair_callback(void){atomic_fetch_add(&pair_callbacks,1);return 7;}
int main(int argc,char **argv){
    CHECK(argc>=2);mode=argv[1];CHECK(sg_mutex_init(&log_lock));CHECK(!net_start());
    if(!strcmp(mode,"pair_start")){
        CHECK(argc==3);sg3_pair_fail_start=(unsigned)atoi(argv[2]);uint32_t out[10];
#define B1_CFG 65536,65536,1048576,1048576,65536,2,2,10000,3000
        liza_rt_group_run_pair(B1_CFG,B1_CFG,pair_callback,pair_callback,pair_callback,pair_callback,out);
        CHECK(out[4]==SG2_STARTUP_FAILED&&out[9]==SG2_STARTUP_FAILED&&!atomic_load(&pair_callbacks));
        puts("pair owner startup rollback passed");net_stop();return 0;
    }
    unsigned loops=!strcmp(mode,"reuse")?100:1,baseline=0;size_t bytes=0;
    for(unsigned loop=0;loop<loops;loop++){
        test_group a,b;setup(&a);setup(&b);a.tag='a';b.tag='b';sg_thread ta,tb;
        /* B stays live throughout A startup, fault, shutdown and destruction. */
        CHECK(sg_start(&tb,owner,&b,1048576));await(&b.ready);progress(&b);
        atomic_store(&foreign_generation,atomic_load(&b.generation));
        if(!strcmp(mode,"startup")){CHECK(argc==3);a.config.fail_at=(unsigned)atoi(argv[2]);}
        if(!strcmp(mode,"fault"))a.config.data_fault=1;
        if(!strcmp(mode,"held")||!strcmp(mode,"deadline"))atomic_store(&a.hold,1);
        if(!strcmp(mode,"deadline"))a.config.shutdown_ms=150;
        CHECK(sg_start(&ta,owner,&a,1048576));
        if(a.config.fail_at){await(&a.done);CHECK(!atomic_load(&a.callbacks));finish(&a,ta,SG2_STARTUP_FAILED);progress(&b);finish(&b,tb,SG2_OK);continue;}
        await(&a.ready);CHECK(atomic_load(&a.port)!=atomic_load(&b.port));
        uint64_t started_until=sg_now()+5000;
        while(!atomic_load(&a.generation)){CHECK(sg_now()<started_until);sg_pause();}
        atomic_store(&held_generation,atomic_load(&a.generation));
        if(!a.config.data_fault){liza_sg2_report rejected;CHECK(liza_sg2_run(&a.config,producer,consumer,&rejected)==SG2_BUSY);CHECK(!rejected.generation);}
        atomic_store(&a.stop,1);
        if(!strcmp(mode,"deadline")){sg_join(ta);CHECK(0);}
        if(!strcmp(mode,"held")||!strcmp(mode,"handback")){
            progress(&b);CHECK(!atomic_load(&a.done));finish(&b,tb,SG2_OK);
            CHECK(!atomic_load(&a.done));
            sg_lock(&log_lock);CHECK(!logbook[atomic_load(&a.generation)].destroyed);sg_unlock(&log_lock);
            /* Freed B slot can host another complete group while A remains held. */
            setup(&b);b.tag='c';CHECK(sg_start(&tb,owner,&b,1048576));await(&b.ready);progress(&b);finish(&b,tb,SG2_OK);
            CHECK(!atomic_load(&a.done));atomic_store(&handback_release,1);
            finish(&a,ta,SG2_OK);
        }else{
            finish(&a,ta,a.config.data_fault?SG2_FAULTED:SG2_OK);progress(&b);finish(&b,tb,SG2_OK);
        }
        CHECK(a.report.group_slot!=b.report.group_slot);CHECK(a.report.generation!=b.report.generation);
        unsigned h=handles();if(!loop){baseline=h;bytes=a.report.process_managed_bytes;}else CHECK(h==baseline&&bytes==a.report.process_managed_bytes);
    }
    puts("B1 isolated groups, native joins and bounded reuse passed");net_stop();return 0;
}
