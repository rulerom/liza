/* Single-thread bounded RTP fanout reference for the Liza UDP implementation.
 * IPv4 loopback, POSIX; no dynamic allocation and no payload copies in user code.
 */
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#ifdef NB1B_CONTROL
#include <poll.h>
#endif
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

enum { MAX_PACKET=2048, MAX_RECEIVERS=64 };

static int parse_uint(const char *s, uint32_t max, uint32_t *result) {
    uint32_t n=0;unsigned digits=0;
    if(!*s)return 0;
    for(;*s;s++) {
        if(++digits>10)return 0;
        if(*s<'0' || *s>'9')return 0;
        uint32_t d=(uint32_t)(*s-'0');
        if(n>(max-d)/10)return 0;
        n=n*10+d;
    }
    *result=n;return 1;
}

struct rtp_header { uint8_t version,marker,payload_type; uint16_t sequence; uint32_t timestamp,ssrc,payload_offset,payload_length; };
static uint16_t be16(const uint8_t *p) {return (uint16_t)(((uint16_t)p[0]<<8)|p[1]);}
static uint32_t be32(const uint8_t *p) {return ((uint32_t)be16(p)<<16)|be16(p+2);}
/* Equivalent header extraction, CSRC, extension and padding validation. */
static int parse_rtp(const uint8_t *data, size_t size, struct rtp_header *out) {
    if(size<12 || data[0]>>6!=2)return 0;
    size_t header=12u+4u*(data[0]&15u);
    if(header>size)return 0;
    if(data[0]&16u) {
        if(size-header<4)return 0;
        size_t words=((size_t)data[header+2]<<8)|data[header+3];
        if(words>(size-header-4)/4)return 0;
        header+=4+words*4;
    }
    if(data[0]&32u) {
        uint8_t padding=data[size-1];
        if(!padding || padding>size-header)return 0;
    }
    size_t payload_length=size-header;
    if(data[0]&32u)payload_length-=data[size-1];
    *out=(struct rtp_header){(uint8_t)(data[0]>>6),!!(data[1]&128),data[1]&127,
        be16(data+2),be32(data+4),be32(data+8),(uint32_t)header,(uint32_t)payload_length};
    return 1;
}

