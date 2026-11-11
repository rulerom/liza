# SG4-B2: Dual UDP RTP Owners

Application experiment on the existing SG4-B1 runtime; no compiler or production
runtime changes. Both binaries are Liza programs using the same `rtp.packet`
parser, receiver registry and `fanout` helper. Two SSRCs identify separate streams:
A `0x10203040`, B `0x50607080`. Every valid packet is 1200 bytes and goes to its
own bounded list of at most 64 recipients. Tables and packet buffers belong to
the consumer and never move between groups.

## Treatments

- `single`: two streams share one endpoint and one consumer; that consumer owns
  both recipient tables. `groups.run` supplies its scoped lifecycle.
- `dual`: two consumers each own one endpoint/table. Static
  `producer_a/consumer_a/producer_b/consumer_b` use `groups.run_pair`.
- Two input generators and two collectors are used in **both** treatments.
  Recipient lists and total offered work are identical at each paired point.

This is a comparison of complete network-owner configurations. The number of
UDP receive queues also changes (one versus two), so a gain cannot be assigned
solely to another CPU core. Actual SO_RCVBUF/SO_SNDBUF are recorded. No aggregate
kernel-buffer equalization, affinity or exclusion of background load is claimed.
Two bind addresses on one host do not prove physical NIC isolation. Binding an
IP does not establish a portable egress-NIC routing policy.

## Reproduction

```sh
python3 benchmarks/sg4-dual/test_dual.py -v
python3 benchmarks/sg4-dual/run.py --output /tmp/sg4-b2 --duration 5 --repeats 5
```

POSIX harness: Linux/macOS. B1's Windows runtime acceptance remains separate.
`--bind-a` and `--bind-b` accept IPv4 addresses already configured on the host;
loopback defaults use `127.0.0.1` with distinct kernel-assigned ports. In single
mode both sources target bind-a; in dual mode B targets bind-b. Different bind
IPs can therefore also change the network path, not just ownership. No host
network settings are modified. Collectors are loopback-only, so this first
harness does not implement a multi-host/NIC benchmark. Physical NIC testing is
future work, with routing and collector placement explicitly controlled.

One generated configuration, single/dual executable pair and SSRC-specific
collector pair are reused across every repeat. The manifest saves source/LLVM,
binary SHA-256, build commands, compiler version, baseline commit, bind and
recipient addresses. `MAX_PACKETS=600000` plus 200 warmup inputs bounds identity
storage. Source/binary changes require a fresh series and output directory.

For each profile `(A packets/s, B packets/s)`:

- `(0,2000)`: B control with A idle during measurement (A has normal warmup).
- `(2000,2000)`: balanced lower offered load.
- `(5000,5000)`: balanced higher offered load.
- `(10000,2000)`: asymmetric offered load; whether A is overloaded is measured,
  not assumed from its requested pacing.

Five repeats alternate single/dual then dual/single order. Five-second runs are
an exploratory host-local series, not a stable capacity threshold. Two earlier
functional runs use 2k/2k: A finishes its offer halfway through B's window, drains
for 150ms, then receives stop or an injected local notification-fault state.
B's new packets offered after A's destroy event must still be observed. The
fault injection calls the existing sticky fault mechanism in the benchmark
controller; it is not an actual OS write failure. Expected `Faulted` is validated
in the harness, while B must return normally.

## Phases, observation and lifetime

Each consumer acknowledges Ready at its first real reactor wait, after endpoint,
table and buffer initialization. Generators warm up in their persistent processes
and use one future absolute CLOCK_MONOTONIC measurement start for both streams.
Consumer phase acknowledgements precede that start. At offer end the harness
requests drain, waits 500ms, requests stop, waits for joins, then allows one second
of collector drain. In early-A scenarios only B gets the final drain/stop.

There is one benchmark control thread per consumer. It borrows only that group,
sets phase/stop intent or the explicit test fault and wakes its existing control
source. The consumer joins its controller before returning. A router handles
only process-lifetime pipes and is joined after the group runner returns.
No controller closes a foreign descriptor or accesses a group after handback.
All protocol requests are fixed-size; the driver sends a bounded phase sequence.
The callbacks do not share mutable application state or exchange packets.

The adapter observes receive identities, independent RTP validation, local send
outcomes, consumer CPU, fanout-cycle maxima and lifecycle events. It does not
replace UDP operations/results. Receipt/join masks, generation and the sequence
`join -> handback -> destroy` are checked. Output records are serialized with an
instrumentation mutex; this is observer overhead, not application synchronization.
Per-owner limits, group generation and zero shared socket handles at destruction
are reported. The process-level join pool is counted once. The harness separately
reports its fixed observation storage and controller/router threads; it is not
part of the language group's managed budget. Pair owner threads, participants,
reapers, stacks and OS buffers are distinct resources, as specified in B1.

## Collectors, counters and limitations

The collector is A2's instrumented collector with exactly one generated change:
its SSRC validation constant. That adaptation is hash-recorded. Byte validation,
timestamp position, duplicate bitmap, receive batches, timing hooks and cutoff
inspection remain unchanged. File recording is the default in both treatments;
record compression occurs after both collectors exit. Memory recording remains
available for the explicit exhaustion test; overflow fails the trial.

Counters distinguish generator-local successful sends, unique application input,
local fanout attempts/success/failure and observed receiver/ordinal delivery.
Latency p50/p95/p99 accompanies coverage and per-receiver counts. Early-A tests
also retain coverage/latency for B packets offered after A cleanup, rather than
only packets received later from an old backlog. Failed recorders are not UDP
loss. Corruption, duplicate records, unexpected source ports or unreconciled
counts fail analysis.

macOS system-wide UDP counters bracket setup/warmup/offer/drain and end before
compression; they cannot attribute drops to a socket or stream. Empty cutoff
snapshots do not prove no future arrivals. Same-host generator/collector CPU,
record I/O and kernel queues remain possible bottlenecks. A local send success
is not proof of remote delivery. CPU totals include startup/warmup/drain; consumer
thread CPU is reported separately. Linux service RSS uses live `/proc` VmHWM
before shutdown; raw collector rusage RSS is not isolated Linux process memory.

Functional CI covers identity, malformed RTP/truncation/wrong-stream rejection,
independent stop/fault and recorder failure. It does not enforce a throughput or
latency threshold. No claim of QoS or CPU isolation follows from ownership
isolation, and SG5 is not part of this experiment.

Completed reports can be summarized with `python3 benchmarks/sg4-dual/summarize.py REPORT.json SUMMARY.json`. Pair ratios use adjacent alternating single/dual runs; trial percentiles are never pooled.
