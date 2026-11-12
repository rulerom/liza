#include "net_common.h"
#include <windows.h>
#include <bcrypt.h>
uint64_t liza_rt_net_random(void) {
    uint32_t value;
    if (BCryptGenRandom(NULL, (PUCHAR)&value, sizeof(value), BCRYPT_USE_SYSTEM_PREFERRED_RNG) != 0)
        return (uint64_t)7 << 32;
    return value;
}
