/* Reuse the previous probe's portable socket/thread helpers, not its protocol. */
#define main previous_probe_main
#include "../reactor_wakeup/probe.c"
#undef main

enum { BEFORE_POLL, DURING_RESET, SIGNAL_FAILURE };
typedef struct {
    channel *queue;
    wakeup data, control;
    atomic_int stage, failed, fault, observed;
    int scenario, mutation;
} test_case;

static int wait_stage(atomic_int *stage, int target) {
    uint64_t limit=now_ms()+5000;
    while(atomic_load(stage)<target) { if(now_ms()>=limit)return 0; yield_thread(); }
    return 1;
}
static int readable(wakeup *w, int timeout) {
    poll_item p;memset(&p,0,sizeof(p));p.fd=w->read_fd;p.events=READ_EVENT;
#ifdef _WIN32
    int n=WSAPoll(&p,1,timeout);
#else
    int n=poll(&p,1,timeout);
#endif
    return n==1 && (p.revents&READ_EVENT)!=0;
}
static THREAD_RESULT consumer(void *arg) {
    test_case *t=arg; uint32_t value=0;
    if(t->scenario==DURING_RESET) {
        if(!readable(&t->data,2000)||!wake_drain(&t->data))goto fail;
    } else if(liza_scoped_receive(t->queue,&value)!=CH_EMPTY)goto fail;
    /* BEFORE_POLL: after empty check; DURING_RESET: after consuming old token. */
    atomic_store(&t->stage,1);
    if(!wait_stage(&t->stage,2))goto fail;
    if(t->scenario!=DURING_RESET) {
        if(!readable(&t->data,500)||!wake_drain(&t->data))goto fail;
    } else if(t->mutation==2) {
        /* Broken consumer fails to recheck FIFO after resetting old token. */
        if(!readable(&t->data,500)||!wake_drain(&t->data))goto fail;
        if(!readable(&t->data,100))goto fail;
    }
    if(liza_scoped_receive(t->queue,&value)!=CH_OK||value!=10)goto fail;
    if(t->scenario==DURING_RESET && (liza_scoped_receive(t->queue,&value)!=CH_OK||value!=20))goto fail;
    if(liza_scoped_receive(t->queue,&value)!=CH_EMPTY)goto fail;
    atomic_store(&t->stage,3);THREAD_RETURN;
fail:
    atomic_store(&t->failed,1);atomic_store(&t->stage,3);THREAD_RETURN;
}
static THREAD_RESULT supervisor(void *arg) {
    test_case *t=arg;
    if(!readable(&t->control,2000)||!wake_drain(&t->control)||!atomic_load(&t->fault)) {
        atomic_store(&t->failed,1);THREAD_RETURN;
    }
    atomic_store(&t->observed,1);THREAD_RETURN;
}
static int run_refinement(int scenario,int mutation) {
    test_case t;memset(&t,0,sizeof(t));t.scenario=scenario;t.mutation=mutation;
    t.data.read_fd=t.data.write_fd=t.control.read_fd=t.control.write_fd=BAD_SOCKET;
    atomic_init(&t.stage,0);atomic_init(&t.failed,0);atomic_init(&t.fault,0);atomic_init(&t.observed,0);
    size_t bytes=0;thread_id c,s;int c_started=0,s_started=0,result=1;
    if(liza_scoped_create(2,1024,&t.queue,&bytes)!=CH_OK||!wake_init(&t.data,0)||!wake_init(&t.control,0))goto done;
    if(scenario==DURING_RESET && (liza_scoped_send(t.queue,10)!=CH_OK||!wake_send(&t.data)))goto done;
    if(scenario==SIGNAL_FAILURE){if(!thread_start(&s,supervisor,&t))goto done;s_started=1;}
    if(!thread_start(&c,consumer,&t))goto done;c_started=1;
    if(!wait_stage(&t.stage,1))goto release;
    if(liza_scoped_send(t.queue,scenario==DURING_RESET?20:10)!=CH_OK)goto release;
    if(scenario==SIGNAL_FAILURE) {
        /* Inject data-wake failure after publication. Control is independent. */
        atomic_store(&t.fault,1);
        if(!wake_send(&t.control))goto release;
        if(!thread_join(s))abort();s_started=0;
        if(!atomic_load(&t.observed))goto release;
        /* Test cleanup only; independent supervision did not wake the consumer. */
        if(!wake_send(&t.data))goto release;
    } else if(mutation!=1 && !wake_send(&t.data))goto release;
    atomic_store(&t.stage,2);
    if(!thread_join(c))abort();c_started=0;
    if(!atomic_load(&t.failed) && (scenario!=SIGNAL_FAILURE||atomic_load(&t.observed))) {
        uint32_t value=0;
        /* Drain remaining token before separately checking close notification. */
        if(!wake_drain(&t.data))goto done;
        liza_scoped_close_sender(t.queue);
        if(!wake_send(&t.data)||!readable(&t.data,500)||!wake_drain(&t.data)||liza_scoped_receive(t.queue,&value)!=CH_CLOSED)goto done;
        result=0;
    }
    goto done;
release:
    atomic_store(&t.stage,2);(void)wake_send(&t.data);(void)wake_send(&t.control);
done:
    if(c_started&&!thread_join(c))abort();
    if(s_started&&!thread_join(s))abort();
    if(t.queue)liza_scoped_destroy(t.queue);
    wake_close(&t.data);wake_close(&t.control);
    printf("scenario=%d mutation=%d result=%d fault_observed=%d\n",scenario,mutation,result,atomic_load(&t.observed));
    return result;
}
int main(void) {
#ifdef _WIN32
    WSADATA d;if(WSAStartup(MAKEWORD(2,2),&d))return 1;
#endif
    int result=run_refinement(BEFORE_POLL,0)||run_refinement(DURING_RESET,0)||run_refinement(SIGNAL_FAILURE,0);
    if(!result && (!run_refinement(BEFORE_POLL,1)||!run_refinement(DURING_RESET,2)))result=1;
#ifdef _WIN32
    WSACleanup();
#endif
    return result;
}
