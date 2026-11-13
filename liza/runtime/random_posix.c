#include <stdint.h>
#include <stddef.h>
#include <errno.h>
#ifdef __APPLE__
#include <stdlib.h>
#else
#include <sys/random.h>
#endif
uint64_t liza_rt_net_random(void) {
    uint32_t value;
#ifdef __APPLE__
    arc4random_buf(&value, sizeof(value));
#else
    size_t done=0;
    while (done<sizeof(value)) {
        ssize_t n=getrandom((uint8_t *)&value+done, sizeof(value)-done, 0);
        if (n<0 && errno==EINTR) continue;
        if (n<=0) return (uint64_t)7 << 32;
        done+=(size_t)n;
    }
#endif
    return value;
}
