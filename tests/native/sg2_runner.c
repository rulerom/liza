#define main helper_probe_main
#include "../../experiments/reactor_wakeup/probe.c"
#undef main
#include "../../liza/runtime/reactor_common.h"
#include "../../liza/runtime/sg2.h"
#ifndef _WIN32
#include <dirent.h>
#endif
#define CHECK(x) do{if(!(x)){fprintf(stderr,"failed: %s line %d\n",#x,__LINE__);exit(2);}}while(0)
atomic_int sg2_test_handback_gate,sg2_test_stale_receipt,sg2_test_supervisor_gate;
static atomic_int waiting,port,allow_exit,callback_count;
static const char *mode;
static liza_sg2_config config;
static atomic_uint event_count,destroy_count;
static atomic_uint_fast64_t oracle_joins[3];
static struct {const char *kind;uint64_t generation;unsigned role;} events[4096];
void sg2_test_event(const char *kind,uint64_t gen,unsigned role){
    if(!strcmp(kind,"record_free"))CHECK(atomic_load(&destroy_count)>0);
    if(!strcmp(kind,"join"))atomic_store(&oracle_joins[role],gen);
    if(!strcmp(kind,"receipt"))CHECK(atomic_load(&oracle_joins[role])==gen);
    unsigned i=atomic_fetch_add(&event_count,1);CHECK(i<4096);events[i].kind=kind;events[i].generation=gen;events[i].role=role;
    if(!strcmp(kind,"destroy"))atomic_fetch_add(&destroy_count,1);
    if(!strcmp(kind,"retained")){CHECK(!atomic_load(&destroy_count));printf("retained generation=%llu destroy=%u\n",(unsigned long long)gen,atomic_load(&destroy_count));fflush(stdout);}
    if(!strcmp(kind,"release_rejected")){puts("release_rejected");fflush(stdout);}
    if(!strcmp(kind,"process_abort")){puts("process_abort no-cleanup");fflush(stdout);}
}
static void pause_one(void){
#ifdef _WIN32
    Sleep(1);
#else
    struct timespec t={0,1000000};nanosleep(&t,NULL);
#endif
}
static uint32_t produce(liza_sg2_context *ctx){
    atomic_fetch_add(&callback_count,1);
    while(!atomic_load(&waiting))pause_one();
    if(!strcmp(mode,"long_running")){
        /* A valid operation spans three shutdown budgets without requesting stop. */
        uint64_t start=now_ms();
        while(now_ms()-start<3*(uint64_t)config.shutdown_ms){
            CHECK(!liza_sg2_stopping(ctx));pause_one();
        }
        CHECK(!liza_sg2_stopping(ctx));
    }
    if(!strcmp(mode,"nested")){
        liza_sg2_report r;CHECK(liza_sg2_run(&config,produce,produce,&r)==SG2_BUSY);
    }
    if(!strcmp(mode,"idle")){liza_sg2_request_stop(ctx);return 17;}
    uint32_t sent=liza_sg2_send(ctx,42);
    CHECK(sent==(!strcmp(mode,"fault")||!strcmp(mode,"double_fault")?SG2_PUBLISHED_FAULT:SG2_PUBLISHED));
    if(!strcmp(mode,"fault")||!strcmp(mode,"double_fault"))return 17;
    sock_t client=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);CHECK(client!=BAD_SOCKET);
    struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(0x7f000001u);a.sin_port=htons((uint16_t)atomic_load(&port));
    CHECK(!connect(client,(struct sockaddr*)&a,sizeof(a)));CHECK(send(client,"n",1,0)==1);
    /* Consumer confirms both inputs before producer closes TCP. */
    while(!atomic_load(&allow_exit)&&!liza_sg2_stopping(ctx))pause_one();
    CHECK(!close_socket(client));return 17;
}
static uint32_t consume(liza_sg2_context *ctx){
    atomic_fetch_add(&callback_count,1);reactor *r=NULL;CHECK(!liza_sg2_reactor_create(ctx,0,&r));
    atomic_store(&port,(int)liza_rt_reactor_port(r));uint64_t handles[2];liza_sg2_sources(ctx,handles);
    reactor_source sources[2]={{handles[0],0},{handles[1],0}};uint64_t id[3]={0};int connected=0,got=0,network=0;
    for(;;){
        uint32_t value=0,s=liza_sg2_take_or_arm(ctx,&value);
        if(s==SG2_VALUE){CHECK(value==42);got++;}
        if(got&&network)atomic_store(&allow_exit,1);
        if(s==SG2_CLOSED)break;
        if(s==SG2_VALUE)continue;
        atomic_store(&waiting,1);
        if(!strcmp(mode,"worker_stall")){while(1)pause_one();}
        uint64_t count=liza_rt_reactor_poll_sources(r,-1,sources,2);CHECK(!(count>>32));
        if(sources[1].ready)liza_sg2_control_drain(ctx);
        if(!connected){uint32_t e=liza_rt_reactor_accept(r,id);CHECK(e==0||e==4);connected=!e;}
        if(connected&&!network){uint8_t byte=0;uint64_t read=liza_rt_reactor_read(r,id[0],id[1],id[2],&byte,1,0,1);
            if(!(read>>32)){CHECK(read==1&&byte=='n');network=1;}else CHECK((read>>32)==4);}
    }
    if(strcmp(mode,"idle"))CHECK(got==1);
    if(strcmp(mode,"idle")&&strcmp(mode,"fault"))CHECK(network==1);
    return 23; /* Consumer wrapper closes its registered Reactor. */
}
static unsigned os_handles(void){
#ifdef _WIN32
    DWORD n;CHECK(GetProcessHandleCount(GetCurrentProcess(),&n));return n;
#else
    DIR *d=opendir("/dev/fd");CHECK(d);unsigned n=0;struct dirent *entry;
    while((entry=readdir(d)))if(entry->d_name[0]!='.')n++;
    closedir(d);return n;
#endif
}
static void validate_events(unsigned start,uint64_t gen,int callbacks){
    int exited[3]={0},joined[3]={0},submitted=0,returned=0,destroyed=0;
    unsigned count=atomic_load(&event_count);
    for(unsigned i=start;i<count;i++){
        CHECK(events[i].generation==gen);const char *k=events[i].kind;unsigned role=events[i].role;
        if(!strcmp(k,"submitted"))submitted=1;
        if(!strcmp(k,"callback"))CHECK(callbacks);
        if(!strcmp(k,"exit")){CHECK(!exited[role]);exited[role]=1;}
        if(!strcmp(k,"join")){CHECK(submitted);CHECK(exited[role]);CHECK(!joined[role]);joined[role]=1;}
        if(!strcmp(k,"receipt"))CHECK(joined[role]);
        if(!strcmp(k,"handback"))returned=1;
        if(!strcmp(k,"stopped")){CHECK(returned);if(callbacks)CHECK(joined[0]&&joined[1]&&joined[2]);}
        if(!strcmp(k,"destroy")){CHECK(!submitted||returned);destroyed=1;}
        if(!strcmp(k,"record_free"))CHECK(destroyed&&returned);
    }
}
int main(int argc,char **argv){
    CHECK(argc>=2);mode=argv[1];config=(liza_sg2_config){0};
    config.managed_budget=65536;config.process_budget=65536;config.stack_bytes=1024*1024;config.service_stack_bytes=1024*1024;
    config.reactor_budget=65536;config.reactor_capacity=2;config.slots=2;config.max_threads=3;config.max_socket_handles=5;config.operation_ms=1000;config.shutdown_ms=500;
    if(!strcmp(mode,"long_running"))config.operation_ms=5000;
    if(!strcmp(mode,"fault")||!strcmp(mode,"double_fault"))config.data_fault=1;
    if(!strcmp(mode,"double_fault"))config.control_fault=1;
    if(!strcmp(mode,"startup")){CHECK(argc==3);config.fail_at=(unsigned)atoi(argv[2]);}
    if(!strcmp(mode,"handback"))atomic_store(&sg2_test_handback_gate,1);
    if(!strcmp(mode,"supervisor_stall"))atomic_store(&sg2_test_supervisor_gate,1);
    if(!strcmp(mode,"stale"))atomic_store(&sg2_test_stale_receipt,1);
    int invalid=!strcmp(mode,"budget")||!strcmp(mode,"stack_overflow")||!strcmp(mode,"handles")||!strcmp(mode,"process_budget")||!strcmp(mode,"reactor_budget");
    if(!strcmp(mode,"budget"))config.managed_budget=1;
    if(!strcmp(mode,"stack_overflow"))config.stack_bytes=SIZE_MAX;
    if(!strcmp(mode,"handles"))config.max_socket_handles=4;
    if(!strcmp(mode,"process_budget"))config.process_budget=1;
    if(!strcmp(mode,"reactor_budget"))config.reactor_budget=1;
    unsigned loops=!strcmp(mode,"reuse")?100:!strcmp(mode,"rollback_reuse")?23:1,baseline=0;uint64_t last=0;size_t process_bytes=0;
    for(unsigned i=0;i<loops;i++){
        if(!strcmp(mode,"rollback_reuse"))config.fail_at=(i>0&&i+1<loops)?i:0;
        atomic_store(&destroy_count,0);atomic_store(&waiting,0);atomic_store(&allow_exit,0);atomic_store(&callback_count,0);
        unsigned start=atomic_load(&event_count);liza_sg2_report report;
        uint32_t result=liza_sg2_run(&config,produce,consume,&report);
        if(invalid){CHECK(result==SG2_INVALID);CHECK(!atomic_load(&callback_count));return 0;}
        if(config.fail_at){CHECK(result==SG2_STARTUP_FAILED);CHECK(!atomic_load(&callback_count));}
        else {CHECK(result==(!strcmp(mode,"fault")?SG2_FAULTED:SG2_OK));CHECK(report.producer_result==17&&report.consumer_result==23);}
        CHECK(report.generation>last);last=report.generation;
        validate_events(start,last,config.fail_at==0);
        CHECK(!report.group_socket_handles_live&&!report.group_managed_bytes_live&&!report.join_records_in_use);
        CHECK(!report.participant_threads_live&&!report.participant_native_handles_live&&!report.reactor_socket_handles_live);
        CHECK(report.group_socket_handles_peak<=5);CHECK(report.process_service_threads<=1);
        unsigned handles=os_handles();if(!i){baseline=handles;process_bytes=report.process_managed_bytes;}else CHECK(baseline==handles&&process_bytes==report.process_managed_bytes);
        printf("{\"fifo_allocation_bytes\":%zu,\"participant_threads_live\":%u,\"participant_native_handles_live\":%u,\"participant_stack_requested_bytes\":%zu,\"service_stack_requested_bytes\":%zu,\"reactor_allocation_bytes\":%zu,\"reactor_socket_handles_live\":%u,",report.fifo_allocation_bytes,report.participant_threads_live,report.participant_native_handles_live,report.participant_stack_requested_bytes,report.service_stack_requested_bytes,report.reactor_allocation_bytes,report.reactor_socket_handles_live);
        printf("\"schema_version\":1,\"generation\":%llu,\"phase\":\"%s\",\"result\":%u,\"group_managed_bytes_live\":%zu,\"group_managed_bytes_peak\":%zu,\"group_socket_handles_live\":%u,\"group_socket_handles_peak\":%u,\"process_service_threads\":%u,\"process_managed_bytes\":%zu,\"join_records_in_use\":%u,\"os_handles\":%u,\"startup_steps\":%u,\"os_overhead_accounting\":\"not_bounded_by_managed_budget\"}\n",(unsigned long long)last,config.fail_at?"rolled_back":"destroyed",result,report.group_managed_bytes_live,report.group_managed_bytes_peak,report.group_socket_handles_live,report.group_socket_handles_peak,report.process_service_threads,report.process_managed_bytes,report.join_records_in_use,handles,report.startup_steps);
    }
    return 0;
}