#ifdef NB1B_CONTROL
/* Benchmark-only stdin control, priority over a ready UDP socket. */
static ssize_t controlled_recv(int fd,struct msghdr *msg) {
    for(;;) {
        struct pollfd fds[2]={{STDIN_FILENO,POLLIN,0},{fd,POLLIN,0}};
        int r=poll(fds,2,-1);
        if(r<0){if(errno==EINTR)continue;return -1;}
        if(fds[0].revents&(POLLIN|POLLHUP|POLLERR)) {
            char c;ssize_t n=read(STDIN_FILENO,&c,1);
            if(n!=1)return -1;
            if(c=='D')return -2;
            if(c=='S')return -3;
            return -1;
        }
        if(fds[1].revents&POLLIN) {
            ssize_t n=recvmsg(fd,msg,0);
            if(n<0 && (errno==EINTR || errno==EAGAIN || errno==EWOULDBLOCK))continue;
            return n;
        }
        if(fds[1].revents&(POLLERR|POLLHUP|POLLNVAL))return -1;
    }
}
#endif
int main(int argc,char **argv) {
    uint32_t packets,ssrc;
    if(argc<4 || argc>3+MAX_RECEIVERS || !parse_uint(argv[1],2147483647u,&packets) || !packets ||
       !parse_uint(argv[2],UINT32_MAX,&ssrc)) {fputs("invalid arguments\n",stderr);return 2;}
    struct receiver { uint32_t ssrc; uint8_t active,known; uint32_t ipv4; uint16_t port; };
    struct receiver receivers[MAX_RECEIVERS]={0};
    unsigned count=(unsigned)(argc-3);
    for(unsigned i=0;i<count;i++) {
        uint32_t port;
        if(!parse_uint(argv[i+3],65535,&port) || !port) {fputs("invalid receiver port\n",stderr);return 2;}
        receivers[i].ssrc=i;receivers[i].active=1;receivers[i].known=1;
        receivers[i].ipv4=0x7f000001u;receivers[i].port=(uint16_t)port;
    }
    int fd=socket(AF_INET,SOCK_DGRAM,0);
    if(fd<0){perror("socket");return 1;}
    struct sockaddr_in addr;memset(&addr,0,sizeof(addr));addr.sin_family=AF_INET;addr.sin_addr.s_addr=htonl(0x7f000001u);
    if(bind(fd,(struct sockaddr *)&addr,sizeof(addr))<0){perror("bind");close(fd);return 1;}
    socklen_t addrlen=sizeof(addr);
    if(getsockname(fd,(struct sockaddr *)&addr,&addrlen)<0){perror("getsockname");close(fd);return 1;}
    if(printf("%u\n",(unsigned)ntohs(addr.sin_port))<0 || fflush(stdout)!=0){close(fd);return 1;}
    unsigned errors=0;
    uint64_t rx=0, valid=0, invalid=0, wrong=0, truncated=0, attempted=0, succeeded=0, failed=0, reason=0;
#ifdef NB1B_CONTROL
    uint64_t phase_rx=0,phase_valid=0;int phase_seen=0;
#endif
    for(uint32_t i=0;i<packets && !errors;i++) {
        uint8_t data[MAX_PACKET];struct iovec vec={data,sizeof(data)};struct msghdr msg;
        memset(&msg,0,sizeof(msg));msg.msg_iov=&vec;msg.msg_iovlen=1;
#ifdef NB1B_CONTROL
        ssize_t n=controlled_recv(fd,&msg);
        if(n==-2){if(phase_seen){errors++;break;}phase_seen=1;phase_rx=rx;phase_valid=valid;if(puts("PHASE")<0 || fflush(stdout)!=0){errors++;break;}continue;}
        if(n==-3){if(!phase_seen){errors++;break;}reason=1;break;}
#else
        ssize_t n=recvmsg(fd,&msg,0);
#endif
        if(n<0){perror("recvmsg");errors++;continue;}
        if(msg.msg_flags&MSG_TRUNC){rx++;truncated++;continue;}
#ifndef NB1B_CONTROL
        if(n==8 && memcmp(data,"LZSTOP01",8)==0){reason=1;break;}
#endif
        rx++;
        struct rtp_header header;
        if(!parse_rtp(data,(size_t)n,&header)){invalid++;continue;}
        if(header.ssrc!=ssrc){wrong++;continue;}
        valid++;
        for(unsigned j=0;j<count;j++) {
            if(!receivers[j].active || !receivers[j].known)continue;
            struct sockaddr_in destination;memset(&destination,0,sizeof(destination));
            destination.sin_family=AF_INET;destination.sin_addr.s_addr=htonl(receivers[j].ipv4);
            destination.sin_port=htons(receivers[j].port);
            attempted++;
            ssize_t sent=sendto(fd,data,(size_t)n,0,(struct sockaddr *)&destination,sizeof(destination));
            if(sent!=n){errors++;failed++;} else succeeded++;
        }
    }
    if(close(fd)<0)errors++;
    if(errors)reason=2;
    if(fprintf(stderr,"received=%llu\naccepted_valid=%llu\ninvalid=%llu\nwrong_ssrc=%llu\ntruncated=%llu\nsend_attempted=%llu\nsend_succeeded=%llu\nsend_failed=%llu\nstop_reason=%llu\n",(unsigned long long)rx,(unsigned long long)valid,(unsigned long long)invalid,(unsigned long long)wrong,(unsigned long long)truncated,(unsigned long long)attempted,(unsigned long long)succeeded,(unsigned long long)failed,(unsigned long long)reason)<0)errors++;
#ifdef NB1B_CONTROL
    if(fprintf(stderr,"phase_received=%llu\nphase_valid=%llu\nphase_seen=%d\n",(unsigned long long)phase_rx,(unsigned long long)phase_valid,phase_seen)<0)errors++;
#endif
    return errors?3:0;
}
