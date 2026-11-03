# SG4-A2 latency follow-up

This experiment investigates the macOS 5k p99 difference from the initial
five-second series. It does not start SG4-B or change the Liza/C applications.

## Preserved baseline

`paired.py` reuses the exact `liza`, `c` and `collector` executables from an
existing `run.py` output directory. SHA-256 values are checked before every
trial, and the baseline manifest and generated endpoint ports are retained.
The generator and harness source hashes are also recorded. No new binaries
are substituted into this series.

```sh
python3 benchmarks/sg4-fanout/paired.py \
  --baseline /private/tmp/sg4-macos-nb1 \
  --output /private/tmp/sg4-macos-paired60
python3 benchmarks/sg4-fanout/windows.py /private/tmp/sg4-macos-paired60
```

Defaults: 5k input packets/s, 64 recipients inherited from baseline, three
60-second pairs ordered Liza/C, C/Liza, Liza/C. This reverses order between
pairs but the odd pair count is not fully counterbalanced. Three pairs are an
exploratory stability check, not a statistical significance test. Warmup,
phases, drain and shutdown match the original harness. A two-second quiet gap
follows completed accounting/compression before the next trial. Each trial
requires at least 1 GiB free disk space; low space stops the suite and retains
completed samples. Performance data are never discarded because of loss.

Generator and collector CPU totals are normalized by the actual offered
interval and reported separately from fanout CPU. Their totals include warmup
and drain; they are not isolated phase CPU. There is no exclusive host
reservation or macOS core affinity claim. Similar average CPU does not rule
out short scheduler pauses or contention. A causal competition experiment
would require isolated placement or an independently varied collector load.

Window analysis runs only after all measurements finish. It groups packets
by input ordinal into five-second offer windows and reports delivery coverage
and p99 for each window. A whole-minute percentile can otherwise dilute a
short latency burst. Windows include eventual delivery during bounded drain;
they are not independent replicates.

## Separate stage instrumentation

```sh
python3 benchmarks/sg4-fanout/diagnose.py \
  --baseline /private/tmp/sg4-macos-nb1 \
  --output /private/tmp/sg4-macos-stages
```

This creates separate diagnostic binaries with `SG4_STAGE_TIMING`, preserving
application source hashes and generated ports. It runs Liza and C at 5k for
30 seconds each. Wall-clock timing hooks change timing, so these results must
not be pooled with baseline. Compression level 1 is used only after the
processes have exited; compression CPU is outside the measured interval.

Four bounded 1us histograms measure native receive, receive-return to first
send, the complete fanout, and last-send return to the next event call. The
second interval includes observer validation, application RTP parsing, checks
and destination lookup. It is **not** an isolated pure-parser benchmark.
Fanout includes the receiver loop and all send calls. >=10ms is an overflow
bucket, with separate exact maxima.

Every 256th ordinal records receive-return, first-send entry and last-send
return timestamps in a fixed 4096-entry buffer. The post-processor joins those
with generator and collector records. Generator-to-receive includes the send
syscall and pre-receive queue/scheduling time; first-send-entry to first
collector receive includes send processing and collector observation delay.
Last-send-return to last-receiver observation can be negative because another
core can receive before send returns. These are userspace boundaries, not
kernel arrival timestamps. Sparse sample tail percentiles are descriptive.

The stage test verifies that both callbacks produce the expected packets,
histogram counts equal completed fanouts, and sampled stage timestamps are
ordered. Production runtime, Semantic IR and both application implementations
remain unchanged.
