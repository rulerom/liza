#include <stdint.h>
#include <stdlib.h>
static uint32_t must_not_run(void) {abort();}
extern uint32_t liza_rt_channels_run(uint32_t,uint64_t,uint32_t (*)(void),uint32_t (*)(void),uint32_t *,uint32_t *,uint32_t *);
int main(void) {
    uint32_t p=99,c=99,d=99;
    uint32_t status=liza_rt_channels_run(8,1024,must_not_run,must_not_run,&p,&c,&d);
    return status==2 && !p && !c && !d ? 0 : 1;
}
