# Scoped channel B0 — C runtime probe

This is an isolated experimental C prototype for the [scoped channel contract](../../docs/scoped-channels-contract.md), not a Liza API or a production runtime. One producer and one consumer exchange `u32` through a bounded FIFO guarded by one mutex (POSIX) or SRW lock (Windows). The full allocated `channel` object includes metadata, alignment and all preallocated slots. `ch_create` checks the byte budget and integer limits before allocation. OS/allocator overhead and thread stacks are outside that budget. No send, receive or close allocates memory. Caller must join every accessing thread before destroying the channel; C cannot enforce SPSC role or scoped ownership.

```sh
python3 -m unittest discover -s experiments/scoped_channel -v
```

The native test checks capacity, budget, FIFO, wraparound, Full/Empty/Closed, drain after sender close, discards and repeated close, 1000 send/receiver-close races, and 100,000 sequential messages per run for capacities 1/4/16/64. Separate fault injection simulates allocation failure; a negative control deliberately corrupts the queue on Full and must fail. Testing uses bounded subprocess timeouts. OS threads and mutexes are real; this is still testing, not a universal correctness proof.

`try` does not wait for queue space or a message, but can wait to acquire the mutex. Timings, contention and mutex hold durations have **not yet been measured**; no latency or scaling claim follows. Worker group creation failure, compiler endpoint checks, explicit join enforcement, integration with Liza, fault injection for mutex initialization and independent formal models remain work for subsequent stages. No socket, region or arbitrary value is transferred.
