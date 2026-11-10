# Collector reliability experiment

The historical first C trial in `macos-paired60.json.gz` missed 124256 output
copies after all input and local sends succeeded. This experiment preserves the
original service binaries and analyzes the receiver instead of changing SG4-B.

## Exact historical audit

```sh
python3 benchmarks/sg4-fanout/missing.py \
  --report /private/tmp/sg4-macos-paired60/report.json \
  --case /private/tmp/sg4-macos-paired60/pair-0-1-c --sample 1 \
  --output /tmp/missing.json
```

The audit verifies the uncompressed record hash, validates identities, rebuilds
bounded per-receiver timestamp arrays and emits exact missing ordinal ranges.
It reconciles every receiver and the total with the original report. Neighbor
observations and generator timestamps bracket each gap; they are not socket
arrival timestamps. The audit reports the largest global gap between valid
observations and per-receiver last observations. Historical kernel drops and
store-call timings cannot be recovered: they were not recorded.

## Matched collector A/B

```sh
python3 benchmarks/sg4-fanout/test_collector_ab.py -v
python3 benchmarks/sg4-fanout/collector_ab.py \
  --baseline /private/tmp/sg4-macos-nb1 --output /tmp/collector-ab60
```

The default sequence is one unmodified collector reference, then file/memory
and memory/file pairs, each with 60s of 5k input packets/s and 64 recipients.
The same original C service binary is used throughout; the original Liza binary
is also hash-checked but not executed. This holds the application fixed while
investigating the collector. It is an exploratory two-pair comparison, not a
statistical proof. Liza/C application sources, generator and original collector
source are unchanged.

The new `collector_ab.c` is a diagnostic copy of the original collector. One
binary chooses file or memory mode via environment. Both retain recvfrom,
timestamp placement, every-byte payload validation, duplicate bitmap, 64-packet
per-socket batch and stop policy. Both have the same timing hooks. The original
collector reference has no such hooks; A (file with hooks) is not bit-identical
to the historical collector, and differences from the reference include this
instrumentation. No precision claim hides that distinction.

Memory mode preallocates and touches all record pages before Ready. Capacity is
`receivers * (offered packets + warmup)`, at most 64 * 600200 records, each 16
bytes. At 60s/5k this is 307404800 bytes. Duplicate-map and timing storage are
additional and bounded. File mode retains stdio buffering and writes per record;
it does not fsync each packet. Memory mode copies the same record into the array
and writes it after stop. The filesystem is still used after the measurement.

`SG4_COLLECTOR_RECORD_LIMIT` is a test override bounded by that capacity. On
exhaustion the collector writes `record_overflow:true`, `measurement_valid:false`,
received/stored counts and exits 4. The harness fails the trial rather than
reporting a UDP loss. Allocation or write failures likewise fail the process.
The test checks malformed/empty/oversized packets, duplicates, identical
receiver/ordinal identity sets in original/A/B, and an intentional overflow.

## Observation boundaries

- Poll, receive, record store and time between receive calls have bounded 1us
  histograms, totals and exact maxima. >=10ms is overflow. These are wall times,
  including possible preemption. They do not distinguish a blocked write from
  descheduling inside that interval. `outside_recv` includes idle polling,
  validation and storage, so its total overlaps the component totals.
- Store calls >=100us are logged with start/end, ordinal and receiver in an
  8192-entry array. Excess events increment `store_events_dropped`; packet
  recording continues, and the incomplete diagnostic trace is explicit.
- On the original stop request, before flushing, each socket is inspected with
  FIONREAD and zero-timeout poll. The primary drain policy is not extended.
  Queued bytes/readiness show work at the cutoff; an empty snapshot does not
  guarantee no future kernel arrival. Last per-receiver observation times are
  retained. A zero-length datagram can be readable with zero FIONREAD bytes.
- `netstat -s -p udp` snapshots bracket setup, warmup, measurement and drain,
  ending just after collector exit and before report analysis/compression.
  macOS's full-socket-buffer counter is system-wide, not per socket. Background
  traffic is not excluded. A matching delta is supporting evidence, not proof
  of attribution to a particular recipient.
- Post-exit archive compression/fsync completes before a two-second quiet gap.
  Source/binary/config hashes, actual socket buffer sizes and failed cases are
  preserved. Generator/collector CPU includes warmup and final flushing; it is
  not isolated measurement-phase CPU.

No phase error, missing disk record or successful local send is silently
reclassified as network loss. If the event does not recur, the report must say
so; no improvement alone proves the historical pause's cause.

## Controlled pause (separate experiment)

```sh
python3 benchmarks/sg4-fanout/collector_pause.py \
  --baseline /private/tmp/sg4-macos-nb1 --output /tmp/collector-pause
```

This compiles with `SG4_COLLECTOR_TESTING` and injects one 500ms sleep inside
record storage at receiver 0, ordinal 12700. It is a five-second 5k test with
kernel snapshots, not part of the unforced A/B series. The hook is absent from
ordinary builds. It tests the pause/overflow mechanism, not filesystem failure.
The functional test also verifies the hook with a low-rate packet corpus.

[Measured results](../../docs/sg4-a2-collector.md).
