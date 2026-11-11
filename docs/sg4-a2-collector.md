# SG4-A2: collector reliability

The historical C run contains a **479.511 ms gap between valid collector
observations**. A controlled collector pause reproduced output loss together
with UDP receive-buffer overflow. The cause of the historical pause remains
unknown: its records cannot distinguish filesystem I/O from descheduling.
SG4-B and Linux capacity claims remain deferred.

## Historical evidence

The audit verifies the original decompressed record SHA-256 and reconciles
each receiver with the original report. All 124256 missing copies are accounted
for by one contiguous ordinal range per receiver, with **1925–1954 missing
copies per receiver**, not a uniform 1941. The union spans ordinals
235565–237519, generated 47.073203–47.464003 seconds after measurement began.
Those are generation times, not kernel arrival or drop times.

The global observation gap is at 47.038688–47.518199 seconds. Its adjacent
records are receiver 2, ordinals 234928 and 234929. Per-receiver observation
gaps reach 479.511–484.719 ms. All 64 receivers subsequently observe the final
ordinal 300199, about 533 ms before service stop. This is an internal gap, not
simply a missing final suffix at the drain boundary. It does not exclude every
possible phase or recording error. Historical kernel overflow counters and
record-store timings were not collected and cannot be reconstructed.

## Unforced collector A/B

On the same Apple M4 macOS host, the original C service executable is reused
unchanged: 64 receivers, 1200-byte packets, 5k input packets/s, 60 seconds.
The sequence is original reference, file/memory, then memory/file. File and
memory modes use the same diagnostic binary, validation and timestamp placement.
The original reference has no added timing hooks.

| Order | Collector | Delivery p99 (ms) | Missing copies | Collector CPU (s) | Peak RSS (MiB) |
| --- | --- | ---: | ---: | ---: | ---: |
| 0 | Original | 0.4 | 0 | 48.37 | 19.67 |
| 1 | File | 1.0 | 0 | 48.67 | 19.98 |
| 2 | Memory | 89.4 | 0 | 48.72 | 309.94 |
| 3 | Memory | 26.9 | 0 | 49.10 | 306.94 |
| 4 | File | 5.1 | 0 | 48.80 | 19.95 |

Every run received all 300000 inputs and delivered all 19200000 measurement
copies. The system-wide UDP full-socket-buffer counter increased by zero in
each run. No record-buffer overflow occurred. Instrumented socket snapshots
were empty at stop; that snapshot cannot rule out future arrivals.

The large historical loss did **not recur**. Memory mode still exhibits latency
tails, so per-record file writing is not necessary for every tail. Two pairs
do not establish a general ranking or exonerate historical file I/O. Memory
mode adds roughly 293 MiB of prefaulted record storage and changes memory
pressure; neither affinity nor exclusive host scheduling is enforced.

Maximum file-store wall times were 5.331 and 7.673 ms; memory stores reached
2.379 and 1.396 ms. Wall times include preemption. Memory mode's final flush
took 542.203 and 425.579 ms **after capture stopped**, outside delivery timestamp
collection. CPU totals include warmup, drain and this flush. Maximum idle poll
and outside-receive intervals include intentional phase waits and must not be
reported as active measurement stalls.

## Controlled pause

A separate test-only build pauses for 500 ms while storing receiver 0,
ordinal 12700, in a five-second 5k run. The measured store interval is
**502.686 ms**, with a **502.688 ms** observation gap. The application receives
all inputs and reports successful local sends, but the collector misses
**121175 copies**. The system-wide full-socket-buffer counter increases by
**exactly 121175**. Exact missing ranges and neighboring timestamps are archived.

This demonstrates a mechanism: a collector pause can exhaust receive queues
and produce the observed class of gap. The deliberate sleep is neither a
filesystem fault nor proof of what caused the historical pause. Global kernel
counters are supporting evidence and cannot individually attribute drops to
each socket. No memory-recording overflow or corrupt packet was reported.

## Reproduction and limits

[Collector protocol and commands](https://github.com/rulerom/liza/blob/76ba608a235d48b91ca57e02b16c1c5af8a12ca1/benchmarks/sg4-fanout/COLLECTOR.md) describe
the bounded buffers, explicit recorder failure, timing hooks, cutoff inspection
and kernel snapshots. [Evidence archives](https://github.com/rulerom/liza/blob/76ba608a235d48b91ca57e02b16c1c5af8a12ca1/benchmarks/sg4-fanout/results/README.md)
include manifests, source/binary hashes and per-receiver ranges. Raw records
remain in local temporary run directories; those paths are not permanent public
artifact hosting. The original Liza/C applications, runtime and baseline are
unchanged. This experiment investigates the collector using C only; it supplies
no new Liza/C speed comparison.

Functional tests compare original/file/memory identities, malformed packets,
duplicates, explicit bounded-memory exhaustion, pause instrumentation and audit
hash rejection. The remaining causal question needs scheduling/I/O evidence
during a naturally recurring pause. Scaling the service before that evidence
would risk optimizing around the measurement system.
