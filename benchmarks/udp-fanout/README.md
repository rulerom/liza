# Single-thread RTP fanout: Liza and C

This first real-UDP comparison runs the **same single-thread application
contract** on C and Liza: one IPv4 loopback socket, 1–64 static IPv4 loopback
receiver addresses, a 2048-byte receive buffer, RTP v2 header/CSRC/extension/
padding validation, one configured author SSRC and delivery of the unchanged
packet to each receiver. Both do O2 native builds, use one bounded packet buffer,
scan the active receiver slots and send sequentially. SSRC is a full u32; the
packet limit is 1..2147483647. No generated payload is copied to a second user
buffer by fanout. Kernel copying, compiler-generated copies and allocations
are **not instrumented**.

Both consume up to the requested number of incoming datagrams in normal
operation; a benchmark-only UDP stop marker can end the run earlier. A malformed, nonmatching SSRC or truncated datagram counts toward the
input limit but is not forwarded. On receive error both exit status 3 immediately;
on send error they attempt remaining destinations for that packet and then exit
3. Bad command-line arguments exit 2. These runtime failure paths have **not yet
been verified with fault injection**. This is not the VideoGrace Translator:
it has no live receiver registration, NAT rebinding, RTCP handling, encryption,
HTTP or multithreading. The C reference currently uses POSIX sockets and is not
built on Windows.

## Run

Requires Python, Clang and POSIX socket support. All sockets are loopback and
nothing is sent over the physical network. Run from repository root:

```sh
python3 benchmarks/udp-fanout/run.py --output /tmp/fanout-check.json --check-only
python3 benchmarks/udp-fanout/run.py --output /tmp/fanout-pilot.json --receivers 16 --packets 100 --pps 100 --repeats 3
```

Use fresh output paths. Before any timed runs, the same independent gate is run
on both binaries, checking full 32-bit SSRC and a mix of valid/invalid RTP,
CSRC, extension, padding, oversized and empty datagrams. It verifies recipient
bytes and source port and rejects missing, duplicate or unexpected deliveries.
Normal samples also require every expected output; a lossy run is rejected, not
reported as faster. Variant ordering is deterministically shuffled each repeat.
Raw per-datagram latency, flags, tool versions and hashes are saved in JSON.

A sample measures paced input and collection with a Python client/collector on
the same host. `elapsed_including_drain_s` includes deliberate pacing and drain;
**it is not throughput**. Latencies include scheduler, network stack and Python
collector. One host, low packet rate, limited repetitions and the Python GIL
preclude a performance-parity conclusion. These samples are useful to validate
the setup, not to claim maximum capacity or tail-latency guarantees. Separate
load generator, independent network, offered/accepted/delivered packet rates,
CPU by process, syscall counts, loss accounting and broader repeated workloads
are required for a benchmark; the 100-Mbit LAN would cap results.

## Saved correctness and latency pilot

The [raw report](results/macos-loopback-pilot.json) records commit `b0ea6a8`,
three repeats per implementation at 100 input packets/s with 16 recipients.
Each variant received all 1,600 expected outputs in each repeat. Per-run p50
was 0.271–0.284 ms for Liza and 0.263–0.303 ms for C; p99 was 0.476–0.543 ms
and 0.497–0.517 ms respectively. These figures include Python collection and OS
scheduling. They are a low-rate pilot, not a throughput measurement or evidence
of a general performance advantage.

## Offered-load pilot

The original pilot used a fixed input count and forced termination on lost input.
The current `load.py` records losses and, after a fixed external drain interval,
retries a benchmark-only loopback UDP stop marker with a bounded deadline. A
missing marker may still require forced termination, which is recorded.
Each output is checked against its sequence and payload. Input delivery to the
server is **not** instrumented; a missing output may result from input socket,
server, output socket or the Python collector. Duplicate/invalid output and
latencies for received packets are separately recorded.

```sh
python3 benchmarks/udp-fanout/load.py --output /tmp/load.json --packets 500 --repeats 3
python3 benchmarks/udp-fanout/load.py --output /tmp/high.json --packets 1000 --repeats 3 --rates 5000 10000 20000 --receivers 64
```

[Basic series](results/macos-load-baseline.json.gz) and [higher-rate series](results/macos-load-high.json.gz)
are gzip-compressed raw JSON from Apple M4 loopback with Python sender and
collector on the same machine. Three shuffled repeats per combination. Basic:
16/64 receivers, 500/1000/3000 offered packets/s, 500 packets per repeat.
Higher rate: 64 receivers, 5000/10000/20000 offered packets/s, 1000 packets
per repeat. Rate is offered input, not measured output throughput; each RTP
packet is 1200 bytes. Actual generator timing and per-output latencies are in
raw results. These very short runs are not steady state.

At 10k input packets/s all 64,000 expected outputs per repeat were observed in
both implementations, while delivered-only p99 rose to roughly 107–115 ms.
At 20k, Liza missed 3,776–4,096 and C missed 3,712–7,552 of 64,000 expected
outputs per repeat; all six processes required termination after the timeout.
This does not locate the bottleneck or establish comparative capacity. The Python
collector validates and allocates per-packet data on the same host and can itself
fall behind; latency excludes lost datagrams. There is no warm-up, confidence
interval, CPU attribution, NIC test, RTP control workload or VideoGrace-equivalent
lifecycle. Verify on an independent generator and collector before conclusions.

## NB1-A: boundary counters and bounded external drain

