#define main platform_main
#include "experiments/reactor_wakeup/probe.c"
#undef main
#define PROTOCOL_TRACE(p, op, value, result, reason) printf("%s %u %d %d %d %d %d\n",op,(unsigned)(value),(int)(result),(int)(reason),(p)->armed,(p)->pending,(p)->fault)
#include "protocol.h"
static void start(protocol *p) {if(!protocol_init(p))abort();puts("start");}
static void take(protocol *p) {uint32_t v=0;int f=0;(void)take_or_arm(p,&v,&f);}
static void send_value(protocol *p,uint32_t v) {liza_scoped_status why;(void)publish(p,v,&why);}
static void readiness(protocol *p) {
    poll_item fd;memset(&fd,0,sizeof(fd));fd.fd=p->wake.read_fd;fd.events=READ_EVENT;
#ifdef _WIN32
    int n=WSAPoll(&fd,1,500);
#else
    int n=poll(&fd,1,500);
#endif
    printf("ready %d\n",n>0&&(fd.revents&READ_EVENT)!=0);
}
static THREAD_RESULT sender(void *p) {send_value(p,42);THREAD_RETURN;}
int main(void) {
#ifdef _WIN32
    WSADATA d;if(WSAStartup(MAKEWORD(2,2),&d))return 2;
#endif
    protocol p;
    start(&p);take(&p);send_value(&p,10);readiness(&p);send_value(&p,20);
    send_value(&p,30);take(&p);take(&p);take(&p);(void)protocol_close(&p);readiness(&p);take(&p);protocol_destroy(&p);
    start(&p);take(&p);p.inject_failure=1;puts("inject");send_value(&p,30);
    printf("fault %d\n",protocol_fault(&p));take(&p);send_value(&p,40);protocol_destroy(&p);
    for(int i=0;i<30;i++) {
        start(&p);take(&p);thread_id t;if(!thread_start(&t,sender,&p))abort();
        (void)protocol_close(&p);if(!thread_join(t))abort();readiness(&p);take(&p);take(&p);protocol_destroy(&p);
    }
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}
