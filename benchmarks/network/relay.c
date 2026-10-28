/* Exploratory poll-based relay: eight pairs, two 2048-byte bounded queues. */
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#define PAIRS 8
#define CAP 2048
struct direction { unsigned char data[CAP]; size_t head, tail; int eof, fin; };
struct pair { int client, upstream, connecting; struct direction f, r; };
static volatile sig_atomic_t stop;
static void on_signal(int n) { (void)n; stop=1; }
static int nonblock(int fd) { int f=fcntl(fd,F_GETFL); return f<0 ? -1 : fcntl(fd,F_SETFL,f|O_NONBLOCK); }
static int retry(void) { return errno==EAGAIN || errno==EWOULDBLOCK || errno==EINTR; }
static void drop(struct pair *p) { if(p->client>=0) close(p->client); if(p->upstream>=0) close(p->upstream); memset(p,0,sizeof *p); p->client=p->upstream=-1; }
static int transfer(int from,int to,struct direction *d,short rev,short wev) {
    if(!d->eof && d->tail<CAP && (rev&(POLLIN|POLLHUP|POLLERR))) {
        ssize_t n=read(from,d->data+d->tail,CAP-d->tail);
        if(n>0) d->tail+=(size_t)n; else if(n==0) d->eof=1; else if(!retry()) return -1;
    }
    if(d->head<d->tail && (wev&(POLLOUT|POLLHUP|POLLERR))) {
        ssize_t n=send(to,d->data+d->head,d->tail-d->head,0);
        if(n>0) d->head+=(size_t)n; else if(n<0 && !retry()) return -1;
        if(d->head==d->tail) d->head=d->tail=0;
    }
    if(d->eof && d->head==d->tail && !d->fin) { if(shutdown(to,SHUT_WR)<0 && errno!=ENOTCONN) return -1; d->fin=1; }
    return 0;
}
int main(int argc,char **argv) {
    if(argc!=2) return 2;
    char *end; long port=strtol(argv[1],&end,10); if(*end || port<1 || port>65535) return 2;
    signal(SIGPIPE,SIG_IGN); signal(SIGTERM,on_signal); signal(SIGINT,on_signal);
    int listener=socket(AF_INET,SOCK_STREAM,0); if(listener<0 || nonblock(listener)) return 3;
    struct sockaddr_in address={0}; address.sin_family=AF_INET; address.sin_addr.s_addr=htonl(0x7f000001u);
    if(bind(listener,(void*)&address,sizeof address)||listen(listener,16)) return 3;
    socklen_t length=sizeof address; if(getsockname(listener,(void*)&address,&length)) return 3;
    printf("%u\n",(unsigned)ntohs(address.sin_port)); fflush(stdout);
    struct pair pairs[PAIRS]; memset(pairs,0,sizeof pairs); for(int i=0;i<PAIRS;i++) pairs[i].client=pairs[i].upstream=-1;
    while(!stop) {
        struct pollfd fds[1+2*PAIRS]; memset(fds,0,sizeof fds); fds[0]=(struct pollfd){listener,POLLIN,0};
        for(int i=0;i<PAIRS;i++) {
            struct pair *p=&pairs[i]; fds[1+2*i].fd=p->client; fds[2+2*i].fd=p->upstream;
            if(p->client<0) continue;
            if(!p->connecting && !p->f.eof && p->f.tail<CAP) fds[1+2*i].events|=POLLIN;
            if(p->r.head<p->r.tail) fds[1+2*i].events|=POLLOUT;
            if(p->connecting || p->f.head<p->f.tail) fds[2+2*i].events|=POLLOUT;
            if(!p->connecting && !p->r.eof && p->r.tail<CAP) fds[2+2*i].events|=POLLIN;
        }
        if(poll(fds,1+2*PAIRS,100)<0) { if(errno==EINTR) continue; return 3; }
        if(fds[0].revents&POLLIN) {
            int i; for(i=0;i<PAIRS && pairs[i].client>=0;i++) {} if(i<PAIRS) {
                int c=accept(listener,NULL,NULL); if(c>=0) { int u=socket(AF_INET,SOCK_STREAM,0); if(u<0 || nonblock(c)||nonblock(u)) { close(c); if(u>=0)close(u); } else {
                    address.sin_port=htons((uint16_t)port); int rc=connect(u,(void*)&address,sizeof address);
                    if(rc<0 && errno!=EINPROGRESS) { close(c);close(u); } else { pairs[i].client=c;pairs[i].upstream=u;pairs[i].connecting=rc<0; }
                }}
            }
        }
        for(int i=0;i<PAIRS;i++) { struct pair *p=&pairs[i]; if(p->client<0)continue;
            short c=fds[1+2*i].revents,u=fds[2+2*i].revents;
            if((c|u)&POLLNVAL) { drop(p);continue; }
            if(p->connecting && (u&(POLLOUT|POLLERR|POLLHUP))) { int err=0; socklen_t n=sizeof err; if(getsockopt(p->upstream,SOL_SOCKET,SO_ERROR,&err,&n)||err) {drop(p);continue;} p->connecting=0; }
            if(p->connecting)continue;
            if(transfer(p->client,p->upstream,&p->f,c,u)||transfer(p->upstream,p->client,&p->r,u,c)||(p->f.fin && p->r.fin)) drop(p);
        }
    }
    for(int i=0;i<PAIRS;i++) drop(&pairs[i]); close(listener); return 0;
}
