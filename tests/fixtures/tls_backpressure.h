/* Deterministic pressure around real TLS and real TCP. No wire substitution. */
#include <stdint.h>
#include <stdio.h>
#ifdef LIZA_TLS_BP_ENGINE
#define liza_tls_read bp_real_tls_read
#define liza_tls_write bp_real_tls_write
#define liza_tls_feed bp_real_tls_feed
#define liza_tls_drain bp_real_tls_drain
#define liza_tls_shutdown bp_real_tls_shutdown
#include LIZA_TLS_BP_ENGINE
#undef liza_tls_read
#undef liza_tls_write
#undef liza_tls_feed
#undef liza_tls_drain
#undef liza_tls_shutdown
extern void bp_plain_read(void);
extern void bp_full_bio(void);
extern void bp_close_start(void);
extern void bp_full_input(void);
extern void bp_input_progress(void);
static unsigned needs_drain;
liza_tls_result liza_tls_read(liza_tls*t,uint8_t*d,uint32_t n,uint64_t now){
    liza_tls_result r=bp_real_tls_read(t,d,n,now);if(r.count)bp_plain_read();return r;
}
liza_tls_result liza_tls_write(liza_tls*t,const uint8_t*d,uint32_t n,uint64_t now){
    if(needs_drain){fprintf(stderr,"plaintext retry before BIO drain\n");return (liza_tls_result){LIZA_TLS_INVALID,0,0,LIZA_TLS_OPEN,0,0};}
    liza_tls_result r=bp_real_tls_write(t,d,n,now);
    if(r.status==LIZA_TLS_WANT&&(r.wants&LIZA_TLS_OUTPUT)){needs_drain=1;bp_full_bio();}
    return r;
}
liza_tls_result liza_tls_feed(liza_tls*t,const uint8_t*d,uint32_t n,uint64_t now){
    liza_tls_result r=bp_real_tls_feed(t,d,n,now);if(r.count)bp_input_progress();if(n&&r.status==LIZA_TLS_WANT&&!r.count)bp_full_input();return r;
}
liza_tls_result liza_tls_drain(liza_tls*t,uint8_t*d,uint32_t n,uint64_t now){
    liza_tls_result r=bp_real_tls_drain(t,d,n,now);if(r.count)needs_drain=0;return r;
}
liza_tls_result liza_tls_shutdown(liza_tls*t,uint64_t now){
    bp_close_start();return bp_real_tls_shutdown(t,now);
}
#else
#define liza_rt_reactor_write bp_real_write
#define liza_rt_reactor_poll bp_real_poll
#define liza_rt_reactor_ready bp_real_ready
#define liza_rt_reactor_close bp_real_close
#include LIZA_TLS_BP_REACTOR
#undef liza_rt_reactor_write
#undef liza_rt_reactor_poll
#undef liza_rt_reactor_ready
#undef liza_rt_reactor_close
static unsigned plain,full_bio,closing,phase,permit,blocked,polls,waiting,reads_during_gate,violations;
static uint32_t saved_count,saved_hash,input_gate_polls,input_full,input_stalled;
void bp_plain_read(void){plain=1;if(phase==1&&!permit)reads_during_gate++;}
void bp_full_bio(void){full_bio++;}
void bp_full_input(void){input_full=1;input_stalled=1;}
void bp_input_progress(void){input_stalled=0;}
void bp_close_start(void){if(!closing){closing=1;phase=2;permit=0;polls=0;waiting=0;}}
static uint32_t bp_hash(const uint8_t*d,uint32_t n){uint32_t h=2166136261u;while(n--){h^=*d++;h*=16777619u;}return h;}
uint64_t liza_rt_reactor_write(reactor*r,uint64_t o,uint64_t g,uint64_t s,const uint8_t*d,uint32_t n,uint32_t a,uint32_t c){
    if(plain&&!phase){phase=1;permit=0;polls=0;waiting=0;}
    if(phase&&!permit){
        if(waiting){violations++;fprintf(stderr,"write retry before writable readiness\n");return (uint64_t)7<<32;}
        saved_count=c;saved_hash=bp_hash(d+a,c);waiting=1;blocked++;return (uint64_t)4<<32;
    }
    if(waiting){if(c!=saved_count||bp_hash(d+a,c)!=saved_hash){violations++;return (uint64_t)7<<32;}waiting=0;}
    return bp_real_write(r,o,g,s,d,n,a,c>97?97:c);
}
uint64_t liza_rt_reactor_poll(reactor*r,uint32_t timeout){
    if(phase&&!permit&&waiting){
        if(phase==1&&input_stalled){
            for(uint32_t i=0;i<r->capacity;i++)if(r->slots[i].live&&(r->slots[i].interest&1)){
                violations++;fprintf(stderr,"read readiness with full TLS input\n");return (uint64_t)7<<32;
            }
        }
        polls++;if(phase==1)input_gate_polls++;
        if((phase==1&&full_bio&&input_stalled&&polls>=3)||(phase==2&&polls>=3))permit=1;
        if(!permit){
            /* Model a non-writable socket: input readiness remains real. */
            uint32_t interests[REACTOR_MAX];
            for(uint32_t i=0;i<r->capacity;i++){interests[i]=r->slots[i].interest;r->slots[i].interest&=1;}
            uint64_t result=bp_real_poll(r,(full_bio||phase==2)?0:timeout);
            for(uint32_t i=0;i<r->capacity;i++){r->slots[i].interest=interests[i];r->slots[i].ready&=~2u;}
            return result;
        }
    }
    return bp_real_poll(r,timeout);
}
uint64_t liza_rt_reactor_ready(reactor*r,uint64_t o,uint64_t g,uint64_t s){return bp_real_ready(r,o,g,s);}
uint32_t liza_rt_reactor_close(reactor*r){
    if(input_gate_polls>256){violations++;fprintf(stderr,"excessive readiness polls during bounded input\n");}
    fprintf(stderr,"TLS_BP blocked=%u bio_full=%u concurrent_reads=%u closing=%u violations=%u polls=%u input_full=%u\n",blocked,full_bio,reads_during_gate,closing,violations,input_gate_polls,input_full);
    return bp_real_close(r);
}
#endif
