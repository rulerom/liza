/* Deterministic sequential schedules over the actual FIFO, simulated wake source.
   This is not a concurrent runtime implementation or an OS wakeup test. */
#include "scoped_channel_core.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "failed at line %d\n", __LINE__); return 1; } } while (0)

int main(void) {
    channel *q = NULL; size_t bytes = 0; uint32_t value = 0;
    int token = 0, observed_fault = 0;
    CHECK(liza_scoped_create(2, 1024, &q, &bytes) == CH_OK);
    /* Publication after an empty check, before the consumer's poll. */
    CHECK(liza_scoped_receive(q, &value) == CH_EMPTY);
    CHECK(liza_scoped_send(q, 10) == CH_OK); token = 1;
    CHECK(token); token = 0; /* wake and drain */
    CHECK(liza_scoped_send(q, 20) == CH_OK); token = 1;
    /* New work is inspected after draining the old token, before rearming. */
    CHECK(liza_scoped_receive(q, &value) == CH_OK && value == 10);
    CHECK(liza_scoped_receive(q, &value) == CH_OK && value == 20);
    CHECK(liza_scoped_receive(q, &value) == CH_EMPTY);
    CHECK(token); token = 0;
    /* Fault after publication must not pretend the message was unsent. */
    CHECK(liza_scoped_send(q, 30) == CH_OK);
    observed_fault = 1; /* simulated independent supervisor, not implemented */
    CHECK(observed_fault && liza_scoped_receive(q, &value) == CH_OK && value == 30);
    liza_scoped_close_sender(q); token = 1;
    CHECK(token && liza_scoped_receive(q, &value) == CH_CLOSED);
    liza_scoped_destroy(q);
    puts("selected FIFO schedules and simulated notification faults passed");
    return 0;
}
