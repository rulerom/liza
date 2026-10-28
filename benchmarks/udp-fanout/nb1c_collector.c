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
#define MAX_RECEIVERS 64
#define MAX_PACKETS 60000
#define PACKET_SIZE 1200
struct record {uint64_t time_ns;uint32_t sequence;uint16_t receiver,source_port;};
_Static_assert(sizeof(struct record)==16,"unexpected record layout");
static uint32_t be32(const unsigned char *p){return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
int main(int argc,char **argv){
 if(argc!=5)return 2;
 char *end;long num=strtol(argv[1],&end,10);if(*end||num<1||num>MAX_RECEIVERS)return 2;
 long packets=strtol(argv[2],&end,10);if(*end||packets<1||packets>MAX_PACKETS)return 2;
 FILE *records=fopen(argv[3],"wb");if(!records)return 3;
 unsigned char *seen=calloc((size_t)num*(size_t)packets,1);if(!seen)return 3;
 struct pollfd fds[MAX_RECEIVERS+1];int actual_buffers[MAX_RECEIVERS];memset(fds,0,sizeof fds);fds[0].fd=STDIN_FILENO;fds[0].events=POLLIN;
 printf("{\"ports\":[");
 for(int i=0;i<num;i++){
  int fd=socket(AF_INET,SOCK_DGRAM,0);if(fd<0)return 3;
  int flags=fcntl(fd,F_GETFL);if(flags<0||fcntl(fd,F_SETFL,flags|O_NONBLOCK))return 3;
  struct sockaddr_in a;memset(&a,0,sizeof a);a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(0x7f000001u);
  if(bind(fd,(struct sockaddr*)&a,sizeof a))return 3;
  socklen_t n=sizeof a;if(getsockname(fd,(struct sockaddr*)&a,&n))return 3;
  int bytes=0;socklen_t blen=sizeof bytes;if(getsockopt(fd,SOL_SOCKET,SO_RCVBUF,&bytes,&blen))return 3;actual_buffers[i]=bytes;
  fds[i+1].fd=fd;fds[i+1].events=POLLIN;printf("%s%u",i?",":"",(unsigned)ntohs(a.sin_port));
 }
 printf("],\"receive_buffers\":[");for(int i=0;i<num;i++)printf("%s%d",i?",":"",actual_buffers[i]);puts("]}");fflush(stdout);
 uint64_t received=0,invalid=0,duplicates=0;int running=1;
 while(running){
  int n=poll(fds,(nfds_t)num+1,-1);if(n<0){if(errno==EINTR)continue;return 3;}
  if(fds[0].revents&(POLLIN|POLLHUP|POLLERR)){char cmd;if(read(0,&cmd,1)!=1||cmd!='S')return 3;running=0;break;}
  for(int i=0;i<num;i++)if(fds[i+1].revents&POLLIN){
   /* Bound work per socket to avoid starving other receiver queues. */
   for(int batch=0;batch<64;batch++){
    unsigned char data[2048];struct sockaddr_in peer;socklen_t plen=sizeof peer;
    ssize_t len=recvfrom(fds[i+1].fd,data,sizeof data,0,(struct sockaddr*)&peer,&plen);
    if(len<0){if(errno==EAGAIN||errno==EWOULDBLOCK)break;if(errno==EINTR)continue;return 3;}
    struct timespec ts;if(clock_gettime(CLOCK_MONOTONIC,&ts))return 3;
    if(len!=PACKET_SIZE || data[0]!=128 || data[1]!=96 || be32(data+8)!=0x10203040u){invalid++;continue;}
    uint32_t seq=be32(data+12);if(seq>=(uint32_t)packets || be32(data+4)!=seq || data[2]!=(uint8_t)(seq>>8) || data[3]!=(uint8_t)seq){invalid++;continue;}
    int valid=1;for(int j=16;j<PACKET_SIZE;j++)if(data[j]!=(uint8_t)seq){valid=0;break;}
    if(!valid){invalid++;continue;}
    size_t idx=(size_t)i*(size_t)packets+seq;if(seen[idx]){duplicates++;continue;}seen[idx]=1;
    struct record record={(uint64_t)ts.tv_sec*1000000000u+(uint64_t)ts.tv_nsec,seq,(uint16_t)i,ntohs(peer.sin_port)};
    if(fwrite(&record,sizeof record,1,records)!=1)return 3;received++;
   }
  }
 }
 if(fclose(records))return 3;for(int i=0;i<num;i++)close(fds[i+1].fd);free(seen);
 struct rusage r;if(getrusage(RUSAGE_SELF,&r))return 3;
 FILE *meta=fopen(argv[4],"w");if(!meta)return 3;
 fprintf(meta,"{\"received\":%llu,\"invalid\":%llu,\"duplicates\":%llu,\"user_s\":%.6f,\"system_s\":%.6f,\"maxrss_native\":%ld}\n",(unsigned long long)received,(unsigned long long)invalid,(unsigned long long)duplicates,r.ru_utime.tv_sec+r.ru_utime.tv_usec/1e6,r.ru_stime.tv_sec+r.ru_stime.tv_usec/1e6,r.ru_maxrss);
 return fclose(meta)?3:0;
}
