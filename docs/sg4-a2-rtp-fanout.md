# SG4-A2: scoped RTP fanout workload

SG4-A2 measures one network owner written in Liza against a C callback using the
same SG2 lifecycle and SG3 UDP implementation. It changes no production runtime
semantics. Source and reproduction instructions are in
[`benchmarks/sg4-fanout`](https://github.com/rulerom/liza/tree/main/benchmarks/sg4-fanout).

## Workload and evidence

Each valid 1200-byte RTP packet with SSRC `0x10203040` is sent sequentially to
64 configured recipients. One datagram and at most 64 sends occur between calls
to `groups.next()`. Failed sends are counted without retry; malformed, truncated
and wrong-SSRC datagrams are dropped. The Liza application reuses `rtp.packet`
and `rtp.receivers`. C uses equivalent validation and a bounded 64-slot table.

The standard series offers 2k, 5k and 10k packets/s for five seconds, with five
repeats per implementation. Case order is shuffled with seed 4182. Each process
warms up with 200 packets at 1k/s, then acknowledges measurement readiness.
The endpoint is bound and included in Reactor's wait set before initial Ready.
After measurement there is 0.5s service drain, shutdown/join and 1s collector
drain. All repeats of a configuration use the same binaries and generated ports.

The committed reports retain individual samples, histogram bins, counters,
phase timestamps, generated configuration, exact compiler commands, source/LLVM
and binary SHA-256 values. Raw per-packet records and binaries are retained in
the invocation's output directory; they are not embedded in the repository.
Latency uses one host's `CLOCK_MONOTONIC`; no cross-host clock subtraction is used.
Histogram percentiles are upper bounds, with 100us resolution for delivery and
10us for active fanout cycles. Percentiles describe delivered packets only.

A benchmark-only observer is linked identically into both implementations. It
classifies received RTP independently and cross-checks the application's returned
accepted count. Its extra parsing and accounting cost is included. A separate
collector validates bytes and receiver/ordinal identities. This compares
application implementations on a shared runtime, not two independent runtimes.

## First macOS series

Measured revision: `1d26433e81ca0641f4c6c8035b1f7f87a32a8c70`.
Apple M4, 10 logical CPUs, 16 GiB host RAM; Apple Clang 21.0.0, `-O2`, ARM64.
Generator, service and collector ran on host loopback. No CPU pinning or exclusive
host reservation was used. Actual service socket buffers: receive 786896 bytes,
send 9216 bytes, identical across both variants and all repeats.

The following values are medians of five trials. Throughput includes the bounded
drain divided by the actual offered interval; the reports also distinguish
packets delivered within the offered interval itself.

| Offered input/s | Variant | Received/s | Delivered copies/s | Delivery coverage | Delivery p99 upper bound |
| --- | --- | ---: | ---: | ---: | ---: |
| 2,000 | Liza | 2,000 | 127,997 | 100% | 0.4 ms |
| 2,000 | C | 2,000 | 127,997 | 100% | 0.4 ms |
| 5,000 | Liza | 5,000 | 319,997 | 100% | 21.2 ms |
| 5,000 | C | 5,000 | 319,997 | 100% | 10.8 ms |
| 10,000 | Liza | 6,406 | 409,979 | 64.06% | 111.7 ms |
| 10,000 | C | 6,569 | 420,401 | 65.69% | 105.8 ms |

At 10k, received throughput ranged from 6,238–6,744/s for Liza and
6,229–6,723/s for C. The median difference is about 2.5%, with overlapping
ranges; these five trials do not establish a stable language overhead.
At 5k, p99 ranged from 10.3–43.6ms for Liza and 8.5–24.4ms for C.
The worse Liza median is a finding to investigate, not explained away by similar
throughput. C also had one 18.7ms p99 outlier at 2k; it remains in the report.

Every received valid packet produced 64 successful sends and 64 observed copies.
There were no send failures, duplicate or corrupt deliveries in this series.
The observed shortage is between generator local-send success and application
receive. Successful local sends are not generally delivery guarantees; the
independent collector establishes delivery for these trials.

| Offered input/s | Variant | Process user CPU | Process system CPU | Peak RSS | Active cycle p99 |
| --- | --- | ---: | ---: | ---: | ---: |
| 2,000 | Liza | 0.063 s | 1.797 s | 1.484 MiB | 280 us |
| 2,000 | C | 0.057 s | 1.766 s | 1.484 MiB | 290 us |
| 5,000 | Liza | 0.169 s | 3.906 s | 1.500 MiB | 240 us |
| 5,000 | C | 0.159 s | 3.936 s | 1.500 MiB | 290 us |
| 10,000 | Liza | 0.209 s | 4.858 s | 1.516 MiB | 310 us |
| 10,000 | C | 0.194 s | 4.908 s | 1.516 MiB | 220 us |

CPU is the measurement-plus-drain process delta, not a CPU percentage. RSS is
process peak including startup and warmup; it excludes separate generator and
collector processes. Callback thread CPU and the other processes' CPU/RSS are
retained in each report sample. Supervisor/service CPU is included in process
CPU but not individually available. Active-cycle p99 excludes blocking waits and
is therefore not delivery p99. The longest observed active cycle was 6.573ms;
maximum stop observation and completed-run latencies were 1.371ms and 5.038ms.
Those stop samples follow drain and do not establish shutdown latency under load.

The measured limit is dominated by system CPU, with approximately one consumer
CPU saturated at 10k and a similarly busy independent collector. Each accepted
packet causes 64 UDP sends. This supports a syscall/network-stack bottleneck in
this local topology rather than an assertion that bounds checks dominate. It
does not identify the physical-network limit. No MT architecture is selected from these data.

Separate two-second macOS `sample PID 2 1` profiles, excluded from the main
series, found consumer stacks in `__sendto` in 1710/1739 samples for Liza and
1678/1721 for C. The compressed stack reports accompany the measurement
archives. These are wall-time stack samples, not exact CPU attribution inside
the kernel, but support the UDP send path as the common bottleneck. They do not
explain the difference between the five-repeat p99 medians at 5k.

## Linux VM series

Measured source snapshot: `e1a3d2020f9c8f1bf9d93d67d41715e588587190`.
This adds Linux feature-test compile flags to the macOS measurement revision;
application and runtime code are unchanged. Ubuntu 24.04 ARM64, Clang 18.1.3,
`-O2`, Colima VM with 4 vCPUs and 8307175424 bytes RAM on the same M4 host.
Kernel: `6.8.0-117-generic`. Image ID:
`sha256:7f2466cc1e39fb02077ce1b40cef20cc56ee4266921259754798539272f19a72`.
Source was copied into the container; the report's Git working-tree status is
unavailable and its revision is supplied explicitly. File hashes are recorded.
The macOS and VM suites ran sequentially. UDP traffic stayed inside VM loopback.
Actual service send and receive buffers were both 212992 bytes.

| Offered input/s | Variant | Received/s | Delivered copies/s | Median coverage | Median delivery p99 |
| --- | --- | ---: | ---: | ---: | ---: |
| 2,000 | Liza | 2,000 | 127,997 | 100% | 0.3 ms |
| 2,000 | C | 2,000 | 127,997 | 100% | 0.3 ms |
| 5,000 | Liza | 5,000 | 319,995 | 100% | 0.2 ms |
| 5,000 | C | 5,000 | 319,994 | 100% | 0.2 ms |
| 10,000 | Liza | 10,000 | 639,990 | 100% | 0.4 ms |
| 10,000 | C | 10,000 | 639,990 | 100% | 0.4 ms |

A 100% median is not a claim that every run was lossless. At 10k Liza's coverage
ranged from 99.89–100% and C's from 97.984–100%; p99 ranged from 0.2–4.1ms and
0.2–12.9ms respectively. All accepted packets reached all recipients, with no
send failures or collector corruption/duplicates. The tested rates therefore
do not locate the Linux VM's sustained throughput ceiling.

Median measurement-plus-drain process CPU (user/system seconds) was
0.109/1.037, 0.197/1.512 and 0.279/3.445 for Liza, and
0.173/1.012, 0.381/1.334 and 0.311/3.465 for C at 2k/5k/10k.
Different kernels, socket buffers, toolchains and VM scheduling prevent using
these tables as a controlled macOS-versus-Linux comparison.

Linux memory caveat: the original five-repeat archive's `maxrss_native` and
`fanout_peak_rss_bytes` use `getrusage`, which can retain the pre-exec Python
launcher's high-water mark. Do not use those original Linux fields as the
service's own RSS. A reproduction with an unchanged tiny C process showed
`ru_maxrss` rising from 10496 to 112896 KiB when the parent allocated 100 MiB,
while `/proc/self/status` VmHWM stayed 1336 KiB. The harness now reads the live
service's VmHWM/VmRSS before shutdown; a separately labelled memory follow-up
uses this method. It measures peak through drain, excluding subsequent cleanup.
The separate 10k follow-up observed peak/resident RSS of 1692/1692 KiB for Liza and 1676/1676 KiB for C (one trial each, not five-repeat medians).
Generator/collector Linux `maxrss_native` remain raw rusage values, not isolated
post-exec memory estimates. The original evidence is preserved, not rewritten.

## Resource and development costs

The configured limits are 64 KiB group managed memory, 64 KiB process managed
memory, 64 KiB Reactor budget and a 4 KiB Region with a 2048-byte packet buffer.
Three participant stacks request 1 MiB each; the process-lifetime join service
requests another 1 MiB. Kernel socket buffers and stacks are not counted as FIFO
bytes or an exact RSS cap. The measurement adapter additionally owns one
controller thread, two pipe handles, a 600200-byte bitmap and an 80008-byte
histogram. The collector's bitmap is bounded by 64 × 600200 bytes. Reports retain
actual socket buffer sizes and separately account for these harness resources.

Physical source-line counts (including blanks and comments, not normalized for
formatting): Liza workload 74 lines, reused RTP parser 26 and receiver module 61;
C workload 54 plus RTP parser header 28. C's receiver table is inline and its ABI
declarations are included in that count. Both share the adapter and SG2 cleanup,
so these counts are not a claim that Liza requires less code. Liza explicitly
releases the Buffer and closes its Region; C closes its Region and handles
allocation failure manually. Neither callback performs socket or native-thread
cleanup: the shared runtime owns it.

Liza's existing Semantic IR tests reject producer-only/consumer-only capability
violations and invalid Buffer ownership. This workload depends on those checks;
it does not claim a new compiler guarantee or full verification of C/runtime.

## Acceptance and remaining scope

Functional tests run both callbacks against valid, malformed, wrong-SSRC,
truncated and empty datagrams. A separate test-only build injects WouldBlock for
one recipient and verifies no retry and continued delivery to the other. A short
end-to-end series checks timing epochs and independent counters. CI runs these
functional tests on Linux and macOS; it imposes no performance threshold on
shared runners. Windows functional coverage remains the SG4-A1 suite.

These are five-second loopback observations. Separate 60-second stability runs,
physical-network measurements, remote phase control and overloaded command-p99
measurements remain outstanding. The benchmark accepts `--duration 60` but that
option alone is not evidence of a completed long run. SG4-B remains deferred.
