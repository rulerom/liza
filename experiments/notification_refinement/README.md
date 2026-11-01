# Notification runtime refinement probe

This experimental harness combines the actual bounded SPSC FIFO with local TCP
notification sockets, native threads, and test-only atomic scheduling gates.
It is not a production notification protocol and changes no Liza API/runtime.

| Abstract action | Evidence in this probe |
| --- | --- |
| `publish` | `liza_scoped_send` completes before the data socket write. |
| `arm` | Consumer checks `CH_EMPTY`, announces a gate, then polls after producer publication. This does not prove it was asleep. |
| `signal_ok` | A successful socket write is followed by readable `poll`/`WSAPoll` and a real socket read. |
| `reset` | Consumer drains an old token, pauses, producer publishes a second value and sends another token, then consumer checks both FIFO values. |
| `signal_fail` | Failure is injected after actual FIFO publication. A second socket wakes a separate supervisor thread, which reads the fault flag; test cleanup then wakes consumer through the data socket and it receives the original message. |
| `close` | After consumer join, sender close and a socket notification are checked sequentially. A concurrent close race is not covered. |

Two negative controls intentionally suppress a wake and deliberately discard a
new notification without rechecking the queue. The latter waits for actual
socket readiness before discarding to avoid relying on TCP scheduling. Both
must be detected by bounded test timeouts; those are not production deadlines.

The independent control socket and supervisor exist only in this test. Their
creation, memory budget, failure, lifecycle, scheduling progress, and recovery
are not specified for production. Fault observation is not fault resolution.
The data wake failure is injected, not a genuine OS failure; the fault case
does not establish that the consumer was already asleep. Gates use active
waiting solely to force test schedules. The tests do not prove all schedules,
socket fairness, absence of lost wakes, or refinement of the abstract model.
Socket buffering is outside the FIFO budget. No general `arm` protocol,
coalescing algorithm, or lost-wakeup-safe shutdown has been implemented.

```sh
python3 -m unittest discover -s experiments/notification_refinement -v
```
