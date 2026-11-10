/* B2 observation/control only: no UDP payload/result substitution. POSIX.
 * Every controller borrows exactly one group and is joined before its consumer exits. */
#define _DARWIN_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#define liza_rt_group_run b2_run_original
#define liza_rt_group_run_pair b2_pair_original
#define liza_rt_group_next b2_next_original
#define liza_rt_group_udp_bind b2_bind_original
#define liza_rt_group_udp_receive b2_receive_original
#define liza_rt_group_udp_send b2_send_original
#define liza_rt_reactor_poll_sources b2_poll
#include "sg3_common.h"
#undef liza_rt_group_run
#undef liza_rt_group_run_pair
#undef liza_rt_group_next
#undef liza_rt_group_udp_bind
#undef liza_rt_group_udp_receive
#undef liza_rt_group_udp_send
#undef liza_rt_reactor_poll_sources
#include <stdio.h>
#include <stdarg.h>
#include <sys/resource.h>
#include <poll.h>
#include "config.h"
#include "packet.h"
#define BINS 10001
struct counts {uint64_t received,unique,valid,invalid,filtered,truncated,attempted,succeeded,failed,duplicates;};
typedef struct {
    unsigned id;uint32_t (*producer)(void),(*consumer)(void);
    struct counts stats[2][2];unsigned char seen[2][MAX_PACKETS+WARMUP];
    uint64_t cycle_hist[BINS],cycles,cycle_max,cycle_start,polls,returns;
    uint64_t ready_ns,measure_ns,drain_ns,consumer_cpu,producer_cpu;
    uint64_t invalid[2],filtered[2],truncated[2];
    atomic_uint_fast64_t generation,stop_ns,stopping_ns,exit_ns,destroy_ns;
    atomic_uint joins,receipts;atomic_int handback,destroyed,phase_request,active;
    int applied,phase,packet_phase,stream,rcvbuf,sndbuf;
    int commands[2],done[2];pthread_t controller;sg_group *borrowed;
} observation;
static observation owners[2];static _Thread_local observation *local;
static pthread_mutex_t output_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_t router;static int router_done[2];static unsigned owner_count;
static atomic_uint_fast64_t event_number;
atomic_int sg2_test_handback_gate,sg2_test_stale_receipt,sg2_test_supervisor_gate;
static uint64_t now(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();return (uint64_t)t.tv_sec*1000000000u+t.tv_nsec;}
static uint64_t cpu(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return (uint64_t)t.tv_sec*1000000000u+t.tv_nsec;}
static void emit(const char *fmt,...){if(pthread_mutex_lock(&output_lock))abort();va_list a;va_start(a,fmt);vprintf(fmt,a);va_end(a);putchar('\n');fflush(stdout);if(pthread_mutex_unlock(&output_lock))abort();}
static void require(int yes){if(!yes)abort();}
void sg3_test_config(liza_sg2_config *c){(void)c;}
void sg2_test_event(const char *kind,uint64_t gen,unsigned role){
    if(!strcmp(kind,"process_abort")){emit("{\"event\":\"process_abort\",\"generation\":%llu}",(unsigned long long)gen);return;}
    for(unsigned i=0;i<owner_count;i++)if(atomic_load(&owners[i].generation)==gen){
        observation *o=&owners[i];uint64_t seq=atomic_fetch_add(&event_number,1)+1;
        if(!strcmp(kind,"join"))atomic_fetch_or(&o->joins,1u<<role);
        if(!strcmp(kind,"receipt")){require((atomic_load(&o->joins)&(1u<<role))!=0);atomic_fetch_or(&o->receipts,1u<<role);}
        if(!strcmp(kind,"handback")){require(atomic_load(&o->joins)==7);atomic_store(&o->handback,1);}
        if(!strcmp(kind,"destroy")){
            require(atomic_load(&o->handback)&&atomic_load(&o->joins)==7&&!atomic_load(&o->active));
            require(o->borrowed->sockets==0&&o->borrowed->owned_reactor==NULL);
            atomic_store(&o->destroy_ns,now());atomic_store(&o->destroyed,1);
        }
        emit("{\"event\":\"%s\",\"owner\":%u,\"generation\":%llu,\"role\":%u,\"sequence\":%llu,\"time_ns\":%llu}",kind,i,(unsigned long long)gen,role,(unsigned long long)seq,(unsigned long long)now());
        return;
    }
}
static void phase(void){
    observation *o=local;int req=atomic_load(&o->phase_request);
    if(req>o->applied){
        require(req==o->applied+1);
        if(req==1){o->phase=1;o->measure_ns=now();}else o->drain_ns=now();
        o->applied=req;emit("{\"event\":\"phase\",\"owner\":%u,\"phase\":%d,\"time_ns\":%llu}",o->id,req,(unsigned long long)now());
    }
}
static void *control(void *ptr){
    observation *o=ptr;char c;
    for(;;){
        struct pollfd fds[2]={{o->commands[0],POLLIN,0},{o->done[0],POLLIN,0}};
        int n=poll(fds,2,-1);if(n<0){if(errno==EINTR)continue;abort();}
        if(fds[1].revents)return NULL;
        if(read(o->commands[0],&c,1)!=1)abort();
        if(c=='S'||c=='F'){
            atomic_store(&o->stop_ns,now());
            if(c=='F')sg_fault(o->borrowed,1);else atomic_store(&o->borrowed->stop_intent,1);
            return NULL;
        }
        require(c=='M'||c=='D');atomic_store(&o->phase_request,c=='M'?1:2);
        require(sg_wake_send(&o->borrowed->control));
    }
}
static void *route(void *unused){
    (void)unused;
    for(;;){
        struct pollfd fds[2]={{STDIN_FILENO,POLLIN,0},{router_done[0],POLLIN,0}};
        int n=poll(fds,2,-1);if(n<0){if(errno==EINTR)continue;abort();}
        if(fds[1].revents)return NULL;
        char cmd[3];for(unsigned j=0;j<3;j++)if(read(STDIN_FILENO,&cmd[j],1)!=1)abort();
        require(cmd[2]=='\n'&&(cmd[0]=='M'||cmd[0]=='D'||cmd[0]=='S'||cmd[0]=='F'));
        unsigned id=(unsigned)(cmd[1]-'0');require(id<owner_count&&atomic_load(&owners[id].active));
        require(write(owners[id].commands[1],cmd,1)==1);
    }
}
uint64_t liza_rt_reactor_poll_sources(reactor *,int32_t,sg3_source *,uint32_t);
uint64_t b2_poll(reactor *r,int32_t timeout,sg3_source *sources,uint32_t n){
    observation *o=local;require(o!=NULL);
    if(!o->ready_ns){o->ready_ns=now();emit("{\"event\":\"ready\",\"owner\":%u,\"port\":%llu,\"rcvbuf\":%d,\"sndbuf\":%d,\"time_ns\":%llu}",o->id,(unsigned long long)liza_rt_group_udp_port(),o->rcvbuf,o->sndbuf,(unsigned long long)o->ready_ns);}
    o->polls++;uint64_t result=liza_rt_reactor_poll_sources(r,timeout,sources,n);o->returns++;phase();return result;
}
uint32_t liza_rt_group_udp_bind(uint32_t ip,uint16_t port){return b2_bind_original(ip,port);}
uint32_t b2_net_bind_original(uint32_t,uint16_t,uint64_t *);
uint32_t liza_rt_net_udp_bind(uint32_t ip,uint16_t port,uint64_t *out){
    uint32_t e=b2_net_bind_original(ip,port,out);
    if(!e){socklen_t n=sizeof(int);require(local!=NULL);require(!getsockopt((int)*out,SOL_SOCKET,SO_RCVBUF,&local->rcvbuf,&n));require(!getsockopt((int)*out,SOL_SOCKET,SO_SNDBUF,&local->sndbuf,&n));}
    return e;
}
uint64_t liza_rt_group_next(void){
    observation *o=local;
    if(o->cycle_start){uint64_t d=now()-o->cycle_start;if(o->packet_phase==1){o->cycles++;if(d>o->cycle_max)o->cycle_max=d;unsigned b=(unsigned)(d/10000);o->cycle_hist[b<BINS?b:BINS-1]++;}o->cycle_start=0;}
    phase();uint64_t event=b2_next_original();
    if(event>>32==1)o->cycle_start=now();
    if(event>>32==3||event>>32==4)atomic_store(&o->stopping_ns,now());
    return event;
}
uint32_t liza_rt_group_udp_receive(uint8_t *data,uint32_t capacity,uint64_t *meta){
    observation *o=local;uint32_t e=b2_receive_original(data,capacity,meta);o->stream=-1;o->packet_phase=o->phase?1:0;
    if(e){if(e==8)o->truncated[o->packet_phase]++;return e;}
    uint32_t n=(uint32_t)(*meta&65535),seq=n>=16?be32(data+12):UINT32_MAX;
    if(seq<WARMUP)o->packet_phase=0;
    struct rtp_header h;
    if(!parse_rtp(data,n,&h)){o->invalid[o->packet_phase]++;return e;}
    int stream=h.ssrc==SSRC_A?0:h.ssrc==SSRC_B?1:-1;
    if(stream<0||(!B2_SINGLE&&stream!=(int)o->id)){o->filtered[o->packet_phase]++;return e;}
    o->stream=stream;struct counts *s=&o->stats[stream][o->packet_phase];s->received++;s->valid++;
    if(seq<MAX_PACKETS+WARMUP){if(o->seen[stream][seq])s->duplicates++;else{o->seen[stream][seq]=1;s->unique++;}}
    return e;
}
uint64_t liza_rt_group_udp_send(const uint8_t *data,uint32_t n,uint32_t start,uint32_t count,uint32_t ip,uint16_t port){
    observation *o=local;require(o->stream>=0);struct counts *s=&o->stats[o->stream][o->packet_phase];s->attempted++;
    uint64_t e=b2_send_original(data,n,start,count,ip,port);if(e>>32)s->failed++;else s->succeeded++;return e;
}
static uint32_t produce(unsigned i){local=&owners[i];atomic_store(&local->generation,sg3_context()->group->generation);uint64_t t=cpu();uint32_t result=local->producer();local->producer_cpu=cpu()-t;local=NULL;return result;}
static uint32_t consume(unsigned i){
    local=&owners[i];observation *o=local;o->borrowed=sg3_context()->group;atomic_store(&o->generation,o->borrowed->generation);
    atomic_store(&o->active,1);require(!pthread_create(&o->controller,NULL,control,o));
    uint64_t t=cpu();uint32_t result=o->consumer();o->consumer_cpu=cpu()-t;
    require(write(o->done[1],"X",1)==1&&!pthread_join(o->controller,NULL));
    atomic_store(&o->active,0);atomic_store(&o->exit_ns,now());local=NULL;return result;
}
static uint32_t p0(void){return produce(0);}static uint32_t p1(void){return produce(1);}
static uint32_t c0(void){return consume(0);}static uint32_t c1(void){return consume(1);}
static void begin(unsigned n){owner_count=n;require(!pipe(router_done));for(unsigned i=0;i<n;i++){owners[i].id=i;require(!pipe(owners[i].commands)&&!pipe(owners[i].done));}require(!pthread_create(&router,NULL,route,NULL));}
static void end(void){
    require(write(router_done[1],"X",1)==1&&!pthread_join(router,NULL));close(router_done[0]);close(router_done[1]);
    for(unsigned i=0;i<owner_count;i++){
        close(owners[i].commands[0]);close(owners[i].commands[1]);close(owners[i].done[0]);close(owners[i].done[1]);
        require(atomic_load(&owners[i].destroyed)&&atomic_load(&owners[i].joins)==7&&atomic_load(&owners[i].receipts)==7);
    }
}
static void report(unsigned i,uint32_t result,uint32_t producer,uint32_t consumer,uint32_t fault,uint32_t control_fault){
    observation *o=&owners[i];
    emit("{\"event\":\"owner_result\",\"owner\":%u,\"generation\":%llu,\"result\":%u,\"producer\":%u,\"consumer\":%u,\"fault\":%u,\"control_fault\":%u,\"joins\":%u,\"receipts\":%u,\"destroy_ns\":%llu,\"exit_ns\":%llu,\"stop_ns\":%llu,\"stopping_ns\":%llu,\"consumer_cpu_ns\":%llu,\"producer_cpu_ns\":%llu,\"poll_calls\":%llu,\"poll_returns\":%llu,\"cycle_max_ns\":%llu,\"group_managed_budget\":65536,\"region_budget\":4096,\"reactor_budget\":65536,\"participant_stack_requested_bytes\":3145728,\"service_stack_requested_bytes\":1048576,\"group_socket_handles_live\":0}",i,(unsigned long long)atomic_load(&o->generation),result,producer,consumer,fault,control_fault,atomic_load(&o->joins),atomic_load(&o->receipts),(unsigned long long)atomic_load(&o->destroy_ns),(unsigned long long)atomic_load(&o->exit_ns),(unsigned long long)atomic_load(&o->stop_ns),(unsigned long long)atomic_load(&o->stopping_ns),(unsigned long long)o->consumer_cpu,(unsigned long long)o->producer_cpu,(unsigned long long)o->polls,(unsigned long long)o->returns,(unsigned long long)o->cycle_max);
    emit("{\"event\":\"unclassified\",\"owner\":%u,\"invalid\":%llu,\"filtered\":%llu,\"truncated\":%llu}",i,(unsigned long long)o->invalid[1],(unsigned long long)o->filtered[1],(unsigned long long)o->truncated[1]);
    uint64_t accepted=0;
    for(unsigned stream=0;stream<2;stream++){
        struct counts *s=&o->stats[stream][1];accepted+=s->valid+o->stats[stream][0].valid;
        emit("{\"event\":\"stream_result\",\"owner\":%u,\"stream\":%u,\"received\":%llu,\"unique\":%llu,\"valid\":%llu,\"invalid\":%llu,\"filtered\":%llu,\"truncated\":%llu,\"attempted\":%llu,\"succeeded\":%llu,\"failed\":%llu,\"duplicates\":%llu}",i,stream,(unsigned long long)s->received,(unsigned long long)s->unique,(unsigned long long)s->valid,(unsigned long long)s->invalid,(unsigned long long)s->filtered,(unsigned long long)s->truncated,(unsigned long long)s->attempted,(unsigned long long)s->succeeded,(unsigned long long)s->failed,(unsigned long long)s->duplicates);
    }
    require(producer==0&&accepted==consumer);
}
static void usage(void){struct rusage u;require(!getrusage(RUSAGE_SELF,&u));emit("{\"event\":\"usage\",\"user_s\":%.6f,\"system_s\":%.6f,\"maxrss_native\":%ld,\"process_managed_bytes\":%zu,\"harness_observation_bytes\":%zu,\"harness_threads_peak\":%u}",u.ru_utime.tv_sec+u.ru_utime.tv_usec/1e6,u.ru_stime.tv_sec+u.ru_stime.tv_usec/1e6,u.ru_maxrss,sizeof(services)+sizeof(admitted)+sizeof(next_generation),sizeof(owners),owner_count+1);}
uint32_t liza_rt_group_run(uint64_t m,uint64_t p,uint64_t st,uint64_t ss,uint64_t rb,uint32_t rc,uint32_t sl,uint32_t op,uint32_t sh,uint32_t(*producer)(void),uint32_t(*consumer)(void),uint32_t *pr,uint32_t *cr,uint32_t *fault,uint32_t *control_fault){
    begin(1);owners[0].producer=producer;owners[0].consumer=consumer;
    uint32_t result=b2_run_original(m,p,st,ss,rb,rc,sl,op,sh,p0,c0,pr,cr,fault,control_fault);
    end();report(0,result,*pr,*cr,*fault,*control_fault);usage();return result;
}
void liza_rt_group_run_pair(uint64_t am,uint64_t ap,uint64_t ast,uint64_t ass,uint64_t ar,uint32_t ac,uint32_t asl,uint32_t ao,uint32_t ash,uint64_t bm,uint64_t bp,uint64_t bst,uint64_t bss,uint64_t br,uint32_t bc,uint32_t bsl,uint32_t bo,uint32_t bsh,sg3_fn pa,sg3_fn ca,sg3_fn pb,sg3_fn cb,uint32_t out[10]){
    begin(2);owners[0].producer=pa;owners[0].consumer=ca;owners[1].producer=pb;owners[1].consumer=cb;
    b2_pair_original(am,ap,ast,ass,ar,ac,asl,ao,ash,bm,bp,bst,bss,br,bc,bsl,bo,bsh,p0,c0,p1,c1,out);
    end();report(0,out[4],out[0],out[1],out[2],out[3]);report(1,out[9],out[5],out[6],out[7],out[8]);usage();
}
