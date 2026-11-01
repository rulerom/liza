# Notification protocol: boundary validation

This checks selected actual C executions against a separate Python boundary
specification. It is not a proof over all C schedules, memory models or OS
failures. The production runtime and Liza API are unchanged.

The trace hook records operations immediately before releasing the outer
protocol mutex. An operation may contain several abstract actions: publish and
notify, or reset, inspect and arm. The Python checker reconstructs a FIFO,
sender closure, arming, notification obligation and sticky fault from operation
inputs, then compares results and recorded boundary flags. It does not use the
reported flags to select the expected transition. The original finite model
is not treated as a literal step-by-step simulation of the implementation.

The trace hook and its placement are trusted instrumentation. Logging changes
timing. Histories cover sequential publication/reset/failure cases and 30
sender-close/publication races per binary. The order of events under the mutex
is checked: a published value precedes close; a post-close send is rejected.
This is not a general real-time history linearizer. No consumer-close race or
unresponsive mutex is included.

Socket readiness is additionally observed after quiescent notification points.
A missing signal yields a `ready 0` event after a finite poll, and the checker
reports its event number. The subprocess timeout is only a last-resort harness
guard; it is not the expected negative-control result. Successful readiness is
not evidence that consumer code was scheduled or processed a message.

## Mutations and exact findings

| Mutation | Detected evidence |
| --- | --- |
| Omit the actual wake write, still claim pending | Real socket is not readable at the selected observation point |
| Skip FIFO inspection and claim Empty | FIFO/result and arm state disagree with the reconstructed queue |
| Clear pending immediately after a successful signal | Boundary metadata differs from this protocol's contract |
| Return notification failure without sticky fault | Post-publication failure has no recorded fault |

Clearing `pending` alone does **not** erase a TCP byte. Its detected mismatch
must not be described as a proven lost wakeup. A different protocol might
legitimately use different metadata.

Moving `close_sender` outside the protocol mutex is not included as an assumed
failing mutation: the FIFO itself serializes close and publication. It could
change which boundary snapshots are legal without violating FIFO semantics.
Such a mutation requires instrumentation at the FIFO linearization point and
a revised history abstraction before claiming a real close/publication bug.
No fifth counterexample is claimed.

`fault` and `protocol_fault()` still depend on the protocol mutex. These tests
cover notification failure with functioning synchronization, not an unresponsive
group. No supervisor progress, controlled shutdown or watchdog guarantee is
established.

```sh
python3 -m unittest discover -s verification/notification_runtime -v
```
