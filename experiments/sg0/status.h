#include <stdatomic.h>
#include <stdint.h>
#include <limits.h>
enum worker_state { IDLE, BUSY, STOPPING, EXITED };
typedef struct { atomic_uint_fast64_t version, state, obligation, deadline, epoch; } status_record;
typedef struct { uint64_t state, obligation, deadline, epoch; } status_value;
static void status_init(status_record *r) {
    atomic_init(&r->version,0);atomic_init(&r->state,IDLE);
    atomic_init(&r->obligation,0);atomic_init(&r->deadline,0);atomic_init(&r->epoch,0);
}
/* Single writer, all accesses seq_cst. Failure leaves the last record intact. */
static int status_write(status_record *r,status_value v) {
    uint64_t version=atomic_load(&r->version);
    if((version&1)||version>=UINT64_MAX-1||v.epoch==UINT64_MAX||v.obligation==UINT64_MAX)return 0;
    atomic_store(&r->version,version+1);
    atomic_store(&r->state,v.state);atomic_store(&r->obligation,v.obligation);
    atomic_store(&r->deadline,v.deadline);atomic_store(&r->epoch,v.epoch);
    atomic_store(&r->version,version+2);return 1;
}
static int status_read(status_record *r,status_value *out) {
    for(unsigned i=0;i<8;i++) {
        uint64_t before=atomic_load(&r->version);
#ifndef SG_BROKEN_SNAPSHOT
        if(before&1)continue;
#else
        (void)before;
#endif
        status_value v={atomic_load(&r->state),atomic_load(&r->obligation),atomic_load(&r->deadline),atomic_load(&r->epoch)};
        uint64_t after=atomic_load(&r->version);
#ifdef SG_BROKEN_SNAPSHOT
        (void)after;*out=v;return 1;
#else
        if(before==after&&!(after&1)){*out=v;return 1;}
#endif
    }
    return 0;
}
static int overdue(status_value v,uint64_t now) {
    return (v.state==BUSY||v.state==STOPPING)&&now>=v.deadline;
}
