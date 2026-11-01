#define main prior_probe_main
#include "../reactor_wakeup/probe.c"
#undef main
#include "../notification_protocol/protocol.h"
#include "../sg0/status.h"

enum group_state { STARTING, RUNNING, STARTUP_FAILED, FAULTED, GROUP_STOPPING, UNRESPONSIVE, STOPPED, PROCESS_ABORT };
enum { EV_RUNNING=1, EV_STARTUP_FAILED, EV_WORKER_EXIT, EV_SUPERVISOR_EXIT,
       EV_WORKER_JOIN, EV_SUPERVISOR_JOIN, EV_FAULT, EV_STOPPING, EV_UNRESPONSIVE,
       EV_RETAINED, EV_STOPPED, EV_DESTROY, EV_ABORT, EV_PRODUCER_EXIT, EV_PRODUCER_JOIN, EV_NETWORK_CLOSE };
static const char *event_names[]={"invalid","running","startup_failed","worker_exit","supervisor_exit",
    "worker_join","supervisor_join","faulted","stopping","unresponsive","retained","stopped","destroy","process_abort","producer_exit","producer_join","network_close"};
/* Process-lifetime journal and join service: neither holds a group pointer. */
static double cpu_ms(int thread) {
#ifdef _WIN32
    FILETIME created,exited,kernel,user;
    int ok=thread?GetThreadTimes(GetCurrentThread(),&created,&exited,&kernel,&user):
                  GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user);
    if(!ok)abort();
    ULARGE_INTEGER k,u;k.LowPart=kernel.dwLowDateTime;k.HighPart=kernel.dwHighDateTime;
    u.LowPart=user.dwLowDateTime;u.HighPart=user.dwHighDateTime;
    return (double)(k.QuadPart+u.QuadPart)/10000.0;
#else
    struct timespec t;
    if(clock_gettime(thread?CLOCK_THREAD_CPUTIME_ID:CLOCK_PROCESS_CPUTIME_ID,&t))abort();
    return (double)t.tv_sec*1000.0+(double)t.tv_nsec/1000000.0;
