/* Private bounded input ABI: high 32 bits error, low 32 bits bytes read.
   The complete output is initialized even on failure; no heap allocation. */
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#define CAPACITY 2048u
static uint32_t file_error(int e) {
    if (e == ENOENT || e == ENOTDIR) return 1;
    if (e == EACCES || e == EPERM) return 2;
    if (e == EINVAL) return 4;
    if (e == ENAMETOOLONG) return 5;
    if (e == EAGAIN || e == EWOULDBLOCK) return 6;
    return 7;
}
uint64_t liza_rt_read_file(const uint8_t *path, uint32_t length, uint8_t *out) {
    memset(out, 0, CAPACITY);
    if (length == 0 || memchr(path, 0, length)) return (uint64_t)4 << 32;
    if (length > 4095) return (uint64_t)5 << 32;
    char name[4096];
    memcpy(name, path, length); name[length] = 0;
    int fd;
    do { fd = open(name, O_RDONLY | O_CLOEXEC); } while (fd < 0 && errno == EINTR);
    if (fd < 0) return (uint64_t)file_error(errno) << 32;
    uint32_t count = 0, error = 0;
    for (;;) {
        uint8_t extra;
        ssize_t n = read(fd, count < CAPACITY ? out + count : &extra,
                         count < CAPACITY ? CAPACITY - count : 1);
        if (n < 0) {
            if (errno == EINTR) continue;
            error = file_error(errno); break;
        }
        if (n == 0) break;
        if (count == CAPACITY) { error = 3; break; }
        count += (uint32_t)n;
    }
    /* Never retry close: the descriptor may already have been released. */
    if (close(fd) < 0 && !error) error = file_error(errno);
    return ((uint64_t)error << 32) | count;
}
