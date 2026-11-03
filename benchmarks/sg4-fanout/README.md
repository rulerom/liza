# SG4-A2: scoped UDP RTP fanout

One consumer, real 1200-byte RTP, 64 bounded receiver slots, sequential sends,
SG3 UDP and the same SG2 lifecycle in Liza and C. No new runtime API or MT scaling.
The generated endpoint configuration and binaries are reused across every repeat;
source, LLVM and binary SHA-256 values and exact build commands are recorded.

```sh
python3 benchmarks/sg4-fanout/test_workload.py -v
python3 benchmarks/sg4-fanout/run.py --output /tmp/sg4-run
```

Default: 2k/5k/10k input packets/s, 5 seconds, five repeats each, alternating via
seeded shuffled case order. `--duration 60` enables separate long runs. Output
must be a new directory; it retains generated sources, binaries, per-case raw
records (gzip), counters and `report.json`. This is POSIX loopback, not a physical
network benchmark. Linux-in-Docker is a VM measurement on macOS and must be
labelled accordingly. Windows functional acceptance remains SG4-A1.

## Boundaries and accounting

`fanout.liza` uses the existing `rtp.packet` and `rtp.receivers` modules. One
packet and at most 64 sends are processed between `groups.next()` calls. Each
failed send is counted and is not retried; other recipients are still attempted.
Malformed, wrong-SSRC and truncated datagrams are discarded. The C callback uses
the same header validation, 64-slot table, Region allocation and SG3 ABI.

`adapter.c` is **benchmark-only**, with the same object linked into both binaries:

- It observes real UDP operations without changing payloads or I/O results.
  An independent C parser classifies received packets for counters; this extra
  cost is included in both variants. The application's returned accepted count
  must match the observer. This is not a measurement of an uninstrumented service.
- Its controller uses a separate stdin control channel and the existing control
  wake for phase acknowledgements. Stop sets SG2's normal stop intent. No command
  is encoded in an I/O error, no UDP receive implementation is substituted, and
  no socket is closed from the controller thread.
- The controller is joined by the consumer wrapper before consumer exit, ending
  its borrow of group state before SG2 can destroy it. The harness's extra thread,
  two pipe handles, bitmap and histogram are outside the SG2 managed budget.
- Ready is printed only at the first real Reactor wait, after successful UDP bind.
  Warmup (200 packets, 1k/s) runs in the same generator, service and collector
  processes; after 0.2s drain, measurement is acknowledged before new input.
  Measurement packets use a distinct full-u32 ordinal range.
- After generator completion: phase acknowledgement, 0.5s service drain, stop and
  native joins/handback, then 1s collector drain. All actual phase timestamps are
  saved. The measurement CPU delta includes drain; callback CPU covers warmup too.

`input_sent` is the generator's successful local send count, `received_unique`
is the observer's unique input count, `succeeded` is successful local fanout send,
and `delivered_unique` is the collector's unique receiver/ordinal observation.
The independent collector validates every byte, source port, sequence and receiver;
corruption/duplicates/accounting mismatches invalidate a trial. Failed trials
remain in the report. Loss is not hidden by excluding overloaded trials.

Latency uses explicit `CLOCK_MONOTONIC` in Python and C on the same machine.
The 100us histogram reports upper bounds; >=5s is an overflow bucket, not an exact
percentile. Delivery coverage is shown relative to offered outputs and successful
sends. Cross-machine monotonic clocks cannot be subtracted. Cycle timing is a
10us histogram with >=100ms overflow plus an exact maximum; it measures active
work before returning to control inspection, not idle waiting. There is one
startup command latency sample per process; this is **not** a command p99 study.

Process user/system CPU and peak RSS include the benchmark observer. Callback
thread CPU is recorded; supervisor/service thread CPU is unavailable separately,
but included in process CPU. Socket buffer sizes are read from the real sockets
and required to match across cases. No exact-RSS or physical wire-loss claim.

Functional tests include malformed/SSRC/truncated/empty input and an explicit
`BENCH_TEST_SEND_FAIL` build. That test-only build changes one send outcome to
WouldBlock and checks no retry plus continued delivery to the other receiver;
the measured build never defines this macro.

The immutable generated config currently chooses loopback endpoints. Dynamic
receiver configuration, long-lived producer control, remote generator/collector,
and SG4-B are not implemented. Benchmarks provide workload feedback rather than
claiming a complete production VideoGrace service.

## Linux VM reproduction

```sh
docker build -t liza-sg4-bench -f benchmarks/sg4-fanout/Dockerfile benchmarks/sg4-fanout
docker run --rm -v "$PWD:/src:ro" -v /tmp/sg4-linux-output:/out liza-sg4-bench --output /out/run
```

Record the image ID, Docker/VM CPU and memory configuration and host model. Run
Linux and macOS measurements sequentially to avoid competition between the two
suites. Archives and interpretation will be added after the first full series.
