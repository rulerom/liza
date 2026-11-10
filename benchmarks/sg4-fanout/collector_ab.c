/* NB1-C POSIX collector: separate process, bounded duplicate bitmap. */
#define _DARWIN_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>
#include <sys/ioctl.h>
#define MAX_RECEIVERS 64
#include "config.h"
#define PACKET_SIZE 1200
struct record {uint64_t time_ns;uint32_t sequence;uint16_t receiver,source_port;};
_Static_assert(sizeof(struct record)==16,"unexpected record layout");
static uint64_t ns(void){struct timespec t;if(clock_gettime(CLOCK_MONOTONIC,&t))abort();return (uint64_t)t.tv_sec*1000000000u+t.tv_nsec;}
struct timing {uint64_t calls,total,max,hist[10001];};
static struct timing polling,receiving,storing,between;
struct store_event {uint64_t begin,end;uint32_t seq,receiver;};
static struct store_event store_events[8192];
static unsigned store_events_used,store_events_dropped;
#ifdef SG4_COLLECTOR_TESTING
static long test_pause_seq=-1;static int test_paused;
#endif
static void observe(struct timing *t,uint64_t n){t->calls++;t->total+=n;if(n>t->max)t->max=n;t->hist[n/1000<10001?n/1000:10000]++;}
static void timing_json(FILE *f,const char *name,struct timing *t){fprintf(f,"\"%s\":{\"calls\":%llu,\"total_ns\":%llu,\"max_ns\":%llu,\"hist_1us\":{",name,(unsigned long long)t->calls,(unsigned long long)t->total,(unsigned long long)t->max);int first=1;for(unsigned i=0;i<10001;i++)if(t->hist[i]){fprintf(f,"%s\"%u\":%llu",first?"":",",i,(unsigned long long)t->hist[i]);first=0;}fprintf(f,"}}");}
static uint32_t be32(const unsigned char *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
int main(int argc,char **argv){
 if(argc!=5)return 2;
#ifdef SG4_COLLECTOR_TESTING
 const char *pause=getenv("SG4_COLLECTOR_TEST_PAUSE_SEQ");
 if(pause){char *e;test_pause_seq=strtol(pause,&e,10);if(*e||test_pause_seq<0||test_pause_seq>=MAX_PACKETS+WARMUP)return 2;}
#endif
 char *end;long num=strtol(argv[1],&end,10);if(*end||num<1||num>MAX_RECEIVERS)return 2;
 long packets=strtol(argv[2],&end,10);if(*end||packets<1||packets>MAX_PACKETS+WARMUP)return 2;
 const char *mode=getenv("SG4_COLLECTOR_MODE");int buffered=mode&&strcmp(mode,"memory")==0;
 if(mode&&strcmp(mode,"memory")&&strcmp(mode,"file"))return 2;
 size_t record_limit=(size_t)num*(size_t)packets;
 const char *limit=getenv("SG4_COLLECTOR_RECORD_LIMIT");if(limit){char *e;unsigned long long v=strtoull(limit,&e,10);if(*e||v>record_limit)return 2;record_limit=(size_t)v;}
 struct record *memory=NULL;
 if(buffered){memory=malloc((record_limit?record_limit:1)*sizeof *memory);if(!memory)return 3;memset(memory,0,(record_limit?record_limit:1)*sizeof *memory);volatile unsigned char *touch=(volatile unsigned char *)memory;for(size_t k=0;k<(record_limit?record_limit:1)*sizeof *memory;k+=4096)touch[k]=0;}
 FILE *records=fopen(argv[3],"wb");if(!records)return 3;
 unsigned char *seen=calloc((size_t)num*(size_t)packets,1);if(!seen)return 3;
 struct pollfd fds[MAX_RECEIVERS+1];int actual_buffers[MAX_RECEIVERS];memset(fds,0,sizeof fds);fds[0].fd=STDIN_FILENO;fds[0].events=POLLIN;
 printf("{\"mode\":\"%s\",\"record_limit\":%zu,\"record_bytes\":%zu,\"ports\":[",buffered?"memory":"file",record_limit,buffered?record_limit*sizeof *memory:0);
 for(int i=0;i<num;i++){
  int fd=socket(AF_INET,SOCK_DGRAM,0);if(fd<0)return 3;
  int flags=fcntl(fd,F_GETFL);if(flags<0||fcntl(fd,F_SETFL,flags|O_NONBLOCK))return 3;
  struct sockaddr_in a;memset(&a,0,sizeof a);a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(0x7f000001u);a.sin_port=htons(ports[i]);
  if(bind(fd,(struct sockaddr*)&a,sizeof a))return 3;
  socklen_t n=sizeof a;if(getsockname(fd,(struct sockaddr*)&a,&n))return 3;
  int bytes=0;socklen_t blen=sizeof bytes;if(getsockopt(fd,SOL_SOCKET,SO_RCVBUF,&bytes,&blen))return 3;actual_buffers[i]=bytes;
  fds[i+1].fd=fd;fds[i+1].events=POLLIN;printf("%s%u",i?",":"",(unsigned)ntohs(a.sin_port));
 }
 printf("],\"receive_buffers\":[");for(int i=0;i<num;i++)printf("%s%d",i?",":"",actual_buffers[i]);puts("]}");fflush(stdout);
 uint64_t received=0,invalid=0,duplicates=0,last_return=0,stop_ns=0,stored=0;int running=1,overflow=0;
 uint64_t per_receiver[MAX_RECEIVERS]={0},last_receive[MAX_RECEIVERS]={0};
 int pending_bytes[MAX_RECEIVERS]={0},pending_events[MAX_RECEIVERS]={0};
 while(running){
  uint64_t poll_begin=ns();int n=poll(fds,(nfds_t)num+1,-1);observe(&polling,ns()-poll_begin);if(n<0){if(errno==EINTR)continue;return 3;}
  if(fds[0].revents&(POLLIN|POLLHUP|POLLERR)){char cmd;if(read(0,&cmd,1)!=1||cmd!='S')return 3;stop_ns=ns();running=0;break;}
  for(int i=0;i<num;i++)if(fds[i+1].revents&POLLIN){
   /* Bound work per socket to avoid starving other receiver queues. */
   for(int batch=0;batch<64;batch++){
    unsigned char data[2048];struct sockaddr_in peer;socklen_t plen=sizeof peer;
    uint64_t recv_begin=ns();if(last_return)observe(&between,recv_begin-last_return);
    ssize_t len=recvfrom(fds[i+1].fd,data,sizeof data,0,(struct sockaddr*)&peer,&plen);
    last_return=ns();observe(&receiving,last_return-recv_begin);
    if(len<0){if(errno==EAGAIN||errno==EWOULDBLOCK)break;if(errno==EINTR)continue;return 3;}
    struct timespec ts;if(clock_gettime(CLOCK_MONOTONIC,&ts))return 3;
    if(len!=PACKET_SIZE || data[0]!=128 || data[1]!=96 || be32(data+8)!=0x10203040u){invalid++;continue;}
    uint32_t seq=be32(data+12);if(seq>=(uint32_t)packets || be32(data+4)!=seq || data[2]!=(uint8_t)(seq>>8) || data[3]!=(uint8_t)seq){invalid++;continue;}
    int valid=1;for(int j=16;j<PACKET_SIZE;j++)if(data[j]!=(uint8_t)seq){valid=0;break;}
    if(!valid){invalid++;continue;}
    size_t idx=(size_t)i*(size_t)packets+seq;if(seen[idx]){duplicates++;continue;}seen[idx]=1;
    struct record record={(uint64_t)ts.tv_sec*1000000000u+(uint64_t)ts.tv_nsec,seq,(uint16_t)i,ntohs(peer.sin_port)};
    received++;per_receiver[i]++;last_receive[i]=record.time_ns;
    uint64_t store_begin=ns();
#ifdef SG4_COLLECTOR_TESTING
    if(!test_paused&&i==0&&test_pause_seq==(long)seq){struct timespec delay={0,500000000};while(nanosleep(&delay,&delay)&&errno==EINTR){}test_paused=1;}
#endif
    if(buffered){if(stored==record_limit){overflow=1;running=0;observe(&storing,ns()-store_begin);goto finished;}memory[stored]=record;}
    else if(fwrite(&record,sizeof record,1,records)!=1)return 3;
    stored++;uint64_t store_end=ns();observe(&storing,store_end-store_begin);
    if(store_end-store_begin>=100000){if(store_events_used<8192)store_events[store_events_used++]=(struct store_event){store_begin,store_end,seq,(uint32_t)i};else store_events_dropped++;}
   }
  }
 }
finished:
 if(!stop_ns)stop_ns=ns();
 /* Observe cutoff before flushing; no extra drain silently changes acceptance. */
 struct pollfd tail[MAX_RECEIVERS];for(int i=0;i<num;i++){tail[i]=fds[i+1];tail[i].revents=0;if(ioctl(tail[i].fd,FIONREAD,&pending_bytes[i]))return 3;}
 if(poll(tail,(nfds_t)num,0)<0)return 3;
 for(int i=0;i<num;i++)pending_events[i]=tail[i].revents;
 uint64_t flush_begin=ns();
 if(buffered&&fwrite(memory,sizeof *memory,stored,records)!=stored)return 3;
 if(fclose(records))return 3;
 uint64_t flush_ns=ns()-flush_begin;free(memory);
 for(int i=0;i<num;i++)close(fds[i+1].fd);free(seen);
 struct rusage r;if(getrusage(RUSAGE_SELF,&r))return 3;
 FILE *meta=fopen(argv[4],"w");if(!meta)return 3;
 fprintf(meta,"{\"mode\":\"%s\",\"measurement_valid\":%s,\"record_overflow\":%s,\"record_limit\":%zu,\"records_stored\":%llu,\"stop_ns\":%llu,\"flush_ns\":%llu,",buffered?"memory":"file",overflow?"false":"true",overflow?"true":"false",record_limit,(unsigned long long)stored,(unsigned long long)stop_ns,(unsigned long long)flush_ns);
#ifdef SG4_COLLECTOR_TESTING
 fprintf(meta,"\"test_pause_injected\":%s,",test_paused?"true":"false");
#endif
 fprintf(meta,"\"store_events_threshold_ns\":100000,\"store_events_dropped\":%u,\"store_events\":[",store_events_dropped);
 for(unsigned j=0;j<store_events_used;j++){struct store_event *v=&store_events[j];fprintf(meta,"%s[%llu,%llu,%u,%u]",j?",":"",(unsigned long long)v->begin,(unsigned long long)v->end,v->seq,v->receiver);}fprintf(meta,"],");
 fprintf(meta,"\"timing\":{");timing_json(meta,"poll",&polling);fputc(',',meta);timing_json(meta,"recv",&receiving);fputc(',',meta);timing_json(meta,"store",&storing);fputc(',',meta);timing_json(meta,"outside_recv",&between);fprintf(meta,"},\"receivers\":[");
 for(int i=0;i<num;i++)fprintf(meta,"%s{\"id\":%d,\"received\":%llu,\"last_observed_ns\":%llu,\"pending_bytes_at_stop\":%d,\"poll_events_at_stop\":%d}",i?",":"",i,(unsigned long long)per_receiver[i],(unsigned long long)last_receive[i],pending_bytes[i],pending_events[i]);fprintf(meta,"],");
 fprintf(meta,"\"received\":%llu,\"invalid\":%llu,\"duplicates\":%llu,\"user_s\":%.6f,\"system_s\":%.6f,\"maxrss_native\":%ld}\n",(unsigned long long)received,(unsigned long long)invalid,(unsigned long long)duplicates,r.ru_utime.tv_sec+r.ru_utime.tv_usec/1e6,r.ru_stime.tv_sec+r.ru_stime.tv_usec/1e6,r.ru_maxrss);
 if(fclose(meta))return 3;return overflow?4:0;
}
