#ifndef LIZA_WAIT_PROBE_H
#define LIZA_WAIT_PROBE_H
#include <stdint.h>
#ifdef _WIN32
#include <windows.h>
typedef CRITICAL_SECTION wait_mutex;
typedef CONDITION_VARIABLE wait_cond;
#else
#include <pthread.h>
typedef pthread_mutex_t wait_mutex;
typedef pthread_cond_t wait_cond;
#endif
typedef enum { W_OK,W_TIMEOUT,W_CLOSED,W_CLOCK_ERROR,W_SYSTEM_ERROR } wait_status;
typedef struct {
    wait_mutex mutex;wait_cond changed;
    uint32_t slots[64],capacity,head,tail,count;
    int sender_closed,receiver_closed,fail_clock,fail_wait;
    uint64_t decision_ms,first_wait_deadline;
    uint32_t waiters,wait_calls,deadline_changes,inject_spurious;
} wait_channel;
int wait_init(wait_channel *c,uint32_t capacity);
void wait_destroy(wait_channel *c); /* after join */
int wait_now(uint64_t *ms);
wait_status wait_send(wait_channel *c,uint32_t value,uint64_t deadline);
wait_status wait_receive(wait_channel *c,uint32_t *value,uint64_t deadline);
void wait_close_sender(wait_channel *c);
uint32_t wait_close_receiver(wait_channel *c);
uint32_t wait_waiters(wait_channel *c);
void wait_poke(wait_channel *c); /* testing spurious wakeup */
#endif
