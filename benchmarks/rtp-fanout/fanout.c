/* Experimental bounded one-packet-in-flight fanout, POSIX only. */
#define _POSIX_C_SOURCE 200809L
#include <arpa/inet.h>
#include <errno.h>
#include <poll.h>
#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#define MAX_WORKERS 8
#define MAX_RECEIVERS 512
#define MAX_PACKET 2048
struct shared { pthread_mutex_t mu; pthread_cond_t work,done; unsigned epoch,completed,workers,receivers; int stop,fd; size_t length; unsigned char packet[MAX_PACKET]; struct sockaddr_in addresses[MAX_RECEIVERS]; uint64_t packets,sent,errors; };
struct worker { struct shared *s; unsigned id; };
static volatile sig_atomic_t stopping;
static void signal_stop(int sig) { (void)sig; stopping=1; }
static void *worker_main(void *arg) {
    struct worker *w=arg; struct shared *s=w->s; unsigned seen=0;
    pthread_mutex_lock(&s->mu);
    for (;;) {
        while(!s->stop && seen==s->epoch) pthread_cond_wait(&s->work,&s->mu);
        if(s->stop) break;
        seen=s->epoch; const size_t len=s->length; pthread_mutex_unlock(&s->mu);
        uint64_t sent=0,errors=0;
        for(unsigned i=w->id;i<s->receivers;i+=s->workers) {
            ssize_t n=sendto(s->fd,s->packet,len,0,(struct sockaddr*)&s->addresses[i],sizeof(s->addresses[i]));
            if(n==(ssize_t)len)sent++;else errors++;
        }
        pthread_mutex_lock(&s->mu);s->sent+=sent;s->errors+=errors;
        if(++s->completed==s->workers)pthread_cond_signal(&s->done);
    }
    pthread_mutex_unlock(&s->mu);return NULL;
}
int main(int argc,char **argv) {
    if(argc<4){fprintf(stderr,"usage: fanout workers input_port receiver_port...\n");return 2;}
    char *end;long nw=strtol(argv[1],&end,10);if(*end||nw<0||nw>MAX_WORKERS)return 2;
    long port=strtol(argv[2],&end,10);if(*end||port<0||port>65535||argc-3>MAX_RECEIVERS)return 2;
    struct shared s={0};s.workers=(unsigned)nw;s.receivers=(unsigned)(argc-3);
    if(pthread_mutex_init(&s.mu,NULL)||pthread_cond_init(&s.work,NULL)||pthread_cond_init(&s.done,NULL))return 3;
    s.fd=socket(AF_INET,SOCK_DGRAM,0);if(s.fd<0)return 3;
    struct sockaddr_in addr={0};addr.sin_family=AF_INET;addr.sin_addr.s_addr=htonl(0x7f000001u);addr.sin_port=htons((uint16_t)port);
    if(bind(s.fd,(struct sockaddr*)&addr,sizeof addr))return 3;
    socklen_t alen=sizeof addr;if(getsockname(s.fd,(struct sockaddr*)&addr,&alen))return 3;
    for(unsigned i=0;i<s.receivers;i++) {long p=strtol(argv[i+3],&end,10);if(*end||p<1||p>65535)return 2;s.addresses[i]=addr;s.addresses[i].sin_port=htons((uint16_t)p);}
    signal(SIGINT,signal_stop);signal(SIGTERM,signal_stop);
    pthread_t threads[MAX_WORKERS];struct worker ws[MAX_WORKERS];unsigned started=0;
    for(unsigned i=0;i<s.workers;i++){ws[i]=(struct worker){&s,i};if(pthread_create(&threads[i],NULL,worker_main,&ws[i])){stopping=1;break;}started++;}
    if(started!=s.workers){pthread_mutex_lock(&s.mu);s.stop=1;pthread_cond_broadcast(&s.work);pthread_mutex_unlock(&s.mu);for(unsigned i=0;i<started;i++)pthread_join(threads[i],NULL);close(s.fd);return 3;}
    printf("%u\n",(unsigned)ntohs(addr.sin_port));fflush(stdout);
    while(!stopping){struct pollfd pfd={s.fd,POLLIN,0};int r=poll(&pfd,1,100);if(r<0){if(errno==EINTR)continue;break;}if(!r)continue;
        struct iovec iov={s.packet,MAX_PACKET};struct msghdr msg={0};msg.msg_iov=&iov;msg.msg_iovlen=1;
        ssize_t n=recvmsg(s.fd,&msg,0);if(n<0){if(errno==EINTR)continue;break;}if(msg.msg_flags&MSG_TRUNC)continue;
        if(s.workers==0){
            s.packets++;
            for(unsigned i=0;i<s.receivers;i++){
                ssize_t sent=sendto(s.fd,s.packet,(size_t)n,0,(struct sockaddr*)&s.addresses[i],sizeof(s.addresses[i]));
                if(sent==n)s.sent++;else s.errors++;
            }
            continue;
        }
        pthread_mutex_lock(&s.mu);s.length=(size_t)n;s.completed=0;s.epoch++;s.packets++;pthread_cond_broadcast(&s.work);
        while(s.completed<s.workers)pthread_cond_wait(&s.done,&s.mu);
        pthread_mutex_unlock(&s.mu);
    }
    pthread_mutex_lock(&s.mu);s.stop=1;pthread_cond_broadcast(&s.work);pthread_mutex_unlock(&s.mu);
    for(unsigned i=0;i<started;i++)pthread_join(threads[i],NULL);
    fprintf(stderr,"{\"packets\":%llu,\"sent\":%llu,\"errors\":%llu}\n",(unsigned long long)s.packets,(unsigned long long)s.sent,(unsigned long long)s.errors);
    close(s.fd);pthread_cond_destroy(&s.work);pthread_cond_destroy(&s.done);pthread_mutex_destroy(&s.mu);return 0;
}
