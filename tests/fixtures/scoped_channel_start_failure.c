#include <stdint.h>
#include <stdlib.h>
static uint32_t must_not_run(void) {abort();}
extern uint64_t liza_rt_channels_run(uint32_t,uint64_t,uint32_t (*)(void),uint32_t (*)(void));
int main(void) {
    return liza_rt_channels_run(8,1024,must_not_run,must_not_run)==((uint64_t)2<<56) ? 0 : 1;
}