#endif
}
static atomic_uint event_count;
static atomic_int events[128];
static void event(int kind) {
    unsigned slot=atomic_fetch_add(&event_count,1);if(slot>=128)abort();
    atomic_store(&events[slot],kind);
}
static void dump_events(void) {
    unsigned n=atomic_load(&event_count);if(n>128)abort();
    for(unsigned i=0;i<n;i++){int e=atomic_load(&events[i]);if(!e)abort();printf("%u %s\n",i,event_names[e]);}
}
static void pause_ms(unsigned ms) {
#ifdef _WIN32
    Sleep(ms);
#else
    struct timespec t={(time_t)(ms/1000),(long)(ms%1000)*1000000};
    while(nanosleep(&t,&t)&&errno==EINTR){}
#endif
}
#define REQUIRE(x) do {if(!(x)){fprintf(stderr,"check failed: %s at %d\n",#x,__LINE__);exit(2);}} while(0)
typedef struct {
    protocol p;wakeup control;
    status_record worker, supervisor;
    atomic_int gate, release, supervisor_release, shutdown, monitor_stop, fault_code;
    atomic_int worker_started, worker_waiting, supervisor_started, callbacks, worker_overdue;
    atomic_uint received;
    atomic_int producer_admitted,producer_release,fault_observed;
    atomic_uint_fast64_t shutdown_deadline, delivery_deadline;
    /* Socket belongs exclusively to worker. Owner receives only its address. */
    struct sockaddr_in network_address;
    atomic_int network_ready, poll_gate;
    atomic_uint network_received, poll_calls, poll_returns;
    double worker_cpu_ms;
    uint64_t worker_wall_ms;
    int mode;
} group;
enum { NORMAL, IDLE_TEST, NOTIFY_FAULT, MUTEX_STALL, SUPERVISOR_STALL, START_FAIL, ABORT_TEST, SNAPSHOT_TEST, STALE_IDLE, ADMISSION_RACE, ODD_SNAPSHOT, START_FAIL_FIRST, NETWORK_ONLY, SIMULTANEOUS };
typedef struct {thread_id worker,supervisor,producer;int have_worker,have_supervisor,have_producer;atomic_int worker_joined,supervisor_joined,producer_joined,done;} join_service;
static join_service joins;
static THREAD_RESULT reaper(void *unused) {
    (void)unused;
    if(joins.have_producer){if(!thread_join(joins.producer))abort();event(EV_PRODUCER_JOIN);atomic_store(&joins.producer_joined,1);}
    if(joins.have_worker){if(!thread_join(joins.worker))abort();event(EV_WORKER_JOIN);atomic_store(&joins.worker_joined,1);}
    if(joins.have_supervisor){if(!thread_join(joins.supervisor))abort();event(EV_SUPERVISOR_JOIN);atomic_store(&joins.supervisor_joined,1);}
    atomic_store(&joins.done,1);THREAD_RETURN;
}
static void start_reaper(void) {
    thread_id t;REQUIRE(thread_start(&t,reaper,NULL));
#ifdef _WIN32
    REQUIRE(CloseHandle(t));
#else
    REQUIRE(pthread_detach(t)==0);
#endif
}
static int all_joined(void) {
    return (!joins.have_producer||atomic_load(&joins.producer_joined))&&
           (!joins.have_worker||atomic_load(&joins.worker_joined))&&
           (!joins.have_supervisor||atomic_load(&joins.supervisor_joined));
}
static int release_allowed(enum group_state state) {
#ifdef SG_BROKEN_RELEASE
    return state==UNRESPONSIVE||all_joined();
#else
    return state==STOPPED&&all_joined();
#endif
}
static void set_fault(group *g,int code) {int zero=0;atomic_compare_exchange_strong(&g->fault_code,&zero,code);}
static void publish_status(group *g,status_record *r,status_value v) {
    if(!status_write(r,v)){set_fault(g,2);}
}
/* Admission is linearized at the shutdown load under protocol lock. A send
   admitted before the request may commit afterward; worker closes under the
   same lock before drain, so no admitted publication can be skipped. */
static publication group_send(group *g,uint32_t value) {
    enter(&g->p);
    if(atomic_load(&g->shutdown)||g->p.fault){leave(&g->p);return NOT_PUBLISHED;}
    if(g->mode==ADMISSION_RACE){atomic_store(&g->producer_admitted,1);while(!atomic_load(&g->producer_release))pause_ms(1);}
    atomic_store(&g->delivery_deadline,now_ms()+500);
    liza_scoped_status s=liza_scoped_send(g->p.fifo,value);
    publication result=NOT_PUBLISHED;
    if(s==CH_OK){result=notify_locked(&g->p)?PUBLISHED:PUBLISHED_FAULT;if(result==PUBLISHED_FAULT)set_fault(g,1);}
    else atomic_store(&g->delivery_deadline,0);
    leave(&g->p);return result;
}
/* A minimal experimental reactor: one owner and one OS wait for all sources.
   No production Liza reactor API or fallback periodic timeout is used. */