The [instrumented report](results/macos-nb1a.json.gz) records 64 recipients,
1000 offered packets per sample, three shuffled repeats per variant at 5k, 10k
and 20k input packets/s, and 0.5 seconds external drain before the stop marker.
It records received, accepted, invalid, wrong SSRC and truncated counts, send
attempt/success/failure, stop reason and collector unique output. This first instrumented report did not retain generator intervals; per-output
latencies are conditional on receipt.

All 18 processes stopped normally via the control marker. At 5k and 10k, each
received 1000 inputs, reported 64000 successful local sends, and the collector
observed all 64000 outputs. At 10k, delivered-only p99 ranged 102.6–141.1 ms;
one C sample offered only about 9150 input packets/s. At 20k, each generator
reported 1000 successful sends, Liza received 933–934 and C 920–941 before stop.
For every received packet the programs reported 64 successful local sends; the
collector observed all outputs corresponding to those sends. This localizes the
observed count difference before the application's receive boundary, but packets
may have been dropped or arrived after the stop marker; it does not identify the
kernel queue or distinguish loss from reordering across the control boundary.
The 20k samples are brief and the receiver/Python collector share one host.

The marker is unauthenticated and loopback-only; it is not a production shutdown
API. UDP does not guarantee delivery or ordering of the marker. The controller
can still force termination after the deadline and records that fact; this is
not a hard real-time guarantee. The old fixed-count pilot above is retained as a
historical comparison, not an instrumented result. NB1-B still requires an
independent generator/collector, CPU/RSS and socket-level loss metrics.

A [follow-up series with generator intervals and send errors](results/macos-nb1a-intervals.json.gz)
repeated the same configuration at commit `7b9b2b7`. All 18 runs stopped
normally, with no generator send errors. At 5k and 10k each variant received
1000 inputs and all 64000 successful outputs reached the collector. At 20k,
Liza received 857–931 and C 930–937 of 1000 inputs; all corresponding reported
successful sends were observed. Delivered-only p99 at 10k was 109.6–120.3 ms
for Liza and 112.9–115.9 ms for C. Results remain short loopback samples, not
isolated throughput limits or evidence that one implementation is faster.

## NB1-B: separate processes and control pipe

```sh
python3 -m unittest discover -s benchmarks/udp-fanout -p test_nb1b.py -v
python3 benchmarks/udp-fanout/nb1b.py --output /tmp/nb1b.json --packets 1000 --repeats 3 --receivers 64 --rates 5000 10000 20000 --drain .5
```

POSIX only. The generator, fanout and collector are separate native processes
on the **same host**, with no CPU affinity. The controller sends `D` over the
fanout's stdin pipe when the generator exits; the server snapshots counters and
acknowledges `PHASE`. After the configured drain it receives `S` over the same
pipe and reports final counters. The phase boundary is **when the fanout consumes
D**, not the exact instant the last input was offered. Generator completion,
control send, acknowledgement and stop timestamps are recorded. `drain_received`
is the difference between final and phase-observed counts.

The Liza executable is generated from the application with a **benchmark-only
POSIX runtime shim**: it polls stdin and the UDP socket and reserves the otherwise
handled Interrupted/WouldBlock results for D/S. It retries those real socket
errors. The C build uses a matching poll/control mechanism. The shim changes the
runtime and adds polling overhead; results are not timings of the unmodified
production UDP runtime. `LZSTOP01` is ordinary invalid media data in this mode.
Control pipe closure and abnormal exits are errors, not successful drain.

Generator and collector report process user/system CPU and maximum RSS using
`getrusage`; fanout CPU and resident memory are sampled with `ps` before input
and just before stop (live RSS, not peak). Host UDP counters are captured where
available (`netstat` on macOS, `/proc/net/snmp` on Linux); their deltas are
system-wide and may include unrelated applications. No claim assigns them to a
socket. Delivered-only latency excludes losses and includes the collector's
scheduling/processing. A receiver may still have queued data when the collector
stops; output missing relative to successful sends can include that queue.
Runtimes, generated code, warmup, packet counts, CPU scaling and OS traffic must
be considered before interpreting this as a service comparison.

### Saved NB1-B local series

[Raw samples](results/macos-nb1b.json.gz), Apple M4 / macOS loopback,
commit `391a26a`, 64 receivers, 1000 offered packets per run, 3 shuffled repeats
of Liza/C at 5k/10k/20k input packets/s, 0.5s drain. At 5k both processed all
1000 by the observed phase boundary. At 10k all were eventually processed;
337–361 per run were processed during drain. At 20k Liza processed 968–974 and
C 966–968; 614–618 per run were processed during drain. Each process stopped
normally and the collector observed all reported successful sends.

The system-wide macOS full-socket-buffer drop counter increased 26–34 per 20k
sample, with no increase in these 5k/10k samples. The increase matched the
missing input count in this particular run, but the counter is host-wide, so
this is correlation, not independent per-socket attribution. At 10k, measured
fanout CPU was about 0.16 s per run; collector CPU was about 0.20 s and generator
CPU about 0.035–0.045 s, including their own startup. Fanout RSS is a live sample
around 1.4 MB; collector maximum RSS was about 33.6 MB. `ps` precision, process
startup, separate runtimes and measurement windows limit comparison.

This is not an isolated machine or capacity benchmark. The control shim adds a
poll around receive, phase acknowledgement is after generator process exit, and
all three processes and unrelated host activity share CPU and OS counters. A
sample at 5k showed a 256 ms delivered-only p99 outlier, so do not infer stable
latency or compare language speed from three short repeats. Different socket
buffer sizes, longer runs, native CPU samples and a separate load machine remain
necessary; the available 100-Mbit LAN cannot sustain the target fanout rate.
