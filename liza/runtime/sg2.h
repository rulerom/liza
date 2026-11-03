#ifndef LIZA_SG2_H
#define LIZA_SG2_H
#include <stdint.h>
#include <stddef.h>
/* Internal C interface, not a language binding. */
typedef struct reactor reactor;
typedef struct liza_sg2_context liza_sg2_context;
typedef uint32_t (*liza_sg2_fn)(liza_sg2_context *);
typedef struct {
    size_t managed_budget,process_budget,stack_bytes,service_stack_bytes,reactor_budget;
    uint32_t reactor_capacity;
    uint32_t slots,max_threads,max_socket_handles,operation_ms,shutdown_ms;
#ifdef LIZA_SG2_TESTING
    unsigned fail_at,data_fault,control_fault;
#endif
} liza_sg2_config;
typedef struct {
    uint32_t schema_version,result,fault,control_fault,producer_result,consumer_result;
    uint64_t generation;
    size_t group_managed_bytes_live,group_managed_bytes_peak,fifo_allocation_bytes;
    unsigned group_socket_handles_live,group_socket_handles_peak,participant_threads_live;
    unsigned participant_native_handles_live,process_service_threads,join_records_in_use;
    size_t participant_stack_requested_bytes,service_stack_requested_bytes,process_managed_bytes;
    size_t reactor_allocation_bytes;
    unsigned reactor_socket_handles_live,startup_steps;
} liza_sg2_report;
enum { SG2_OK,SG2_BUSY,SG2_INVALID,SG2_STARTUP_FAILED,SG2_FAULTED };
enum { SG2_NOT_PUBLISHED,SG2_PUBLISHED,SG2_PUBLISHED_FAULT };
enum { SG2_VALUE,SG2_EMPTY,SG2_CLOSED,SG2_NOTIFY_FAULT };
uint32_t liza_sg2_run(const liza_sg2_config *,liza_sg2_fn,liza_sg2_fn,liza_sg2_report *);
uint32_t liza_sg2_send(liza_sg2_context *,uint32_t);
uint32_t liza_sg2_take_or_arm(liza_sg2_context *,uint32_t *);
/* Consumer-only. Borrowed handles remain group-owned through all joins. */
uint32_t liza_sg2_reactor_create(liza_sg2_context *,uint16_t port,reactor **out);
/* Registered Reactor is closed by the consumer wrapper after callback return. */
void liza_sg2_sources(liza_sg2_context *,uint64_t out[2]);
void liza_sg2_control_drain(liza_sg2_context *);
/* Any participant can ask; only owner writes the control wake. */
void liza_sg2_request_stop(liza_sg2_context *);
int liza_sg2_stopping(liza_sg2_context *);
void liza_sg2_busy(liza_sg2_context *);
#ifdef LIZA_SG2_TESTING
#include <stdatomic.h>
extern atomic_int sg2_test_handback_gate;
extern atomic_int sg2_test_stale_receipt,sg2_test_supervisor_gate;
void sg2_test_event(const char *,uint64_t,unsigned);
#endif
#endif
