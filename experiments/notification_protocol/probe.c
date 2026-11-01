#define main platform_probe_main
#include "../reactor_wakeup/probe.c"
#undef main
#include "protocol.h"
#define CHECK(x) do {if(!(x)){fprintf(stderr,"check failed line %d\n",__LINE__);abort();}} while(0)
static int ready(protocol *p) {
    poll_item fd;memset(&fd,0,sizeof(fd));fd.fd=p->wake.read_fd;fd.events=READ_EVENT;
#ifdef _WIN32
    int n=WSAPoll(&fd,1,1000);
#else
    int n=poll(&fd,1,1000);
#endif
    return n==1&&(fd.revents&READ_EVENT);
}
typedef struct {protocol *p;atomic_int go;publication result;} race;
static THREAD_RESULT race_publish(void *arg) {
    race *r=arg;while(!atomic_load(&r->go))yield_thread();
    liza_scoped_status why;r->result=publish(r->p,42,&why);THREAD_RETURN;
}
int main(void) {
#ifdef _WIN32
    WSADATA d;CHECK(!WSAStartup(MAKEWORD(2,2),&d));
#endif
    protocol p;uint32_t value=0;int fault=0;liza_scoped_status why;
    CHECK(protocol_init(&p));
    CHECK(take_or_arm(&p,&value,&fault)==CH_EMPTY&&!fault);
    CHECK(publish(&p,10,&why)==PUBLISHED);CHECK(ready(&p));
    CHECK(publish(&p,20,&why)==PUBLISHED);
    CHECK(publish(&p,30,&why)==NOT_PUBLISHED&&why==CH_FULL);
    CHECK(take_or_arm(&p,&value,&fault)==CH_OK&&value==10);
    CHECK(take_or_arm(&p,&value,&fault)==CH_OK&&value==20);
    CHECK(take_or_arm(&p,&value,&fault)==CH_EMPTY&&!fault);
    p.inject_failure=1;CHECK(publish(&p,30,&why)==PUBLISHED_FAULT);
    CHECK(protocol_fault(&p));CHECK(take_or_arm(&p,&value,&fault)==CH_OK&&value==30&&fault);
    CHECK(publish(&p,40,&why)==NOT_PUBLISHED);protocol_destroy(&p);
    for(int i=0;i<100;i++) {
        CHECK(protocol_init(&p));CHECK(take_or_arm(&p,&value,&fault)==CH_EMPTY);
        race r;r.p=&p;r.result=NOT_PUBLISHED;atomic_init(&r.go,0);thread_id t;
        CHECK(thread_start(&t,race_publish,&r));atomic_store(&r.go,1);
        CHECK(protocol_close(&p));CHECK(thread_join(t));CHECK(ready(&p));
        liza_scoped_status s=take_or_arm(&p,&value,&fault);CHECK(!fault);
        if(r.result==PUBLISHED){CHECK(s==CH_OK&&value==42);s=take_or_arm(&p,&value,&fault);}
        else CHECK(r.result==NOT_PUBLISHED);
        CHECK(s==CH_CLOSED);protocol_destroy(&p);
    }
#ifdef _WIN32
    WSACleanup();
#endif
    puts("publication, coalescing, fault integrity, close races and join-before-destroy passed");return 0;
}