static int wait_control(group *g,sock_t network) {
    poll_item fds[3];memset(fds,0,sizeof(fds));
    fds[0].fd=g->p.wake.read_fd;fds[0].events=READ_EVENT;
    fds[1].fd=g->control.read_fd;fds[1].events=READ_EVENT;
    fds[2].fd=network;fds[2].events=READ_EVENT;
    atomic_store(&g->worker_waiting,1);
    if(g->mode==SIMULTANEOUS)
        while(!atomic_load(&g->poll_gate))pause_ms(1);
    atomic_fetch_add(&g->poll_calls,1);
#ifdef _WIN32
    int n=WSAPoll(fds,3,-1);
#else
    int n=poll(fds,3,-1);
    if(n<0&&errno==EINTR)return 1;
#endif
    atomic_fetch_add(&g->poll_returns,1);
    if(n<=0||((fds[0].revents|fds[1].revents|fds[2].revents)&(POLLERR|POLLHUP|POLLNVAL))) {
        set_fault(g,3);return 0;
    }
    if(fds[1].revents&READ_EVENT)REQUIRE(wake_drain(&g->control));
    if(fds[2].revents&READ_EVENT) {
        char byte=0;REQUIRE(recv(network,&byte,1,0)==1&&byte=='n');
        atomic_fetch_add(&g->network_received,1);
    }
    return 1;
}
static sock_t open_network(group *g) {
    sock_t fd=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);REQUIRE(fd!=BAD_SOCKET);
    memset(&g->network_address,0,sizeof(g->network_address));
    g->network_address.sin_family=AF_INET;
    g->network_address.sin_addr.s_addr=htonl(0x7f000001u);
    REQUIRE(bind(fd,(struct sockaddr*)&g->network_address,sizeof(g->network_address))==0);
#ifdef _WIN32
    int length=sizeof(g->network_address);
#else
    socklen_t length=sizeof(g->network_address);
