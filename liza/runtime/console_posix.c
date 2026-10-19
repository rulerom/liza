/* Private scalar ABI: high 32 bits = error, low 32 bits = bytes written.
 * No heap, stdio buffering, locale formatting, or process-wide signal changes.
 */
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <errno.h>
#include <signal.h>
#include <pthread.h>
#include <unistd.h>

static uint32_t error_kind(int e) {
    switch(e) {
    case EBADF: return 1;
    case EACCES: case EPERM: return 2;
    case EPIPE: return 3;
    case EAGAIN: return 4;
#if EWOULDBLOCK != EAGAIN
    case EWOULDBLOCK: return 4;
#endif
    case ENOSPC: return 5;
    default: return 6;
    }
}

uint64_t liza_rt_write(const uint8_t *data, uint32_t length) {
    if (!length) return 0;
    sigset_t blocked, old, pending;
    sigemptyset(&blocked);
    sigaddset(&blocked, SIGPIPE);
    if (pthread_sigmask(SIG_BLOCK, &blocked, &old)) return (uint64_t)6 << 32;
    if (sigpending(&pending)) {
        pthread_sigmask(SIG_SETMASK, &old, 0);
        return (uint64_t)6 << 32;
    }
    int already_pending = sigismember(&pending, SIGPIPE);
    uint32_t done=0, error=0;
    while (done < length) {
        /* Bounded request fits ssize_t on every supported host. */
        uint32_t chunk=length-done;
        if (chunk>1048576) chunk=1048576;
        ssize_t n=write(STDOUT_FILENO, data+done, chunk);
        if (n>0) {done+=(uint32_t)n; continue;}
        if (n<0 && errno==EINTR) continue;
        int e=n<0 ? errno : EIO;
        error=error_kind(e);
        if (e==EPIPE && !already_pending) {
            /* An ignored SIGPIPE need not be pending. Never wait for it then.
             * Only consume a newly generated signal before restoring the mask.
             */
            if (!sigpending(&pending) && sigismember(&pending,SIGPIPE)) {
                int caught;
                sigwait(&blocked,&caught);
            }
        }
        break;
    }
    if (pthread_sigmask(SIG_SETMASK,&old,0)) error=6;
    return ((uint64_t)error<<32)|done;
}

static uint64_t number(uint64_t magnitude, int negative) {
    uint8_t buffer[21];
    unsigned start=sizeof buffer;
    do {buffer[--start]=(uint8_t)('0'+magnitude%10); magnitude/=10;} while(magnitude);
    if (negative) buffer[--start]='-';
    return liza_rt_write(buffer+start,(uint32_t)(sizeof buffer-start));
}
uint64_t liza_rt_print_u64(uint64_t value) {return number(value,0);}
uint64_t liza_rt_print_i64(int64_t value) {
    /* Unsigned negation includes INT64_MIN without signed overflow. */
    return number(value<0 ? UINT64_C(0)-(uint64_t)value : (uint64_t)value,value<0);
}
