#define _POSIX_C_SOURCE 200809L
#define liza_rt_group_send sg3_original_send
#define liza_rt_group_stopping sg3_original_stopping
#define liza_rt_group_stop sg3_original_stop
#define liza_rt_reactor_poll_sources sg3_test_poll
#include "sg3_common.h"
#undef liza_rt_group_send
#undef liza_rt_group_stopping
#undef liza_rt_group_stop
#undef liza_rt_reactor_poll_sources
#include <stdio.h>
atomic_int sg2_test_handback_gate,sg2_test_stale_receipt,sg2_test_supervisor_gate;
static atomic_uint submitted,joined,handback;
#ifdef SG3_CLOSED_IDLE
static _Atomic(sg_group *) closed_idle_group;
#endif
void sg3_test_config(liza_sg2_config *cfg){
#ifdef SG3_STARTUP_FAIL
    cfg->fail_at=23;
#endif
#ifdef SG3_DATA_FAIL
    cfg->data_fault=1;
#endif
#ifdef SG3_DOUBLE_FAIL
    cfg->data_fault=1;cfg->control_fault=1;
#endif
#ifdef SG3_CLOSED_IDLE
    cfg->operation_ms=1000;
#endif
    (void)cfg;
}
void sg2_test_event(const char *kind,uint64_t generation,unsigned role){
    (void)generation;(void)role;
    if(!strcmp(kind,"submitted"))atomic_store(&submitted,role);
    if(!strcmp(kind,"join"))atomic_fetch_add(&joined,1);
#ifdef SG3_CLOSED_IDLE
    if(!strcmp(kind,"join")&&role==0){
        sg_group *g;
        while(!(g=atomic_load(&closed_idle_group)))sg_pause();
        uint64_t start=sg_now();while(sg_now()-start<1500)sg_pause();
        if(atomic_load(&g->fault)||atomic_load(&g->shutdown))_Exit(94);
        atomic_store(&g->stop_intent,1);
    }
#endif
    if(!strcmp(kind,"handback"))atomic_store(&handback,1);
    if(!strcmp(kind,"destroy")&&atomic_load(&submitted)){
        if(atomic_load(&joined)!=atomic_load(&submitted)||!atomic_load(&handback))_Exit(91);
    }
    if(!strcmp(kind,"process_abort")){fputs("sg3 escalation: no result\n",stderr);fflush(stderr);}
#ifdef SG3_REORDER_STOP
    if(!strcmp(kind,"test_reordered_stop")){
        /* Keep the publication gap open until the consumer detects it. */
        for(;;)sg_pause();
    }
#endif
}
uint32_t liza_rt_group_send(uint32_t value){
#if defined(SG3_DATA_FAIL) || defined(SG3_DOUBLE_FAIL)
    sg_group *g=sg_current->group;
    for(;;){sg_lock(&g->lock);int armed=g->armed;sg_unlock(&g->lock);if(armed)break;sg_pause();}
#endif
    return sg3_original_send(value);
}

uint32_t liza_rt_group_stopping(void){
    sg_group *g=sg3_context()->group;
    if(!atomic_load(&g->shutdown))return 0;
    if(!atomic_load(&g->shutdown_deadline)){
        fputs("shutdown_without_deadline\n",stderr);fflush(stderr);_Exit(92);
    }
    return sg3_original_stopping();
}

static atomic_int poll_entered;
uint64_t liza_rt_reactor_poll_sources(reactor *,int32_t,sg3_source *,uint32_t);
uint64_t sg3_test_poll(reactor *r,int32_t timeout,sg3_source *sources,uint32_t count){
    uint64_t start=sg_now();
    int first=!atomic_exchange(&poll_entered,1);
#ifdef SG3_CLOSED_IDLE
    int after_closed=sg3_closed;
    if(after_closed)atomic_store(&closed_idle_group,sg3_context()->group);
#endif
    uint64_t result=liza_rt_reactor_poll_sources(r,timeout,sources,count);
#ifdef SG3_CLOSED_IDLE
    if(after_closed&&(timeout!=-1||sg_now()-start<1500))_Exit(95);
#endif
#ifdef SG3_IDLE_STOP
    if(timeout!=-1||(first&&sg_now()-start<750))_Exit(93);
#else
    (void)start;(void)first;
#endif
    return result;
}
uint32_t liza_rt_group_stop(void){
#ifdef SG3_IDLE_STOP
    while(!atomic_load(&poll_entered))sg_pause();
    uint64_t start=sg_now();while(sg_now()-start<750)sg_pause();
#endif
    return sg3_original_stop();
}
