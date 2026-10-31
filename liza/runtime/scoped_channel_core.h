#ifndef LIZA_CHANNEL_PROBE_H
#define LIZA_CHANNEL_PROBE_H
#include <stddef.h>
#include <stdint.h>

typedef struct channel channel;
typedef enum { CH_OK, CH_FULL, CH_EMPTY, CH_CLOSED, CH_INVALID, CH_NOMEM } liza_scoped_status;
/* Allocation includes metadata, lock, padding and all fixed u32 slots.
   Allocator/OS overhead and thread stacks are not included. */
liza_scoped_status liza_scoped_create(size_t slots, size_t budget, channel **out, size_t *bytes);
liza_scoped_status liza_scoped_send(channel *c, uint32_t value);
liza_scoped_status liza_scoped_receive(channel *c, uint32_t *value);
void liza_scoped_close_sender(channel *c);
/* Return number discarded by this call; subsequent closes return zero. */
size_t liza_scoped_close_receiver(channel *c);
/* Only after all send/receive/close calls have stopped and threads joined. */
void liza_scoped_destroy(channel *c);
#ifdef CH_MEASURE
typedef struct { uint64_t acquisitions, contended, wait_ns, hold_ns, max_wait_ns, max_hold_ns; } liza_scoped_metrics;
void liza_scoped_get_metrics(channel *c, liza_scoped_metrics *out);
#endif
#endif
