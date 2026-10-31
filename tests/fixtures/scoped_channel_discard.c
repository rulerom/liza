#include <stdatomic.h>
#include <stdint.h>
static atomic_int published;
extern uint32_t liza_rt_channels_send(uint32_t);
extern uint32_t liza_rt_channels_run(uint32_t,uint64_t,uint32_t (*)(void),uint32_t (*)(void),uint32_t *,uint32_t *,uint32_t *);
static uint32_t producer(void) {
    if(liza_rt_channels_send(42)!=0)return 1;
    atomic_store(&published,1);
    return 0;
}
static uint32_t consumer(void) {
    while(!atomic_load(&published)){}
    return 0;
}
int main(void) {uint32_t p=99,c=99,d=99;uint32_t status=liza_rt_channels_run(1,1024,producer,consumer,&p,&c,&d);return status==0 && !p && !c && d==1?0:1;}
