# Channel deadline wait — C runtime probe

This is a **standalone experiment**, not the Liza runtime or an implementation
of the whole [deadline contract](../../docs/scoped-channel-wait-contract.md).
It uses a fixed-capacity `u32` FIFO, a mutex and condition variable, with one
absolute monotonic deadline reused after every wake. Status order under the
lock is terminal `Closed`, clock failure / `Timeout`, then success. FIFO state
and the input are unchanged on timeout. Normal close broadcasts to waiters;
consumer close discards queued values. The prototype keeps all 64 potential slots
in a single fixed-size stack object (`sizeof(wait_channel)`); it does not
implement the production channel byte-budget API, and OS synchronization
implementation costs are outside this object.

Linux selects `CLOCK_MONOTONIC` for `pthread_cond_timedwait`; macOS uses a
relative `pthread_cond_timedwait_relative_np` duration calculated from the
same monotonic deadline; Windows uses relative `SleepConditionVariableCS` and
`GetTickCount64`. Relative waits may begin late if the caller is descheduled
between reading the clock and entering the wait. Platform precision and
semantics require independent verification; do not infer exact timing bounds.

**Known unmet contract:** the initial mutex acquisition and its reacquisition
after a condition wait use ordinary blocking mutex operations. They can delay
observation of the deadline; no bounded lock acquisition, wall-clock return
bound or reactor integration is implemented. The held-mutex test demonstrates
this limitation. Unexpected OS synchronization errors abort rather than claim
that protected state remains usable. The injected wait error happens before
the OS wait while the mutex is known to be held; it does not establish recovery
from arbitrary real synchronization errors. Fault and spurious injection fields
are test instrumentation, not an API design.

```sh
python3 -m unittest discover -s experiments/channel_wait -v
python3 experiments/channel_wait/measure.py --output /tmp/channel-wait.json --repeats 10
```

Tests exercise queued-message/expired-deadline precedence, `Closed`, FIFO,
clock and simulated wait errors, registered waiter notification on freed slot
and closure, injected spurious wakeups and preservation of the original
deadline. Negative controls intentionally suppress notification or extend the
deadline; both must fail. Test joins precede destruction. This is finite
runtime testing, not a model proof of all interleavings; group startup failure, independent model checking and reactor wakeups remain
unimplemented. A separate test holds the mutex across a condition timeout and
observes delayed reacquisition; if scheduling has already passed the deadline
before the lock is obtained, that individual measurement is marked skipped.

The [local diagnostic report](results/macos-probe.json) records ten runs on
one macOS host, compiler and source hashes. With an artificial 100 ms held
mutex and a deadline 30 ms away, the sampled decision and return were 70–75 ms
late. In the injected-spurious scenario, sampled decision/return were 0–1 ms
late. Holding the mutex across a condition timeout made both observations
61–66 ms late in these samples. The clock resolution is milliseconds and the run is short and
instrumented. These values are not p99, a speed comparison or a bound under OS
scheduling. The report records the dirty source state and exact source hashes.
