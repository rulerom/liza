# Notification protocol: finite model

This is an independent abstract state exploration, not the implementation of
notifications or a proof about the C runtime, OS, memory model, or scheduler.
It explores all reachable states with capacities 1 and 2, at most two distinct
publications, one producer, one consumer and sender close. The queue preserves
FIFO and accounting. A producer cannot begin another operation while its signal
is owed. A prior durable signal may be coalesced; resetting it is performed by
a running consumer which must recheck the queue before arming.

The checked safety property forbids an armed consumer with queued work or a
close, no durable or in-flight signal, and no independently observed fault.
`SignalOwed` is allowed as an in-flight state, **not** evidence of delivery.
The fault transition assumes an independent, reliable supervisor observation;
no such production mechanism is implemented here. Neither producer progress
nor wake delivery nor scheduling fairness is proved. The model does not cover
consumer close, cancellation, resource exhaustion or arbitrary message counts.

Four mutations check that the property catches lost wakes, arming without an
empty check, clearing a newer wake while asleep, and a hidden signal failure.
The shortest counterexample is printed for each. `trace.c` executes selected
deterministic schedules against the actual C FIFO, with a *simulated* token and
supervisor. It does not test actual wake primitives or thread interleavings;
the platform probe in `experiments/reactor_wakeup` addresses different cases.

```sh
python3 -m unittest discover -s verification/notification_protocol -v
```
