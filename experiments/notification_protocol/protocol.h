#ifndef PROTOCOL_TRACE
#define PROTOCOL_TRACE(p, op, value, result, reason) ((void)0)
#endif
/* Experimental wrapper; included after reactor_wakeup's platform helpers.
 * All users must use this wrapper, never access fifo directly. */
typedef enum { NOT_PUBLISHED, PUBLISHED, PUBLISHED_FAULT } publication;
typedef struct {
#ifdef _WIN32
    SRWLOCK lock;
#else
    pthread_mutex_t lock;
#endif
    channel *fifo;
    wakeup wake;
    int armed, pending, fault, inject_failure;
} protocol;
static void enter(protocol *p) {
#ifdef _WIN32
    AcquireSRWLockExclusive(&p->lock);
#else
    if(pthread_mutex_lock(&p->lock))abort();
#endif
}
static void leave(protocol *p) {
#ifdef _WIN32
    ReleaseSRWLockExclusive(&p->lock);
#else
    if(pthread_mutex_unlock(&p->lock))abort();
#endif
}
static int protocol_init(protocol *p) {
    memset(p,0,sizeof(*p));size_t bytes=0;
#ifdef _WIN32
    InitializeSRWLock(&p->lock);
#else
    if(pthread_mutex_init(&p->lock,NULL))return 0;
#endif
    if(liza_scoped_create(2,1024,&p->fifo,&bytes)!=CH_OK)goto fail;
    if(wake_init(&p->wake,0))return 1;
    liza_scoped_destroy(p->fifo);
fail:
#ifndef _WIN32
    if(pthread_mutex_destroy(&p->lock))abort();
#endif
    return 0;
}
static int notify_locked(protocol *p) {
    if(p->fault)return 0;
    if(!p->armed||p->pending)return 1;
    if(p->inject_failure||!wake_send(&p->wake)){p->fault=1;return 0;}
    p->pending=1;return 1;
}
static publication publish(protocol *p,uint32_t value,liza_scoped_status *reason) {
    enter(p);
    if(p->fault){*reason=CH_CLOSED;PROTOCOL_TRACE(p,"publish",value,NOT_PUBLISHED,*reason);leave(p);return NOT_PUBLISHED;}
    *reason=liza_scoped_send(p->fifo,value);
    if(*reason!=CH_OK){PROTOCOL_TRACE(p,"publish",value,NOT_PUBLISHED,*reason);leave(p);return NOT_PUBLISHED;}
    publication result=notify_locked(p)?PUBLISHED:PUBLISHED_FAULT;
    PROTOCOL_TRACE(p,"publish",value,result,*reason);leave(p);return result;
}
/* Sole consumer: only CH_EMPTY with fault==0 permits poll. The caller must
 * call this again before each sleep, including after unrelated network I/O. */
static liza_scoped_status take_or_arm(protocol *p,uint32_t *value,int *fault) {
    enter(p);p->armed=0;
    if(p->pending){if(!wake_drain(&p->wake))p->fault=1;p->pending=0;}
    liza_scoped_status s=liza_scoped_receive(p->fifo,value);
    if(s==CH_EMPTY&&!p->fault)p->armed=1;
    *fault=p->fault;PROTOCOL_TRACE(p,"take",s==CH_OK?*value:0,s,0);leave(p);return s;
}
/* Sender close is serialized with publication and wakes an armed consumer. */
static int protocol_close(protocol *p) {
    enter(p);liza_scoped_close_sender(p->fifo);int ok=notify_locked(p);PROTOCOL_TRACE(p,"close",0,ok,0);leave(p);return ok;
}
/* Independent supervisor may observe this sticky state through shared memory;
 * no automatic detection, wake or progress guarantee is implied. */
static int protocol_fault(protocol *p) {enter(p);int f=p->fault;leave(p);return f;}
static void protocol_destroy(protocol *p) {
    /* Owner obligation: all accessing threads joined before this call. */
    wake_close(&p->wake);liza_scoped_destroy(p->fifo);
#ifndef _WIN32
    if(pthread_mutex_destroy(&p->lock))abort();
#endif
}
