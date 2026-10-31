#include <stdatomic.h>
#include <stdint.h>
static atomic_int published;
extern uint32_t liza_rt_channels_send(uint32_t);
extern uint64_t liza_rt_channels_run(uint32_t,uint64_t,uint32_t (*)(void),uint32_t (*)(void));
static uint32_t producer(void) {
    if(liza_rt_channels_send(42)!=0)return 1;
    atomic_store(&published,1);
    return 0;
}
static uint32_t consumer(void) {
    while(!atomic_load(&published)){}
    return 0;
}
int main(void) {return liza_rt_channels_run(1,1024,producer,consumer)==((uint64_t)1<<32)?0:1;}
