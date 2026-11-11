# SG4-A2: investigating macOS latency tails

The original five-second series showed delivery-p99 medians of 21.2ms for
Liza and 10.8ms for C at 5k input packets/s. This follow-up checks whether that
ratio persists, locates delay within the receive/fanout path, and records
generator/collector CPU separately. It does not introduce SG4-B or change the
Liza/C applications, Semantic IR or production runtime.

## Baseline replay

The exact original M4 executables were reused, with SHA-256 verification before
every trial. All three binaries (Liza, C and collector), generated recipient
ports, 1200-byte packets, 64 recipients and 200-packet warmup were preserved.
The generator source is unchanged. Each case offered 5k packets/s for 60 seconds;
accounting and compression finished before a two-second quiet interval and the
next case. Three pairs reverse order, but an odd pair count is not fully
counterbalanced. No core affinity or exclusive host reservation was imposed.

| Pair and order | Liza delivery p99 | C delivery p99 | Liza coverage | C coverage |
| --- | ---: | ---: | ---: | ---: |
| 1: Liza, C | 1.3 ms | 49.0 ms | 100% | 99.3528% |
| 2: C, Liza | 59.5 ms | 47.1 ms | 100% | 100% |
| 3: Liza, C | 52.3 ms | 12.8 ms | 100% | 100% |

The medians are 52.3ms and 47.1ms, but three pairs with this variability cannot
establish a stable language-specific effect. The within-implementation spread
is larger than the original difference, and the paired difference changes sign.
The original roughly twofold ratio is not a reliable estimate from these data.
This does not prove equal latency or exclude a smaller systematic difference.
Percentiles are 100us histogram upper bounds and apply only to delivered copies.

All six trials received all 300000 offered packets and successfully issued all
19200000 local sends. In the first C trial the collector missed 124256 copies;
this is an output delivery gap after successful local sends, unlike the input
loss observed in the earlier overloaded 10k series. No local send error,
corruption or duplicate was reported.

## Five-second windows reveal bursts

Whole-minute percentiles can hide short events. Each packet was assigned to a
five-second offered-input window by its ordinal, including eventual delivery
within bounded drain. These windows are descriptive, not independent trials.

| Trial | Worst window | Window delivery p99 | Coverage in that window |
| --- | --- | ---: | ---: |
| Pair 1 Liza | 0–5 s | 6.9 ms | 100% |
| Pair 1 C | 45–50 s | 542.3 ms | 92.234% |
| Pair 2 C | 40–45 s | 99.9 ms | 100% |
| Pair 2 Liza | 35–40 s | 82.2 ms | 100% |
| Pair 3 Liza | 35–40 s | 66.2 ms | 100% |
| Pair 3 C | 20–25 s | 24.2 ms | 100% |

The large first-C output event cannot be diagnosed from average CPU alone.
Generator timing also varies: in pair 2 C's worst window its largest interpacket
gap was 8.258ms and it emitted 388 catch-up intervals shorter than 20us. Pair 1
C's 542ms delivery-tail window had a much smaller maximum generator gap of
2.033ms. Generator burstiness therefore matters, but does not by itself explain
all observed delivery delays. Collector scheduling, kernel queues and blocking
output of raw records remain possible contributors; they were not independently
controlled here.

## Process CPU control

The table shows CPU seconds divided by the actual offered interval, in pair
order. A value of 1 is approximately one fully occupied core. Fanout is the
measurement-plus-drain CPU delta; generator and collector include warmup/drain.
These are process averages, not time-resolved scheduler measurements.

| Process | Liza trials | C trials |
| --- | --- | --- |
| Fanout | 0.810 / 0.837 / 0.834 | 0.813 / 0.820 / 0.813 |
| Collector | 0.824 / 0.841 / 0.838 | 0.816 / 0.826 / 0.818 |
| Generator | 0.044 / 0.056 / 0.052 | 0.047 / 0.047 / 0.047 |

The collector consumes about as much CPU as the fanout. These values do not show
whole-machine CPU exhaustion and do not rule out short pauses or competition
for particular cores. They neither establish nor eliminate a causal contention
effect. A controlled collector-placement/load experiment is still needed before
attributing the difference to shared-core competition.

## Separate stage-instrumented runs

Separate binaries added wall-clock hooks only to the benchmark adapter. The
application, RTP module and runtime source hashes were checked against baseline.
These 30-second Liza/C diagnostic cases are not pooled with the baseline replay;
the hooks add time and about 441 KiB of bounded histogram/sample storage outside
the group's managed budget. Both cases processed all 150000 packets and delivered
all copies. Their end-to-end p99 was 12.4ms and 11.6ms respectively.

| Active stage, p99 upper bound | Liza | C |
| --- | ---: | ---: |
| SG3 receive call, including runtime checks | 3 us | 3 us |
| Receive return → first send entry | 2 us | 2 us |
| First send entry → 64th send return | 264 us | 207 us |
| Last send return → next event call | 2 us | 2 us |

Receive-to-first-send includes observer RTP validation, application parsing,
checks and the first destination lookup. It is not isolated parser time.
Fanout includes the receiver loop and all sends. These stage distributions
cannot be added to reconstruct an end-to-end percentile.

Every 256th ordinal was correlated with generator and collector timestamps:
586 packets per implementation. Sparse sample tails are diagnostic, not precise
estimates of the full population's p99.

| Sampled interval, p99 | Liza | C |
| --- | ---: | ---: |
| Generator send timestamp → receive return | 12.638 ms | 10.082 ms |
| First send entry → first recipient observed | 0.049 ms | 0.035 ms |
| Last send return → last recipient observed | 0.069 ms | 0.040 ms |

In these diagnostic runs, most of the sampled tail precedes receive return;
the active parse/fanout path is much shorter. The generator timestamp precedes
its send syscall and collector timestamps follow recvfrom, so this does not
separate kernel queueing from scheduling or generator bursts. Another core may
receive before a send returns, so the last interval is retained as a signed
quantity. The separate first-C delivery stall in the baseline series did not
recur in these diagnostic runs and must not be assigned this same explanation.

## Evidence and next decision

Source and reproduction instructions:
[latency harness](https://github.com/rulerom/liza/blob/752f88732c07de4dca33a238268a02a5d1c090dc/benchmarks/sg4-fanout/LATENCY.md).
Compressed reports in `benchmarks/sg4-fanout/results/`:
`macos-paired60.json.gz`, `macos-paired60-windows.json.gz`, `macos-stages.json.gz`.
They retain per-trial histograms, counters, CPU, stage samples, build provenance
and hashes. Raw records remain in `/private/tmp/sg4-macos-paired60` and
`/private/tmp/sg4-macos-stages`; these temporary directories are not permanent
public artifact hosting. Paired replay used the original `run.py` from `3eb8d9a`
and the paired runner recorded in `766666e`; diagnostic builds record their own
source hashes. Record compression is outside the load interval.

The evidence does not justify blaming Liza's parser or selecting an MT design.
It supports testing burst/queue behavior and independently controlling the
collector before claiming a causal language latency difference. SG4-B and the
higher-rate Linux capacity search remain deferred. The original throughput
results are preserved, including their loss and topology qualifications.
