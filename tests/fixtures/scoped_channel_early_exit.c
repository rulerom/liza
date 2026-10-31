/* Consumer exits early; producer must see Closed and the queue is freed once. */
#include <stdatomic.h>
#include <stdint.h>
#include <stdlib.h>
extern uint32_t liza_rt_channels_send(uint32_t);
extern uint32_t liza_rt_channels_run(uint32_t,uint64_t,uint32_t (*)(void),uint32_t (*)(void),uint32_t *,uint32_t *,uint32_t *);
static atomic_int producer_done,consumer_done,free_count,free_early;
void tracked_free(void *p) {
    if(!atomic_load(&producer_done)||!atomic_load(&consumer_done))atomic_store(&free_early,1);
    atomic_fetch_add(&free_count,1);
    free(p);
}
static uint32_t producer(void) {
    for(;;){uint32_t s=liza_rt_channels_send(7);if(s==2)break;if(s>2)abort();}
    atomic_store(&producer_done,1);return 17;
}
static uint32_t consumer(void) {atomic_store(&consumer_done,1);return 23;}
int main(void) {
    for(unsigned i=0;i<50;i++) {
        atomic_store(&producer_done,0);atomic_store(&consumer_done,0);
        atomic_store(&free_count,0);atomic_store(&free_early,0);
        uint32_t p=0,c=0,d=0;
        uint32_t status=liza_rt_channels_run(1,1024,producer,consumer,&p,&c,&d);
        if(status||p!=17||c!=23||d>1||atomic_load(&free_count)!=1||atomic_load(&free_early))return 1;
    }
    return 0;
}
