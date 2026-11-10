/* Benchmark-only observation/control. UDP results and payloads are unchanged.
 * POSIX harness; production SG2/SG3 sources are included, not patched. */
#define _DARWIN_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#define liza_rt_group_run bench_run_original
#define liza_rt_group_next bench_next_original
#define liza_rt_group_send bench_send_original
#define liza_rt_group_udp_bind bench_bind_original
#define liza_rt_group_udp_receive bench_receive_original
#define liza_rt_group_udp_send bench_udp_send_original
#define liza_rt_reactor_poll_sources bench_poll
#include "sg3_common.h"
#undef liza_rt_group_run
#undef liza_rt_group_next
#undef liza_rt_group_send
#undef liza_rt_group_udp_bind
#undef liza_rt_group_udp_receive
#undef liza_rt_group_udp_send
#undef liza_rt_reactor_poll_sources
#include <stdio.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <poll.h>
#include "config.h"
#include "packet.h"
#define BINS 10001
#define BIN_NS 10000u
struct counts {uint64_t received,unique,valid,invalid,wrong_ssrc,truncated,attempted,succeeded,failed,duplicates;};
static struct counts stats[2];
static unsigned char seen[MAX_PACKETS+WARMUP];
static uint64_t cycle_hist[BINS],cycle_max,cycles,cycle_start,poll_calls,poll_returns;
static uint64_t phase_received,phase_valid,ready_ns,measure_ns,drain_ns,stop_ns,stopping_ns,finished_ns;
static uint64_t producer_cpu,consumer_cpu,command_sent_ns,command_seen_ns;
static int rcvbuf,sndbuf,current_phase,current_packet,applied;
static atomic_int requested;
static int done_pipe[2];
static pthread_t controller_thread;
static int controller_joined;
static _Atomic(sg_group *) group;
static uint32_t (*app_producer)(void),(*app_consumer)(void);
static struct rusage measure_usage;
static uint64_t now(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();return (uint64_t)t.tv_sec*1000000000u+t.tv_nsec;}
static uint64_t cpu(void){struct timespec t;if(clock_gettime(CLOCK_THREAD_CPUTIME_ID,&t))abort();return (uint64_t)t.tv_sec*1000000000u+t.tv_nsec;}
#ifdef SG4_STAGE_TIMING
#include "stages.h"
#endif
static double seconds(struct timeval t){return t.tv_sec+t.tv_usec/1e6;}
static void phase(void){
 int req=atomic_load(&requested);
 if(req>applied){
  if(req==1){measure_ns=now();current_phase=1;if(getrusage(RUSAGE_SELF,&measure_usage))abort();}
  if(req==2){drain_ns=now();phase_received=stats[1].received;phase_valid=stats[1].valid;}
  applied=req;printf("{\"phase\":%d,\"time_ns\":%llu}\n",req,(unsigned long long)now());fflush(stdout);
 }
}
static void *controller(void *unused){
 (void)unused;char c;
 for(;;){
  struct pollfd fds[2]={{0,POLLIN,0},{done_pipe[0],POLLIN,0}};
  int ready=poll(fds,2,-1);if(ready<0){if(errno==EINTR)continue;abort();}
  if(fds[1].revents)return NULL;
  if(read(0,&c,1)!=1)break;
  sg_group *g=atomic_load(&group);if(!g)abort();
  if(c=='S'){stop_ns=now();atomic_store(&g->stop_intent,1);return NULL;}
  if(c!='M'&&c!='D')abort();
  atomic_store(&requested,c=='M'?1:2);
  if(!sg_wake_send(&g->control))abort();
 }
 sg_group *g=atomic_load(&group);if(g){stop_ns=now();atomic_store(&g->stop_intent,1);}return NULL;
}
uint64_t liza_rt_reactor_poll_sources(reactor *,int32_t,sg3_source *,uint32_t);
uint64_t bench_poll(reactor *r,int32_t timeout,sg3_source *sources,uint32_t count){
 if(!ready_ns){ready_ns=now();printf("{\"ready_ns\":%llu,\"port\":%llu,\"rcvbuf\":%d,\"sndbuf\":%d}\n",(unsigned long long)ready_ns,(unsigned long long)liza_rt_group_udp_port(),rcvbuf,sndbuf);fflush(stdout);}
 poll_calls++;
 uint64_t result=liza_rt_reactor_poll_sources(r,timeout,sources,count);
 poll_returns++;phase();return result;
}
uint32_t bench_net_bind_original(uint32_t,uint16_t,uint64_t *);
uint32_t liza_rt_net_udp_bind(uint32_t ip,uint16_t port,uint64_t *out){
 uint32_t e=bench_net_bind_original(ip,port,out);
 if(!e){socklen_t n=sizeof(int);if(getsockopt((int)*out,SOL_SOCKET,SO_RCVBUF,&rcvbuf,&n)||getsockopt((int)*out,SOL_SOCKET,SO_SNDBUF,&sndbuf,&n))abort();}
 return e;
}
uint32_t liza_rt_group_udp_bind(uint32_t ip,uint16_t port){
 uint32_t e=bench_bind_original(ip,port);if(!e)atomic_store(&group,sg3_context()->group);return e;
}
uint32_t liza_rt_group_send(uint32_t value){command_sent_ns=now();return bench_send_original(value);}
uint64_t liza_rt_group_next(void){
#ifdef SG4_STAGE_TIMING
 stage_next();
#endif
 if(cycle_start){uint64_t elapsed=now()-cycle_start;if(current_packet==1){cycles++;if(elapsed>cycle_max)cycle_max=elapsed;uint64_t bin=elapsed/BIN_NS;cycle_hist[bin<BINS?bin:BINS-1]++;}cycle_start=0;}
 phase();uint64_t e=bench_next_original();
 if(e>>32==1)cycle_start=now();
 if(e>>32==0)command_seen_ns=now();
 if(e>>32==3)stopping_ns=now();
 return e;
}
uint32_t liza_rt_group_udp_receive(uint8_t *data,uint32_t capacity,uint64_t *meta){
#ifdef SG4_STAGE_TIMING
 uint64_t stage_begin=now();
#endif
 uint32_t e=bench_receive_original(data,capacity,meta);
#ifdef SG4_STAGE_TIMING
 uint64_t stage_end=now();
#endif
 current_packet=current_phase?1:0;
 if(e){if(e==8){stats[current_packet].received++;stats[current_packet].truncated++;}return e;}
 uint32_t n=(uint32_t)(*meta&65535),seq=n>=16?be32(data+12):UINT32_MAX;
 if(seq<WARMUP)current_packet=0;
 struct counts *s=&stats[current_packet];s->received++;
 if(seq<MAX_PACKETS+WARMUP){if(!seen[seq]){seen[seq]=1;s->unique++;}else s->duplicates++;}
 struct rtp_header h;
 if(!parse_rtp(data,n,&h))s->invalid++;
 else if(h.ssrc!=0x10203040)s->wrong_ssrc++;
 else s->valid++;
#ifdef SG4_STAGE_TIMING
 stage_receive(stage_begin,stage_end,seq,current_packet==1&&seq>=WARMUP&&seq<MAX_PACKETS+WARMUP);
#endif
 return e;
}
uint64_t liza_rt_group_udp_send(const uint8_t *p,uint32_t n,uint32_t start,uint32_t count,uint32_t ip,uint16_t port){
 struct counts *s=&stats[current_packet];s->attempted++;
#ifdef SG4_STAGE_TIMING
 stage_send_begin();
#endif
 uint64_t e;
#ifdef BENCH_TEST_SEND_FAIL
 if(port==ports[0])e=(uint64_t)4<<32;else
#endif
 e=bench_udp_send_original(p,n,start,count,ip,port);
#ifdef SG4_STAGE_TIMING
 stage_send_end();
#endif
 if(e>>32)s->failed++;else s->succeeded++;
 return e;
}
static uint32_t producer(void){uint64_t t=cpu();uint32_t r=app_producer();producer_cpu=cpu()-t;return r;}
static uint32_t consumer(void){
 uint64_t t=cpu();uint32_t r=app_consumer();consumer_cpu=cpu()-t;
 /* End the harness borrow before the consumer can exit and SG2 can destroy. */
 if(write(done_pipe[1],"X",1)!=1||pthread_join(controller_thread,NULL))abort();
 controller_joined=1;return r;
}
uint32_t liza_rt_group_run(uint64_t managed,uint64_t process,uint64_t stack,uint64_t service_stack,uint64_t reactor_budget,uint32_t capacity,uint32_t slots,uint32_t operation,uint32_t shutdown,uint32_t(*p)(void),uint32_t(*c)(void),uint32_t *pr,uint32_t *cr,uint32_t *fault,uint32_t *control){
 app_producer=p;app_consumer=c;
 if(pipe(done_pipe))abort();
 if(pthread_create(&controller_thread,NULL,controller,NULL))abort();
 uint32_t result=bench_run_original(managed,process,stack,service_stack,reactor_budget,capacity,slots,operation,shutdown,producer,consumer,pr,cr,fault,control);
 finished_ns=now();
 /* On startup failure no Ready was emitted; parent timeout terminates this process. */
 if(result==SG2_STARTUP_FAILED||result==SG2_INVALID)abort();
 if(!controller_joined){if(write(done_pipe[1],"X",1)!=1||pthread_join(controller_thread,NULL))abort();}
 close(done_pipe[0]);close(done_pipe[1]);
 struct rusage usage;if(getrusage(RUSAGE_SELF,&usage))abort();
 struct counts *s=&stats[1];
 printf("{\"result\":%u,\"producer\":%u,\"consumer\":%u,\"fault\":%u,\"control_fault\":%u,",result,*pr,*cr,*fault,*control);
#ifdef SG4_STAGE_TIMING
 stage_output();
#endif
 printf("\"received\":%llu,\"received_unique\":%llu,\"valid\":%llu,\"invalid\":%llu,\"wrong_ssrc\":%llu,\"truncated\":%llu,\"duplicates\":%llu,\"attempted\":%llu,\"succeeded\":%llu,\"failed\":%llu,",(unsigned long long)s->received,(unsigned long long)s->unique,(unsigned long long)s->valid,(unsigned long long)s->invalid,(unsigned long long)s->wrong_ssrc,(unsigned long long)s->truncated,(unsigned long long)s->duplicates,(unsigned long long)s->attempted,(unsigned long long)s->succeeded,(unsigned long long)s->failed);
 printf("\"warmup_valid\":%llu,\"phase_received\":%llu,\"phase_valid\":%llu,\"measure_ns\":%llu,\"drain_ns\":%llu,\"stop_ns\":%llu,\"stopping_ns\":%llu,\"finished_ns\":%llu,",(unsigned long long)stats[0].valid,(unsigned long long)phase_received,(unsigned long long)phase_valid,(unsigned long long)measure_ns,(unsigned long long)drain_ns,(unsigned long long)stop_ns,(unsigned long long)stopping_ns,(unsigned long long)finished_ns);
 printf("\"cycles\":%llu,\"cycle_max_ns\":%llu,\"poll_calls\":%llu,\"poll_returns\":%llu,\"command_samples\":1,\"command_latency_ns\":%llu,",(unsigned long long)cycles,(unsigned long long)cycle_max,(unsigned long long)poll_calls,(unsigned long long)poll_returns,(unsigned long long)(command_seen_ns-command_sent_ns));
 printf("\"user_s\":%.6f,\"system_s\":%.6f,\"measurement_drain_user_s\":%.6f,\"measurement_drain_system_s\":%.6f,\"maxrss_native\":%ld,\"producer_cpu_ns\":%llu,\"consumer_cpu_ns\":%llu,\"supervisor_cpu_ns\":null,\"service_cpu_ns\":null,",seconds(usage.ru_utime),seconds(usage.ru_stime),seconds(usage.ru_utime)-seconds(measure_usage.ru_utime),seconds(usage.ru_stime)-seconds(measure_usage.ru_stime),usage.ru_maxrss,(unsigned long long)producer_cpu,(unsigned long long)consumer_cpu);
 printf("\"cycle_hist_10us\":{");int first=1;for(unsigned i=0;i<BINS;i++)if(cycle_hist[i]){printf("%s\"%u\":%llu",first?"":",",i,(unsigned long long)cycle_hist[i]);first=0;}puts("}}");fflush(stdout);
 if(*cr!=stats[0].valid+stats[1].valid) return SG2_FAULTED;
 return result;
}
