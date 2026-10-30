/* Runtime identity test: each worker owns its reactor until join. */
#include "reactor_common.h"
extern uint64_t liza_rt_workers_run(uint32_t, uint32_t (*)(uint32_t));
static reactor *instances[8];
static uint32_t create_worker(uint32_t id) {
    return liza_rt_reactor_create(0,1,&instances[id]);
}
int main(void) {
    for (unsigned round=0;round<30;round++) {
        memset(instances,0,sizeof(instances));
        if (liza_rt_workers_run(8,create_worker)) return 1;
        for (unsigned i=0;i<8;i++) {
            reactor *r=instances[i];if (!r || !r->owner) return 2;
            r->slots[0].live=1;r->slots[0].generation=1;
            if (!reactor_find(r,r->owner,1,0)) return 3;
            for (unsigned j=0;j<8;j++) if (i!=j) {
                if (r->owner==instances[j]->owner) return 4;
                if (reactor_find(r,instances[j]->owner,1,0)) return 5;
            }
            r->slots[0].live=0;
        }
        for (unsigned i=0;i<8;i++) if (liza_rt_reactor_close(instances[i])) return 6;
    }
    /* At exhaustion one worker may get the final identity, never wrap. */
    memset(instances,0,sizeof(instances));
    atomic_store(&reactor_next_owner,UINT64_MAX-1);
    (void)liza_rt_workers_run(8,create_worker);
    unsigned successes=0;
    for (unsigned i=0;i<8;i++) if (instances[i]) {
        if (instances[i]->owner!=UINT64_MAX) return 7;
        successes++;
        if (liza_rt_reactor_close(instances[i])) return 8;
    }
    if (successes!=1 || atomic_load(&reactor_next_owner)!=UINT64_MAX) return 9;
    return 0;
}
