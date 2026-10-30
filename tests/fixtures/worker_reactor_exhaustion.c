#if defined(__linux__)
#define _DEFAULT_SOURCE 1
#endif
/* Inject exhaustion after listener creation and observe one close attempt. */
#define liza_rt_net_listen_at test_net_listen_at
#define liza_rt_net_close test_net_close
#include "reactor_common.h"
#undef liza_rt_net_listen_at
#undef liza_rt_net_close
uint32_t liza_rt_net_listen_at(uint32_t, uint16_t, uint64_t *);
uint32_t liza_rt_net_close(uint64_t);
static unsigned close_calls;
static uint32_t injected_close_error;
uint32_t test_net_listen_at(uint32_t ip,uint16_t port,uint64_t *out) {
    uint32_t result=liza_rt_net_listen_at(ip,port,out);
    if (!result) atomic_store(&reactor_next_owner,UINT64_MAX);
    return result;
}
uint32_t test_net_close(uint64_t handle) {
    ++close_calls;
    uint32_t result=liza_rt_net_close(handle);
    return result ? result : injected_close_error;
}
int main(void) {
    for (unsigned fail=0;fail<2;fail++) {
        atomic_store(&reactor_next_owner,UINT64_MAX-1);
        close_calls=0;injected_close_error=fail?7:0;
        reactor *r=NULL;
        uint32_t result=liza_rt_reactor_create_at(0x7f000001u,0,1,&r);
        if (r || close_calls!=1 || result!=(fail?7u:11u)) return 1;
    }
    return 0;
}
