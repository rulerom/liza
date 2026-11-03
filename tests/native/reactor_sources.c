/* Exercise the actual runtime implementation, with existing experimental
 * channel/wake helpers as its caller. No language binding is introduced. */
#define main platform_probe_main
#include "../../experiments/reactor_wakeup/probe.c"
#undef main
#include "../../experiments/notification_protocol/protocol.h"
#include "../../liza/runtime/reactor_common.h"
#define CHECK(x) do {if(!(x)){fprintf(stderr,"failed %s line %d\n",#x,__LINE__);exit(2);}} while(0)
static void pause_one(void) {
#ifdef _WIN32
    Sleep(1);
#else
    struct timespec t={0,1000000};nanosleep(&t,NULL);
#endif
}
typedef struct {
    protocol channel;wakeup control;
    atomic_uint port,calls,returns,commands,network;
    atomic_int waiting,gate,stop,multiple;
    int mode;
} fixture;
static THREAD_RESULT serve(void *ptr) {
    fixture *f=ptr;reactor *r=NULL;CHECK(!liza_rt_reactor_create(0,2,&r));
    uint64_t port=liza_rt_reactor_port(r);CHECK(port&&!(port>>32));atomic_store(&f->port,(unsigned)port);
    uint64_t id[3]={0};int connected=0,closing=0;
    reactor_source sources[2]={{(uint64_t)f->channel.wake.read_fd,0},{(uint64_t)f->control.read_fd,0}};
    for(;;) {
        if(atomic_load(&f->stop)&&!closing){closing=1;(void)protocol_close(&f->channel);}
        uint32_t value=0;int fault=0;
        liza_scoped_status s=take_or_arm(&f->channel,&value,&fault);
        if(s==CH_OK){CHECK(value==42);atomic_fetch_add(&f->commands,1);continue;}
        if(s==CH_CLOSED)break;
        CHECK(s==CH_EMPTY);
        /* Known notification fault is handled by independent control wake.
           Caller has already requested stop in this fault-injection case. */
        atomic_store(&f->waiting,1);
        while(!atomic_load(&f->gate))pause_one();
        atomic_fetch_add(&f->calls,1);
        uint64_t result=liza_rt_reactor_poll_sources(r,-1,sources,2);
        CHECK(!(result>>32)&&result>0);atomic_fetch_add(&f->returns,1);
        CHECK(!(sources[0].ready&4)&&!(sources[1].ready&4));
        if(sources[1].ready&1)CHECK(wake_drain(&f->control));
        if(f->mode==3&&!connected&&(sources[0].ready&1)&&result>=2)atomic_store(&f->multiple,1);
        if(!connected) {
            uint32_t e=liza_rt_reactor_accept(r,id);
            CHECK(e==0||e==4);if(!e)connected=1;
        }
        if(connected&&!atomic_load(&f->network)) {
            uint8_t byte=0;uint64_t got=liza_rt_reactor_read(r,id[0],id[1],id[2],&byte,1,0,1);
            if(!(got>>32)){CHECK(got==1&&byte=='n');atomic_fetch_add(&f->network,1);}
            else CHECK((got>>32)==4);
        }
    }
    if(connected)CHECK(!liza_rt_reactor_disconnect(r,id[0],id[1],id[2]));
    CHECK(!liza_rt_reactor_close(r));THREAD_RETURN;
}
static void wait_uint(atomic_uint *v,unsigned target) {
    uint64_t until=now_ms()+3000;
    while(atomic_load(v)<target){CHECK(now_ms()<until);pause_one();}
}
static void boundary_checks(void) {
    reactor *r=NULL;CHECK(!liza_rt_reactor_create(0,1,&r));
    wakeup w;CHECK(wake_init(&w,0));
    reactor_source sources[3]={{(uint64_t)w.read_fd,99},{(uint64_t)w.read_fd,99},{0,0}};
    CHECK(liza_rt_reactor_poll_sources(r,0,sources,3)==net_failure(6));
    CHECK(liza_rt_reactor_poll_sources(r,0,NULL,1)==net_failure(6));
    CHECK(liza_rt_reactor_poll_sources(r,-2,sources,1)==net_failure(6));CHECK(!sources[0].ready);
    CHECK(liza_rt_reactor_poll_sources(r,0,sources,2)==net_failure(6));
    sources[0].socket=(uint64_t)NET_INVALID;
    CHECK(liza_rt_reactor_poll_sources(r,0,sources,1)==net_failure(6));
    sources[0].socket=r->listener;
    CHECK(liza_rt_reactor_poll_sources(r,0,sources,1)==net_failure(6));
    sources[0].socket=(uint64_t)w.read_fd;
    CHECK(liza_rt_reactor_poll_sources(r,0,sources,1)==0);CHECK(!sources[0].ready);
    CHECK(wake_send(&w));
    CHECK(liza_rt_reactor_poll_sources(r,1000,sources,1)==1);CHECK(sources[0].ready==1);
    /* Runtime must leave token readable until caller resets it. */
    CHECK(liza_rt_reactor_poll_sources(r,0,sources,1)==1);CHECK(wake_drain(&w));
    CHECK(liza_rt_reactor_poll_sources(r,0,sources,1)==0);CHECK(!sources[0].ready);
    CHECK(liza_rt_reactor_poll(r,UINT32_MAX)==net_failure(6));
    CHECK(!liza_rt_reactor_stop_accepting(r));
    CHECK(liza_rt_reactor_poll_sources(r,-1,NULL,0)==net_failure(6));
    CHECK(liza_rt_reactor_poll(r,0)==0);
    CHECK(!liza_rt_reactor_close(r));
    /* Borrowed descriptor survives reactor destruction. */
    CHECK(wake_send(&w));CHECK(wake_drain(&w));wake_close(&w);
    puts("boundary validation, readiness reset, borrowed ownership passed");
}
int main(int argc,char **argv) {
    CHECK(argc==2);
#ifdef _WIN32
    WSADATA data;CHECK(!WSAStartup(MAKEWORD(2,2),&data));
#endif
    if(!strcmp(argv[1],"boundary")){boundary_checks();return 0;}
    fixture f;memset(&f,0,sizeof(f));
    const char *names[]={"idle","command","network","both","fault"};f.mode=-1;
    for(int i=0;i<5;i++)if(!strcmp(argv[1],names[i]))f.mode=i;
    CHECK(f.mode>=0);CHECK(protocol_init(&f.channel));CHECK(wake_init(&f.control,0));
    atomic_init(&f.port,0);atomic_init(&f.calls,0);atomic_init(&f.returns,0);
    atomic_init(&f.commands,0);atomic_init(&f.network,0);atomic_init(&f.waiting,0);
    atomic_init(&f.gate,0);atomic_init(&f.stop,0);atomic_init(&f.multiple,0);
    thread_id worker;CHECK(thread_start(&worker,serve,&f));
    uint64_t until=now_ms()+3000;
    while(!atomic_load(&f.waiting)){CHECK(now_ms()<until);pause_one();}
    sock_t client=BAD_SOCKET;
    if(f.mode==2||f.mode==3) {
        client=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);CHECK(client!=BAD_SOCKET);
        struct sockaddr_in a;memset(&a,0,sizeof(a));a.sin_family=AF_INET;
        a.sin_addr.s_addr=htonl(0x7f000001u);a.sin_port=htons((uint16_t)atomic_load(&f.port));
        CHECK(!connect(client,(struct sockaddr*)&a,sizeof(a)));CHECK(send(client,"n",1,0)==1);
    }
    if(f.mode==1||f.mode==3||f.mode==4) {
        if(f.mode==4){enter(&f.channel);f.channel.inject_failure=1;leave(&f.channel);}
        liza_scoped_status why;
        CHECK(publish(&f.channel,42,&why)==(f.mode==4?PUBLISHED_FAULT:PUBLISHED));CHECK(why==CH_OK);
    }
    if(f.mode==3) {
        /* Confirm transport readiness without consuming it before opening gate. */
        poll_item fd;memset(&fd,0,sizeof(fd));fd.fd=f.channel.wake.read_fd;fd.events=READ_EVENT;
#ifdef _WIN32
        CHECK(WSAPoll(&fd,1,1000)==1);
#else
        CHECK(poll(&fd,1,1000)==1);
#endif
        CHECK(fd.revents&READ_EVENT);
    }
    atomic_store(&f.gate,1);
    if(f.mode==0) {
        wait_uint(&f.calls,1);uint64_t start=now_ms();
        while(now_ms()-start<750)pause_one();
        CHECK(atomic_load(&f.calls)==1&&atomic_load(&f.returns)==0);
    }
    if(f.mode==1||f.mode==3)wait_uint(&f.commands,1);
    if(f.mode==2||f.mode==3)wait_uint(&f.network,1);
    atomic_store(&f.stop,1);CHECK(wake_send(&f.control));
    CHECK(thread_join(worker));
    CHECK(atomic_load(&f.commands)==(unsigned)(f.mode==1||f.mode==3||f.mode==4));
    CHECK(atomic_load(&f.network)==(unsigned)(f.mode==2||f.mode==3));
    if(f.mode==3)CHECK(atomic_load(&f.multiple));
    if(f.mode==0)CHECK(atomic_load(&f.calls)==1&&atomic_load(&f.returns)==1);
    CHECK(protocol_fault(&f.channel)==(f.mode==4));
    liza_scoped_status reason;CHECK(publish(&f.channel,99,&reason)==NOT_PUBLISHED);
    /* No thread can access shared protocol/control resources after join. */
    protocol_destroy(&f.channel);wake_close(&f.control);
    if(client!=BAD_SOCKET)CHECK(!close_socket(client));
    printf("%s calls=%u returns=%u commands=%u network=%u joined-before-destroy\n",argv[1],atomic_load(&f.calls),atomic_load(&f.returns),atomic_load(&f.commands),atomic_load(&f.network));
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}