#endif
    REQUIRE(getsockname(fd,(struct sockaddr*)&g->network_address,&length)==0);
    REQUIRE(nonblock(fd));atomic_store(&g->network_ready,1);return fd;
}
static void worker_callback(group *g,sock_t network) {
    atomic_fetch_add(&g->callbacks,1);atomic_store(&g->worker_started,1);
    if(g->mode==MUTEX_STALL||g->mode==ABORT_TEST) {
        publish_status(g,&g->worker,(status_value){BUSY,1,now_ms()+500,0});
        enter(&g->p);atomic_store(&g->worker_started,2);
        while(!atomic_load(&g->release))pause_ms(1);
        leave(&g->p);
    }
    if(g->mode==ODD_SNAPSHOT) {
        atomic_store(&g->worker.version,1);atomic_store(&g->worker.state,BUSY);
        while(!atomic_load(&g->release))pause_ms(1);
        atomic_store(&g->worker.state,IDLE);atomic_store(&g->worker.version,2);
    }
    if(g->mode==STALE_IDLE) {
        while(!atomic_load(&g->release))pause_ms(1);
    }
    uint64_t epoch=0;int closing=0;
    for(;;) {
        if(atomic_load(&g->shutdown)&&!closing) {
            closing=1;publish_status(g,&g->worker,(status_value){STOPPING,0,atomic_load(&g->shutdown_deadline),epoch});
            (void)protocol_close(&g->p);
        }
        #ifdef SG1_SKIP_RECHECK
        /* Bad reset after network dispatch: consumes signal then sleeps without FIFO inspection. */
        if(!closing&&atomic_load(&g->network_received)) {
            REQUIRE(wake_drain(&g->p.wake));
            if(!wait_control(g,network))return;
            continue;
        }
#endif
        uint32_t value=0;int fault=0;liza_scoped_status s=take_or_arm(&g->p,&value,&fault);
        if(fault)set_fault(g,1);
        if(s==CH_OK){REQUIRE(value==42);atomic_fetch_add(&g->received,1);atomic_store(&g->delivery_deadline,0);epoch++;continue;}
        if(s==CH_CLOSED)return;
        REQUIRE(s==CH_EMPTY);
        if(!closing)publish_status(g,&g->worker,(status_value){IDLE,0,0,epoch});
        if(!wait_control(g,network))return;
    }
}
static THREAD_RESULT worker_entry(void *ptr) {
    group *g=ptr;while(!atomic_load(&g->gate))pause_ms(1);
    if(atomic_load(&g->gate)>0) {
        sock_t network=open_network(g);double cpu=cpu_ms(1);uint64_t wall=now_ms();
        worker_callback(g,network);
        g->worker_cpu_ms=cpu_ms(1)-cpu;g->worker_wall_ms=now_ms()-wall;
        REQUIRE(close_socket(network)==0);event(EV_NETWORK_CLOSE);
    }
    publish_status(g,&g->worker,(status_value){EXITED,0,0,0});event(EV_WORKER_EXIT);THREAD_RETURN;
}
static THREAD_RESULT supervisor_entry(void *ptr) {
    group *g=ptr;while(!atomic_load(&g->gate))pause_ms(1);
    if(atomic_load(&g->gate)>0) {
        atomic_store(&g->supervisor_started,1);uint64_t epoch=0,unavailable_since=0;
        while(!atomic_load(&g->monitor_stop)) {
            publish_status(g,&g->supervisor,(status_value){BUSY,epoch+1,now_ms()+500,epoch});
            if(g->mode==SUPERVISOR_STALL)while(!atomic_load(&g->supervisor_release))pause_ms(1);
            if(atomic_load(&g->fault_code))atomic_store(&g->fault_observed,1);
            status_value v;uint64_t now=now_ms();
            if(status_read(&g->worker,&v)) {
                unavailable_since=0;
                if(overdue(v,now))atomic_store(&g->worker_overdue,1);
            } else {if(!unavailable_since)unavailable_since=now;if(now-unavailable_since>=500)atomic_store(&g->worker_overdue,1);}
            uint64_t delivery=atomic_load(&g->delivery_deadline);
            if(delivery&&now>=delivery)atomic_store(&g->worker_overdue,1);
            /* Completed a scan, not a claim of worker application progress. */
            if(epoch==UINT64_MAX-1){set_fault(g,2);break;}epoch++;pause_ms(2);
        }
    }
    publish_status(g,&g->supervisor,(status_value){EXITED,0,0,0});event(EV_SUPERVISOR_EXIT);THREAD_RETURN;
}
typedef struct {status_record record;atomic_int stage,release;} snapshot_test;
static THREAD_RESULT snapshot_writer(void *ptr) {
    snapshot_test *t=ptr;
    atomic_store(&t->record.version,1);atomic_store(&t->record.state,BUSY);
    atomic_store(&t->stage,1);
    while(!atomic_load(&t->release))pause_ms(1);
    atomic_store(&t->record.obligation,7);atomic_store(&t->record.deadline,1000);
    atomic_store(&t->record.epoch,3);atomic_store(&t->record.version,2);THREAD_RETURN;
}
static void check_snapshot(void) {
    snapshot_test t;status_init(&t.record);atomic_init(&t.stage,0);atomic_init(&t.release,0);
    thread_id writer;REQUIRE(thread_start(&writer,snapshot_writer,&t));
    while(!atomic_load(&t.stage))pause_ms(1);
    status_value v;int accepted=status_read(&t.record,&v);
    int false_timeout=accepted&&overdue(v,500);
    atomic_store(&t.release,1);REQUIRE(thread_join(writer));
    REQUIRE(!false_timeout);REQUIRE(!accepted);
    REQUIRE(status_read(&t.record,&v)&&v.state==BUSY&&v.deadline==1000&&v.obligation==7&&v.epoch==3);
    REQUIRE(!overdue(v,500));v.epoch=4;REQUIRE(status_write(&t.record,v));
    REQUIRE(status_read(&t.record,&v)&&overdue(v,1000));
    atomic_store(&t.record.version,UINT64_MAX-1);REQUIRE(!status_write(&t.record,v));
    REQUIRE(atomic_load(&t.record.version)==UINT64_MAX-1);
    puts("snapshot_consistent bounded_retry deadline_preserved overflow_rejected");
}
static THREAD_RESULT producer_entry(void *ptr) {
    group *g=ptr;while(!atomic_load(&g->gate))pause_ms(1);
    if(atomic_load(&g->gate)>0){while(!atomic_load(&g->worker_waiting))pause_ms(1);REQUIRE(group_send(g,42)==PUBLISHED);}
    event(EV_PRODUCER_EXIT);THREAD_RETURN;
}
static void request_stop(group *g) {
    if(atomic_load(&g->shutdown))return;
    atomic_store(&g->shutdown_deadline,now_ms()+500);
    atomic_store(&g->shutdown,1);
    #ifndef SG1_DROP_SHUTDOWN
    if(!wake_send(&g->control))set_fault(g,3);
#endif
}
static void init_group(group *g,int mode) {
    memset(g,0,sizeof(*g));g->mode=mode;
    status_init(&g->worker);status_init(&g->supervisor);
    atomic_init(&g->gate,0);atomic_init(&g->release,0);atomic_init(&g->supervisor_release,0);
    atomic_init(&g->shutdown,0);atomic_init(&g->monitor_stop,0);atomic_init(&g->fault_code,0);
    atomic_init(&g->worker_started,0);atomic_init(&g->worker_waiting,0);atomic_init(&g->supervisor_started,0);
    atomic_init(&g->callbacks,0);atomic_init(&g->worker_overdue,0);atomic_init(&g->received,0);
    atomic_init(&g->fault_observed,0);atomic_init(&g->producer_admitted,0);atomic_init(&g->producer_release,0);
    atomic_init(&g->network_ready,0);atomic_init(&g->poll_gate,0);
    atomic_init(&g->network_received,0);atomic_init(&g->poll_calls,0);atomic_init(&g->poll_returns,0);
    atomic_init(&g->shutdown_deadline,0);atomic_init(&g->delivery_deadline,0);
    REQUIRE(atomic_is_lock_free(&g->worker.version));
    REQUIRE(protocol_init(&g->p));
    if(!wake_init(&g->control,0)){protocol_destroy(&g->p);REQUIRE(0);}
    if(mode==NOTIFY_FAULT)g->p.inject_failure=1;
}
static int mode_for(const char *s) {
    const char *names[]={"normal","idle","fault","mutex_stall","supervisor_stall","startup_fail","abort","snapshot","stale_idle","admission_race","snapshot_stall","startup_fail_first","network","simultaneous"};
    for(int i=0;i<14;i++)if(!strcmp(s,names[i]))return i;
    return -1;
}
int main(int argc,char **argv) {
    REQUIRE(argc==2);int mode=mode_for(argv[1]);REQUIRE(mode>=0);
    if(mode==SNAPSHOT_TEST){check_snapshot();return 0;}
#ifdef _WIN32
    WSADATA d;REQUIRE(WSAStartup(MAKEWORD(2,2),&d)==0);
#endif
    atomic_init(&event_count,0);for(unsigned i=0;i<128;i++)atomic_init(&events[i],0);
    memset(&joins,0,sizeof(joins));atomic_init(&joins.worker_joined,0);atomic_init(&joins.supervisor_joined,0);atomic_init(&joins.done,0);atomic_init(&joins.producer_joined,0);
    group *g=malloc(sizeof(*g));REQUIRE(g);init_group(g,mode);
    enum group_state state=STARTING;unsigned free_count=0;
    joins.have_worker=mode!=START_FAIL_FIRST&&thread_start(&joins.worker,worker_entry,g);
    /* Deterministic failure of second creation, before opening start gate. */
    joins.have_supervisor=joins.have_worker&&mode!=START_FAIL&&thread_start(&joins.supervisor,supervisor_entry,g);
    if(mode==ADMISSION_RACE&&joins.have_supervisor)joins.have_producer=thread_start(&joins.producer,producer_entry,g);
    if(!joins.have_supervisor||(mode==ADMISSION_RACE&&!joins.have_producer)){state=STARTUP_FAILED;event(EV_STARTUP_FAILED);atomic_store(&g->gate,-1);}
    else {state=RUNNING;event(EV_RUNNING);atomic_store(&g->gate,1);}
    start_reaper();uint64_t start=now_ms(),unresponsive_since=0;int sent=0,saw_fault=0,saw_unresponsive=0;
    uint64_t idle_since=0;
    uint64_t supervisor_missing=0;int released=0,network_sent=0;double process_cpu=cpu_ms(0);
    while(!all_joined()) {
        uint64_t now=now_ms();
        if(now-start>5000){event(EV_ABORT);dump_events();fflush(stdout);_Exit(86);}
        if(state!=STARTUP_FAILED) {
            if(mode==IDLE_TEST&&!idle_since&&atomic_load(&g->poll_calls))idle_since=now;
            if(!network_sent&&(mode==NETWORK_ONLY||mode==SIMULTANEOUS)&&atomic_load(&g->worker_waiting)) {
                REQUIRE(atomic_load(&g->network_ready));
                sock_t sender=socket(AF_INET,SOCK_DGRAM,IPPROTO_UDP);REQUIRE(sender!=BAD_SOCKET);
                REQUIRE(sendto(sender,"n",1,0,(struct sockaddr*)&g->network_address,sizeof(g->network_address))==1);
                REQUIRE(close_socket(sender)==0);network_sent=1;
                if(mode==SIMULTANEOUS){REQUIRE(group_send(g,42)==PUBLISHED);sent=1;}
                atomic_store(&g->poll_gate,1);
            }
            if(!sent&&(mode==NORMAL||mode==NOTIFY_FAULT||mode==STALE_IDLE)&&
               (atomic_load(&g->worker_waiting)||(mode==STALE_IDLE&&atomic_load(&g->worker_started)))) {
                publication result=group_send(g,42);REQUIRE(result==(mode==NOTIFY_FAULT?PUBLISHED_FAULT:PUBLISHED));sent=1;
            }
            if(mode==ADMISSION_RACE&&atomic_load(&g->producer_admitted)&&!atomic_load(&g->shutdown)) {
                request_stop(g);uint64_t d=atomic_load(&g->shutdown_deadline);request_stop(g);REQUIRE(d==atomic_load(&g->shutdown_deadline));
                state=GROUP_STOPPING;event(EV_STOPPING);atomic_store(&g->producer_release,1);
            }
            if(atomic_load(&g->fault_observed)&&!saw_fault){saw_fault=1;state=FAULTED;event(EV_FAULT);request_stop(g);state=GROUP_STOPPING;event(EV_STOPPING);}
            if((mode==NORMAL||mode==IDLE_TEST||mode==NETWORK_ONLY||mode==SIMULTANEOUS)&&atomic_load(&g->worker_waiting)&&(mode!=NORMAL||atomic_load(&g->received)==1)&&(mode!=NETWORK_ONLY||atomic_load(&g->network_received)==1)&&
               (mode!=SIMULTANEOUS||(atomic_load(&g->network_received)==1&&atomic_load(&g->received)==1))&&
               (mode==IDLE_TEST?(idle_since&&now-idle_since>=750):now-start>=750)&&!atomic_load(&g->shutdown)) {
                REQUIRE(!atomic_load(&g->worker_overdue));
                if(mode==IDLE_TEST){REQUIRE(atomic_load(&g->poll_calls)==1);REQUIRE(atomic_load(&g->poll_returns)==0);}
                request_stop(g);state=GROUP_STOPPING;event(EV_STOPPING);
            }
            status_value sv;int sup_bad=0;
            if(status_read(&g->supervisor,&sv)){supervisor_missing=0;sup_bad=overdue(sv,now);}
            else {if(!supervisor_missing)supervisor_missing=now;sup_bad=now-supervisor_missing>=500;}
            uint64_t deadline=atomic_load(&g->shutdown_deadline);
            int late=(deadline&&now>=deadline&&!all_joined());
            if(now-start>=1000&&(!atomic_load(&g->worker_started)||!atomic_load(&g->supervisor_started)))sup_bad=1;
            if(!saw_unresponsive&&(atomic_load(&g->worker_overdue)||sup_bad||late)) {
                if(mode==MUTEX_STALL||mode==ABORT_TEST)REQUIRE(atomic_load(&g->worker_started)==2);
                saw_unresponsive=1;state=UNRESPONSIVE;unresponsive_since=now;event(EV_UNRESPONSIVE);
#ifdef SG_BROKEN_STOPPED
                state=STOPPED;
#endif
                REQUIRE(state!=STOPPED);REQUIRE(!release_allowed(state));REQUIRE(free_count==0);event(EV_RETAINED);
                request_stop(g);
            }
#if defined(SG1_DROP_SHUTDOWN) || defined(SG1_SKIP_RECHECK)
            REQUIRE(!saw_unresponsive); /* Explicit counterexample, before process timeout. */
#endif
            if(saw_unresponsive&&!released&&now-unresponsive_since>=150) {
                REQUIRE(!all_joined());REQUIRE(!release_allowed(state));REQUIRE(free_count==0);
                if(mode==ABORT_TEST){event(EV_ABORT);dump_events();fflush(stdout);_Exit(86);}
                atomic_store(&g->release,1);atomic_store(&g->supervisor_release,1);released=1;
                state=GROUP_STOPPING;event(EV_STOPPING);
            }
            /* Supervisor continues until worker really joined, not just Exited. */
            if(atomic_load(&joins.worker_joined))atomic_store(&g->monitor_stop,1);
        }
        pause_ms(1);
    }
    if(mode==MUTEX_STALL||mode==SUPERVISOR_STALL||mode==STALE_IDLE||mode==ODD_SNAPSHOT)REQUIRE(saw_unresponsive);
    if(mode==NORMAL||mode==IDLE_TEST||mode==ADMISSION_RACE||mode==NETWORK_ONLY||mode==SIMULTANEOUS)REQUIRE(!saw_unresponsive);
    if(mode==NOTIFY_FAULT)REQUIRE(saw_fault&&atomic_load(&g->received)==1);
    if(mode==START_FAIL||mode==START_FAIL_FIRST)REQUIRE(atomic_load(&g->callbacks)==0);
    if(mode==NORMAL||mode==STALE_IDLE||mode==ADMISSION_RACE)REQUIRE(atomic_load(&g->received)==1);
    REQUIRE(protocol_fault(&g->p)==(mode==NOTIFY_FAULT));
    if(mode!=START_FAIL&&mode!=START_FAIL_FIRST){liza_scoped_status why;REQUIRE(publish(&g->p,99,&why)==NOT_PUBLISHED);}
    if(mode==NETWORK_ONLY||mode==SIMULTANEOUS)REQUIRE(atomic_load(&g->network_received)==1);
    if(mode==SIMULTANEOUS)REQUIRE(atomic_load(&g->received)==1);
    if(mode==IDLE_TEST)REQUIRE(atomic_load(&g->poll_calls)==1&&atomic_load(&g->poll_returns)==1);
    printf("metrics wall_ms=%llu worker_cpu_ms=%.3f process_cpu_ms=%.3f poll_calls=%u poll_returns=%u network=%u commands=%u\n",
        (unsigned long long)g->worker_wall_ms,g->worker_cpu_ms,cpu_ms(0)-process_cpu,
        atomic_load(&g->poll_calls),atomic_load(&g->poll_returns),atomic_load(&g->network_received),atomic_load(&g->received));
    state=STOPPED;REQUIRE(release_allowed(state));event(EV_STOPPED);
    protocol_destroy(&g->p);wake_close(&g->control);free_count++;event(EV_DESTROY);free(g);
    REQUIRE(free_count==1);dump_events();puts("free_count=1");
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}
